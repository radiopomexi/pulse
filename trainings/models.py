from django.conf import settings
from django.db import models

class ExerciseCategory(models.TextChoices):
    STRENGTH = ('strength', 'Сила')
    CARDIO = ('cardio', 'Кардио')
    MOBILITY = ('mobility', 'Мобильность')
    MIXED = ('mixed', 'Смешанное')

class WorkoutType(models.TextChoices):
    STRENGTH = ('strength', 'Сила')
    CARDIO = ('cardio', 'Кардио')
    FLEXIBILITY = ('flexibility', 'Гибкость')
    CIRCUIT = ('circuit', 'Круговая')
    OTHER = ('other', 'Другое')

class Exercise(models.Model):
    name = models.CharField('Название', max_length=200)
    category = models.CharField('Тип', max_length=20, choices=ExerciseCategory.choices, default=ExerciseCategory.STRENGTH)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Упражнение'
        verbose_name_plural = 'Упражнения'

    def __str__(self) -> str:
        return self.name

class WorkoutSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_sessions')
    date = models.DateField('Дата')
    title = models.CharField('Название', max_length=200, blank=True)
    notes = models.TextField('Заметки', blank=True)
    duration_minutes = models.PositiveSmallIntegerField('Длительность, мин', null=True, blank=True)
    workout_type = models.CharField('Тип тренировки', max_length=20, choices=WorkoutType.choices, default=WorkoutType.STRENGTH)
    training_plan = models.ForeignKey('plans.TrainingPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='workout_sessions', verbose_name='План')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Тренировка'
        verbose_name_plural = 'Тренировки'

    def __str__(self) -> str:
        return f'{self.user.email} — {self.date}'

    def total_tonnage(self) -> float:
        return float(sum((we.volume for we in self.workout_exercises.all())))

    @property
    def total_volume(self) -> float:
        return self.total_tonnage()

class WorkoutExercise(models.Model):
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='workout_exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name='workout_entries')
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    sets = models.PositiveSmallIntegerField('Подходы', default=3)
    reps = models.PositiveSmallIntegerField('Повторы', default=10)
    weight_kg = models.DecimalField('Вес, кг', max_digits=7, decimal_places=2, default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Упражнение в тренировке'
        verbose_name_plural = 'Упражнения в тренировке'

    def __str__(self) -> str:
        return f'{self.exercise.name} ({self.session.date})'

    @property
    def volume(self) -> float:
        return float(self.sets * self.reps * self.weight_kg)

class BodyMetric(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='body_metrics')
    date = models.DateField('Дата')
    weight_kg = models.FloatField('Вес, кг')
    body_fat_percent = models.FloatField('% жира', null=True, blank=True)
    note = models.TextField('Заметка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Замер тела'
        verbose_name_plural = 'Замеры тела'

    def __str__(self) -> str:
        return f'{self.user_id} {self.date} {self.weight_kg} кг'
