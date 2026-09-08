import hmac
import hashlib
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Customer,
    Address,
    Product,
    DeliveryDriver,
    Order,
    OrderStatus,
    PaymentTransaction,
    PaymentStatus,
    PaymentMethod,
    DeliveryTrackingLog,
)
from .serializers import (
    CustomerSerializer,
    AddressSerializer,
    ProductSerializer,
    DeliveryDriverSerializer,
    OrderSerializer,
    DriverStatusUpdateSerializer,
    MobileMoneyWebhookSerializer,
)


class MobileMoneyWebhookView(APIView):
    """
    Production-grade Webhook Endpoint for MTN MoMo and Orange Money Cameroon.
    
    Security & Reliability features:
    1. Shared secret / Signature verification (prevents malicious spoofed callbacks).
    2. Enforced Idempotency (handles network retries without double-crediting orders).
    3. Concurrency Lock via database SELECT FOR UPDATE (prevents race conditions).
    4. Exact Amount verification (stops underpaid transactions).
    5. Complete audit trail in PaymentTransaction & DeliveryTrackingLog.
    """
    authentication_classes = []
    permission_classes = []

    def _verify_signature(self, request, provider: str) -> bool:
        """
        Verify incoming webhook signature or callback secret header.
        Supports 'X-Callback-Secret' or 'X-Signature' (HMAC-SHA256).
        """
        secret = (
            getattr(settings, "MOMO_WEBHOOK_SECRET", "momo_webhook_secret_cm_2026")
            if provider == PaymentMethod.MTN_MOMO
            else getattr(settings, "ORANGE_WEBHOOK_SECRET", "orange_webhook_secret_cm_2026")
        )
        
        # Check direct header secret (common in sandbox / dev integrations)
        received_secret = request.headers.get("X-Callback-Secret")
        if received_secret and received_secret == secret:
            return True

        # Check HMAC SHA-256 signature if present
        received_signature = request.headers.get("X-Signature")
        if received_signature and request.body:
            computed_sig = hmac.new(
                secret.encode("utf-8"),
                request.body,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(received_signature, computed_sig)

        # Allow if secret matches fallback header Authorization
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == secret:
            return True

        return False

    def post(self, request, *args, **kwargs):
        serializer = MobileMoneyWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid webhook payload", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        provider = data["provider"]
        tx_id = data["transaction_id"]
        order_id = data["order_id"]
        amount_fcfa = data["amount_fcfa"]
        tx_status = data["status"]
        phone_number = data["phone_number"]
        
        # 1. Signature Verification
        is_verified = self._verify_signature(request, provider)
        if not is_verified:
            # Log suspicious transaction attempt
            return Response(
                {"error": "Unauthorized webhook: invalid signature or secret token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Idempotency Key Determination
        idempotency_key = data.get("idempotency_key") or f"{provider}_{tx_id}"

        # Check if already processed (Idempotency Guard)
        existing_tx = PaymentTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            return Response(
                {
                    "status": "already_processed",
                    "message": "Webhook already received and acknowledged. Idempotency enforced.",
                    "transaction_id": str(existing_tx.id),
                    "order_id": order_id,
                },
                status=status.HTTP_200_OK
            )

        # 3. Process Transaction inside Atomic Database Block
        try:
            with transaction.atomic():
                # Lock order row to prevent concurrent race condition updates
                order = Order.objects.select_for_update().filter(order_id=order_id).first()
                if not order:
                    return Response(
                        {"error": f"Order {order_id} not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Amount Verification Guard
                if amount_fcfa < order.total_amount_fcfa:
                    # Log underpayment failure
                    PaymentTransaction.objects.create(
                        order=order,
                        provider=provider,
                        provider_tx_id=tx_id,
                        idempotency_key=idempotency_key,
                        amount_fcfa=amount_fcfa,
                        phone_number=phone_number,
                        status=PaymentStatus.FAILED,
                        signature_verified=True,
                        raw_payload=request.data,
                    )
                    DeliveryTrackingLog.objects.create(
                        order=order,
                        status="PAYMENT_FAILED",
                        notes=f"Montant insuffisant reçu via {provider}: {amount_fcfa} FCFA au lieu de {order.total_amount_fcfa} FCFA."
                    )
                    return Response(
                        {"error": "Payment amount mismatch", "expected": order.total_amount_fcfa, "received": amount_fcfa},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Map status
                payment_record_status = PaymentStatus.PAID if tx_status == "SUCCESS" else PaymentStatus.FAILED

                # Create immutable transaction ledger record
                pay_tx = PaymentTransaction.objects.create(
                    order=order,
                    provider=provider,
                    provider_tx_id=tx_id,
                    idempotency_key=idempotency_key,
                    amount_fcfa=amount_fcfa,
                    phone_number=phone_number,
                    status=payment_record_status,
                    signature_verified=True,
                    raw_payload=request.data,
                    processed_at=timezone.now() if tx_status == "SUCCESS" else None,
                )

                if tx_status == "SUCCESS":
                    order.payment_status = PaymentStatus.PAID
                    order.payment_method = provider
                    if order.status == OrderStatus.PENDING_PAYMENT:
                        order.status = OrderStatus.PAID
                    order.save()

                    # Audit trail
                    DeliveryTrackingLog.objects.create(
                        order=order,
                        status="PAYMENT_CONFIRMED",
                        notes=f"Paiement Mobile Money validé ({provider} ref: {tx_id}) pour {amount_fcfa} FCFA."
                    )

                return Response(
                    {
                        "status": "success",
                        "message": "Payment webhook processed successfully",
                        "order_id": order.order_id,
                        "order_status": order.status,
                        "payment_status": order.payment_status,
                        "transaction_id": str(pay_tx.id),
                    },
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            return Response(
                {"error": "Internal server error during transaction processing", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Orders with optimized filtering by status, neighborhood, driver, and date.
    """
    queryset = Order.objects.select_related("customer", "delivery_address", "driver").prefetch_related("items", "items__product")
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        neighborhood = self.request.query_params.get("neighborhood")
        driver_id = self.request.query_params.get("driver")
        payment_status = self.request.query_params.get("payment_status")

        if status_param:
            qs = qs.filter(status=status_param)
        if neighborhood:
            qs = qs.filter(delivery_address__neighborhood__iexact=neighborhood)
        if driver_id:
            qs = qs.filter(driver__driver_id=driver_id)
        if payment_status:
            qs = qs.filter(payment_status=payment_status)

        return qs

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        """
        Action used by delivery driver app to update delivery stage.
        Supports offline sync timestamps and notes.
        """
        order = self.get_object()
        serializer = DriverStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        order.status = new_status
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = timezone.now()
        order.save()

        DeliveryTrackingLog.objects.create(
            order=order,
            status=new_status,
            notes=notes or f"Statut mis à jour par le livreur: {new_status}"
        )

        return Response({
            "message": "Order status updated successfully",
            "order_id": order.order_id,
            "current_status": order.status,
            "delivered_at": order.delivered_at,
        })


class DriverDeliveriesView(APIView):
    """
    Driver view optimized for low-bandwidth mobile app.
    Returns active orders for a driver, grouped or sorted by neighborhood.
    """
    def get(self, request, driver_id):
        driver = DeliveryDriver.objects.filter(driver_id=driver_id).first()
        if not driver:
            return Response({"error": f"Driver {driver_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        orders = (
            Order.objects.filter(
                driver=driver,
                status__in=[OrderStatus.ASSIGNED_TO_DRIVER, OrderStatus.IN_TRANSIT]
            )
            .select_related("customer", "delivery_address")
            .order_by("delivery_address__neighborhood")
        )

        serializer = OrderSerializer(orders, many=True)
        return Response({
            "driver_id": driver.driver_id,
            "driver_name": driver.full_name,
            "total_active_orders": orders.count(),
            "orders": serializer.data,
        })


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filterset_fields = ["category"]


class MetricsSummaryView(APIView):
    """
    Logistics performance metrics and traffic bottleneck analysis.
    """
    def get(self, request):
        from django.db.models import Count, Avg, Sum

        total_orders = Order.objects.count()
        delivered_count = Order.objects.filter(status=OrderStatus.DELIVERED).count()
        paid_count = Order.objects.filter(payment_status=PaymentStatus.PAID).count()
        total_revenue = Order.objects.filter(payment_status=PaymentStatus.PAID).aggregate(
            total=Sum("total_amount_fcfa")
        )["total"] or 0

        # Bottleneck neighborhoods by average delivery duration
        neighborhood_delays = (
            Order.objects.filter(status=OrderStatus.DELIVERED, delivery_duration_hours__isnull=False)
            .values("delivery_address__neighborhood")
            .annotate(
                avg_duration_hrs=Avg("delivery_duration_hours"),
                orders_count=Count("id")
            )
            .order_by("-avg_duration_hrs")[:5]
        )

        return Response({
            "summary": {
                "total_orders": total_orders,
                "paid_orders": paid_count,
                "delivered_orders": delivered_count,
                "delivery_success_rate_percent": round((delivered_count / total_orders * 100), 2) if total_orders else 0,
                "total_revenue_fcfa": total_revenue,
            },
            "top_delayed_neighborhoods": list(neighborhood_delays),
        })
