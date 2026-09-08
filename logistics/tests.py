from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    Customer,
    Address,
    Product,
    DeliveryDriver,
    Order,
    OrderItem,
    PaymentTransaction,
    OrderStatus,
    PaymentStatus,
    PaymentMethod,
    VehicleType,
)


class LogisticsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Seed customer and Cameroonian address
        self.customer = Customer.objects.create(
            full_name="Jean-Paul Atangana",
            phone_number="+237671234567",
            email="atangana@example.cm"
        )
        self.address = Address.objects.create(
            customer=self.customer,
            city="Douala",
            neighborhood="Akwa",
            landmark_reference="Face Boulangerie Saker, Carrefour Idéal",
            contact_phone="+237671234567",
            is_default=True
        )

        # 2. Seed product
        self.product = Product.objects.create(
            name="Smartphone Galaxy A15",
            sku="SM-A15-128G",
            category="Phones & Accessories",
            unit_price_fcfa=95000,
            stock_quantity=15
        )

        # 3. Seed driver
        self.driver = DeliveryDriver.objects.create(
            driver_id="DRV-007",
            full_name="Ibrahim Mbarga",
            phone_number="+237699887766",
            vehicle_type=VehicleType.MOTO,
            is_available=True,
            current_neighborhood="Akwa"
        )

        # 4. Seed test order
        self.order = Order.objects.create(
            order_id="ECM-00101",
            customer=self.customer,
            delivery_address=self.address,
            driver=self.driver,
            status=OrderStatus.PENDING_PAYMENT,
            payment_method=PaymentMethod.MTN_MOMO,
            payment_status=PaymentStatus.PENDING,
            total_amount_fcfa=95000,
            distance_km=4.5
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price_fcfa=95000,
            subtotal_fcfa=95000
        )

        self.webhook_url = reverse("payment-webhook")

    def test_webhook_unauthorized_without_secret(self):
        """Webhooks without signature/secret header must be rejected with 401."""
        payload = {
            "transaction_id": "MOMO-TX-9901",
            "order_id": self.order.order_id,
            "provider": PaymentMethod.MTN_MOMO,
            "amount_fcfa": 95000,
            "phone_number": "+237671234567",
            "status": "SUCCESS"
        }
        response = self.client.post(self.webhook_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_successful_payment_and_order_transition(self):
        """Valid webhook should update order status to PAID and record payment transaction."""
        payload = {
            "transaction_id": "MOMO-TX-9901",
            "order_id": self.order.order_id,
            "provider": PaymentMethod.MTN_MOMO,
            "amount_fcfa": 95000,
            "phone_number": "+237671234567",
            "status": "SUCCESS",
            "idempotency_key": "IDEMP-MOMO-9901"
        }
        headers = {"HTTP_X_CALLBACK_SECRET": "momo_webhook_secret_cm_2026"}
        response = self.client.post(self.webhook_url, payload, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")

        # Refresh order
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.order.payment_status, PaymentStatus.PAID)

        # Verify transaction log created
        tx = PaymentTransaction.objects.get(idempotency_key="IDEMP-MOMO-9901")
        self.assertEqual(tx.amount_fcfa, 95000)
        self.assertTrue(tx.signature_verified)

    def test_webhook_enforces_idempotency_on_duplicates(self):
        """Duplicate webhook deliveries (common during telecom network retries) must not re-process."""
        payload = {
            "transaction_id": "MOMO-TX-9902",
            "order_id": self.order.order_id,
            "provider": PaymentMethod.MTN_MOMO,
            "amount_fcfa": 95000,
            "phone_number": "+237671234567",
            "status": "SUCCESS",
            "idempotency_key": "IDEMP-DUPLICATE-CHECK"
        }
        headers = {"HTTP_X_CALLBACK_SECRET": "momo_webhook_secret_cm_2026"}

        # 1st call: Success
        res1 = self.client.post(self.webhook_url, payload, format="json", **headers)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["status"], "success")

        # 2nd call: Idempotent return (no duplicate records, no errors)
        res2 = self.client.post(self.webhook_url, payload, format="json", **headers)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["status"], "already_processed")

        # Confirm only ONE transaction exists in DB
        self.assertEqual(PaymentTransaction.objects.filter(idempotency_key="IDEMP-DUPLICATE-CHECK").count(), 1)

    def test_webhook_rejects_underpayment(self):
        """Underpaid webhook must fail with 400 and not mark order as PAID."""
        payload = {
            "transaction_id": "MOMO-TX-9903",
            "order_id": self.order.order_id,
            "provider": PaymentMethod.MTN_MOMO,
            "amount_fcfa": 1000,  # 1000 FCFA instead of 95,000 FCFA
            "phone_number": "+237671234567",
            "status": "SUCCESS",
            "idempotency_key": "IDEMP-UNDERPAY-1"
        }
        headers = {"HTTP_X_CALLBACK_SECRET": "momo_webhook_secret_cm_2026"}
        response = self.client.post(self.webhook_url, payload, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.order.payment_status, PaymentStatus.PENDING)

    def test_driver_order_status_update(self):
        """Driver app can update status to IN_TRANSIT and DELIVERED."""
        url = reverse("order-update-status", kwargs={"pk": self.order.pk})

        response = self.client.post(
            url,
            {"status": OrderStatus.IN_TRANSIT, "notes": "Colis récupéré, en route vers Akwa"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_TRANSIT)

    def test_driver_assigned_orders_view(self):
        """Driver view returns active deliveries sorted for low battery/offline efficiency."""
        url = reverse("driver-orders", kwargs={"driver_id": self.driver.driver_id})
        self.order.status = OrderStatus.ASSIGNED_TO_DRIVER
        self.order.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_active_orders"], 1)
        self.assertEqual(response.data["orders"][0]["neighborhood"], "Akwa")
