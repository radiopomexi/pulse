from django.conf import settings
from django.db import models
from trainings.models import WorkoutType

class TrainingPlan(models.Model):
    name = models.CharField('Название плана', max_length=200)
    description = models.TextField('Описание', blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_plans')
    starts_on = models.DateField('Дата начала', null=True, blank=True)
    ends_on = models.DateField('Дата окончания', null=True, blank=True)
    workout_type = models.CharField('Тип тренировки', max_length=20, choices=WorkoutType.choices, default=WorkoutType.STRENGTH, blank=True)
    duration_minutes = models.IntegerField('Длительность тренировки, мин', null=True, blank=True)
    is_public = models.BooleanField('Общедоступный план', default=False, help_text='Виден в каталоге всем спортсменам.')
    strict_schedule = models.BooleanField(
        'Жёсткое расписание по дням',
        default=False,
        help_text='Включите, если план привязан к датам и выполняется в рамках периода; иначе — гибкое расписание (в любой день).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'План тренировок'
        verbose_name_plural = 'Планы тренировок'

    def __str__(self) -> str:
        return self.name

class PlanExercise(models.Model):
    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name='plan_exercises')
    exercise = models.ForeignKey('trainings.Exercise', on_delete=models.CASCADE, related_name='plan_links')
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    target_sets = models.PositiveSmallIntegerField('Подходы', default=4)
    target_reps = models.PositiveSmallIntegerField('Повторы', default=8)
    target_weight_kg = models.DecimalField('Целевой вес, кг', max_digits=7, decimal_places=2, null=True, blank=True)
    notes = models.CharField('Заметка', max_length=255, blank=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Упражнение в плане'
        verbose_name_plural = 'Упражнения в плане'

    def __str__(self) -> str:
        return f'{self.plan.name}: {self.exercise.name}'

class PlanAssignment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = ('active', 'Активен')
        COMPLETED = ('completed', 'Завершён')
        PAUSED = ('paused', 'Пауза')
    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name='assignments')
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='plan_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments_made')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Назначение плана'
        verbose_name_plural = 'Назначения планов'
        constraints = [models.UniqueConstraint(fields=['plan', 'athlete'], name='unique_plan_assignment_per_athlete')]

    def __str__(self) -> str:
        return f'{self.plan.name} → {self.athlete.email}'

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED
