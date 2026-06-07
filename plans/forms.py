from __future__ import annotations
from django import forms
from django.core.exceptions import ValidationError
from trainings.models import WorkoutType
from .models import TrainingPlan

class TrainingPlanMetaForm(forms.ModelForm):

    class Meta:
        model = TrainingPlan
        fields = ('name', 'description', 'starts_on', 'ends_on', 'workout_type', 'duration_minutes', 'is_public', 'strict_schedule')
        widgets = {
            'starts_on': forms.DateInput(attrs={'type': 'date'}),
            'ends_on': forms.DateInput(attrs={'type': 'date'}),
            'workout_type': forms.Select(),
            'duration_minutes': forms.NumberInput(attrs={'min': 1, 'max': 600, 'step': 1, 'inputmode': 'numeric'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'plan-public-toggle__input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wt = self.fields['workout_type']
        wt.required = False
        wt.choices = [('', 'Не указан')] + list(WorkoutType.choices)
        self.fields['starts_on'].required = False
        self.fields['ends_on'].required = False
        self.fields['is_public'].label = False
        ss = self.fields['strict_schedule']
        ss.widget = forms.RadioSelect(
            choices=[
                (False, 'Гибкое расписание — выполнение в любой день, многократно'),
                (True, 'Жёсткое расписание — в рамках дат начала и окончания'),
            ]
        )
        ss.label = ''

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('starts_on')
        end = cleaned.get('ends_on')
        if start and end and end < start:
            self.add_error('ends_on', 'Дата окончания не может быть раньше даты начала.')
        if cleaned.get('strict_schedule') and not (start and end):
            raise ValidationError('При жёстком расписании укажите дату начала и дату окончания.')
        return cleaned
