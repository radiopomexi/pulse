from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0007_alter_trainingplan_workout_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingplan',
            name='is_public',
            field=models.BooleanField(default=False, help_text='Виден в каталоге всем спортсменам.', verbose_name='Общедоступный план'),
        ),
    ]
