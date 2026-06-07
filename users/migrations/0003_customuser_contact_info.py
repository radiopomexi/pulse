from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('users', '0002_trainer_links_and_plan_dates')]
    operations = [migrations.AddField(model_name='customuser', name='contact_info', field=models.CharField(blank=True, help_text='Телефон, Telegram и т.п.', max_length=255, verbose_name='Контакты'))]
