"""
URL configuration for starterproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.conf import settings
#for open api
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from des import urls as des_urls
urlpatterns = [
    # path('', include('hrm.urls')),
    path('', include('users.urls')),
    path('', include('others.urls')),
    path('', include('cms.urls')),
    path('', include('driveapp.urls')),
    # path('', include('books.urls')),
    # path('', include('lmsfeatures.urls')),
    # path('', include('phonebook.urls')),
    path('', include('filehandler.urls')),
    path('', include('globalapp.urls')),
    path('api/payment/', include('epspayment.urls')),  # EPS Payment URLs
    path('', include('packages.urls')),  # Package Management URLs
    path('admin/', admin.site.urls),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path(r'^django-des/', include(des_urls)),
    # Optional UI:
    path('swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # path('api/docs/', schema_view),
    
]+ static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)\
 +static(settings.STATIC_URL,document_root = settings.STATIC_ROOT)

urlpatterns+= staticfiles_urlpatterns()
