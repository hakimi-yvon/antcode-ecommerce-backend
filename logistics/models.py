import uuid
from django.db import models
from django.utils import timezone


class ProductCategory(models.TextChoices):
    ELECTRONICS = "Electronics", "Electronics"
    FASHION = "Fashion", "Fashion"
    HOME_GOODS = "Home Goods", "Home Goods"
    GROCERIES = "Groceries", "Groceries"
    BEAUTY = "Beauty", "Beauty"
    PHONES = "Phones & Accessories", "Phones & Accessories"


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    category = models.CharField(max_length=50, choices=ProductCategory.choices, db_index=True)
    unit_price_fcfa = models.PositiveIntegerField(help_text="Unit price in FCFA (no decimals)")
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku}) - {self.unit_price_fcfa} FCFA"


class Customer(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, db_index=True, help_text="Ex: +237 670000000")
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class Address(models.Model):
    """
    Cameroonian urban address representation.
    Addresses in Douala/Yaoundé do not use postal codes, but city, neighborhood,
    and precise local landmarks (e.g., 'Carrefour Shell, barrière noire').
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    city = models.CharField(max_length=60, default="Douala")
    neighborhood = models.CharField(max_length=100, db_index=True, help_text="Ex: Akwa, Bastos, Mendong, Bonapriso")
    landmark_reference = models.TextField(help_text="Detailed landmark description: e.g. Face pharmacie du carrefour")
    contact_phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Addresses"
        indexes = [
            models.Index(fields=["city", "neighborhood"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name} - {self.neighborhood}, {self.city}"


class VehicleType(models.TextChoices):
    MOTO = "Moto", "Moto (Benskin)"
    SMALL_TRUCK = "Small Truck", "Small Truck"
    PICKUP = "Pickup", "Pickup"
    VAN = "Van", "Delivery Van"


class DeliveryDriver(models.Model):
    driver_id = models.CharField(max_length=30, unique=True, db_index=True, help_text="Ex: DRV-012")
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=30, choices=VehicleType.choices, default=VehicleType.MOTO)
    is_available = models.BooleanField(default=True, db_index=True)
    current_neighborhood = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver_id} - {self.full_name} ({self.vehicle_type})"


class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "En attente de paiement"
    PAID = "PAID", "Payée"
    PROCESSING = "PROCESSING", "En préparation"
    ASSIGNED_TO_DRIVER = "ASSIGNED_TO_DRIVER", "Assignée au livreur"
    IN_TRANSIT = "IN_TRANSIT", "En cours de livraison"
    DELIVERED = "DELIVERED", "Livrée"
    RETURNED = "RETURNED", "Retournée"
    CANCELLED = "CANCELLED", "Annulée"


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "MTN MoMo", "MTN Mobile Money"
    ORANGE_MONEY = "Orange Money", "Orange Money"
    CASH_ON_DELIVERY = "Cash on Delivery", "Cash on Delivery (COD)"


class PaymentStatus(models.TextChoices):
    PENDING = "Pending", "En attente"
    PAID = "Paid", "Payé"
    FAILED = "Failed", "Échoué"


class Order(models.Model):
    order_id = models.CharField(max_length=50, unique=True, db_index=True, help_text="Ex: ECM-00042")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    delivery_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")
    driver = models.ForeignKey(
        DeliveryDriver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders"
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MTN_MOMO,
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )
    total_amount_fcfa = models.PositiveIntegerField(default=0)
    distance_km = models.FloatField(default=5.0)
    delivery_duration_hours = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # High-performance composite indexes for peak-load query optimization
            models.Index(fields=["status", "created_at"], name="idx_order_status_created"),
            models.Index(fields=["payment_status", "created_at"], name="idx_order_pay_status_created"),
            models.Index(fields=["driver", "status"], name="idx_order_driver_status"),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.customer.full_name} [{self.status}] ({self.total_amount_fcfa} FCFA)"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_fcfa = models.PositiveIntegerField()
    subtotal_fcfa = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        self.subtotal_fcfa = self.quantity * self.unit_price_fcfa
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} for {self.order.order_id}"


class PaymentTransaction(models.Model):
    """
    Immutable ledger of payment webhook events received from MTN MoMo / Orange Money.
    Includes Idempotency Key and Signature verification to guarantee zero duplicate credits.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    provider = models.CharField(max_length=30, choices=PaymentMethod.choices)
    provider_tx_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    idempotency_key = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Hash or unique key from provider to enforce idempotency"
    )
    amount_fcfa = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    signature_verified = models.BooleanField(default=False)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status"]),
        ]

    def __str__(self):
        return f"TX {self.provider} - Order {self.order.order_id} ({self.amount_fcfa} FCFA) [{self.status}]"


class DeliveryTrackingLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tracking_logs")
    status = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.order.order_id} -> {self.status} at {self.recorded_at}"
