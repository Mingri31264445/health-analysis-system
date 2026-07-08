from django.urls import path

from .views import (
    feature_gate,
    forgot_password_view,
    home,
    login_view,
    logout_view,
    questionnaire_view,
    register_view,
    start_analysis_view,
)

urlpatterns = [
    path("", home, name="home"),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("logout/", logout_view, name="logout"),
    path("start/", start_analysis_view, name="start_analysis"),
    path("questionnaire/", questionnaire_view, name="questionnaire"),
    path("analysis/<str:feature_key>/", feature_gate, name="feature_gate"),
]
