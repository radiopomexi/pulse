from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0005_default_duration_minutes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='trainingplan',
            old_name='default_duration_minutes',
            new_name='duration_minutes',
        ),
        migrations.AlterField(
            model_name='trainingplan',
            name='duration_minutes',
            field=models.IntegerField(blank=True, null=True, verbose_name='Длительность тренировки, мин'),
        ),
    ]
