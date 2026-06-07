from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from typing import Any
from django.db.models import Max
from django.utils import timezone
from plans.models import PlanAssignment, TrainingPlan
from trainings.models import BodyMetric, WorkoutExercise, WorkoutSession, WorkoutType

def _local_today() -> date:
    return timezone.localdate()

def workouts_last_days(user, days: int=7) -> int:
    start = _local_today() - timedelta(days=days - 1)
    return WorkoutSession.objects.filter(user=user, date__gte=start).count()

def volume_last_days(user, days: int=7) -> float:
    start = _local_today() - timedelta(days=days - 1)
    qs = WorkoutExercise.objects.filter(session__user=user, session__date__gte=start)
    return sum((we.volume for we in qs.iterator()))

def _volume_between(user, start: date, end: date) -> float:
    qs = WorkoutExercise.objects.filter(session__user=user, session__date__gte=start, session__date__lte=end)
    return sum((we.volume for we in qs.iterator()))

def calendar_week_volume_change_label(user) -> str:
    today = _local_today()
    mon_this = today - timedelta(days=today.weekday())
    prev_sun = mon_this - timedelta(days=1)
    mon_prev = mon_this - timedelta(days=7)
    current = _volume_between(user, mon_this, today)
    previous = _volume_between(user, mon_prev, prev_sun)
    if current <= 0 and previous <= 0:
        return '0%'
    if previous <= 0:
        return 'старт'
    pct = (current - previous) / previous * 100.0
    rounded = int(round(pct))
    if rounded > 0:
        return f'+{rounded}%'
    return f'{rounded}%'

def landing_week_volume_change_label(user) -> str:
    return calendar_week_volume_change_label(user)

def landing_distinct_workout_days(user, days: int=7) -> int:
    today = _local_today()
    start = today - timedelta(days=days - 1)
    return WorkoutSession.objects.filter(user=user, date__gte=start, date__lte=today).values('date').distinct().count()

def workout_streak(user) -> int:
    today = _local_today()

    def has(d: date) -> bool:
        return WorkoutSession.objects.filter(user=user, date=d).exists()
    end = today
    if not has(today):
        if has(today - timedelta(days=1)):
            end = today - timedelta(days=1)
        else:
            return 0
    streak = 0
    d = end
    while has(d):
        streak += 1
        d -= timedelta(days=1)
    return streak

def active_plans_count(user) -> int:
    return PlanAssignment.objects.filter(athlete=user, status=PlanAssignment.Status.ACTIVE).count()

def chart_volume_by_week(user, weeks: int=8) -> dict[str, Any]:
    end = _local_today()
    start = end - timedelta(weeks=weeks)
    rows = WorkoutExercise.objects.filter(session__user=user, session__date__gte=start).select_related('session')
    buckets: dict[date, float] = defaultdict(float)
    for we in rows:
        d = we.session.date
        monday = d - timedelta(days=d.weekday())
        buckets[monday] += we.volume
    labels: list[str] = []
    values: list[float] = []
    for i in range(weeks - 1, -1, -1):
        monday = end - timedelta(days=end.weekday()) - timedelta(weeks=i)
        labels.append(monday.strftime('%d.%m'))
        values.append(round(buckets.get(monday, 0.0), 1))
    return {'labels': labels, 'values': values}

def chart_sessions_by_day(user, days: int=7) -> dict[str, Any]:
    end = _local_today()
    dow_ru = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    labels: list[str] = []
    values: list[int] = []
    for i in range(days - 1, -1, -1):
        d = end - timedelta(days=i)
        labels.append(dow_ru[d.weekday()])
        values.append(WorkoutSession.objects.filter(user=user, date=d).count())
    return {'labels': labels, 'values': values}

def mini_calendar_payload(user, year: int | None=None, month: int | None=None) -> dict[str, Any]:
    from calendar import monthrange
    today = _local_today()
    y = year or today.year
    m = month or today.month
    days_with = set(WorkoutSession.objects.filter(user=user, date__year=y, date__month=m).values_list('date__day', flat=True))
    _, last_day = monthrange(y, m)
    day_details: dict[str, list[dict[str, Any]]] = {}
    for day in range(1, last_day + 1):
        d = date(y, m, day)
        sessions = WorkoutSession.objects.filter(user=user, date=d).prefetch_related('workout_exercises__exercise').order_by('created_at')
        if not sessions:
            continue
        iso = d.isoformat()
        sess_list: list[dict[str, Any]] = []
        for s in sessions:
            wes = list(s.workout_exercises.all())
            names: list[str] = []
            for we in wes[:12]:
                ex = we.exercise
                names.append(getattr(ex, 'name', None) or '—')
            ex_str = ', '.join(names)
            if len(wes) > 12:
                ex_str += '…'
            vol = sum((we.volume for we in wes))
            sess_list.append({'title': s.title or 'Тренировка', 'workout_type': s.get_workout_type_display(), 'exercise_count': len(wes), 'tonnage': round(vol, 1), 'exercises': ex_str or '—'})
        day_details[iso] = sess_list
    return {'year': y, 'month': m, 'today': {'y': today.year, 'm': today.month, 'd': today.day}, 'daysWithWorkouts': sorted((int(d) for d in days_with)), 'dayDetails': day_details}

def calendar_events_month(user, year: int, month: int) -> list[dict[str, Any]]:
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    out: list[dict[str, Any]] = []
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        sessions = WorkoutSession.objects.filter(user=user, date=d).prefetch_related('workout_exercises')
        sess_payload: list[dict[str, Any]] = []
        for s in sessions:
            wes = list(s.workout_exercises.all())
            ex_count = len(wes)
            vol = sum((we.volume for we in wes))
            sess_payload.append({'id': s.pk, 'title': s.title or 'Тренировка', 'workout_type': s.get_workout_type_display(), 'exercise_count': ex_count, 'tonnage': round(vol, 1), 'duration': s.duration_minutes or ''})
        plans_payload: list[dict[str, Any]] = []
        for a in PlanAssignment.objects.filter(athlete=user, status=PlanAssignment.Status.ACTIVE).select_related('plan'):
            p: TrainingPlan = a.plan
            if getattr(p, 'strict_schedule', False):
                so, eo = p.starts_on, p.ends_on
                if not so or not eo:
                    continue
                if d < so or d > eo:
                    continue
            else:
                so, eo = (p.starts_on, p.ends_on)
                if so and d < so:
                    continue
                if eo and d > eo:
                    continue
            plans_payload.append({'plan_id': p.pk, 'name': p.name})
        if sess_payload or plans_payload:
            out.append({'date': d.isoformat(), 'sessions': sess_payload, 'plans': plans_payload})
    return out

def profile_workout_type_distribution(user) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    for value, _ in WorkoutType.choices:
        counts[value] = 0
    for wt in WorkoutSession.objects.filter(user=user).values_list('workout_type', flat=True):
        counts[wt] = counts.get(wt, 0) + 1
    labels: list[str] = []
    data: list[int] = []
    for value, label in WorkoutType.choices:
        c = counts.get(value, 0)
        if c:
            labels.append(label)
            data.append(c)
    if not data:
        labels = ['Нет данных']
        data = [1]
    return {'labels': labels, 'values': data}

def chart_exercise_max_weight_by_week(user, *, months: int=2, top_n: int=3) -> dict[str, Any]:
    end = _local_today()
    start = end - timedelta(days=30 * months + 14)
    vol_by_ex: dict[int, float] = defaultdict(float)
    name_by_id: dict[int, str] = {}
    for we in WorkoutExercise.objects.filter(session__user=user, session__date__gte=start).select_related('exercise'):
        eid = we.exercise_id
        name_by_id[eid] = we.exercise.name
        vol_by_ex[eid] += we.volume
    top_ids = sorted(vol_by_ex.keys(), key=lambda i: vol_by_ex[i], reverse=True)[:top_n]
    if not top_ids:
        return {'labels': [], 'datasets': []}
    mon_end = end - timedelta(days=end.weekday())
    weeks: list[date] = []
    mon_scan = mon_end - timedelta(weeks=8)
    while mon_scan <= mon_end:
        weeks.append(mon_scan)
        mon_scan += timedelta(days=7)
    labels = [x.strftime('%d.%m') for x in weeks]
    datasets: list[dict[str, Any]] = []
    for eid in top_ids:
        series: list[float | None] = []
        for monday in weeks:
            window_end = monday + timedelta(days=6)
            agg = WorkoutExercise.objects.filter(session__user=user, exercise_id=eid, session__date__gte=monday, session__date__lte=window_end).aggregate(m=Max('weight_kg'))['m']
            if agg is None:
                series.append(None)
            else:
                series.append(round(float(agg), 2))
        datasets.append({'label': name_by_id[eid], 'data': series})
    return {'labels': labels, 'datasets': datasets}

def body_weight_chart_series(user, min_points: int=2) -> dict[str, Any]:
    rows = list(BodyMetric.objects.filter(user=user).order_by('date', 'created_at'))
    if len(rows) < min_points:
        return {'labels': [], 'values': [], 'has_enough': False}
    labels = [r.date.strftime('%d.%m') for r in rows]
    values = [round(r.weight_kg, 2) for r in rows]
    return {'labels': labels, 'values': values, 'has_enough': True}


def body_weight_profile_summary(user) -> dict[str, Any]:
    latest = BodyMetric.objects.filter(user=user).order_by('-date', '-created_at').first()
    if not latest:
        return {'has_current': False, 'current_kg': None, 'current_date': None, 'change_kg': None, 'change_display': None, 'change_positive': None}
    today = _local_today()
    cutoff = today - timedelta(days=30)
    baseline = BodyMetric.objects.filter(user=user, date__lte=cutoff).order_by('-date', '-created_at').first()
    cur = float(latest.weight_kg)
    if baseline:
        delta = round(cur - float(baseline.weight_kg), 1)
    else:
        delta = None
    change_display = None
    change_positive = None
    if delta is not None:
        if delta > 0:
            change_display = f'+{delta} кг'
            change_positive = True
        elif delta < 0:
            change_display = f'{delta} кг'
            change_positive = False
        else:
            change_display = '0 кг'
            change_positive = None
    return {'has_current': True, 'current_kg': round(cur, 2), 'current_date': latest.date, 'change_kg': delta, 'change_display': change_display, 'change_positive': change_positive}

def user_training_metrics(user) -> dict[str, Any]:
    return {'workouts_week': workouts_last_days(user, 7), 'volume_week': volume_last_days(user, 7), 'streak': workout_streak(user), 'active_plans': active_plans_count(user), 'volume_week_change': calendar_week_volume_change_label(user)}
