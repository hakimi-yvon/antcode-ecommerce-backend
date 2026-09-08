import random
import uuid
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from logistics.models import (
    Customer,
    Address,
    Product,
    ProductCategory,
    DeliveryDriver,
    VehicleType,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
    DeliveryTrackingLog,
)


class Command(BaseCommand):
    help = "Generate 500+ realistic Cameroonian e-commerce orders and transactions for peak-load benchmarking"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=500,
            help="Number of mock orders/transactions to generate (default: 500)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        self.stdout.write(self.style.NOTICE(f"🚀 Seeding database with {count} realistic Cameroonian orders..."))

        # 1. Predefined reference data
        NEIGHBORHOODS_DATA = [
            ("Douala", "Akwa", "Face Boulangerie Saker, Boulevard de la Liberté"),
            ("Douala", "Bonapriso", "Derrière Clinique Soppo Priso, Rue des Palmiers"),
            ("Douala", "Bonamoussadi", "Carrefour Denver, face pharmacie"),
            ("Douala", "Deido", "Rond-point Deido, près de la station Total"),
            ("Douala", "New Bell", "Marché Nkololoun, entrée principale"),
            ("Yaoundé", "Bastos", "Face Ambassade de Grèce, montée Bastos"),
            ("Yaoundé", "Mendong", "Carrefour Simbock, derrière station Tradex"),
            ("Yaoundé", "Nlongkak", "Rond-point Nlongkak, près de l'immeuble ministériel"),
            ("Yaoundé", "Biyem-Assi", "Carrefour Acacias, face collège Vogt"),
            ("Yaoundé", "Ngousso", "Hôpital Général, entrée urgences"),
        ]

        DRIVERS_DATA = [
            ("DRV-001", "Paul Ondoua", "+237670112233", VehicleType.MOTO, "Akwa"),
            ("DRV-002", "Alain Tchakounte", "+237690445566", VehicleType.MOTO, "Bonapriso"),
            ("DRV-003", "Fabrice Mvogo", "+237671889900", VehicleType.SMALL_TRUCK, "Bastos"),
            ("DRV-004", "Samuel Eto'o Junior", "+237691223344", VehicleType.MOTO, "Mendong"),
            ("DRV-005", "Christian Bassogog", "+237672556677", VehicleType.VAN, "Bonamoussadi"),
            ("DRV-006", "Didier Kamga", "+237692889911", VehicleType.MOTO, "Deido"),
            ("DRV-007", "Boris Nkodo", "+237673334455", VehicleType.MOTO, "Nlongkak"),
            ("DRV-008", "Hermann Fotso", "+237693667788", VehicleType.PICKUP, "Biyem-Assi"),
            ("DRV-009", "Junior Song", "+237674990011", VehicleType.MOTO, "Ngousso"),
            ("DRV-010", "Marc Atangana", "+237694112233", VehicleType.MOTO, "New Bell"),
        ]

        PRODUCTS_DATA = [
            ("Smartphone Infinix Hot 40", "INF-HOT40", ProductCategory.PHONES, 89000),
            ("Smartphone Tecno Spark 20", "TEC-SPK20", ProductCategory.PHONES, 82000),
            ("Écouteurs sans fil Oraimo FreePods 4", "ORA-FP4", ProductCategory.ELECTRONICS, 18500),
            ("Powerbank Oraimo 20000mAh", "ORA-PB20K", ProductCategory.ELECTRONICS, 14000),
            ("Smart TV Samsung 43 pouces 4K", "SAM-TV43", ProductCategory.ELECTRONICS, 210000),
            ("Sac à dos imperméable urbain", "BAG-URB01", ProductCategory.FASHION, 12000),
            ("Baskets Sneaker respirantes", "SNK-SPORT-42", ProductCategory.FASHION, 19500),
            ("Cafetière électrique compacte", "HOME-COFF01", ProductCategory.HOME_GOODS, 25000),
            ("Ventilateur rechargeable solaire", "SOLAR-FAN-16", ProductCategory.HOME_GOODS, 32000),
            ("Huile d'Argan Pure 100ml", "BEAU-ARG100", ProductCategory.BEAUTY, 7500),
            ("Pack Savons noirs locaux (x3)", "BEAU-SAV-CM", ProductCategory.BEAUTY, 4500),
            ("Sac de Riz parfumé 25kg", "GROC-RIZ25", ProductCategory.GROCERIES, 21500),
            ("Carton d'huile de palme raffinée Mayor (15L)", "GROC-HMAY15", ProductCategory.GROCERIES, 18000),
        ]

        FIRST_NAMES = ["Jean", "Pierre", "Michel", "Marie", "Chantal", "Alain", "Emmanuel", "Clarisse", "Nathalie", "Serge", "Rodrigue", "Amina", "Fatima", "Oumarou", "Valerie"]
        LAST_NAMES = ["Mbida", "Kamdem", "Fopa", "Essomba", "Mballa", "Nguemo", "Aboubakar", "Ewondo", "Tchinda", "Biya", "Bello", "Ndjock", "Moukoko"]

        # 2. Seed drivers
        drivers = []
        for code, name, phone, vtype, neigh in DRIVERS_DATA:
            driver, _ = DeliveryDriver.objects.get_or_create(
                driver_id=code,
                defaults={
                    "full_name": name,
                    "phone_number": phone,
                    "vehicle_type": vtype,
                    "is_available": True,
                    "current_neighborhood": neigh,
                }
            )
            drivers.append(driver)

        # 3. Seed products
        products = []
        for name, sku, cat, price in PRODUCTS_DATA:
            prod, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat,
                    "unit_price_fcfa": price,
                    "stock_quantity": random.randint(30, 200),
                    "is_active": True,
                }
            )
            products.append(prod)

        # 4. Seed customers & addresses
        customers = []
        addresses = []
        for i in range(1, 101):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            # Cameroonian phone numbers: 67x (MTN) or 69x (Orange)
            prefix = random.choice(["67", "69", "65", "68"])
            suffix = f"{random.randint(1000000, 9999999)}"
            phone = f"+237{prefix}{suffix[:7]}"
            
            cust = Customer.objects.create(
                full_name=f"{fn} {ln}",
                phone_number=phone,
                email=f"{fn.lower()}.{ln.lower()}{i}@example.cm"
            )
            customers.append(cust)

            city, neigh, landmark = random.choice(NEIGHBORHOODS_DATA)
            addr = Address.objects.create(
                customer=cust,
                city=city,
                neighborhood=neigh,
                landmark_reference=landmark,
                contact_phone=phone,
                is_default=True,
            )
            addresses.append(addr)

        # 5. Generate Orders & PaymentTransactions
        start_date = timezone.now() - timedelta(days=60)
        orders_batch = []
        items_batch = []
        transactions_batch = []

        PAYMENT_DISTRIBUTION = [
            (PaymentMethod.MTN_MOMO, 0.55),
            (PaymentMethod.ORANGE_MONEY, 0.35),
            (PaymentMethod.CASH_ON_DELIVERY, 0.10),
        ]

        STATUS_DISTRIBUTION = [
            (OrderStatus.DELIVERED, 0.65),
            (OrderStatus.IN_TRANSIT, 0.12),
            (OrderStatus.PAID, 0.10),
            (OrderStatus.ASSIGNED_TO_DRIVER, 0.05),
            (OrderStatus.PENDING_PAYMENT, 0.05),
            (OrderStatus.CANCELLED, 0.03),
        ]

        def weighted_choice(choices):
            total = sum(w for c, w in choices)
            r = random.uniform(0, total)
            upto = 0
            for c, w in choices:
                if upto + w >= r:
                    return c
                upto += w
            return choices[-1][0]

        self.stdout.write("🧹 Cleaning previous orders to ensure clean batch...")
        Order.objects.all().delete()
        PaymentTransaction.objects.all().delete()

        self.stdout.write("📦 Generating 500+ order records with linked items and payments...")

        for i in range(1, count + 1):
            order_id = f"ECM-{i:05d}"
            customer = random.choice(customers)
            # Find customer address
            address = customer.addresses.first() or random.choice(addresses)
            driver = random.choice(drivers)
            pmethod = weighted_choice(PAYMENT_DISTRIBUTION)
            order_status = weighted_choice(STATUS_DISTRIBUTION)

            # Payment status logic
            if order_status in [OrderStatus.DELIVERED, OrderStatus.IN_TRANSIT, OrderStatus.PAID, OrderStatus.ASSIGNED_TO_DRIVER]:
                pstatus = PaymentStatus.PAID
            elif order_status == OrderStatus.CANCELLED:
                pstatus = random.choice([PaymentStatus.FAILED, PaymentStatus.PENDING])
            else:
                pstatus = PaymentStatus.PENDING

            # Pick 1 to 3 items
            selected_products = random.sample(products, k=random.randint(1, 3))
            total_amount = 0
            item_tuples = []
            for prod in selected_products:
                qty = random.randint(1, 3)
                subtotal = qty * prod.unit_price_fcfa
                total_amount += subtotal
                item_tuples.append((prod, qty, prod.unit_price_fcfa, subtotal))

            order_date = start_date + timedelta(
                days=random.randint(0, 58),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            dist_km = round(random.uniform(2.0, 18.0), 1)
            duration_hrs = round(random.normalvariate(26.0, 12.0), 1)
            if duration_hrs < 1.0:
                duration_hrs = 1.5

            delivered_date = order_date + timedelta(hours=duration_hrs) if order_status == OrderStatus.DELIVERED else None

            order = Order(
                order_id=order_id,
                customer=customer,
                delivery_address=address,
                driver=driver,
                status=order_status,
                payment_method=pmethod,
                payment_status=pstatus,
                total_amount_fcfa=total_amount,
                distance_km=dist_km,
                delivery_duration_hours=duration_hrs if order_status == OrderStatus.DELIVERED else None,
                delivered_at=delivered_date,
            )
            orders_batch.append((order, item_tuples, pstatus, pmethod, total_amount, customer.phone_number))

        # Save orders and linked records inside a single atomic transaction
        created_orders = []
        with transaction.atomic():
            for order, items, pstatus, pmethod, total_amount, phone in orders_batch:
                order.save()
                created_orders.append(order)

                # Save items
                for prod, qty, price, subtotal in items:
                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        quantity=qty,
                        unit_price_fcfa=price,
                        subtotal_fcfa=subtotal
                    )

                # Save payment transaction
                if pmethod in [PaymentMethod.MTN_MOMO, PaymentMethod.ORANGE_MONEY]:
                    prefix = "MOMO" if pmethod == PaymentMethod.MTN_MOMO else "OM"
                    tx_ref = f"{prefix}-CM-{order.order_id}-{uuid.uuid4().hex[:6].upper()}"
                    idemp = f"{pmethod}_{tx_ref}"
                    PaymentTransaction.objects.create(
                        order=order,
                        provider=pmethod,
                        provider_tx_id=tx_ref,
                        idempotency_key=idemp,
                        amount_fcfa=total_amount,
                        phone_number=phone,
                        status=pstatus,
                        signature_verified=True,
                        raw_payload={
                            "transaction_id": tx_ref,
                            "order_id": order.order_id,
                            "amount_fcfa": total_amount,
                            "phone_number": phone,
                            "status": "SUCCESS" if pstatus == PaymentStatus.PAID else "FAILED",
                        },
                        processed_at=order.created_at if pstatus == PaymentStatus.PAID else None
                    )

                # Initial tracking log
                DeliveryTrackingLog.objects.create(
                    order=order,
                    status=order.status,
                    notes=f"Commande créée avec mode de règlement: {pmethod}."
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully created {len(created_orders)} orders, "
                f"{PaymentTransaction.objects.count()} payment transactions, "
                f"and {OrderItem.objects.count()} order items!"
            )
        )
