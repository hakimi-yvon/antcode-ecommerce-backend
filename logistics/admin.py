from django.contrib import admin
from .models import (
    Customer,
    Address,
    Product,
    DeliveryDriver,
    Order,
    OrderItem,
    PaymentTransaction,
    DeliveryTrackingLog,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_number", "email", "created_at")
    search_fields = ("full_name", "phone_number", "email")
    list_filter = ("created_at",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "neighborhood", "city", "contact_phone", "is_default")
    list_filter = ("city", "neighborhood", "is_default")
    search_fields = ("customer__full_name", "neighborhood", "landmark_reference", "contact_phone")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "unit_price_fcfa", "stock_quantity", "is_active")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "sku")


@admin.register(DeliveryDriver)
class DeliveryDriverAdmin(admin.ModelAdmin):
    list_display = ("driver_id", "full_name", "phone_number", "vehicle_type", "is_available", "current_neighborhood")
    list_filter = ("vehicle_type", "is_available", "current_neighborhood")
    search_fields = ("driver_id", "full_name", "phone_number")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal_fcfa",)


class DeliveryTrackingLogInline(admin.TabularInline):
    model = DeliveryTrackingLog
    extra = 0
    readonly_fields = ("recorded_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "customer",
        "status",
        "payment_method",
        "payment_status",
        "total_amount_fcfa",
        "driver",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "delivery_address__neighborhood", "created_at")
    search_fields = ("order_id", "customer__full_name", "customer__phone_number", "delivery_address__neighborhood")
    inlines = [OrderItemInline, DeliveryTrackingLogInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "provider",
        "provider_tx_id",
        "amount_fcfa",
        "status",
        "signature_verified",
        "created_at",
    )
    list_filter = ("provider", "status", "signature_verified", "created_at")
    search_fields = ("idempotency_key", "provider_tx_id", "order__order_id", "phone_number")
    readonly_fields = ("id", "idempotency_key", "raw_payload", "created_at", "processed_at")


@admin.register(DeliveryTrackingLog)
class DeliveryTrackingLogAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "notes", "recorded_at")
    list_filter = ("status", "recorded_at")
    search_fields = ("order__order_id", "notes")
