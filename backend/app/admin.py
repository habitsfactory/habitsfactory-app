from django.contrib import admin
from .models import Habit, Completion, Category, HabitCorrelation, InviteLink

admin.site.register(Habit)
admin.site.register(Completion)
admin.site.register(Category)
admin.site.register(HabitCorrelation)
admin.site.register(InviteLink)
