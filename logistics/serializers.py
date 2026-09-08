from rest_framework import serializers
from .models import (
    Customer,
    Address,
    Product,
    DeliveryDriver,
    Order,
    OrderItem,
    PaymentTransaction,
    DeliveryTrackingLog,
    PaymentMethod,
    PaymentStatus,
    OrderStatus,
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "category", "unit_price_fcfa", "stock_quantity", "is_active"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "city", "neighborhood", "landmark_reference", "contact_phone", "is_default"]


class CustomerSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "full_name", "phone_number", "email", "addresses"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    product_sku = serializers.ReadOnlyField(source="product.sku")

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_sku", "quantity", "unit_price_fcfa", "subtotal_fcfa"]


class DeliveryDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryDriver
        fields = ["driver_id", "full_name", "phone_number", "vehicle_type", "is_available", "current_neighborhood"]


class DeliveryTrackingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTrackingLog
        fields = ["status", "notes", "recorded_at"]


class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source="customer.full_name")
    customer_phone = serializers.ReadOnlyField(source="customer.phone_number")
    neighborhood = serializers.ReadOnlyField(source="delivery_address.neighborhood")
    city = serializers.ReadOnlyField(source="delivery_address.city")
    landmark_reference = serializers.ReadOnlyField(source="delivery_address.landmark_reference")
    driver_name = serializers.ReadOnlyField(source="driver.full_name")
    items = OrderItemSerializer(many=True, read_only=True)
    tracking_logs = DeliveryTrackingLogSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_id",
            "customer",
            "customer_name",
            "customer_phone",
            "delivery_address",
            "neighborhood",
            "city",
            "landmark_reference",
            "driver",
            "driver_name",
            "status",
            "payment_method",
            "payment_status",
            "total_amount_fcfa",
            "distance_km",
            "delivery_duration_hours",
            "items",
            "tracking_logs",
            "created_at",
            "updated_at",
            "delivered_at",
        ]


class DriverStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED, OrderStatus.RETURNED]
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MobileMoneyWebhookSerializer(serializers.Serializer):
    """
    Serializer validating incoming payment callbacks from MTN MoMo and Orange Money Cameroon.
    """
    transaction_id = serializers.CharField(
        max_length=120,
        help_text="Provider external transaction reference (e.g. MOMO-CM-98231)"
    )
    order_id = serializers.CharField(
        max_length=50,
        help_text="Merchant order ID (e.g. ECM-00042)"
    )
    provider = serializers.ChoiceField(
        choices=[PaymentMethod.MTN_MOMO, PaymentMethod.ORANGE_MONEY]
    )
    amount_fcfa = serializers.IntegerField(
        min_value=100,
        help_text="Transaction amount in FCFA"
    )
    phone_number = serializers.CharField(
        max_length=20,
        help_text="Payer phone number (e.g. +237670000000)"
    )
    status = serializers.ChoiceField(
        choices=["SUCCESS", "FAILED", "PENDING"]
    )
    idempotency_key = serializers.CharField(
        max_length=150,
        required=False,
        help_text="Unique event delivery ID for idempotency checking"
    )
