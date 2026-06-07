from django.contrib import admin
from .models import BodyMetric, Exercise, WorkoutExercise, WorkoutSession

class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 0

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'title', 'workout_type', 'training_plan', 'duration_minutes')
    list_filter = ('date', 'workout_type')
    search_fields = ('user__email', 'title')
    inlines = [WorkoutExerciseInline]

@admin.register(WorkoutExercise)
class WorkoutExerciseAdmin(admin.ModelAdmin):
    list_display = ('session', 'exercise', 'sets', 'reps', 'weight_kg')

@admin.register(BodyMetric)
class BodyMetricAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight_kg', 'body_fat_percent', 'created_at')
    list_filter = ('date',)
    search_fields = ('user__email',)
