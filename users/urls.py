from django.urls import path
from users import views
from rest_framework.routers import DefaultRouter,SimpleRouter
router = SimpleRouter()
router.register(r'roles',views.RoleViewSet,basename="roles")
router.register(r'menus',views.GroupViewSet,basename="menus")
router.register(r'permissions',views.PermissionViewSet,basename="permissions")
router.register(r'users',views.UserViewSet,basename="users")
urlpatterns = [
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', views.LogoutView.as_view(), name='logout'), 
    path('users/update-profile/', views.UserViewSet.as_view({'patch': 'update_profile'}), name='update_profile'),
    path('google-login/', views.GoogleLoginView.as_view(), name='google_login'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordFormView.as_view(), name='reset-password-form'),
    # users/urls.py
    path('google-signup/', views.GoogleSignupView.as_view(), name='google_signup'),


]
urlpatterns+= router.urls