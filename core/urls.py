from django.urls import path
from .views import home, upload_meridian_result, upload_bfs_test, bfs_detail

urlpatterns = [
    path("", home, name="home"),
    path("Meridian/upload/", upload_meridian_result, name="upload_meridian_result"),
    path('bfs/upload/', upload_bfs_test, name='upload_bfs_test'),
    path('bfs/<int:pk>/', bfs_detail, name='bfs_detail'),
]