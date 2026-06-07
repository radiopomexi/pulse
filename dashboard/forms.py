from django import forms
from trainings.models import BodyMetric, WorkoutType

class QuickSessionForm(forms.Form):
    date = forms.DateField(label='Дата', widget=forms.DateInput(attrs={'type': 'date'}))
    title = forms.CharField(label='Название', max_length=200, required=False)
    duration_minutes = forms.IntegerField(label='Длительность, мин', min_value=1, max_value=600, required=False)
    workout_type = forms.ChoiceField(label='Тип тренировки', choices=WorkoutType.choices, initial=WorkoutType.STRENGTH)

class BodyMetricForm(forms.ModelForm):

    class Meta:
        model = BodyMetric
        fields = ('date', 'weight_kg', 'body_fat_percent', 'note')
        labels = {'date': 'Дата', 'weight_kg': 'Вес, кг', 'body_fat_percent': '% жира (необязательно)', 'note': 'Заметка'}
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}), 'weight_kg': forms.NumberInput(attrs={'step': '0.1', 'min': '20', 'max': '400', 'inputmode': 'decimal'}), 'body_fat_percent': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '80', 'inputmode': 'decimal', 'placeholder': '—'}), 'note': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body_fat_percent'].required = False
        self.fields['note'].required = False

    def clean(self):
        cleaned = super().clean()
        bf = cleaned.get('body_fat_percent')
        if bf == '':
            cleaned['body_fat_percent'] = None
        return cleaned

class CalculatorForm(forms.Form):
    sex = forms.ChoiceField(label='Пол', choices=[('m', 'Мужской'), ('f', 'Женский')])
    age = forms.IntegerField(label='Возраст, лет', min_value=14, max_value=100)
    height_cm = forms.DecimalField(label='Рост, см', min_value=100, max_value=250, max_digits=5, decimal_places=1)
    weight_kg = forms.DecimalField(label='Вес, кг', min_value=30, max_value=300, max_digits=5, decimal_places=1)
    activity = forms.ChoiceField(label='Активность', choices=[('1.2', 'Минимальная (сидячий образ жизни)'), ('1.375', 'Лёгкая (1–3 тренировки в неделю)'), ('1.55', 'Умеренная (3–5 тренировок)'), ('1.725', 'Высокая (6–7 тренировок)'), ('1.9', 'Очень высокая (физический труд + спорт)')], initial='1.375')
