from django.urls import path, re_path
from .views import DriveExplorerView
from rest_framework.routers import DefaultRouter,SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'mouza-map-data',views.MouzamapdataViewSet,basename="mouza-map-data")
router.register(r'divisions', views.Division2ViewSet, basename='division2')
router.register(r'districts', views.District2ViewSet, basename='district2')
router.register(r'sub-districts', views.SubDistrictViewSet, basename='subdistrict')
urlpatterns = [
    re_path(r'^api/drive/folders/(?P<path>.+)/$', DriveExplorerView.as_view(), name='drive-explorer'),
    path('api/drive/folders/', DriveExplorerView.as_view(), name='drive-root'),  # For the root level
    path('api/drive/search-file/', views.DriveFileSearchView.as_view(), name='drive-file-search'),
    path('api/drive/preview/', views.DriveFilePreviewByIdView.as_view(), name='drive_preview'),
    path('user-files/', views.UserPurchasedFilesView.as_view(), name='user-purchased-files'),
    path('user-files-batch/', views.UserPurchasedFilesBatchView.as_view(), name='user-purchased-files-batch'),
    path("drive/convert-file/", views.DriveFileConvertView.as_view(), name="drive_convert_file"),
    
]
urlpatterns+= router.urls