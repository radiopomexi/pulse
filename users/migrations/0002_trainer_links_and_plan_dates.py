import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

def copy_trainer_athletes_to_links(apps, schema_editor):
    TrainerAthleteLink = apps.get_model('users', 'TrainerAthleteLink')
    db_table = 'users_trainerprofile_athletes'
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute(f'SELECT trainerprofile_id, customuser_id FROM {db_table}')
        except Exception:
            return
        for trainerprofile_id, customuser_id in cursor.fetchall():
            TrainerAthleteLink.objects.get_or_create(trainer_profile_id=trainerprofile_id, athlete_id=customuser_id, defaults={'confirmed': True})

def noop_reverse(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [('users', '0001_initial')]
    operations = [migrations.CreateModel(name='TrainerAthleteLink', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('confirmed', models.BooleanField(default=False, verbose_name='Подтверждено атлетом')), ('created_at', models.DateTimeField(auto_now_add=True)), ('athlete', models.ForeignKey(limit_choices_to={'role': 'athlete'}, on_delete=django.db.models.deletion.CASCADE, related_name='trainer_links', to=settings.AUTH_USER_MODEL)), ('trainer_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='athlete_links', to='users.trainerprofile'))], options={'verbose_name': 'Связь тренер — атлет', 'verbose_name_plural': 'Связи тренер — атлет'}), migrations.RunPython(copy_trainer_athletes_to_links, noop_reverse), migrations.RemoveField(model_name='trainerprofile', name='athletes'), migrations.AddField(model_name='trainerprofile', name='athletes', field=models.ManyToManyField(blank=True, related_name='trainers', through='users.TrainerAthleteLink', to=settings.AUTH_USER_MODEL, verbose_name='Подопечные')), migrations.AddConstraint(model_name='trainerathletelink', constraint=models.UniqueConstraint(fields=('trainer_profile', 'athlete'), name='unique_trainer_athlete_link'))]
