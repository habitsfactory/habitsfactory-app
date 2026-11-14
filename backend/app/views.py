from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from .serializers import (
    HabitSerializer,
    CategorySerializer,
    SiteSettingsSerializer,
    HabitCorrelationSerializer,
    TagSerializer,
    InviteLinkSerializer,
)
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from .models import Habit, Completion, Category, SiteSettings, Tag, InviteLink
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db.models import Max, Q
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


DATE_HEADER_RE = re.compile(r"^(\d{1,4})[-/.](\d{1,2})[-/.](\d{1,4})$")


def parse_date_headers(headers):
    """Find the date columns of an imported CSV. Returns {header: date}.

    Accepts YYYY-MM-DD (what the export writes) and the spreadsheet styles
    DD-MM-YYYY / MM-DD-YYYY, with "-", "/" or "." as separator. Year-last
    dates are read day-first unless the file itself proves otherwise (a
    second number above 12 and never a first number above 12).
    """
    parts = {}
    for header in headers:
        match = DATE_HEADER_RE.match((header or "").strip())
        if match:
            parts[header] = tuple(int(group) for group in match.groups())

    year_last = [p for p in parts.values() if p[0] <= 31]
    month_first = any(b > 12 for _, b, _ in year_last) and not any(
        a > 12 for a, _, _ in year_last
    )

    dates = {}
    for header, (a, b, c) in parts.items():
        if a > 31:
            year, month, day = a, b, c
        elif month_first:
            year, month, day = c, a, b
        else:
            year, month, day = c, b, a
        if year < 1900:
            continue
        try:
            dates[header] = date(year, month, day)
        except ValueError:
            continue
    return dates


HABIT_TYPE_ORDER = [choice for choice, _ in Habit.TYPE_CHOICES]
VALID_HABIT_TYPES = set(HABIT_TYPE_ORDER)


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
        # Automatically set the user when creating a habit; new habits go last
        last = Habit.objects.filter(user=self.request.user).aggregate(Max("order"))
        serializer.save(
            user=self.request.user, order=(last["order__max"] or 0) + 1
        )

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Set the display order of the user's habits.

        Expects {"order": [habit_id, ...]}; habits not listed keep their position.
        """
        ids = request.data.get("order")
        if not isinstance(ids, list) or not all(
            isinstance(i, int) and not isinstance(i, bool) for i in ids
        ):
            return Response(
                {"error": "order must be a list of habit ids"}, status=400
            )

        habits = {h.id: h for h in Habit.objects.filter(user=request.user, id__in=ids)}
        updated = []
        for position, habit_id in enumerate(ids, start=1):
            habit = habits.get(habit_id)
            if habit is not None:
                habit.order = position
                updated.append(habit)
        Habit.objects.bulk_update(updated, ["order"])

        return Response({"status": "order updated"})

    @staticmethod
    def _validate_completion_value(habit, raw):
        """Return (Decimal value, None) or (None, error message)."""
        if isinstance(raw, bool):
            raw = int(raw)
        try:
            val = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return None, "value must be a number"

        if not val.is_finite() or val < 0:
            return None, "value must be a positive number"
        # Completion.value is DecimalField(max_digits=10, decimal_places=2)
        if val >= Decimal("100000000"):
            return None, "value is too large"

        if habit.habit_type == "boolean" and val not in (0, 1):
            return None, "value must be 0 or 1 for a yes/no habit"
        if habit.habit_type == "rating":
            max_rating = habit.max_value or 5
            if val != val.to_integral_value() or val > max_rating:
                return None, f"value must be a whole number between 0 and {max_rating}"
        if habit.habit_type == "percentage" and val > 100:
            return None, "value must be between 0 and 100"

        return val, None

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        habit = self.get_object()
        completion_date_str = request.data.get("date")  # Get date from request

        # Default to 1 for booleans
        val, error = self._validate_completion_value(
            habit, request.data.get("value", 1)
        )
        if error:
            return Response({"error": error}, status=400)

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

        # The server runs in UTC, so a user ahead of UTC can legitimately be
        # one day ahead of the server's "today" — but no further.
        if completion_date > date.today() + timedelta(days=1):
            return Response(
                {"error": "Cannot log a habit for a future date"}, status=400
            )

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
        habits = list(self.get_queryset())

        # One query for every habit's completions (instead of one per habit)
        points_by_habit = defaultdict(list)
        completions = (
            Completion.objects.filter(
                habit__in=habits, date__gte=start_date, date__lte=end_date
            )
            .order_by("date")
            .values("habit_id", "date", "value")
        )
        for completion in completions:
            points_by_habit[completion["habit_id"]].append(
                {
                    "date": completion["date"].isoformat(),
                    "value": float(completion["value"]),
                }
            )

        # Structure: { habit_type: [{ habit_name, habit_id, color, data: [{ date, value }] }] }
        result = {type_name: [] for type_name in HABIT_TYPE_ORDER}

        for habit in habits:
            data_points = points_by_habit[habit.id]

            # Only include habits that have data (and a type the charts know)
            if data_points and habit.habit_type in result:
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
        Format: First columns are habit metadata (name, type, color, icon, category, tags, unit, max_value),
        subsequent columns are dates (one per day).
        Each row contains the metadata and values for that habit on each day.
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

        # Get all habits for the user (including tags)
        habits = self.get_queryset().prefetch_related('tags', 'category').order_by("name")

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

        # Write header row (Metadata columns + Date columns)
        header = [
            "Habit Name",
            "Type",
            "Color",
            "Icon",
            "Category",
            "Tags",
            "Unit",
            "Max Value"
        ] + [d.strftime("%Y-%m-%d") for d in date_list]
        writer.writerow(header)

        # Write data rows
        for habit in habits:
            # Get all completions for this habit in the date range
            completions = Completion.objects.filter(
                habit=habit, date__gte=start_date, date__lte=end_date
            ).order_by("date")

            # Create a dictionary for quick lookup
            completion_dict = {c.date: float(c.value) for c in completions}

            # Prepare metadata
            category_name = habit.category.name if habit.category else ""
            tags_string = ":".join([tag.name for tag in habit.tags.all()])
            unit = habit.unit if habit.unit else ""
            max_value = habit.max_value if habit.max_value else ""

            # Build row: metadata followed by values for each date
            row = [
                habit.name,
                habit.habit_type,
                habit.color,  # Already in hexadecimal format (e.g., #d97706)
                habit.icon,
                category_name,
                tags_string,
                unit,
                max_value
            ]
            
            # Add completion values for each date
            for date_item in date_list:
                value = completion_dict.get(date_item, "")
                row.append(value)

            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()

        return Response({"csv_content": csv_content})

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        """
        Import habit completion data from CSV.
        Expected format matches export_csv format:
        - Columns 1-8: Habit Name, Type, Color, Icon, Category, Tags, Unit, Max Value
        - Remaining columns: Dates (YYYY-MM-DD) with completion values
        
        Creates or updates habits and their completions.
        """
        csv_content = request.data.get("csv_content")
        
        if not csv_content:
            return Response({"error": "csv_content is required"}, status=400)
        
        import csv
        import random
        from io import StringIO
        
        def generate_random_color():
            """Generate a random hex color"""
            return "#{:06x}".format(random.randint(0, 0xFFFFFF))
        
        try:
            # Detect CSV format (French uses semicolon, English uses comma)
            first_line = csv_content.split('\n')[0] if csv_content else ""
            delimiter = ';' if ';' in first_line else ','
            
            # Parse CSV content
            csv_file = StringIO(csv_content)
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            date_columns = parse_date_headers(reader.fieldnames or [])
            
            # Helper function to parse float values (handles both comma and dot as decimal separator)
            def parse_float(value_str):
                """Parse float from string, handling both French (comma) and English (dot) formats"""
                if not value_str:
                    return None
                value_str = str(value_str).strip()
                if not value_str:
                    return None
                # Replace comma with dot for French format
                value_str = value_str.replace(',', '.')
                try:
                    return float(value_str)
                except (ValueError, TypeError):
                    return None
            
            # Track statistics
            habits_created = 0
            habits_updated = 0
            completions_created = 0
            values_skipped = 0
            categories_created = 0
            tags_created = 0
            categories_cache = {}
            tags_cache = {}
            last_order = Habit.objects.filter(user=request.user).aggregate(Max("order"))
            next_order = (last_order["order__max"] or 0) + 1

            # Process each row (each row is a habit)
            for row in reader:
                # Helper function to safely get and strip string values
                def safe_get(key, default=""):
                    value = row.get(key, default)
                    # Handle cases where value might be a list (duplicate headers) or None
                    if isinstance(value, list):
                        value = value[0] if value else default
                    return str(value).strip() if value is not None else default
                
                # Extract habit metadata
                habit_name = safe_get("Habit Name")
                # A blank or unknown type falls back to yes/no rather than
                # storing a value the rest of the app cannot handle.
                habit_type = safe_get("Type", "boolean").lower()
                if habit_type not in VALID_HABIT_TYPES:
                    habit_type = "boolean"
                color = safe_get("Color")
                icon = safe_get("Icon", "calendar")
                category_name = safe_get("Category")
                tags_string = safe_get("Tags")
                unit = safe_get("Unit") or None
                max_value_str = safe_get("Max Value")
                
                if not habit_name:
                    continue  # Skip rows without habit name
                
                # Assign random color if empty
                if not color:
                    color = generate_random_color()
                
                # Parse max_value (handles both French and English formats)
                max_value = None
                if max_value_str:
                    parsed = parse_float(max_value_str)
                    if parsed is not None:
                        max_value = int(parsed)
                
                # Get or create category
                category = None
                if category_name:
                    if category_name in categories_cache:
                        category = categories_cache[category_name]
                    else:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            user=request.user
                        )
                        categories_cache[category_name] = category
                        if created:
                            categories_created += 1
                
                # Get or create habit
                habit, created = Habit.objects.get_or_create(
                    name=habit_name,
                    user=request.user,
                    defaults={
                        "habit_type": habit_type,
                        "color": color,
                        "icon": icon,
                        "category": category,
                        "unit": unit,
                        "max_value": max_value,
                        # New habits keep the order of the file, after existing ones
                        "order": next_order,
                    }
                )

                if created:
                    habits_created += 1
                    next_order += 1
                else:
                    # Update existing habit
                    habit.habit_type = habit_type
                    habit.color = color
                    habit.icon = icon
                    habit.category = category
                    habit.unit = unit
                    habit.max_value = max_value
                    habit.save()
                    habits_updated += 1
                
                # Process tags (always clear first, then add if present)
                habit.tags.clear()
                
                if tags_string:
                    tag_names = [t.strip() for t in tags_string.split(":") if t.strip()]
                    
                    for tag_name in tag_names:
                        if tag_name in tags_cache:
                            tag = tags_cache[tag_name]
                        else:
                            tag, created = Tag.objects.get_or_create(
                                name=tag_name,
                                user=request.user
                            )
                            tags_cache[tag_name] = tag
                            if created:
                                tags_created += 1
                        
                        habit.tags.add(tag)
                
                # Process completions: one column per day. Cells that are not a
                # number (notes, typos) are skipped and counted.
                pending = {}
                for key, completion_date in date_columns.items():
                    value = row.get(key)
                    # Handle value that might be a list
                    if isinstance(value, list):
                        value = value[0] if value else None
                    if not value or not str(value).strip():
                        continue  # Skip empty values

                    # Handles both French (comma) and English (dot) decimals
                    completion_value = parse_float(value)
                    if (
                        completion_value is None
                        or not math.isfinite(completion_value)
                        or not 0 <= completion_value < 100000000
                    ):
                        values_skipped += 1
                        continue
                    pending[completion_date] = completion_value

                if pending:
                    already_logged = set(
                        Completion.objects.filter(
                            habit=habit, date__in=pending.keys()
                        ).values_list("date", flat=True)
                    )
                    # One statement per habit instead of two queries per cell
                    Completion.objects.bulk_create(
                        [
                            Completion(habit=habit, date=day, value=round(amount, 2))
                            for day, amount in pending.items()
                        ],
                        update_conflicts=True,
                        unique_fields=["habit", "date"],
                        update_fields=["value"],
                    )
                    completions_created += len(pending.keys() - already_logged)

            return Response({
                "status": "success",
                "habits_created": habits_created,
                "habits_updated": habits_updated,
                "completions_created": completions_created,
                "values_skipped": values_skipped,
                "categories_created": categories_created,
                "tags_created": tags_created
            })
        
        except Exception as e:
            return Response(
                {"error": f"Failed to parse CSV: {str(e)}"},
                status=400
            )

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
        habits = list(
            self.get_queryset().select_related("category").prefetch_related("tags")
        )

        # Calculate number of days in range
        days_in_range = (end_date - start_date).days + 1

        # Bulk-fetch all completions for every habit in one query instead of
        # querying per habit (eliminates N+1 — previously one query per habit
        # plus one query per day for streak calculation).
        all_completions = Completion.objects.filter(
            habit__in=habits,
            date__gte=start_date,
            date__lte=end_date,
            value__gt=0,
        ).values("habit_id", "date", "value")

        completions_by_habit = defaultdict(list)
        for c in all_completions:
            completions_by_habit[c["habit_id"]].append(c)

        # The current streak can start before the range, so it needs every
        # completion date of the yes/no habits up to the end of the range.
        boolean_habits = [h for h in habits if h.habit_type == "boolean"]
        dates_until_end = defaultdict(set)
        for habit_id, completion_date in Completion.objects.filter(
            habit__in=boolean_habits, date__lte=end_date, value__gt=0
        ).values_list("habit_id", "date"):
            dates_until_end[habit_id].add(completion_date)

        # Structure: { habit_type: [{ habit_name, color, metrics }] }
        result = {type_name: [] for type_name in HABIT_TYPE_ORDER}

        # Habits with no entry in the range are included too (with zeroed
        # metrics): a habit that was ignored should show as 0%, not vanish.
        for habit in habits:
            if habit.habit_type not in result:
                continue  # legacy rows with an invalid type
            habit_completions = completions_by_habit[habit.id]
            completion_count = len(habit_completions)
            values = [float(c["value"]) for c in habit_completions]

            # Calculate metrics based on habit type
            if habit.habit_type == "boolean":
                completed_dates = {c["date"] for c in habit_completions}
                metrics = {
                    "total_completions": completion_count,
                    "completion_rate": round(
                        (completion_count / days_in_range) * 100, 1
                    ),
                    "days_in_range": days_in_range,
                    "current_streak": self._calculate_current_streak(
                        dates_until_end[habit.id], end_date
                    ),
                    "best_streak": self._calculate_streak(
                        completed_dates, start_date, end_date
                    ),
                }
            elif habit.habit_type == "counter":
                metrics = {
                    "total": sum(values),
                    "average": round(sum(values) / days_in_range, 1),
                    "max": max(values, default=0),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                }
            elif habit.habit_type == "value":
                metrics = {
                    "total": round(sum(values), 1),
                    "average": round(sum(values) / len(values), 1) if values else 0,
                    "max_value": round(max(values, default=0), 1),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                    "unit": habit.unit,
                }
            elif habit.habit_type == "rating":
                metrics = {
                    "average": round(sum(values) / len(values), 1) if values else 0,
                    "max": int(max(values, default=0)),
                    "min": int(min(values, default=0)),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
                    "max_value": habit.max_value,
                }
            elif habit.habit_type == "percentage":
                metrics = {
                    "average": round(sum(values) / len(values), 1) if values else 0,
                    "max": round(max(values, default=0), 1),
                    "min": round(min(values, default=0), 1),
                    "days_tracked": completion_count,
                    "days_in_range": days_in_range,
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

    def _calculate_streak(self, completed_dates, start_date, end_date):
        """Calculate the max streak from a pre-fetched set of boolean completion dates.

        Accepts a set of date objects so no database queries are made here.
        """
        current_date = start_date
        streak = 0
        max_streak = 0
        while current_date <= end_date:
            if current_date in completed_dates:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
            current_date += timedelta(days=1)
        return max_streak

    def _calculate_current_streak(self, completed_dates, end_date):
        """Count the consecutive completed days leading up to end_date.

        A streak is still alive if end_date itself is not done yet (the day
        is not over), so counting then starts from the day before.
        """
        current_date = end_date
        if current_date not in completed_dates:
            current_date -= timedelta(days=1)
        streak = 0
        while current_date in completed_dates:
            streak += 1
            current_date -= timedelta(days=1)
        return streak


class UserInfoView(APIView):
    """
    Get current user information
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _payload(user):
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }

    def get(self, request):
        return Response(self._payload(request.user))

    def patch(self, request):
        """Change the account's email address (the only editable field)."""
        from allauth.account.models import EmailAddress

        user = request.user
        email = str(request.data.get("email") or "").strip()
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"email": ["Enter a valid email address."]}, status=400
            )

        taken = (
            User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists()
            or EmailAddress.objects.filter(email__iexact=email)
            .exclude(user=user)
            .exists()
        )
        if taken:
            return Response(
                {"email": ["A user with this email already exists."]}, status=400
            )

        user.email = email
        user.save(update_fields=["email"])
        # Login goes through allauth, which also matches its own address
        # records: without this the old address would keep working.
        EmailAddress.objects.filter(user=user).delete()
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=False)

        return Response(self._payload(user))


class DeleteAllUserDataView(APIView):
    """
    Delete all habit-related data for the current user.
    This includes: categories, tags, habits (and their completions), and correlations.
    Does NOT delete the user account, invite links, or site settings.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Count items before deletion for reporting
        categories_count = Category.objects.filter(user=user).count()
        tags_count = Tag.objects.filter(user=user).count()
        habits_count = Habit.objects.filter(user=user).count()
        correlations_count = HabitCorrelation.objects.filter(user=user).count()
        # Completions will be cascade deleted with habits
        completions_count = Completion.objects.filter(habit__user=user).count()
        
        # Delete all user data
        Category.objects.filter(user=user).delete()
        Tag.objects.filter(user=user).delete()
        HabitCorrelation.objects.filter(user=user).delete()
        # Delete habits last (will cascade delete completions)
        Habit.objects.filter(user=user).delete()
        
        return Response(
            {
                "status": "success",
                "message": "All habit data deleted successfully",
                "deleted": {
                    "categories": categories_count,
                    "tags": tags_count,
                    "habits": habits_count,
                    "completions": completions_count,
                    "correlations": correlations_count,
                }
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

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
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
        # A malformed token raises ValidationError (not a valid UUID)
        except (InviteLink.DoesNotExist, ValueError, ValidationError):
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


class ComputeRateThrottle(UserRateThrottle):
    """The correlation job is CPU-heavy: limit how often a user can trigger it."""

    scope = "compute"


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

    @action(detail=False, methods=["post"], throttle_classes=[ComputeRateThrottle])
    def compute(self, request):
        """
        Recompute the current user's correlations now, instead of waiting for
        the nightly job. Replaces the user's previous results.

        Body (optional): {"days": 90}  — how far back to look (14 to 730).
        """
        try:
            # Imported here: the scientific stack is only needed for this job
            from .management.commands.compute_correlations import (
                Command,
                DEFAULT_DAYS,
                DEFAULT_MIN_SAMPLE_SIZE,
            )
        except ImportError:
            return Response(
                {"error": "Correlation analysis is not available on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            days = int(request.data.get("days", DEFAULT_DAYS))
        except (TypeError, ValueError):
            days = DEFAULT_DAYS
        days = max(14, min(days, 730))

        # Same window as the nightly job: up to yesterday (today is not over)
        end_date = timezone.now().date() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)

        with transaction.atomic():
            # Also removes the pairs that no longer correlate
            count = Command().compute_user_correlations(
                request.user, start_date, end_date, DEFAULT_MIN_SAMPLE_SIZE
            )

        return Response(
            {
                "status": "computed",
                "correlations": count,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

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

        if not str(habit_id).isdigit():
            return Response(
                {"insights": [], "count": 0, "message": "No correlations found for this habit."}
            )

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
