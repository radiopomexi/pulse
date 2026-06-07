from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_customuser_contact_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='avatar_data',
            field=models.BinaryField(blank=True, null=True, verbose_name='Данные аватара'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='avatar_content_type',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Тип аватара'),
        ),
    ]
