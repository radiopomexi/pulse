from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Role

def _input_attrs():
    return {}

class EmailLoginForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs=_input_attrs()))
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput(attrs=_input_attrs()))
    role = forms.ChoiceField(label='Роль', choices=[(Role.ATHLETE, 'Спортсмен'), (Role.TRAINER, 'Тренер')])

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'role')

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean(self):
        data = super().clean()
        p1 = data.get('password1')
        p2 = data.get('password2')
        if p1 and p2 and (p1 != p2):
            raise ValidationError('Пароли не совпадают.')
        return data

    def save(self, commit=True):
        user: CustomUser = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data['password1'])
        if user.role == Role.TRAINER:
            user.trainer_verified = False
        else:
            user.trainer_verified = True
        if commit:
            user.save()
        return user

class ProfileEditForm(forms.ModelForm):

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'contact_info')
        labels = {'first_name': 'Имя', 'last_name': 'Фамилия', 'email': 'Email', 'contact_info': 'Контакты'}
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'pulse-pe-input', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'pulse-pe-input', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'pulse-pe-input', 'autocomplete': 'email'}),
            'contact_info': forms.TextInput(attrs={'class': 'pulse-pe-input', 'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact_info'].widget.attrs.setdefault('placeholder', 'Телефон, Telegram, ссылка…')
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise ValidationError('Этот email уже занят.')
        return email

    def save(self, commit=True):
        user: CustomUser = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user
