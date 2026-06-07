from django.contrib import admin
from .models import PlanAssignment, PlanExercise, TrainingPlan

class PlanExerciseInline(admin.TabularInline):
    model = PlanExercise
    extra = 0

@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'updated_at')
    search_fields = ('name', 'author__email')
    inlines = [PlanExerciseInline]

@admin.register(PlanAssignment)
class PlanAssignmentAdmin(admin.ModelAdmin):
    list_display = ('plan', 'athlete', 'status', 'created_at')
    list_filter = ('status',)
