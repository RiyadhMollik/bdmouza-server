from django.urls import path
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'system-assets',views.SystemAssetsViewSet,basename="system-assets")
router.register(r'email-configure',views.EmailConfigureViewSet,basename="email-configure")
urlpatterns = [
    

]
urlpatterns+= router.urls