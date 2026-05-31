from django.urls import path
from .views import home, upload_meridian_result

urlpatterns = [
    path("", home, name="home"),
    path("Meridian/upload/", upload_meridian_result, name="upload_meridian_result"),
]