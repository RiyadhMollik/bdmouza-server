from django.urls import path
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
# router.register(r'books',views.BookViewSet,basename="books")
# router.register(r'dummies',views.DummyViewSet,basename="dummies")
router.register(r'package-items',views.PackageItemViewSet,basename="package-items")
router.register(r'packages',views.PackageViewSet,basename="packages")
router.register(r'tutorial',views.TutorialViewSet,basename="tutorial")
router.register(r'purchase',views.UddoktapayPurchaseViewSet,basename="purchase")
router.register(r'extra-features',views.ExtraFeatureViewSet,basename="extra-features")
router.register(r'purchase-alt',views.PurchaseViewSet2,basename="purchase2")

urlpatterns = [
    path("payment-success/", views.PaymentSuccessView.as_view(), name="payment-success"),

]
urlpatterns+= router.urls