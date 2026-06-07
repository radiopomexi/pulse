from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0008_trainingplan_is_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingplan',
            name='strict_schedule',
            field=models.BooleanField(
                default=False,
                verbose_name='Жёсткое расписание по дням',
                help_text='Если включено — план привязан к датам; иначе можно выполнять в любой день.',
            ),
        ),
    ]
