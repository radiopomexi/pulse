from __future__ import annotations
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from plans.models import PlanAssignment, PlanExercise, TrainingPlan
from trainings.models import BodyMetric, Exercise, ExerciseCategory, WorkoutExercise, WorkoutSession, WorkoutType
from users.models import CustomUser, Role, TrainerAthleteLink, TrainerProfile

NUM_BULK_TRAINERS = 40
NUM_BULK_ATHLETES = 96
BULK_PASSWORD = 'demo123'

TRAINER_IDENTITY = [
    ('Илья', 'Козлов'), ('Дарья', 'Орлова'), ('Семён', 'Волков'), ('Алина', 'Морозова'), ('Григорий', 'Соколов'), ('Ксения', 'Лебедева'),
    ('Марк', 'Новиков'), ('Полина', 'Зайцева'), ('Артём', 'Белов'), ('Ева', 'Комарова'), ('Никита', 'Павлов'), ('Мария', 'Семёнова'),
    ('Олег', 'Голубев'), ('Татьяна', 'Виноградова'), ('Роман', 'Богданов'), ('Юлия', 'Фёдорова'), ('Вадим', 'Михайлов'),
    ('Оксана', 'Алексеева'), ('Денис', 'Егоров'), ('Виктория', 'Макарова'), ('Станислав', 'Романов'), ('Кристина', 'Киселёва'),
    ('Матвей', 'Андреев'), ('Софья', 'Жукова'), ('Тимофей', 'Захаров'), ('Вероника', 'Степанова'), ('Арсений', 'Николаев'),
    ('Диана', 'Крылова'), ('Платон', 'Максимов'), ('Алиса', 'Сорокина'), ('Глеб', 'Винокуров'), ('Ярослав', 'Ковалёв'),
]

ATHLETE_IDENTITY = [
    ('Андрей', 'Смирнов'), ('Борис', 'Иванов'), ('Виктор', 'Кузнецов'), ('Глеб', 'Попов'), ('Дмитрий', 'Васильев'), ('Егор', 'Петров'),
    ('Жанна', 'Соколова'), ('Захар', 'Михайлов'), ('Игорь', 'Новиков'), ('Кирилл', 'Фёдоров'), ('Лев', 'Морозов'), ('Максим', 'Волков'),
    ('Нина', 'Алексеева'), ('Ольга', 'Егорова'), ('Павел', 'Лебедев'), ('Руслан', 'Семёнов'), ('Сергей', 'Голубев'), ('Тимур', 'Виноградов'),
    ('Ульяна', 'Богданова'), ('Фёдор', 'Комаров'), ('Ярослав', 'Зайцев'), ('Антон', 'Павлов'), ('Валерия', 'Белова'), ('Георгий', 'Орлов'),
    ('Даниил', 'Козлов'), ('Елисей', 'Соловьёв'), ('Илья', 'Крылов'), ('Константин', 'Титов'), ('Лариса', 'Кузьмина'), ('Милана', 'Жукова'),
    ('Николай', 'Орехов'), ('Олег', 'Дьяков'), ('Платон', 'Баранов'), ('Регина', 'Зыкова'), ('Степан', 'Гуляев'), ('Тамара', 'Рябова'),
    ('Устин', 'Соболев'), ('Феликс', 'Рябов'), ('Эдуард', 'Поляков'), ('Яна', 'Цветкова'), ('Арсений', 'Данилов'), ('Богдан', 'Журавлёв'),
    ('Вера', 'Королёва'), ('Галина', 'Грачёва'), ('Диана', 'Одинцова'), ('Евгений', 'Сазонов'), ('Злата', 'Панкратова'), ('Инна', 'Рогова'),
    ('Клим', 'Маслов'), ('Лидия', 'Орлова'), ('Мирон', 'Сидоров'), ('Надежда', 'Фролова'), ('Оксана', 'Тихонова'), ('Пётр', 'Мартынов'),
    ('Роман', 'Антонов'), ('Светлана', 'Зайцева'), ('Тарас', 'Бондаренко'), ('Ульяна', 'Мельник'), ('Филипп', 'Шевченко'), ('Элина', 'Павленко'),
]

PLAN_TEMPLATES = [
    'Цикл силы · 4 недели', 'Объём и техника', 'Жиросжигание + база', 'Мобильность и СС', 'Гиревой спринт', 'Ноги и задняя цепь',
    'Верх: жим и тяга', 'Кардио-ритм недели', 'Делoad и восстановление', 'Пресс и кор · мини-блок', 'Старт: линейная прогрессия',
    'Интервалы на дорожке', 'Йога-флоу для спины', 'Силовой полный сплит', 'Круговая 20 мин', 'Тяга и стабилизация лопаток',
    'Приседы и выпады · блок', 'Кардио + кор', 'Восстановление после соревнований', 'Микроцикл силы',
]

WORKOUT_ROTATION = (
    WorkoutType.STRENGTH,
    WorkoutType.STRENGTH,
    WorkoutType.CARDIO,
    WorkoutType.FLEXIBILITY,
    WorkoutType.CIRCUIT,
    WorkoutType.STRENGTH,
)

DURATION_ROTATION = (28, 35, 40, 45, 50, 55, 60, 65, 72, 85, 95)


def _pick_workout_type(seed: int) -> str:
    return WORKOUT_ROTATION[seed % len(WORKOUT_ROTATION)]


def _pick_duration_minutes(seed: int) -> int:
    return DURATION_ROTATION[seed % len(DURATION_ROTATION)]


def _pick_workout_type_for_session(offset: int, salt: int) -> str:
    cycle = [WorkoutType.STRENGTH, WorkoutType.STRENGTH, WorkoutType.CARDIO, WorkoutType.FLEXIBILITY, WorkoutType.CIRCUIT]
    return cycle[(offset + salt) % len(cycle)]


def _seed_workouts_for_user(user: CustomUser, exercises: list[Exercise], today, salt: int, density: int = 6, days: int = 90):
    WorkoutSession.objects.filter(user=user).delete()
    for offset in range(days):
        d = today - timedelta(days=offset)
        if (salt + offset * 3) % density == 0:
            continue
        if d.weekday() >= 5 and (salt + offset) % 4 != 0:
            continue
        wtype = _pick_workout_type_for_session(offset, salt)
        title = {
            WorkoutType.STRENGTH: 'Силовой цикл',
            WorkoutType.CARDIO: 'Кардио',
            WorkoutType.FLEXIBILITY: 'Мобильность',
            WorkoutType.CIRCUIT: 'Круговая',
        }.get(wtype, 'Тренировка')
        session = WorkoutSession.objects.create(
            user=user,
            date=d,
            title=title,
            duration_minutes=35 + (offset + salt) % 50,
            workout_type=wtype,
        )
        n_ex = 3 + (offset + salt) % 4
        picks = exercises[:n_ex] if len(exercises) >= n_ex else exercises
        for idx, ex in enumerate(picks):
            WorkoutExercise.objects.create(
                session=session,
                exercise=ex,
                order=idx,
                sets=3 + (idx + salt) % 3,
                reps=6 + (idx + offset) % 6,
                weight_kg=25 + offset * 1.1 + idx * 4 + salt % 15,
            )


def _create_plan_with_exercises(
    author: CustomUser,
    name: str,
    description: str,
    exercises: list[Exercise],
    today,
    start_shift: int,
    duration_days: int,
    *,
    is_public: bool = False,
    workout_type: str = '',
    duration_minutes: int | None = None,
    strict_schedule: bool = False,
) -> TrainingPlan:
    plan, _ = TrainingPlan.objects.get_or_create(author=author, name=name, defaults={'description': description})
    plan.description = description
    plan.starts_on = today - timedelta(days=start_shift)
    plan.ends_on = today + timedelta(days=duration_days)
    plan.is_public = is_public
    plan.workout_type = workout_type or ''
    plan.duration_minutes = duration_minutes
    plan.strict_schedule = strict_schedule
    plan.save(
        update_fields=[
            'description',
            'starts_on',
            'ends_on',
            'is_public',
            'workout_type',
            'duration_minutes',
            'strict_schedule',
        ]
    )
    plan.plan_exercises.all().delete()
    subset = exercises[: 5 + (author.pk or 0) % 4]
    weights = [35, 50, 70, 45, 30, 55, 40, 60, 42]
    for idx, ex in enumerate(subset):
        PlanExercise.objects.create(
            plan=plan,
            exercise=ex,
            order=idx,
            target_sets=3 + idx % 2,
            target_reps=6 + idx % 3 * 2,
            target_weight_kg=weights[idx % len(weights)] if idx < len(weights) else None,
        )
    return plan


def _stagger_public_plan_timestamps() -> None:
    """Разносит updated_at у публичных планов — в каталоге виден «живой» порядок."""
    qs = TrainingPlan.objects.filter(is_public=True).order_by('id')
    plans = list(qs)
    if not plans:
        return
    base = timezone.now()
    chunk: list[TrainingPlan] = []
    for i, p in enumerate(plans):
        p.updated_at = base - timedelta(hours=(i * 11) % (24 * 120))
        chunk.append(p)
        if len(chunk) >= 80:
            TrainingPlan.objects.bulk_update(chunk, ['updated_at'])
            chunk = []
    if chunk:
        TrainingPlan.objects.bulk_update(chunk, ['updated_at'])


class Command(BaseCommand):
    help = 'Создаёт демо-пользователей и тренировочные данные для Pulse (в т.ч. массовую активность и каталог планов).'

    def handle(self, *args, **options):
        self.stdout.write('Создание демо-данных Pulse…')
        admin_user, _ = CustomUser.objects.get_or_create(
            email='admin@pulse.demo',
            defaults={
                'username': 'admin@pulse.demo',
                'first_name': 'Alex',
                'last_name': 'Admin',
                'role': Role.ADMIN,
                'trainer_verified': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin_user.set_password('admin123')
        admin_user.role = Role.ADMIN
        admin_user.trainer_verified = True
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        mod_names = [('Ирина', 'Модерова'), ('Сергей', 'Надзоров'), ('Елена', 'Поддержкина')]
        for mi, (fn, ln) in enumerate(mod_names):
            mod, _ = CustomUser.objects.get_or_create(
                email=f'mod{mi}@pulse.demo',
                defaults={
                    'username': f'mod{mi}@pulse.demo',
                    'first_name': fn,
                    'last_name': ln,
                    'role': Role.MODERATOR,
                    'trainer_verified': False,
                    'is_staff': True,
                    'is_superuser': False,
                },
            )
            mod.set_password('mod123')
            mod.role = Role.MODERATOR
            mod.is_staff = True
            mod.is_superuser = False
            mod.trainer_verified = False
            mod.save()

        coach, _ = CustomUser.objects.get_or_create(
            email='coach@pulse.demo',
            defaults={
                'username': 'coach@pulse.demo',
                'first_name': 'Mira',
                'last_name': 'Coach',
                'role': Role.TRAINER,
                'trainer_verified': True,
            },
        )
        coach.set_password('coach123')
        coach.role = Role.TRAINER
        coach.trainer_verified = True
        coach.save()
        athlete, _ = CustomUser.objects.get_or_create(
            email='athlete@pulse.demo',
            defaults={
                'username': 'athlete@pulse.demo',
                'first_name': 'Leo',
                'last_name': 'Athlete',
                'role': Role.ATHLETE,
            },
        )
        athlete.set_password('athlete123')
        athlete.role = Role.ATHLETE
        athlete.save()
        profile, _ = TrainerProfile.objects.get_or_create(user=coach)
        TrainerAthleteLink.objects.update_or_create(trainer_profile=profile, athlete=athlete, defaults={'confirmed': True})

        exercises_data = [
            ('Жим лёжа', ExerciseCategory.STRENGTH),
            ('Присед со штангой', ExerciseCategory.STRENGTH),
            ('Становая тяга', ExerciseCategory.STRENGTH),
            ('Тяга верхнего блока', ExerciseCategory.STRENGTH),
            ('Жим гантелей сидя', ExerciseCategory.STRENGTH),
            ('Подтягивания', ExerciseCategory.STRENGTH),
            ('Выпады с гантелями', ExerciseCategory.STRENGTH),
            ('Отжимания на брусьях', ExerciseCategory.STRENGTH),
            ('Румынская тяга', ExerciseCategory.STRENGTH),
            ('Жим стоя', ExerciseCategory.STRENGTH),
            ('Планка', ExerciseCategory.MOBILITY),
            ('Беговая дорожка', ExerciseCategory.CARDIO),
            ('Эллипс', ExerciseCategory.CARDIO),
            ('Велоэргометр', ExerciseCategory.CARDIO),
            ('Скакалка', ExerciseCategory.CARDIO),
            ('Бёрпи', ExerciseCategory.STRENGTH),
            ('Растяжка спины', ExerciseCategory.MOBILITY),
            ('Ягодичный мост', ExerciseCategory.STRENGTH),
        ]
        exercises: list[Exercise] = []
        for name, cat in exercises_data:
            ex, _ = Exercise.objects.get_or_create(name=name, defaults={'category': cat})
            exercises.append(ex)

        today = timezone.localdate()
        WorkoutSession.objects.filter(user=athlete).delete()
        BodyMetric.objects.filter(user=athlete).delete()
        for offset in range(48):
            d = today - timedelta(days=offset)
            if d.weekday() >= 5 and offset % 3 != 0:
                continue
            wtype = _pick_workout_type(offset)
            title = {
                WorkoutType.STRENGTH: 'Силовой цикл',
                WorkoutType.CARDIO: 'Кардио',
                WorkoutType.FLEXIBILITY: 'Мобильность',
                WorkoutType.CIRCUIT: 'Круговая',
            }.get(wtype, 'Тренировка')
            session = WorkoutSession.objects.create(
                user=athlete,
                date=d,
                title=title,
                duration_minutes=50 + offset % 5 * 5,
                workout_type=wtype,
            )
            picks = exercises[: 4 + offset % 4]
            for idx, ex in enumerate(picks):
                WorkoutExercise.objects.create(
                    session=session,
                    exercise=ex,
                    order=idx,
                    sets=4,
                    reps=8 + idx % 2 * 2,
                    weight_kg=40 + offset * 0.6 + idx * 5,
                )
        WorkoutSession.objects.filter(user=coach).delete()
        for offset in (0, 1, 2, 3, 5, 7, 10, 14, 21, 28):
            d = today - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            s = WorkoutSession.objects.create(
                user=coach,
                date=d,
                title='Своя тренировка',
                workout_type=WorkoutType.STRENGTH,
                duration_minutes=48 + offset % 6,
            )
            for idx, ex in enumerate(exercises[:4]):
                WorkoutExercise.objects.create(session=s, exercise=ex, order=idx, sets=3, reps=10, weight_kg=50 + idx * 10)
        base_w = 82.5
        for i in range(16):
            d = today - timedelta(weeks=15 - i)
            BodyMetric.objects.create(
                user=athlete,
                date=d,
                weight_kg=round(base_w - i * 0.35 + i % 3 * 0.2, 2),
                body_fat_percent=round(16.0 - i * 0.08, 1) if i % 2 == 0 else None,
                note='Демо-замер' if i == 0 else '',
            )

        plan, _ = TrainingPlan.objects.get_or_create(
            author=coach,
            name='Цикл силы · 4 недели',
            defaults={'description': 'Базовые движения, прогрессия по RPE.'},
        )
        plan.description = 'Базовые движения, прогрессия по RPE. Публичный план в каталоге.'
        plan.starts_on = today - timedelta(days=14)
        plan.ends_on = today + timedelta(days=70)
        plan.is_public = True
        plan.workout_type = WorkoutType.STRENGTH
        plan.duration_minutes = 55
        plan.strict_schedule = False
        plan.save(
            update_fields=[
                'description',
                'starts_on',
                'ends_on',
                'is_public',
                'workout_type',
                'duration_minutes',
                'strict_schedule',
            ]
        )
        plan.plan_exercises.all().delete()
        weights = [60, 80, 100, 45, 25]
        for idx, ex in enumerate(exercises[:5]):
            PlanExercise.objects.create(
                plan=plan,
                exercise=ex,
                order=idx,
                target_sets=4,
                target_reps=8,
                target_weight_kg=weights[idx] if idx < len(weights) else None,
            )
        PlanAssignment.objects.update_or_create(
            plan=plan,
            athlete=athlete,
            defaults={'assigned_by': coach, 'status': PlanAssignment.Status.ACTIVE},
        )

        bulk_trainer_q = Q(email__startswith='bulk-trainer-') & Q(email__endswith='@pulse.demo')
        bulk_athlete_q = Q(email__startswith='bulk-athlete-') & Q(email__endswith='@pulse.demo')
        bulk_trainer_ids = list(CustomUser.objects.filter(bulk_trainer_q).values_list('pk', flat=True))
        bulk_athlete_ids = list(CustomUser.objects.filter(bulk_athlete_q).values_list('pk', flat=True))
        if bulk_trainer_ids:
            TrainingPlan.objects.filter(author_id__in=bulk_trainer_ids).delete()
        if bulk_athlete_ids:
            PlanAssignment.objects.filter(athlete_id__in=bulk_athlete_ids).delete()
            BodyMetric.objects.filter(user_id__in=bulk_athlete_ids).delete()
        WorkoutSession.objects.filter(Q(user_id__in=bulk_trainer_ids) | Q(user_id__in=bulk_athlete_ids)).delete()

        bulk_trainers: list[CustomUser] = []
        for i in range(NUM_BULK_TRAINERS):
            fn, ln = TRAINER_IDENTITY[i % len(TRAINER_IDENTITY)]
            email = f'bulk-trainer-{i:02d}@pulse.demo'
            u, _ = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': fn,
                    'last_name': ln,
                    'role': Role.TRAINER,
                    'trainer_verified': True,
                },
            )
            u.set_password(BULK_PASSWORD)
            u.role = Role.TRAINER
            u.trainer_verified = True
            u.save()
            TrainerProfile.objects.get_or_create(user=u)
            bulk_trainers.append(u)

        bulk_athletes: list[CustomUser] = []
        for i in range(NUM_BULK_ATHLETES):
            fn, ln = ATHLETE_IDENTITY[i % len(ATHLETE_IDENTITY)]
            email = f'bulk-athlete-{i:02d}@pulse.demo'
            u, _ = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': fn,
                    'last_name': ln,
                    'role': Role.ATHLETE,
                },
            )
            u.set_password(BULK_PASSWORD)
            u.role = Role.ATHLETE
            u.save()
            bulk_athletes.append(u)

        for ai, ath in enumerate(bulk_athletes):
            n_links = 3 + ai % 4
            for k in range(n_links):
                ti = (ai + k * 7 + k * k) % len(bulk_trainers)
                tp = bulk_trainers[ti].trainer_profile
                TrainerAthleteLink.objects.update_or_create(
                    trainer_profile=tp,
                    athlete=ath,
                    defaults={'confirmed': True},
                )
        for ai in range(0, len(bulk_athletes), 3):
            TrainerAthleteLink.objects.update_or_create(
                trainer_profile=profile,
                athlete=bulk_athletes[ai],
                defaults={'confirmed': True},
            )

        plans_created = 0
        assignments_created = 0
        for ti, tr in enumerate(bulk_trainers):
            n_plans = 8 + ti % 4
            for pi in range(n_plans):
                tmpl = PLAN_TEMPLATES[(ti + pi * 2) % len(PLAN_TEMPLATES)]
                initials = f"{(tr.first_name or 'T')[:1]}{(tr.last_name or 'R')[:1]}"
                name = f'{tmpl} · {initials}-T{ti:02d}-{pi + 1}'
                desc = (
                    f'Автор: {tr.get_full_name() or tr.email}. План {pi + 1} из серии. '
                    f'Подходит для регулярных тренировок в зале или дома с минимальным оборудованием.'
                )
                seed = ti * 20 + pi * 3
                wt = _pick_workout_type(seed)
                dur = _pick_duration_minutes(seed + ti)
                is_public = pi < 5
                strict = is_public and (ti + pi) % 9 == 0
                p = _create_plan_with_exercises(
                    tr,
                    name,
                    desc,
                    exercises,
                    today,
                    start_shift=8 + (ti + pi) * 2,
                    duration_days=40 + (ti + pi) % 6 * 12,
                    is_public=is_public,
                    workout_type=wt,
                    duration_minutes=dur,
                    strict_schedule=strict,
                )
                plans_created += 1
                n_assign = 4 + (ti + pi) % 5
                for off in range(n_assign):
                    ai = (ti * 11 + pi * 5 + off * 17) % len(bulk_athletes)
                    ath = bulk_athletes[ai]
                    if not TrainerAthleteLink.objects.filter(trainer_profile=tr.trainer_profile, athlete=ath, confirmed=True).exists():
                        continue
                    _, created = PlanAssignment.objects.get_or_create(
                        plan=p,
                        athlete=ath,
                        defaults={'assigned_by': tr, 'status': PlanAssignment.Status.ACTIVE},
                    )
                    if created:
                        assignments_created += 1
                    else:
                        PlanAssignment.objects.filter(plan=p, athlete=ath).update(
                            status=PlanAssignment.Status.ACTIVE,
                            assigned_by=tr,
                        )

        coach_extra_templates = [
            'Старт сезона · coach',
            'Средний блок объёма',
            'Сушка: сила+шаг',
            'Восстановительная неделя',
            'Спринт к соревнованиям',
            'Домашний минимум оборудования',
            'Вечерний лёгкий кардио',
            'Сила: верх тела',
            'Мобильность бёдер и грудного отдела',
        ]
        for ei, tmpl in enumerate(coach_extra_templates):
            name = f'{tmpl} · публичный'
            wt = _pick_workout_type(ei + 40)
            dur = _pick_duration_minutes(ei + 3)
            strict = ei % 7 == 0
            p = _create_plan_with_exercises(
                coach,
                name,
                'Публичный план главного тренера — в каталоге Pulse.',
                exercises,
                today,
                start_shift=5 + ei * 4,
                duration_days=55 + ei * 8,
                is_public=True,
                workout_type=wt,
                duration_minutes=dur,
                strict_schedule=strict,
            )
            plans_created += 1
            for j in range(8):
                ai = (ei * 13 + j * 7) % len(bulk_athletes)
                ath = bulk_athletes[ai]
                if not TrainerAthleteLink.objects.filter(trainer_profile=profile, athlete=ath, confirmed=True).exists():
                    continue
                _, created = PlanAssignment.objects.get_or_create(
                    plan=p,
                    athlete=ath,
                    defaults={'assigned_by': coach, 'status': PlanAssignment.Status.ACTIVE},
                )
                if created:
                    assignments_created += 1

        for ai, ath in enumerate(bulk_athletes):
            _seed_workouts_for_user(ath, exercises, today, salt=ai * 17, density=7, days=56)
        for ti, tr in enumerate(bulk_trainers):
            _seed_workouts_for_user(tr, exercises, today, salt=300 + ti * 13, density=8, days=48)

        for ai, ath in enumerate(bulk_athletes):
            bw = 70.0 + (ai % 28) * 0.65
            for k in range(14):
                d = today - timedelta(weeks=18 - k)
                BodyMetric.objects.get_or_create(
                    user=ath,
                    date=d,
                    defaults={
                        'weight_kg': round(bw - k * 0.1 + k % 5 * 0.04, 2),
                        'body_fat_percent': round(13.0 + ai % 9 * 0.35 - k * 0.04, 1) if k % 2 == 0 else None,
                        'note': '',
                    },
                )

        _stagger_public_plan_timestamps()

        n_public = TrainingPlan.objects.filter(is_public=True).count()
        self.stdout.write(self.style.SUCCESS('Готово.'))
        self.stdout.write('  admin@pulse.demo / admin123')
        self.stdout.write('  mod0@pulse.demo … mod2@pulse.demo / mod123')
        self.stdout.write('  coach@pulse.demo / coach123')
        self.stdout.write('  athlete@pulse.demo / athlete123')
        self.stdout.write(f'  + {NUM_BULK_TRAINERS} тренеров и {NUM_BULK_ATHLETES} атлетов (bulk-*@pulse.demo / {BULK_PASSWORD})')
        self.stdout.write(f'  Планов создано/обновлено: {plans_created}, новых назначений: {assignments_created}.')
        self.stdout.write(f'  Планов в каталоге (is_public): {n_public}.')
