from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    ADMIN = ('admin', 'Администратор')
    MODERATOR = ('moderator', 'Модератор')
    TRAINER = ('trainer', 'Тренер')
    ATHLETE = ('athlete', 'Спортсмен')

class CustomUser(AbstractUser):
    email = models.EmailField('Email', unique=True)
    role = models.CharField('Роль', max_length=20, choices=Role.choices, default=Role.ATHLETE)
    trainer_verified = models.BooleanField('Тренер подтверждён', default=True, help_text='Для тренеров: доступ после подтверждения администратором.')
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    contact_info = models.CharField('Контакты', max_length=255, blank=True, help_text='Телефон, Telegram и т.п.')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        return self.email

    def sync_role_group(self) -> None:
        from django.contrib.auth.models import Group
        mapping = {Role.ADMIN: 'pulse_admin', Role.MODERATOR: 'pulse_moderator', Role.TRAINER: 'pulse_trainer', Role.ATHLETE: 'pulse_athlete'}
        group_name = mapping.get(self.role)
        if not group_name:
            return
        group, _ = Group.objects.get_or_create(name=group_name)
        self.groups.clear()
        self.groups.add(group)

    def save(self, *args, **kwargs):
        if self.role != Role.TRAINER:
            self.trainer_verified = True
        super().save(*args, **kwargs)
        if self.pk:
            self.sync_role_group()

    @property
    def display_role(self) -> str:
        return self.get_role_display()

    def is_elevated_staff(self) -> bool:
        return self.is_superuser or self.role in (Role.ADMIN, Role.MODERATOR)

    def can_access_trainer_features(self) -> bool:
        return self.role == Role.TRAINER and self.trainer_verified

    def is_blocked_trainer(self) -> bool:
        return self.role == Role.TRAINER and (not self.trainer_verified)

class TrainerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='trainer_profile', limit_choices_to={'role': Role.TRAINER})
    athletes = models.ManyToManyField(CustomUser, through='TrainerAthleteLink', related_name='trainers', blank=True, verbose_name='Подопечные')
    bio = models.TextField('О себе', blank=True)

    class Meta:
        verbose_name = 'Профиль тренера'
        verbose_name_plural = 'Профили тренеров'

    def __str__(self) -> str:
        return f'Тренер: {self.user.get_full_name() or self.user.email}'

class TrainerAthleteLink(models.Model):
    trainer_profile = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='athlete_links')
    athlete = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='trainer_links', limit_choices_to={'role': Role.ATHLETE})
    confirmed = models.BooleanField('Подтверждено атлетом', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Связь тренер — атлет'
        verbose_name_plural = 'Связи тренер — атлет'
        constraints = [models.UniqueConstraint(fields=['trainer_profile', 'athlete'], name='unique_trainer_athlete_link')]

    def __str__(self) -> str:
        return f'{self.trainer_profile.user.email} → {self.athlete.email}'
