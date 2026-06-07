from django.core.management.base import BaseCommand

from trainings.exercise_catalog import EXERCISES
from trainings.models import Exercise


class Command(BaseCommand):
    help = 'Заполняет каталог упражнений для планов и тренировок (идемпотентно).'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name, category, description in EXERCISES:
            exercise, was_created = Exercise.objects.get_or_create(
                name=name,
                defaults={'category': category, 'description': description},
            )
            if was_created:
                created += 1
                continue
            fields_to_update: list[str] = []
            if exercise.category != category:
                exercise.category = category
                fields_to_update.append('category')
            if description and not exercise.description:
                exercise.description = description
                fields_to_update.append('description')
            if fields_to_update:
                exercise.save(update_fields=fields_to_update)
                updated += 1
        total = Exercise.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Каталог упражнений: +{created} новых, {updated} обновлено, всего {total}.'
            )
        )
