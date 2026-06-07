from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.timesince import timesince
from django.views import View
from django.views.generic import TemplateView, UpdateView
from urllib.parse import urlencode
from typing import Any, Optional
import json
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from plans.models import PlanAssignment, PlanExercise, TrainingPlan
from trainings.models import BodyMetric, Exercise, WorkoutExercise, WorkoutSession, WorkoutType
from users.forms import ProfileEditForm
from users.models import CustomUser, Role, TrainerAthleteLink
from . import analytics
from .calculator import compute_bmr_bmi
from .forms import BodyMetricForm, CalculatorForm
from .mixins import ApprovedUserJsonMixin, ApprovedUserMixin
from .models import Notification


def _parse_calendar_date(raw: object) -> date_cls:
    s = str(raw).strip()
    if 'T' in s:
        s = s.split('T', 1)[0]
    return date_cls.fromisoformat(s)

def _calendar_nav_year_month(request) -> tuple[int | None, int | None]:
    raw_y = request.GET.get('cal_year')
    if raw_y is None or str(raw_y).strip() == '':
        raw_y = request.POST.get('cal_year')
    raw_m = request.GET.get('cal_month')
    if raw_m is None or str(raw_m).strip() == '':
        raw_m = request.POST.get('cal_month')
    y: int | None = None
    m: int | None = None
    if raw_y is not None and str(raw_y).strip() != '':
        try:
            y = int(raw_y)
        except ValueError:
            y = None
    if raw_m is not None and str(raw_m).strip() != '':
        try:
            m = int(raw_m)
        except ValueError:
            m = None
    if m is not None and (m < 1 or m > 12):
        m = None
    return (y, m)

def trainer_can_view_athlete(viewer: CustomUser, athlete: CustomUser) -> bool:
    if viewer.is_elevated_staff():
        return True
    if viewer.pk == athlete.pk:
        return True
    if not viewer.can_access_trainer_features():
        return False
    tp = getattr(viewer, 'trainer_profile', None)
    if not tp:
        return False
    return tp.athlete_links.filter(athlete=athlete, confirmed=True).exists()


def weight_tracking_page_context(request, subject: CustomUser, *, back_url: str, body_metric_form: Optional[BodyMetricForm]=None) -> dict:
    viewer = request.user
    can_edit = viewer.pk == subject.pk
    form = body_metric_form or BodyMetricForm(initial={'date': timezone.localdate()})
    return {
        'weight_subject': subject,
        'weight_can_edit': can_edit,
        'weight_back_url': back_url,
        'chart_body_weight': analytics.body_weight_chart_series(subject),
        'body_weight_summary': analytics.body_weight_profile_summary(subject),
        'body_metrics_list': BodyMetric.objects.filter(user=subject).order_by('-date', '-created_at')[:80],
        'body_metric_form': form,
    }


class LandingView(TemplateView):
    template_name = 'index.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['show_home_dashboard'] = False
        if not user.is_authenticated:
            User = get_user_model()
            ctx['landing_athletes_count'] = User.objects.filter(role=Role.ATHLETE).count()
            ctx['landing_trainers_count'] = User.objects.filter(role=Role.TRAINER).count()
            ctx['landing_plans_count'] = TrainingPlan.objects.count()
        if user.is_authenticated:
            ctx['hero_volume_change'] = analytics.landing_week_volume_change_label(user)
            ctx['hero_days_with_workouts'] = analytics.landing_distinct_workout_days(user, 7)
            if not user.is_blocked_trainer():
                ctx['show_home_dashboard'] = True
                ctx['nav'] = 'dashboard'
                m = analytics.user_training_metrics(user)
                ctx['metrics'] = {'workouts_week': m['workouts_week'], 'volume_week': m['volume_week'], 'streak': m['streak'], 'active_plans': m['active_plans'], 'volume_week_change': m['volume_week_change']}
                ctx['chart_weeks'] = analytics.chart_volume_by_week(user, 8)
                ctx['chart_days'] = analytics.chart_sessions_by_day(user, 7)
                ctx['chart_types'] = analytics.profile_workout_type_distribution(user)
                ctx['chart_exercise_weeks'] = analytics.chart_exercise_max_weight_by_week(user, top_n=3)
                cy, cm = _calendar_nav_year_month(self.request)
                ctx['calendar_mini'] = analytics.mini_calendar_payload(user, year=cy, month=cm)
                ctx['chart_body_weight'] = analytics.body_weight_chart_series(user)
                ctx['body_metric_post_url'] = reverse('dashboard:landing')
                ctx['body_metric_form'] = kwargs.get('body_metric_form') or BodyMetricForm(initial={'date': timezone.localdate()})
        return ctx

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('users:login'))
        if request.POST.get('action') != 'add_body_metric':
            return HttpResponseRedirect(reverse('dashboard:landing'))
        if request.user.is_blocked_trainer():
            return HttpResponseRedirect(reverse('users:trainer_pending'))
        form = BodyMetricForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.user = request.user
            m.save()
            messages.success(request, 'Замер сохранён.')
            qs = {}
            if request.POST.get('cal_year'):
                qs['cal_year'] = request.POST.get('cal_year')
            if request.POST.get('cal_month'):
                qs['cal_month'] = request.POST.get('cal_month')
            tail = '?' + urlencode(qs) if qs else ''
            return HttpResponseRedirect(reverse('dashboard:landing') + tail + '#pulse-home-dashboard')
        messages.error(request, 'Проверьте поля замера.')
        return self.render_to_response(self.get_context_data(body_metric_form=form))

class DashboardView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'dashboard.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['nav'] = 'dashboard'
        m = analytics.user_training_metrics(user)
        ctx['metrics'] = {'workouts_week': m['workouts_week'], 'volume_week': m['volume_week'], 'streak': m['streak'], 'active_plans': m['active_plans'], 'volume_week_change': m['volume_week_change']}
        ctx['chart_weeks'] = analytics.chart_volume_by_week(user, 8)
        ctx['chart_days'] = analytics.chart_sessions_by_day(user, 7)
        ctx['chart_types'] = analytics.profile_workout_type_distribution(user)
        ctx['chart_exercise_weeks'] = analytics.chart_exercise_max_weight_by_week(user, top_n=3)
        cy, cm = _calendar_nav_year_month(self.request)
        ctx['calendar_mini'] = analytics.mini_calendar_payload(user, year=cy, month=cm)
        ctx['chart_body_weight'] = analytics.body_weight_chart_series(user)
        ctx['body_metric_post_url'] = reverse('dashboard:home')
        ctx['body_metric_form'] = kwargs.get('body_metric_form') or BodyMetricForm(initial={'date': timezone.localdate()})
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('action') == 'add_body_metric':
            form = BodyMetricForm(request.POST)
            if form.is_valid():
                m = form.save(commit=False)
                m.user = request.user
                m.save()
                messages.success(request, 'Замер сохранён.')
            else:
                messages.error(request, 'Проверьте поля замера.')
                return self.render_to_response(self.get_context_data(body_metric_form=form))
        qs = {}
        if request.POST.get('cal_year'):
            qs['cal_year'] = request.POST.get('cal_year')
        if request.POST.get('cal_month'):
            qs['cal_month'] = request.POST.get('cal_month')
        url = reverse('dashboard:home')
        if qs:
            url += '?' + urlencode(qs)
        return HttpResponseRedirect(url)

class ProfileView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'profile.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['nav'] = 'profile'
        ctx['profile_user'] = user
        initials = (user.first_name[:1] + user.last_name[:1]).upper() if user.first_name else user.email[:2].upper()
        ctx['initials'] = initials
        ctx['chart_types'] = analytics.profile_workout_type_distribution(user)
        ctx['chart_exercise_progress'] = analytics.chart_exercise_max_weight_by_week(user, top_n=3)
        ctx['body_weight_summary'] = analytics.body_weight_profile_summary(user)
        ctx['trainer_confirmed_links'] = []
        ctx['trainer_pending_links'] = []
        ctx['athlete_pending_links'] = []
        ctx['athlete_confirmed_links'] = []
        if user.role == Role.TRAINER and getattr(user, 'trainer_profile', None):
            tp = user.trainer_profile
            ctx['trainer_confirmed_links'] = tp.athlete_links.filter(confirmed=True).select_related('athlete')
            ctx['trainer_pending_links'] = tp.athlete_links.filter(confirmed=False).select_related('athlete')
        if user.role == Role.ATHLETE:
            ctx['athlete_pending_links'] = TrainerAthleteLink.objects.filter(athlete=user, confirmed=False).select_related('trainer_profile__user')
            ctx['athlete_confirmed_links'] = TrainerAthleteLink.objects.filter(athlete=user, confirmed=True).select_related('trainer_profile__user')
        return ctx

    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')
        if action == 'invite_athlete' and user.role == Role.TRAINER and user.can_access_trainer_features():
            email = (request.POST.get('athlete_email') or '').strip().lower()
            profile = getattr(user, 'trainer_profile', None)
            if not profile:
                messages.error(request, 'Профиль тренера не найден.')
            elif not email:
                messages.error(request, 'Укажите email атлета.')
            else:
                U = get_user_model()
                try:
                    athlete = U.objects.get(email__iexact=email, role=Role.ATHLETE)
                except U.DoesNotExist:
                    messages.error(request, 'Пользователь с таким email не найден или не спортсмен.')
                else:
                    if athlete.pk == user.pk:
                        messages.error(request, 'Нельзя пригласить самого себя.')
                    else:
                        link, created = TrainerAthleteLink.objects.get_or_create(trainer_profile=profile, athlete=athlete, defaults={'confirmed': False})
                        if created:
                            messages.success(request, f'Приглашение отправлено. Атлет {athlete.email} должен подтвердить связь в профиле.')
                        else:
                            messages.info(request, 'Связь с этим атлетом уже существует.')
        elif action == 'remove_athlete_link' and user.role == Role.TRAINER and user.can_access_trainer_features():
            lid = request.POST.get('link_id')
            profile = getattr(user, 'trainer_profile', None)
            if profile and lid and lid.isdigit():
                deleted, _ = TrainerAthleteLink.objects.filter(pk=int(lid), trainer_profile=profile).delete()
                if deleted:
                    messages.success(request, 'Подопечный удалён из списка.')
                else:
                    messages.error(request, 'Связь не найдена.')
        elif action == 'confirm_trainer_link' and user.role == Role.ATHLETE:
            lid = request.POST.get('link_id')
            if lid and lid.isdigit():
                link = TrainerAthleteLink.objects.filter(pk=int(lid), athlete=user).first()
                if link:
                    link.confirmed = True
                    link.save(update_fields=['confirmed'])
                    messages.success(request, 'Связь с тренером подтверждена.')
                else:
                    messages.error(request, 'Приглашение не найдено.')
        else:
            messages.error(request, 'Действие недоступно.')
        return HttpResponseRedirect(reverse('dashboard:profile'))

class AthleteProfileView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'athlete_profile.html'

    def dispatch(self, request, *args, **kwargs):
        self.athlete = get_object_or_404(CustomUser, pk=kwargs['pk'])
        if not trainer_can_view_athlete(request.user, self.athlete):
            messages.error(request, 'Нет доступа к профилю этого спортсмена.')
            return HttpResponseRedirect(reverse('dashboard:profile'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.athlete
        ctx['nav'] = 'profile'
        ctx['profile_user'] = u
        ctx['initials'] = (u.first_name[:1] + u.last_name[:1]).upper() if u.first_name else u.email[:2].upper()
        ctx['chart_types'] = analytics.profile_workout_type_distribution(u)
        ctx['chart_exercise_progress'] = analytics.chart_exercise_max_weight_by_week(u, top_n=3)
        ctx['body_weight_summary'] = analytics.body_weight_profile_summary(u)
        return ctx


class WeightTrackingView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'profile_weight.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav'] = 'profile'
        ctx['weight_page_title'] = 'Отслеживание веса тела'
        ctx.update(weight_tracking_page_context(self.request, self.request.user, back_url=reverse('dashboard:profile'), body_metric_form=kwargs.get('body_metric_form')))
        return ctx

    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')
        if action == 'add_body_metric':
            form = BodyMetricForm(request.POST)
            if form.is_valid():
                m = form.save(commit=False)
                m.user = user
                m.save()
                messages.success(request, 'Замер сохранён.')
            else:
                messages.error(request, 'Проверьте поля замера.')
                return self.render_to_response(self.get_context_data(body_metric_form=form))
            return HttpResponseRedirect(reverse('dashboard:profile_weight'))
        if action == 'delete_body_metric':
            mid = request.POST.get('metric_id')
            if mid and mid.isdigit():
                deleted, _ = BodyMetric.objects.filter(pk=int(mid), user=user).delete()
                if deleted:
                    messages.success(request, 'Замер удалён.')
                else:
                    messages.error(request, 'Запись не найдена.')
            return HttpResponseRedirect(reverse('dashboard:profile_weight'))
        messages.error(request, 'Действие недоступно.')
        return HttpResponseRedirect(reverse('dashboard:profile_weight'))


class AthleteWeightTrackingView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'profile_weight.html'
    http_method_names = ['get', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        self.athlete = get_object_or_404(CustomUser, pk=kwargs['pk'])
        if not trainer_can_view_athlete(request.user, self.athlete):
            messages.error(request, 'Нет доступа к данным этого спортсмена.')
            return HttpResponseRedirect(reverse('dashboard:profile'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.athlete
        ctx['nav'] = 'profile'
        ctx['weight_page_title'] = f'Вес: {u.get_full_name() or u.email}'
        ctx.update(weight_tracking_page_context(self.request, u, back_url=reverse('dashboard:athlete_profile', kwargs={'pk': u.pk})))
        return ctx


class CalculatorView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'calculator.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav'] = 'calculator'
        ctx['form'] = kwargs.get('form') or CalculatorForm()
        ctx['results'] = kwargs.get('results')
        return ctx

    def post(self, request, *args, **kwargs):
        form = CalculatorForm(request.POST)
        if form.is_valid():
            results = compute_bmr_bmi(form.cleaned_data)
            return self.render_to_response(self.get_context_data(form=form, results=results))
        messages.error(request, 'Проверьте поля калькулятора.')
        return self.render_to_response(self.get_context_data(form=form))

class ProfileEditView(LoginRequiredMixin, ApprovedUserMixin, UpdateView):
    form_class = ProfileEditForm
    template_name = 'profile_edit.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav'] = 'profile'
        return ctx

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        from users.avatar import apply_avatar_change

        user = form.save(commit=False)
        avatar = self.request.FILES.get('avatar')
        clear_avatar = self.request.POST.get('clear_avatar') == '1'
        apply_avatar_change(user, avatar, clear=clear_avatar)
        user.save()
        self.object = user
        messages.success(self.request, 'Профиль сохранён.')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('dashboard:profile')

def _calendar_can_log_sessions(user: CustomUser) -> bool:
    r = getattr(user, 'role', None)
    return r in (Role.ATHLETE, Role.TRAINER, Role.MODERATOR, Role.ADMIN) or user.is_superuser


class CalendarView(LoginRequiredMixin, ApprovedUserMixin, TemplateView):
    template_name = 'calendar.html'

    def get_year_month(self):
        today = timezone.localdate()
        try:
            y = int(self.request.GET.get('year', today.year))
            m = int(self.request.GET.get('month', today.month))
        except (TypeError, ValueError):
            y, m = (today.year, today.month)
        m = max(1, min(12, m))
        return (y, m)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['nav'] = 'calendar'
        y, m = self.get_year_month()
        ctx['calendar_year'] = y
        ctx['calendar_month'] = m
        ctx['calendar_events'] = analytics.calendar_events_month(user, y, m)
        ctx['calendar_can_log'] = _calendar_can_log_sessions(user)
        return ctx


def _session_to_calendar_dict(s: WorkoutSession) -> dict[str, Any]:
    wes = list(s.workout_exercises.select_related('exercise').order_by('order', 'id'))
    exercises: list[dict[str, Any]] = []
    for we in wes:
        exercises.append({'exercise_id': we.exercise_id, 'exercise_name': we.exercise.name, 'sets': we.sets, 'reps': we.reps, 'weight_kg': float(we.weight_kg)})
    return {'id': s.pk, 'title': s.title or '', 'notes': s.notes or '', 'workout_type': s.workout_type, 'duration_minutes': s.duration_minutes, 'training_plan_id': s.training_plan_id, 'exercises': exercises}


class CalendarDayApiView(ApprovedUserJsonMixin, View):
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        if not _calendar_can_log_sessions(request.user):
            return JsonResponse({'error': 'forbidden'}, status=403)
        raw = request.GET.get('date')
        if not raw:
            return JsonResponse({'error': 'date required'}, status=400)
        try:
            d = _parse_calendar_date(raw)
        except ValueError:
            return JsonResponse({'error': 'invalid date'}, status=400)
        user = request.user
        session = WorkoutSession.objects.filter(user=user, date=d).order_by('created_at').select_related('training_plan').prefetch_related('workout_exercises__exercise').first()
        sess_payload: dict[str, Any] | None = None
        if session:
            sess_payload = _session_to_calendar_dict(session)
            if session.training_plan_id:
                link = PlanAssignment.objects.filter(athlete=user, plan_id=session.training_plan_id, status=PlanAssignment.Status.ACTIVE).first()
                if link:
                    sess_payload['linked_assignment_id'] = link.pk
        active_assignments: list[dict[str, Any]] = []
        for a in PlanAssignment.objects.filter(athlete=user, status=PlanAssignment.Status.ACTIVE).select_related('plan').order_by('plan__name'):
            p = a.plan
            active_assignments.append({'assignment_id': a.pk, 'plan_id': p.pk, 'name': p.name})
        catalog = [{'id': ex.pk, 'name': ex.name} for ex in Exercise.objects.all().order_by('name')]
        choices = [{'value': c[0], 'label': c[1]} for c in WorkoutType.choices]
        payload: dict[str, Any] = {'date': d.isoformat(), 'session': sess_payload, 'active_assignments': active_assignments, 'exercise_catalog': catalog, 'workout_type_choices': choices}
        return JsonResponse(payload)


class CalendarPlanDataApiView(ApprovedUserJsonMixin, View):
    """Полные данные плана для автозаполнения модалки календаря (только факты из БД)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk: int, *args, **kwargs):
        if not _calendar_can_log_sessions(request.user):
            return JsonResponse({'error': 'forbidden'}, status=403)
        plan_id = int(pk)
        if not PlanAssignment.objects.filter(athlete=request.user, plan_id=plan_id, status=PlanAssignment.Status.ACTIVE).exists():
            return JsonResponse({'error': 'plan not assigned'}, status=404)
        plan = get_object_or_404(TrainingPlan.objects.only('pk', 'name', 'description', 'workout_type', 'duration_minutes'), pk=plan_id)
        exercises: list[dict[str, Any]] = []
        for pe in PlanExercise.objects.filter(plan_id=plan_id).select_related('exercise').order_by('order', 'id'):
            w = pe.target_weight_kg
            exercises.append({
                'exercise_id': pe.exercise_id,
                'exercise_name': pe.exercise.name,
                'sets': pe.target_sets,
                'reps': pe.target_reps,
                'weight_kg': float(w) if w is not None else None,
            })
        payload: dict[str, Any] = {'plan_id': plan.pk, 'plan_name': plan.name, 'exercises': exercises}
        desc = (plan.description or '').strip()
        if desc:
            payload['description'] = desc
        wt = (plan.workout_type or '').strip()
        if wt and wt in dict(WorkoutType.choices):
            payload['workout_type'] = wt
        if plan.duration_minutes is not None:
            payload['duration_minutes'] = int(plan.duration_minutes)
        return JsonResponse(payload)


class CalendarPlanExercisesApiView(ApprovedUserJsonMixin, View):
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        if not _calendar_can_log_sessions(request.user):
            return JsonResponse({'error': 'forbidden'}, status=403)
        raw = request.GET.get('plan_id')
        if not raw or not str(raw).isdigit():
            return JsonResponse({'error': 'plan_id required'}, status=400)
        plan_id = int(raw)
        if not PlanAssignment.objects.filter(athlete=request.user, plan_id=plan_id, status=PlanAssignment.Status.ACTIVE).exists():
            return JsonResponse({'error': 'plan not assigned'}, status=404)
        plan = TrainingPlan.objects.filter(pk=plan_id).only('name', 'description', 'workout_type', 'starts_on', 'ends_on', 'duration_minutes').first()
        if not plan:
            return JsonResponse({'error': 'plan not found'}, status=404)
        rows: list[dict[str, Any]] = []
        for pe in PlanExercise.objects.filter(plan_id=plan_id).select_related('exercise').order_by('order', 'id'):
            w = float(pe.target_weight_kg) if pe.target_weight_kg is not None else 0.0
            rows.append({'exercise_id': pe.exercise_id, 'exercise_name': pe.exercise.name, 'sets': pe.target_sets, 'reps': pe.target_reps, 'weight_kg': w})
        wt = plan.workout_type or WorkoutType.STRENGTH
        if wt not in dict(WorkoutType.choices):
            wt = WorkoutType.STRENGTH
        plan_notes = (plan.description or '').strip()
        return JsonResponse({
            'rows': rows,
            'workout_type': wt,
            'plan_name': plan.name,
            'plan_description': plan_notes,
            'plan_notes': plan_notes,
            'starts_on': plan.starts_on.isoformat() if plan.starts_on else '',
            'ends_on': plan.ends_on.isoformat() if plan.ends_on else '',
            'duration_minutes': plan.duration_minutes,
        })


class CalendarSessionSaveView(ApprovedUserJsonMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        if not _calendar_can_log_sessions(request.user):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'invalid JSON'}, status=400)
        user = request.user
        raw_date = payload.get('date')
        if not raw_date:
            return JsonResponse({'ok': False, 'error': 'date required'}, status=400)
        try:
            target_date = _parse_calendar_date(raw_date)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'invalid date'}, status=400)
        workout_type = payload.get('workout_type') or WorkoutType.STRENGTH
        if workout_type not in dict(WorkoutType.choices):
            workout_type = WorkoutType.STRENGTH
        title = (payload.get('title') or '')[:200]
        notes = (payload.get('notes') or '')[:5000]
        duration = payload.get('duration_minutes')
        dur_val: int | None = None
        if duration is not None and str(duration).strip() != '':
            try:
                dur_val = int(duration)
                if dur_val < 1 or dur_val > 600:
                    dur_val = None
            except (TypeError, ValueError):
                dur_val = None
        plan_assignment_id = payload.get('plan_assignment_id')
        clear_plan = bool(payload.get('clear_plan'))
        ass_int: int | None = None
        if plan_assignment_id is not None and str(plan_assignment_id).strip() != '':
            try:
                ass_int = int(plan_assignment_id)
            except (TypeError, ValueError):
                ass_int = None
        exercises_in = payload.get('exercises')
        if not isinstance(exercises_in, list):
            exercises_in = []
        parsed_rows: list[tuple[int, int, int, Decimal]] = []
        for row in exercises_in:
            if not isinstance(row, dict):
                continue
            try:
                eid = int(row.get('exercise_id'))
            except (TypeError, ValueError):
                continue
            if not Exercise.objects.filter(pk=eid).exists():
                continue
            try:
                sets = int(row.get('sets', 1))
                reps = int(row.get('reps', 1))
            except (TypeError, ValueError):
                continue
            sets = max(1, min(sets, 99))
            reps = max(1, min(reps, 999))
            try:
                w = Decimal(str(row.get('weight_kg', 0)))
            except (InvalidOperation, TypeError, ValueError):
                w = Decimal('0')
            if w < 0 or w > Decimal('999.99'):
                w = Decimal('0')
            parsed_rows.append((eid, sets, reps, w))
        with transaction.atomic():
            ordered = list(WorkoutSession.objects.filter(user=user, date=target_date).order_by('created_at'))
            for extra in ordered[1:]:
                extra.delete()
            session = ordered[0] if ordered else None
            if session is None:
                session = WorkoutSession(user=user, date=target_date)
            session.title = title
            session.notes = notes
            session.duration_minutes = dur_val
            session.workout_type = workout_type
            if ass_int is not None:
                ass = PlanAssignment.objects.filter(pk=ass_int, athlete=user, status=PlanAssignment.Status.ACTIVE).select_related('plan').first()
                if ass:
                    session.training_plan_id = ass.plan_id
            elif clear_plan:
                session.training_plan_id = None
            session.save()
            session.workout_exercises.all().delete()
            for order, (eid, sets, reps, w) in enumerate(parsed_rows):
                WorkoutExercise.objects.create(session=session, exercise_id=eid, order=order, sets=sets, reps=reps, weight_kg=w)
        session = WorkoutSession.objects.filter(pk=session.pk).prefetch_related('workout_exercises__exercise').first()
        assert session is not None
        return JsonResponse({'ok': True, 'session': _session_to_calendar_dict(session)})


class NotificationsListApiView(ApprovedUserJsonMixin, View):
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        user = request.user
        unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
        items: list[dict[str, Any]] = []
        now = timezone.now()
        for n in Notification.objects.filter(recipient=user).order_by('-created_at')[:20]:
            items.append({'id': n.pk, 'message': n.message, 'link': n.link or '', 'is_read': n.is_read, 'created_at': n.created_at.isoformat(), 'time_label': timesince(n.created_at, now) + ' назад'})
        return JsonResponse({'unread_count': unread_count, 'items': items})


class NotificationMarkReadView(ApprovedUserJsonMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, pk: int, *args, **kwargs):
        updated = Notification.objects.filter(pk=pk, recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'ok': True, 'updated': updated})


class NotificationMarkAllReadView(ApprovedUserJsonMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        n = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'ok': True, 'updated': n})
