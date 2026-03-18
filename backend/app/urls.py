from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .custom_views import CustomRegisterView, RegisterAdminView, ThrottledLoginView
from .views import (
    HabitViewSet,
    CategoryViewSet,
    HabitCorrelationViewSet,
    UserInfoView,
    SiteSettingsViewSet,
    TagViewSet,
    InviteLinkViewSet,
    health,
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r"habits", HabitViewSet, basename="habit")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"settings", SiteSettingsViewSet, basename="settings")
router.register(r"correlations", HabitCorrelationViewSet, basename="correlation")
router.register(r"invite-links", InviteLinkViewSet, basename="invite-link")

urlpatterns = [
    # Health check (public, no auth required)
    path("health/", health, name="health"),
    # Django admin
    path("admin/", admin.site.urls),
    # API routes (habits, categories, tags, correlations, etc.)
    path("api/", include(router.urls)),
    # User info endpoint
    path("api/auth/user/", UserInfoView.as_view(), name="user-info"),
    # Login with rate limiting (must be before the dj_rest_auth include)
    path("api/auth/login/", ThrottledLoginView.as_view(), name="rest_login"),
    # Authentication routes
    path("api/auth/", include("dj_rest_auth.urls")),
    # Custom registration endpoint
    path("api/auth/registration/", CustomRegisterView.as_view(), name="rest_register"),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    # Admin registration endpoint (initial setup)
    path("api/auth/register-admin/", RegisterAdminView.as_view(), name="register-admin"),
]
