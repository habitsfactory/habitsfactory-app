from dj_rest_auth.registration.views import RegisterView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .models import SiteSettings


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
        return Response({
            "superuser_exists": superuser_exists,
            "redirect_url": "/register" if superuser_exists else None
        })

    def post(self, request):
        """Create the initial admin superuser and configure site settings."""
        # Check if a superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            return Response(
                {
                    "detail": "An administrator already exists. Redirecting to registration.",
                    "redirect_url": "/register"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate required fields
        username = request.data.get("username")
        email = request.data.get("email")
        password1 = request.data.get("password1")
        password2 = request.data.get("password2")
        allow_registration = request.data.get("allow_registration", True)

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
            username=username,
            email=email,
            password=password1
        )

        # Configure site settings
        settings = SiteSettings.get_settings()
        settings.allow_registration = allow_registration
        settings.updated_by = user
        settings.save()

        return Response(
            {
                "detail": "Administrator account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser
                },
                "settings": {
                    "allow_registration": settings.allow_registration
                }
            },
            status=status.HTTP_201_CREATED
        )


class CustomRegisterView(RegisterView):
    """
    Custom registration view that checks if registration is allowed
    in the site settings before allowing new user registration.
    """
    
    def create(self, request, *args, **kwargs):
        # Check if registration is allowed
        settings = SiteSettings.get_settings()
        
        if not settings.allow_registration:
            return Response(
                {"detail": "Registration is currently disabled by the site administrator."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # If registration is allowed, proceed with normal registration
        return super().create(request, *args, **kwargs)