from django.core.management.base import BaseCommand

from users.models import CustomUser, Role


class Command(BaseCommand):
    help = 'Создаёт или обновляет production-админа (идемпотентно).'

    def handle(self, *args, **options):
        email = 'admin@pulse.demo'
        password = 'PulseAdmin2026!'
        user = CustomUser.objects.filter(email=email).first()
        created = False
        if user is None:
            user = CustomUser.objects.filter(username=email).first()
        if user is None:
            user = CustomUser(
                email=email,
                username=email,
                first_name='Admin',
                last_name='Pulse',
            )
            created = True
        user.set_password(password)
        user.role = Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.trainer_verified = True
        user.save()
        verb = 'Создан' if created else 'Обновлён'
        self.stdout.write(self.style.SUCCESS(f'{verb} админ: {email}'))
