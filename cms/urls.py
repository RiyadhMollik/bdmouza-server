from django.urls import path
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
# router.register(r'system-assets',views.SystemAssetsViewSet,basename="system-assets")
# router.register(r'email-configure',views.EmailConfigureViewSet,basename="email-configure")
router.register(r'pages',views.PageViewSet,basename="pages")
router.register(r'faqs',views.FAQViewSet,basename="faqs")
router.register(r'testimonials',views.TestimonialViewSet,basename="testimonials")
router.register(r'blogs',views.BlogViewSet,basename="blogs")
router.register(r'banners',views.BannerViewSet,basename="banners")
router.register(r'counters',views.CounterViewSet,basename="counters")
router.register(r'facilities',views.FacilitiesViewSet,basename="facilities")
router.register(r'special-cta',views.SpecialCtaViewSet,basename="special-cta")
router.register(r'bannerlms',views.BannerLMSViewSet,basename="bannerlms")
urlpatterns = [
    

]
urlpatterns+= router.urls