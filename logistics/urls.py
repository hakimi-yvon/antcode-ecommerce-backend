from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MobileMoneyWebhookView,
    OrderViewSet,
    ProductViewSet,
    DriverDeliveriesView,
    MetricsSummaryView,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"products", ProductViewSet, basename="product")

urlpatterns = [
    # Core API endpoints
    path("", include(router.urls)),
    # Mobile Money Payment Webhook
    path("payments/webhook/", MobileMoneyWebhookView.as_view(), name="payment-webhook"),
    # Driver mobile specific route (offline friendly list sorted by neighborhood)
    path("driver/<str:driver_id>/orders/", DriverDeliveriesView.as_view(), name="driver-orders"),
    # Logistics metrics & bottleneck analysis
    path("metrics/summary/", MetricsSummaryView.as_view(), name="metrics-summary"),
]
