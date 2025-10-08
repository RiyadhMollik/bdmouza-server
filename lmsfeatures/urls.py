from django.urls import path
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
# router.register(r'system-assets',views.SystemAssetsViewSet,basename="system-assets")
# router.register(r'email-configure',views.EmailConfigureViewSet,basename="email-configure")
router.register(r'courses',views.CoursesViewSet,basename="courses")
router.register(r'payments',views.PaymentViewSet,basename="payments")
router.register(r'payment-methods',views.PaymentMethodsViewSet,basename="payment-methods")
router.register(r'installation-status',views.InstallationStatusViewSet,basename="installation-status")
router.register(r'enrolled-courses',views.EnrollCourseViewSet,basename="enrolled-courses")
router.register(r'sslcommerz-settings',views.SSLcommerceSettingsViewSet,basename="sslcommerz-settings")
urlpatterns = [
    

]
urlpatterns+= router.urls