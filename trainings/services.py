from __future__ import annotations
from collections import Counter
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from plans.models import TrainingPlan
from trainings.models import ExerciseCategory, WorkoutExercise, WorkoutSession, WorkoutType

def infer_workout_type_from_plan(plan: TrainingPlan) -> str:
    cats: list[str] = []
    for pe in plan.plan_exercises.select_related('exercise'):
        cats.append(pe.exercise.category)
    if not cats:
        return WorkoutType.STRENGTH
    top, _ = Counter(cats).most_common(1)[0]
    mapping = {ExerciseCategory.STRENGTH: WorkoutType.STRENGTH, ExerciseCategory.CARDIO: WorkoutType.CARDIO, ExerciseCategory.MOBILITY: WorkoutType.FLEXIBILITY, ExerciseCategory.MIXED: WorkoutType.CIRCUIT}
    return mapping.get(top, WorkoutType.STRENGTH)

@transaction.atomic
def create_workout_session_from_plan(*, user, plan: TrainingPlan, session_date: date | None=None) -> WorkoutSession:
    d = session_date or timezone.localdate()
    wtype = infer_workout_type_from_plan(plan)
    session = WorkoutSession.objects.create(user=user, date=d, title=plan.name, notes='', training_plan=plan, workout_type=wtype)
    pes = list(plan.plan_exercises.select_related('exercise').order_by('order', 'id'))
    for pe in pes:
        w = pe.target_weight_kg if pe.target_weight_kg is not None else Decimal('0')
        WorkoutExercise.objects.create(session=session, exercise=pe.exercise, order=pe.order, sets=pe.target_sets, reps=pe.target_reps, weight_kg=w)
    return session
