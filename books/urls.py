from django.urls import path
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'books',views.BookViewSet,basename="books")
router.register(r'dummies',views.DummyViewSet,basename="dummies")



urlpatterns = [
    

]
urlpatterns+= router.urls