from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('plans', '0002_initial')]
    operations = [migrations.AddField(model_name='planexercise', name='target_weight_kg', field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Целевой вес, кг')), migrations.AddField(model_name='trainingplan', name='ends_on', field=models.DateField(blank=True, null=True, verbose_name='Дата окончания')), migrations.AddField(model_name='trainingplan', name='starts_on', field=models.DateField(blank=True, null=True, verbose_name='Дата начала'))]
