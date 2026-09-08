import csv
import os
import re
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
    help = "ETL pipeline: Ingest, clean and migrate legacy messy e-commerce orders into normalized Django models"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="/home/hakimi/Téléchargements/ecommerce_orders_messy_data.csv",
            help="Path to the messy CSV file",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"❌ CSV file not found at: {csv_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"🔄 Starting ETL Ingestion & Cleaning on: {csv_path}"))

        # Canonical Neighborhoods and City Mapping
        NEIGHBORHOOD_MAP = {
            "akwa": ("Douala", "Akwa", "Carrefour Idéal, Face Boulangerie Saker"),
            "bonapriso": ("Douala", "Bonapriso", "Rue des Palmiers, Clinique Soppo Priso"),
            "bonamoussadi": ("Douala", "Bonamoussadi", "Carrefour Denver, Face Pharmacie"),
            "deido": ("Douala", "Deido", "Rond-point Deido, Station Total"),
            "new bell": ("Douala", "New Bell", "Marché Nkololoun, Entrée principale"),
            "bastos": ("Yaoundé", "Bastos", "Montée Bastos, Face Ambassade de Grèce"),
            "mendong": ("Yaoundé", "Mendong", "Carrefour Simbock, Derrière Tradex"),
            "nlongkak": ("Yaoundé", "Nlongkak", "Rond-point Nlongkak, Immeuble ministériel"),
            "biyem assi": ("Yaoundé", "Biyem-Assi", "Carrefour Acacias, Face Collège Vogt"),
            "biyem-assi": ("Yaoundé", "Biyem-Assi", "Carrefour Acacias, Face Collège Vogt"),
            "ngousso": ("Yaoundé", "Ngousso", "Hôpital Général, Entrée Urgences"),
        }

        # Date parsing helper
        DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%d %b %Y", "%Y/%m/%d"]

        def parse_date(date_str):
            if not date_str or date_str.strip() in ["N/A", "unknown", "0000-00-00"]:
                return None
            clean_str = date_str.strip()
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(clean_str, fmt)
                except ValueError:
                    continue
            return None

        # Metrics for cleaning report
        stats = {
            "total_rows": 0,
            "duplicates_removed": 0,
            "dates_fixed": 0,
            "neighborhoods_normalized": 0,
            "negative_quantities_fixed": 0,
            "negative_prices_fixed": 0,
            "missing_prices_imputed": 0,
            "anomalous_durations_fixed": 0,
            "anomalous_distances_fixed": 0,
            "missing_drivers_assigned": 0,
            "valid_orders_imported": 0,
        }

        seen_order_ids = set()
        clean_records = []

        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total_rows"] += 1
                order_id = row.get("order_id", "").strip()

                # 1. Deduplication Guard
                if not order_id or order_id in seen_order_ids:
                    stats["duplicates_removed"] += 1
                    continue
                seen_order_ids.add(order_id)

                # 2. Neighborhood Normalization
                raw_neigh = row.get("customer_neighborhood", "").strip()
                lookup_key = raw_neigh.lower().replace("-", " ").strip()
                # Also check with hyphen
                if lookup_key in NEIGHBORHOOD_MAP:
                    city, clean_neigh, landmark = NEIGHBORHOOD_MAP[lookup_key]
                elif raw_neigh.lower() in NEIGHBORHOOD_MAP:
                    city, clean_neigh, landmark = NEIGHBORHOOD_MAP[raw_neigh.lower()]
                else:
                    city, clean_neigh, landmark = "Douala", raw_neigh.title() or "Akwa", "Centre Urbain"
                
                if raw_neigh != clean_neigh:
                    stats["neighborhoods_normalized"] += 1

                # 3. Dates parsing & cleansing
                order_dt = parse_date(row.get("order_date"))
                delivery_dt = parse_date(row.get("delivery_date"))

                # Handle duration
                raw_duration = row.get("delivery_duration_hours", "").strip()
                try:
                    duration_hrs = float(raw_duration) if raw_duration else None
                except ValueError:
                    duration_hrs = None

                if duration_hrs is not None:
                    if duration_hrs < 0:
                        duration_hrs = abs(duration_hrs)
                        stats["anomalous_durations_fixed"] += 1
                    elif duration_hrs > 120.0:
                        # Normalize extreme outlier (e.g. 250h or 300h)
                        duration_hrs = round(duration_hrs / 10.0, 1)
                        stats["anomalous_durations_fixed"] += 1

                # If order date is corrupted, infer from delivery date or fallback
                if not order_dt:
                    stats["dates_fixed"] += 1
                    if delivery_dt and duration_hrs:
                        order_dt = delivery_dt - timedelta(hours=duration_hrs)
                    else:
                        order_dt = datetime(2025, 4, 1, 10, 0, 0)

                # 4. Quantity & Price cleansing
                try:
                    qty = int(float(row.get("quantity", 1)))
                except (ValueError, TypeError):
                    qty = 1
                if qty <= 0:
                    qty = abs(qty) if qty < 0 else 1
                    stats["negative_quantities_fixed"] += 1

                raw_price = row.get("unit_price_fcfa", "").strip()
                try:
                    price = float(raw_price) if raw_price else None
                except ValueError:
                    price = None

                if price is None:
                    price = 15000.0  # Median category default
                    stats["missing_prices_imputed"] += 1
                elif price < 0:
                    price = abs(price)
                    stats["negative_prices_fixed"] += 1

                price_fcfa = int(price)

                # 5. Product Category & Product resolution
                category = row.get("product_category", "Electronics").strip()
                if category not in ProductCategory.values:
                    category = ProductCategory.ELECTRONICS

                # 6. Payment Method normalization
                raw_pm = row.get("payment_method", "").strip().lower()
                if "momo" in raw_pm or "mtn" in raw_pm:
                    clean_pm = PaymentMethod.MTN_MOMO
                elif "orange" in raw_pm:
                    clean_pm = PaymentMethod.ORANGE_MONEY
                else:
                    clean_pm = PaymentMethod.CASH_ON_DELIVERY

                # 7. Payment Status normalization
                raw_ps = row.get("payment_status", "").strip().lower()
                if raw_ps == "paid":
                    clean_ps = PaymentStatus.PAID
                elif raw_ps == "failed":
                    clean_ps = PaymentStatus.FAILED
                else:
                    clean_ps = PaymentStatus.PENDING

                # 8. Delivery Status normalization
                raw_ds = row.get("delivery_status", "").strip().lower()
                if "deliver" in raw_ds:
                    clean_ds = OrderStatus.DELIVERED
                    clean_ps = PaymentStatus.PAID if clean_ps != PaymentStatus.FAILED else PaymentStatus.PAID
                elif "transit" in raw_ds or "delay" in raw_ds:
                    clean_ds = OrderStatus.IN_TRANSIT
                elif "return" in raw_ds:
                    clean_ds = OrderStatus.RETURNED
                elif "cancel" in raw_ds:
                    clean_ds = OrderStatus.CANCELLED
                else:
                    clean_ds = OrderStatus.ASSIGNED_TO_DRIVER

                # 9. Distance cleansing
                try:
                    dist_km = float(row.get("distance_km", 5.0))
                except (ValueError, TypeError):
                    dist_km = 5.0

                if dist_km > 60.0:  # Outlier (25x)
                    dist_km = round(dist_km / 25.0, 1)
                    stats["anomalous_distances_fixed"] += 1

                # 10. Driver resolution
                driver_code = row.get("driver_id", "").strip()
                if not driver_code or driver_code.lower() == "nan":
                    driver_code = "DRV-001"
                    stats["missing_drivers_assigned"] += 1

                clean_records.append({
                    "order_id": order_id,
                    "city": city,
                    "neighborhood": clean_neigh,
                    "landmark": landmark,
                    "order_dt": timezone.make_aware(order_dt) if timezone.is_naive(order_dt) else order_dt,
                    "category": category,
                    "quantity": qty,
                    "unit_price_fcfa": price_fcfa,
                    "total_amount_fcfa": qty * price_fcfa,
                    "payment_method": clean_pm,
                    "payment_status": clean_ps,
                    "delivery_status": clean_ds,
                    "delivery_duration_hours": duration_hrs,
                    "driver_code": driver_code,
                    "distance_km": dist_km,
                })

        self.stdout.write(f"🧹 Data cleaned: {len(clean_records)} records prepared. Persisting into database...")

        # Persist into database using atomic transaction
        with transaction.atomic():
            # Ensure products exist
            category_products = {}
            for cat in ProductCategory.values:
                prod, _ = Product.objects.get_or_create(
                    sku=f"LEGACY-{cat[:3].upper()}-01",
                    defaults={
                        "name": f"Article Standard ({cat})",
                        "category": cat,
                        "unit_price_fcfa": 15000,
                        "stock_quantity": 500,
                        "is_active": True,
                    }
                )
                category_products[cat] = prod

            # Ensure drivers exist
            driver_cache = {}
            for rec in clean_records:
                dcode = rec["driver_code"]
                if dcode not in driver_cache:
                    drv, _ = DeliveryDriver.objects.get_or_create(
                        driver_id=dcode,
                        defaults={
                            "full_name": f"Chauffeur {dcode}",
                            "phone_number": "+237670000000",
                            "vehicle_type": VehicleType.MOTO,
                            "is_available": True,
                        }
                    )
                    driver_cache[dcode] = drv

            # Default legacy customer
            legacy_customer, _ = Customer.objects.get_or_create(
                phone_number="+237670999888",
                defaults={"full_name": "Client E-Commerce (Legacy Import)", "email": "legacy.orders@example.cm"}
            )

            # Insert or update Orders
            for rec in clean_records:
                addr, _ = Address.objects.get_or_create(
                    customer=legacy_customer,
                    neighborhood=rec["neighborhood"],
                    defaults={
                        "city": rec["city"],
                        "landmark_reference": rec["landmark"],
                        "contact_phone": legacy_customer.phone_number,
                    }
                )

                order, created = Order.objects.update_or_create(
                    order_id=rec["order_id"],
                    defaults={
                        "customer": legacy_customer,
                        "delivery_address": addr,
                        "driver": driver_cache.get(rec["driver_code"]),
                        "status": rec["delivery_status"],
                        "payment_method": rec["payment_method"],
                        "payment_status": rec["payment_status"],
                        "total_amount_fcfa": rec["total_amount_fcfa"],
                        "distance_km": rec["distance_km"],
                        "delivery_duration_hours": rec["delivery_duration_hours"],
                    }
                )

                # Link item
                prod = category_products.get(rec["category"])
                OrderItem.objects.get_or_create(
                    order=order,
                    product=prod,
                    defaults={
                        "quantity": rec["quantity"],
                        "unit_price_fcfa": rec["unit_price_fcfa"],
                        "subtotal_fcfa": rec["total_amount_fcfa"],
                    }
                )

                # Link transaction if MoMo / OM
                if rec["payment_method"] in [PaymentMethod.MTN_MOMO, PaymentMethod.ORANGE_MONEY]:
                    idemp = f"IDEMP-LEGACY-{rec['order_id']}"
                    PaymentTransaction.objects.get_or_create(
                        idempotency_key=idemp,
                        defaults={
                            "order": order,
                            "provider": rec["payment_method"],
                            "provider_tx_id": f"TX-LEGACY-{rec['order_id']}",
                            "amount_fcfa": rec["total_amount_fcfa"],
                            "phone_number": legacy_customer.phone_number,
                            "status": rec["payment_status"],
                            "signature_verified": True,
                            "raw_payload": {"source": "legacy_csv_etl_import"},
                        }
                    )

                stats["valid_orders_imported"] += 1

        self.stdout.write(self.style.SUCCESS("=================================================================="))
        self.stdout.write(self.style.SUCCESS("  🎉 ETL INGESTION & DATA SANITIZATION REPORT"))
        self.stdout.write(self.style.SUCCESS("=================================================================="))
        for k, v in stats.items():
            self.stdout.write(f"  • {k.replace('_', ' ').capitalize()}: {v}")
        self.stdout.write(self.style.SUCCESS("=================================================================="))
