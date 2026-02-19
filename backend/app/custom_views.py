from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth.models import User
from django.utils import timezone
from .models import SiteSettings, InviteLink


class LoginRateThrottle(AnonRateThrottle):
    """Strict per-IP rate limit applied only to the login endpoint."""
    scope = "login"


class ThrottledLoginView(LoginView):
    """Login view with a tight rate limit (5 attempts/minute per IP)."""
    throttle_classes = [LoginRateThrottle]


class RegisterAdminView(APIView):
    """
    View for registering the initial admin/superuser.
    This endpoint is only accessible when no superuser exists.
    If a superuser already exists, it returns a redirect instruction.
    """

    permission_classes = []  # Public endpoint

    def get(self, request):
        """Check if a superuser already exists."""
        superuser_exists = User.objects.filter(is_superuser=True).exists()
        return Response(
            {
                "superuser_exists": superuser_exists,
                "redirect_url": "/register" if superuser_exists else None,
            }
        )

    def post(self, request):
        """Create the initial admin superuser and configure site settings."""
        # Check if a superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            return Response(
                {
                    "detail": "An administrator already exists. Redirecting to registration.",
                    "redirect_url": "/register",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate required fields
        username = request.data.get("username")
        email = request.data.get("email")
        password1 = request.data.get("password1")
        password2 = request.data.get("password2")

        errors = {}
        if not username:
            errors["username"] = ["Username is required."]
        if not email:
            errors["email"] = ["Email is required."]
        if not password1:
            errors["password1"] = ["Password is required."]
        if not password2:
            errors["password2"] = ["Password confirmation is required."]
        if password1 and password2 and password1 != password2:
            errors["password2"] = ["Passwords do not match."]
        if password1 and len(password1) < 8:
            errors["password1"] = ["Password must be at least 8 characters."]

        # Check if username or email already exists
        if username and User.objects.filter(username=username).exists():
            errors["username"] = ["A user with this username already exists."]
        if email and User.objects.filter(email=email).exists():
            errors["email"] = ["A user with this email already exists."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Create the superuser
        user = User.objects.create_superuser(
            username=username, email=email, password=password1
        )

        # Initialize site settings
        settings = SiteSettings.get_settings()
        settings.updated_by = user
        settings.save()

        return Response(
            {
                "detail": "Administrator account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomRegisterView(RegisterView):
    """
    Custom registration view that requires a valid invite token.
    Registration is only possible with a valid, non-expired, unused invite link.
    """

    def create(self, request, *args, **kwargs):
        # Extract invite token from request data
        token = request.data.get("invite_token")

        if not token:
            return Response(
                {"detail": "An invite token is required to register."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invite = InviteLink.objects.get(token=token)
        except (InviteLink.DoesNotExist, ValueError):
            return Response(
                {"detail": "Invalid invite link."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not invite.is_valid:
            reason = "expired" if invite.is_expired else "already been used"
            return Response(
                {"detail": f"This invite link has {reason}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Proceed with normal registration
        response = super().create(request, *args, **kwargs)

        # If registration was successful, mark the invite as used
        if response.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ):
            new_user = User.objects.get(username=request.data.get("username"))
            invite.used_by = new_user
            invite.used_at = timezone.now()
            invite.save()

        return response
