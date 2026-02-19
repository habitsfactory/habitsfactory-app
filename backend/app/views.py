from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from .serializers import (
    HabitSerializer,
    CategorySerializer,
    SiteSettingsSerializer,
    HabitCorrelationSerializer,
    TagSerializer,
    InviteLinkSerializer,
)
from datetime import date, datetime, timedelta
from .models import Habit, Completion, Category, SiteSettings, Tag, InviteLink
from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from .models import HabitCorrelation


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by("order", "name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def update_layout(self, request):
        """Update the order of categories"""
        layout_data = request.data.get("layout", [])

        for item in layout_data:
            try:
                category = Category.objects.get(id=item["id"], user=request.user)
                category.order = item.get("order", 0)
                category.save()
            except Category.DoesNotExist:
                pass

        return Response({"status": "layout updated"})


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tag.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]
    # Add queryset attribute for the router
    queryset = Habit.objects.all()

    def get_queryset(self):
        # Only return habits for the authenticated user
        queryset = self.queryset.filter(user=self.request.user)
        # Filter by archived status if specified, default to non-archived
        include_archived = self.request.query_params.get("include_archived", "false")
        archived_only = self.request.query_params.get("archived_only", "false")
        if archived_only.lower() == "true":
            queryset = queryset.filter(archived=True)
        elif include_archived.lower() != "true":
            queryset = queryset.filter(archived=False)
        return queryset

    def get_serializer_context(self):
        """Pass the requested date to the serializer"""
        context = super().get_serializer_context()
        # Get date from query params, default to today
        date_str = self.request.query_params.get("date")
        if date_str:
            try:
                context["date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                context["date"] = date.today()
        else:
            context["date"] = date.today()
        return context

    def perform_create(self, serializer):
        # Automatically set the user when creating a habit
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        habit = self.get_object()
        val = request.data.get("value", 1)  # Default to 1 for booleans
        completion_date_str = request.data.get("date")  # Get date from request

        # Parse date or use today
        if completion_date_str:
            try:
                completion_date = datetime.strptime(
                    completion_date_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"}, status=400
                )
        else:
            completion_date = date.today()

        # Update or create completion for the specified date
        completion, created = Completion.objects.update_or_create(
            habit=habit,
            date=completion_date,
            defaults={"value": val},
        )

        return Response(
            {
                "status": "updated" if not created else "created",
                "new_value": float(completion.value),
            }
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive a habit."""
        habit = self.get_object()
        habit.archived = True
        habit.save()
        return Response({"status": "archived", "id": habit.id})

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        """Unarchive a habit."""
        # Fetch habit directly without relying on get_queryset() which filters by archived status
        try:
            habit = Habit.objects.get(id=pk, user=request.user)
        except Habit.DoesNotExist:
            return Response({"error": "Habit not found"}, status=404)

        habit.archived = False
        habit.save()
        return Response({"status": "unarchived", "id": habit.id})

    def destroy(self, request, pk=None):
        """Delete a habit (works for both active and archived habits)."""
        # Fetch habit directly without relying on get_queryset() which filters by archived status
        try:
            habit = Habit.objects.get(id=pk, user=request.user)
        except Habit.DoesNotExist:
            return Response(
                {"error": "Habit not found"}, status=status.HTTP_404_NOT_FOUND
            )

        habit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def graph_data(self, request):
        """
        Get habit completion data for graphing within a date range.
        Returns data grouped by habit type.
        """
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "start_date and end_date are required"}, status=400
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, status=400
            )

        # Get all habits for the user
        habits = self.get_queryset()

        # Structure: { habit_type: [{ habit_name, habit_id, color, data: [{ date, value }] }] }
        result = {"boolean": [], "counter": [], "value": [], "rating": []}

        for habit in habits:
            # Get completions for this habit in the date range
            completions = Completion.objects.filter(
                habit=habit, date__gte=start_date, date__lte=end_date
            ).order_by("date")

            # Build data points
            data_points = []
            for completion in completions:
                data_points.append(
                    {
                        "date": completion.date.isoformat(),
                        "value": float(completion.value),
                    }
                )

            # Only include habits that have data
            if data_points:
                habit_data = {
                    "habit_id": habit.id,
                    "habit_name": habit.name,
                    "color": habit.color,
                    "data": data_points,
                }

                result[habit.habit_type].append(habit_data)

        return Response(result)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        """
        Export habit completion data as CSV for a date range.
        Format: First column is habit name, subsequent columns are dates (one per day).
        Each row contains the values for that habit on each day.
        """
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "start_date and end_date are required"}, status=400
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, status=400
            )

        # Get all habits for the user
        habits = self.get_queryset().order_by("name")

        # Generate list of all dates in range
        from datetime import timedelta

        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)

        # Build CSV content
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write header row (Habit Name, Date1, Date2, ...)
        header = ["Habit Name"] + [d.strftime("%Y-%m-%d") for d in date_list]
        writer.writerow(header)

        # Write data rows
        for habit in habits:
            # Get all completions for this habit in the date range
            completions = Completion.objects.filter(
                habit=habit, date__gte=start_date, date__lte=end_date
            ).order_by("date")

            # Create a dictionary for quick lookup
            completion_dict = {c.date: float(c.value) for c in completions}

            # Build row: habit name followed by values for each date
            row = [habit.name]
            for date_item in date_list:
                value = completion_dict.get(date_item, "")
                row.append(value)

            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()

        return Response({"csv_content": csv_content})

    @action(detail=False, methods=["get"])
    def date_range(self, request):
        """
        Get the minimum and maximum dates for all completions for the user's habits.
        Returns the date range of all available data.
        """
        # Get all habits for the user
        habits = self.get_queryset()

        # Get all completions for these habits
        completions = Completion.objects.filter(habit__in=habits).order_by("date")

        if not completions.exists():
            return Response(
                {"start_date": None, "end_date": None, "message": "No data available"}
            )

        min_date = completions.first().date
        max_date = completions.last().date

        return Response(
            {"start_date": min_date.isoformat(), "end_date": max_date.isoformat()}
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Get summary statistics for habits over a date range (default: last 7 days).
        Returns metrics grouped by habit type.
        """
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "start_date and end_date are required"}, status=400
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, status=400
            )

        # Get all habits for the user
        habits = self.get_queryset()

        # Calculate number of days in range
        days_in_range = (end_date - start_date).days + 1

        # Structure: { habit_type: [{ habit_name, color, metrics }] }
        result = {"boolean": [], "counter": [], "value": [], "rating": []}

        for habit in habits:
            # Get completions for this habit in the date range
            completions = Completion.objects.filter(
                habit=habit, date__gte=start_date, date__lte=end_date, value__gt=0
            )

            completion_count = completions.count()

            if completion_count == 0:
                continue

            # Calculate metrics based on habit type
            if habit.habit_type == "boolean":
                # For boolean: completion rate
                metrics = {
                    "total_completions": completion_count,
                    "completion_rate": round(
                        (completion_count / days_in_range) * 100, 1
                    ),
                    "days_in_range": days_in_range,
                    "streak": self._calculate_streak(habit, start_date, end_date),
                }
            elif habit.habit_type == "counter":
                # For counter: total, average, max
                values = [float(c.value) for c in completions]
                metrics = {
                    "total": sum(values),
                    "average": round(sum(values) / days_in_range, 1),
                    "max": max(values),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                }
            elif habit.habit_type == "value":
                # For value: count, km, hour, etc.
                values = [float(c.value) for c in completions]
                metrics = {
                    "total": round(sum(values), 1),
                    "average": round(sum(values) / len(values), 1),
                    "max_value": round(max(values), 1),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                    "unit": habit.unit,
                }
            elif habit.habit_type == "rating":
                # For rating: average, distribution
                values = [float(c.value) for c in completions]
                metrics = {
                    "average": round(sum(values) / len(values), 1),
                    "max": int(max(values)),
                    "min": int(min(values)),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                    "max_value": habit.max_value,
                }

            result[habit.habit_type].append(
                {
                    "habit_id": habit.id,
                    "habit_name": habit.name,
                    "category_id": habit.category.id if habit.category else None,
                    "category_name": habit.category.name if habit.category else None,
                    "color": habit.color,
                    "icon": habit.icon,
                    "metrics": metrics,
                    "tags": [
                        {"id": tag.id, "name": tag.name, "color": tag.color}
                        for tag in habit.tags.all()
                    ],
                }
            )

        return Response(result)

    def _calculate_streak(self, habit, start_date, end_date):
        """Calculate current streak for a habit ending on end_date"""
        current_date = start_date
        streak = 0
        max_streak = 0
        while True:
            completion = Completion.objects.filter(
                habit=habit, date=current_date, value=1
            ).first()

            if completion:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

            current_date = current_date + timedelta(days=1)
            if current_date > end_date:
                break

        return max_streak


class UserInfoView(APIView):
    """
    Get current user information
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            }
        )


class SiteSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for site-wide settings. Only admin users can modify settings.
    All authenticated users can view settings (to check if registration is allowed).
    """

    serializer_class = SiteSettingsSerializer
    queryset = SiteSettings.objects.all()

    def get_permissions(self):
        """
        Allow all authenticated users to view settings,
        but only admin users can modify them.
        """
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Always return the singleton settings instance"""
        return SiteSettings.objects.all()

    def list(self, request):
        """
        Return the singleton settings instance for GET
        Handle updates for PATCH on list endpoint
        """
        if request.method == "PATCH":
            # Check if user is admin
            if not (request.user.is_staff or request.user.is_superuser):
                return Response(
                    {"detail": "You do not have permission to perform this action."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            settings = SiteSettings.get_settings()
            serializer = self.get_serializer(settings, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # GET request
        settings = SiteSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve the singleton settings instance"""
        settings = SiteSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def update_settings(self, request):
        """Update the settings via custom action"""
        settings = SiteSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invite links. Only admin users can create/list/delete.
    The validate action is public (used by registration page).
    """

    serializer_class = InviteLinkSerializer
    queryset = InviteLink.objects.all()

    def get_permissions(self):
        if self.action == "validate":
            permission_classes = []
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def create(self, request):
        """Generate a new invite link (admin only)."""
        invite = InviteLink.objects.create(
            created_by=request.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        serializer = self.get_serializer(invite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[])
    def validate(self, request):
        """
        Public endpoint to validate an invite token.
        Query param: ?token=<uuid>
        """
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"valid": False, "detail": "No token provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            invite = InviteLink.objects.get(token=token)
        except (InviteLink.DoesNotExist, ValueError):
            return Response({"valid": False, "detail": "Invalid invite link."})

        if not invite.is_valid:
            reason = "expired" if invite.is_expired else "already used"
            return Response({"valid": False, "detail": f"Invite link is {reason}."})

        return Response({"valid": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def habit_insights(request):
    """
    Get correlation insights for the current user.
    Returns the top correlated habit pairs.

    Query Parameters:
    - limit: Number of insights to return (default: 5)
    - min_correlation: Minimum correlation threshold (default: 0.5)

    Example:
    GET /api/habits/insights/?limit=10&min_correlation=0.6
    """
    user = request.user

    # Get query parameters with defaults
    try:
        limit = int(request.GET.get("limit", 5))
        limit = max(1, min(limit, 50))  # Clamp between 1 and 50
    except ValueError:
        limit = 5

    try:
        min_correlation = float(request.GET.get("min_correlation", 0.5))
        min_correlation = max(0.0, min(min_correlation, 1.0))  # Clamp between 0 and 1
    except ValueError:
        min_correlation = 0.5

    # Fetch correlations for this user
    correlations = (
        HabitCorrelation.objects.filter(user=user, max_correlation__gte=min_correlation)
        .select_related("habit1", "habit1__category", "habit2", "habit2__category")
        .order_by("-max_correlation")[:limit]
    )

    # Serialize the data
    serializer = HabitCorrelationSerializer(correlations, many=True)

    return Response(
        {
            "insights": serializer.data,
            "count": len(serializer.data),
            "filters": {"min_correlation": min_correlation, "limit": limit},
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def habit_insights_for_habit(request, habit_id):
    """
    Get correlations for a specific habit.
    Shows which other habits are most correlated with the given habit.

    Example:
    GET /api/habits/123/insights/
    """
    user = request.user

    try:
        limit = int(request.GET.get("limit", 5))
        limit = max(1, min(limit, 20))
    except ValueError:
        limit = 5

    # Get correlations where the habit appears in either position
    from django.db.models import Q

    correlations = (
        HabitCorrelation.objects.filter(user=user)
        .filter(Q(habit1_id=habit_id) | Q(habit2_id=habit_id))
        .select_related("habit1", "habit1__category", "habit2", "habit2__category")
        .order_by("-max_correlation")[:limit]
    )

    if not correlations.exists():
        return Response(
            {
                "insights": [],
                "count": 0,
                "message": "No correlations found for this habit.",
            }
        )

    serializer = HabitCorrelationSerializer(correlations, many=True)

    return Response(
        {
            "insights": serializer.data,
            "count": len(serializer.data),
            "habit_id": habit_id,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def habit_insights_summary(request):
    """
    Get summary statistics about correlations for the user.

    Returns:
    - Total number of correlations computed
    - Strongest correlation
    - Distribution by strength
    - Last update time
    """
    user = request.user

    correlations = HabitCorrelation.objects.filter(user=user)

    if not correlations.exists():
        return Response(
            {
                "total_correlations": 0,
                "has_data": False,
                "message": "No correlations computed yet. Run the compute_correlations command.",
            }
        )

    # Get strongest correlation
    strongest = correlations.order_by("-max_correlation").first()

    # Count by strength
    very_strong = correlations.filter(max_correlation__gte=0.9).count()
    strong = correlations.filter(
        max_correlation__gte=0.7, max_correlation__lt=0.9
    ).count()
    moderate = correlations.filter(
        max_correlation__gte=0.5, max_correlation__lt=0.7
    ).count()
    weak = correlations.filter(max_correlation__lt=0.5).count()

    return Response(
        {
            "total_correlations": correlations.count(),
            "has_data": True,
            "strongest_correlation": (
                {
                    "habit1": strongest.habit1.name,
                    "habit2": strongest.habit2.name,
                    "correlation": float(strongest.max_correlation),
                }
                if strongest
                else None
            ),
            "distribution": {
                "very_strong": very_strong,
                "strong": strong,
                "moderate": moderate,
                "weak": weak,
            },
            "last_updated": strongest.calculated_at if strongest else None,
            "date_range": (
                {"start": strongest.start_date, "end": strongest.end_date}
                if strongest
                else None
            ),
        }
    )


class HabitCorrelationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing habit correlations (insights).

    Provides:
    - list: Get top correlations for current user
    - retrieve: Get specific correlation by ID
    - summary: Get correlation statistics
    - for_habit: Get correlations for a specific habit
    """

    serializer_class = HabitCorrelationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return correlations for the current user only."""
        return (
            HabitCorrelation.objects.filter(user=self.request.user)
            .select_related("habit1", "habit1__category", "habit2", "habit2__category")
            .order_by("-max_correlation")
        )

    def list(self, request, *args, **kwargs):
        """
        Get top correlations for the current user.

        Query Parameters:
        - limit: Number of insights to return (default: 5, max: 50)
        - min_correlation: Minimum correlation threshold (default: 0.5)

        Example:
        GET /api/correlations/?limit=10&min_correlation=0.6
        """
        # Get and validate query parameters
        try:
            limit = int(request.GET.get("limit", 5))
            limit = max(1, min(limit, 50))  # Clamp between 1 and 50
        except ValueError:
            limit = 5

        try:
            min_correlation = float(request.GET.get("min_correlation", 0.5))
            min_correlation = max(
                0.0, min(min_correlation, 1.0)
            )  # Clamp between 0 and 1
        except ValueError:
            min_correlation = 0.5

        # Filter and limit queryset
        queryset = self.get_queryset().filter(max_correlation__gte=min_correlation)[
            :limit
        ]

        # Serialize
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "insights": serializer.data,
                "count": len(serializer.data),
                "filters": {"min_correlation": min_correlation, "limit": limit},
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Get summary statistics about correlations for the user.

        Returns:
        - Total number of correlations computed
        - Strongest correlation
        - Distribution by strength
        - Last update time

        Example:
        GET /api/correlations/summary/
        """
        correlations = self.get_queryset()

        if not correlations.exists():
            return Response(
                {
                    "total_correlations": 0,
                    "has_data": False,
                    "message": "No correlations computed yet. Run the compute_correlations command.",
                }
            )

        # Get strongest correlation
        strongest = correlations.first()

        # Count by strength
        very_strong = correlations.filter(max_correlation__gte=0.9).count()
        strong = correlations.filter(
            max_correlation__gte=0.7, max_correlation__lt=0.9
        ).count()
        moderate = correlations.filter(
            max_correlation__gte=0.5, max_correlation__lt=0.7
        ).count()
        weak = correlations.filter(max_correlation__lt=0.5).count()

        return Response(
            {
                "total_correlations": correlations.count(),
                "has_data": True,
                "strongest_correlation": (
                    {
                        "habit1": strongest.habit1.name,
                        "habit2": strongest.habit2.name,
                        "correlation": float(strongest.max_correlation),
                    }
                    if strongest
                    else None
                ),
                "distribution": {
                    "very_strong": very_strong,
                    "strong": strong,
                    "moderate": moderate,
                    "weak": weak,
                },
                "last_updated": strongest.calculated_at if strongest else None,
                "date_range": (
                    {"start": strongest.start_date, "end": strongest.end_date}
                    if strongest
                    else None
                ),
            }
        )

    @action(detail=False, methods=["get"], url_path="for-habit/(?P<habit_id>[^/.]+)")
    def for_habit(self, request, habit_id=None):
        """
        Get correlations for a specific habit.
        Shows which other habits are most correlated with the given habit.

        Example:
        GET /api/correlations/for-habit/123/
        """
        try:
            limit = int(request.GET.get("limit", 5))
            limit = max(1, min(limit, 20))
        except ValueError:
            limit = 5

        # Get correlations where the habit appears in either position
        correlations = self.get_queryset().filter(
            Q(habit1_id=habit_id) | Q(habit2_id=habit_id)
        )[:limit]

        if not correlations.exists():
            return Response(
                {
                    "insights": [],
                    "count": 0,
                    "message": "No correlations found for this habit.",
                }
            )

        serializer = self.get_serializer(correlations, many=True)

        return Response(
            {
                "insights": serializer.data,
                "count": len(serializer.data),
                "habit_id": int(habit_id),
            }
        )
