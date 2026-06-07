from __future__ import annotations
from decimal import Decimal
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView, TemplateView, UpdateView
from dashboard.mixins import ApprovedUserMixin
from dashboard.models import Notification
from trainings.models import Exercise, WorkoutType
from users.models import CustomUser, Role
from .forms import TrainingPlanMetaForm
from .models import PlanAssignment, PlanExercise, TrainingPlan

def can_manage_plans(user) -> bool:
    return user.is_elevated_staff() or user.can_access_trainer_features()

def confirmed_athletes_for_trainer(user: CustomUser):
    profile = getattr(user, 'trainer_profile', None)
    if not profile:
        return CustomUser.objects.none()
    return CustomUser.objects.filter(trainer_links__trainer_profile=profile, trainer_links__confirmed=True, role=Role.ATHLETE).distinct().order_by('email')

def user_can_view_plan(user: CustomUser, plan: TrainingPlan) -> bool:
    if user.is_elevated_staff():
        return True
    if plan.author_id == user.id:
        return True
    if PlanAssignment.objects.filter(plan=plan, athlete=user).exists():
        return True
    return bool(plan.is_public and user.is_authenticated)


class PlanAccessMixin(UserPassesTestMixin):
    """Доступ к плану: автор, назначенный атлет, персонал или общедоступный план."""

    def test_func(self) -> bool:
        plan = get_object_or_404(TrainingPlan, pk=self.kwargs['pk'])
        return user_can_view_plan(self.request.user, plan)

    def handle_no_permission(self):
        messages.error(self.request, 'Нет доступа к этому плану.')
        return HttpResponseRedirect(reverse('plans:list'))


class AthleteCatalogAccessMixin(UserPassesTestMixin):
    """Каталог и снятие назначений — только для пользователей без прав управления чужими планами."""

    def test_func(self) -> bool:
        return not can_manage_plans(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, 'Раздел доступен спортсменам.')
        return HttpResponseRedirect(reverse('plans:list'))


class StaffUserPlansMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        u = self.request.user
        return bool(u.is_authenticated and u.is_elevated_staff())

    def handle_no_permission(self):
        messages.error(self.request, 'Недостаточно прав.')
        return HttpResponseRedirect(reverse('dashboard:landing'))


class PlanCatalogView(LoginRequiredMixin, ApprovedUserMixin, AthleteCatalogAccessMixin, ListView):
    """Каталог общедоступных планов с поиском и фильтрами (GET)."""

    template_name = 'plans/plan_catalog.html'
    context_object_name = 'catalog_plans'
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = TrainingPlan.objects.filter(is_public=True).select_related('author').annotate(exercise_count=Count('plan_exercises', distinct=True)).order_by('-updated_at')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        wt = (self.request.GET.get('workout_type') or '').strip()
        allowed_wt = {c[0] for c in WorkoutType.choices}
        if wt in allowed_wt:
            qs = qs.filter(workout_type=wt)
        dur = (self.request.GET.get('duration') or '').strip()
        if dur == 'lt30':
            qs = qs.filter(duration_minutes__isnull=False, duration_minutes__lte=30)
        elif dur == '30-60':
            qs = qs.filter(duration_minutes__gt=30, duration_minutes__lte=60)
        elif dur == '60-90':
            qs = qs.filter(duration_minutes__gt=60, duration_minutes__lte=90)
        elif dur == 'gt90':
            qs = qs.filter(duration_minutes__gt=90)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['nav'] = 'plans'
        ctx['can_manage_plans'] = False
        ctx['workout_type_choices'] = WorkoutType.choices
        ctx['filter_q'] = (self.request.GET.get('q') or '').strip()
        ctx['filter_workout_type'] = (self.request.GET.get('workout_type') or '').strip()
        ctx['filter_duration'] = (self.request.GET.get('duration') or '').strip()
        ctx['catalog_filters_active'] = bool(ctx['filter_q'] or ctx['filter_workout_type'] or ctx['filter_duration'])
        assigned_plan_ids = set(PlanAssignment.objects.filter(athlete=user).values_list('plan_id', flat=True))
        for p in ctx['catalog_plans']:
            p.catalog_already_added = p.pk in assigned_plan_ids
        return ctx


class PlanAssignmentRemoveView(LoginRequiredMixin, ApprovedUserMixin, AthleteCatalogAccessMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, pk, *args, **kwargs):
        assignment = get_object_or_404(PlanAssignment, pk=int(pk), athlete=request.user)
        name = assignment.plan.name
        assignment.delete()
        messages.success(request, f'План «{name}» убран из «Мои планы».')
        return HttpResponseRedirect(reverse('plans:list'))


class PlanUserPlansStaffView(LoginRequiredMixin, ApprovedUserMixin, StaffUserPlansMixin, TemplateView):
    template_name = 'plans/staff_user_plans.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        target = get_object_or_404(CustomUser, pk=self.kwargs['user_id'])
        ctx['nav'] = 'plans'
        ctx['target_user'] = target
        ctx['authored_plans'] = TrainingPlan.objects.filter(author=target).annotate(exercise_count=Count('plan_exercises', distinct=True)).order_by('-updated_at')
        ctx['assigned_plans'] = (
            TrainingPlan.objects.filter(assignments__athlete=target)
            .select_related('author')
            .distinct()
            .annotate(exercise_count=Count('plan_exercises', distinct=True))
            .order_by('-updated_at')
        )
        return ctx


class PlanListView(LoginRequiredMixin, ApprovedUserMixin, ListView):
    context_object_name = 'plans'
    template_name = 'plans/plan_list.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = TrainingPlan.objects.select_related('author').annotate(exercise_count=Count('plan_exercises', distinct=True), assignment_count=Count('assignments', distinct=True))
        if can_manage_plans(user):
            if user.is_elevated_staff():
                return qs.order_by('-updated_at')
            return qs.filter(author=user).order_by('-updated_at')
        return qs.filter(assignments__athlete=user).distinct().order_by('-updated_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['nav'] = 'plans'
        ctx['can_manage_plans'] = can_manage_plans(user)
        ctx['exercises'] = Exercise.objects.all()[:300]
        ctx['workout_type_choices'] = WorkoutType.choices
        plans = list(ctx['plans'])
        for p in plans:
            p.hub_status = 'active'
        if not can_manage_plans(user):
            assign_by_plan = {a.plan_id: a.pk for a in PlanAssignment.objects.filter(athlete=user)}
            for p in plans:
                p.my_assignment_id = assign_by_plan.get(p.pk)
            ctx['catalog_plans'] = []
        else:
            ctx['catalog_plans'] = []
        ctx['plans'] = plans
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('action') != 'create_plan':
            return HttpResponseRedirect(reverse('plans:list'))
        if not can_manage_plans(request.user):
            return HttpResponseForbidden('Недостаточно прав.')
        name = (request.POST.get('plan_name') or '').strip()
        if not name:
            messages.error(request, 'Укажите название плана.')
            return HttpResponseRedirect(reverse('plans:list'))
        description = (request.POST.get('plan_description') or '').strip()
        starts_on = request.POST.get('starts_on') or None
        ends_on = request.POST.get('ends_on') or None
        strict_schedule = (request.POST.get('plan_schedule') or 'flex') == 'strict'
        if strict_schedule and not (starts_on and ends_on):
            messages.error(request, 'При жёстком расписании укажите дату начала и окончания.')
            return HttpResponseRedirect(reverse('plans:list'))
        raw_wt = (request.POST.get('workout_type') or '').strip()
        allowed_wt = {c[0] for c in WorkoutType.choices}
        if raw_wt and raw_wt not in allowed_wt:
            messages.error(request, 'Некорректный тип тренировки.')
            return HttpResponseRedirect(reverse('plans:list'))
        workout_type_val = raw_wt if raw_wt in allowed_wt else ''
        raw_dur = (request.POST.get('duration_minutes') or '').strip()
        duration_minutes = None
        if raw_dur:
            try:
                dv = int(raw_dur)
            except ValueError:
                messages.error(request, 'Некорректная длительность тренировки.')
                return HttpResponseRedirect(reverse('plans:list'))
            if not (1 <= dv <= 600):
                messages.error(request, 'Длительность: от 1 до 600 минут.')
                return HttpResponseRedirect(reverse('plans:list'))
            duration_minutes = dv
        ex_ids = request.POST.getlist('exercise_id')
        sets_list = request.POST.getlist('target_sets')
        reps_list = request.POST.getlist('target_reps')
        weights = request.POST.getlist('target_weight_kg')
        if not ex_ids:
            messages.error(request, 'Добавьте хотя бы одно упражнение.')
            return HttpResponseRedirect(reverse('plans:list'))
        try:
            sets_vals = [int(s) for s in sets_list]
            reps_vals = [int(r) for r in reps_list]
        except ValueError:
            messages.error(request, 'Некорректные числа подходов или повторов.')
            return HttpResponseRedirect(reverse('plans:list'))
        if not len(ex_ids) == len(sets_vals) == len(reps_vals):
            messages.error(request, 'Несовпадение количества полей.')
            return HttpResponseRedirect(reverse('plans:list'))
        with transaction.atomic():
            plan = TrainingPlan.objects.create(
                name=name,
                description=description,
                author=request.user,
                starts_on=starts_on or None,
                ends_on=ends_on or None,
                workout_type=workout_type_val,
                duration_minutes=duration_minutes,
                is_public=request.POST.get('plan_is_public') == 'on',
                strict_schedule=strict_schedule,
            )
            for order, eid in enumerate(ex_ids):
                w = None
                if weights and len(weights) > order and (weights[order] or '').strip():
                    try:
                        w = Decimal(str(weights[order]).replace(',', '.'))
                    except Exception:
                        w = None
                PlanExercise.objects.create(plan=plan, exercise_id=int(eid), order=order, target_sets=max(1, sets_vals[order]), target_reps=max(1, reps_vals[order]), target_weight_kg=w)
        messages.success(request, 'План сохранён. Назначьте спортсменов на странице плана.')
        return HttpResponseRedirect(reverse('plans:list'))


class PlanCatalogSelfAddView(LoginRequiredMixin, ApprovedUserMixin, View):
    """Спортсмен добавляет себе общедоступный план из каталога."""

    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        if can_manage_plans(request.user):
            messages.error(request, 'Каталог для самостоятельного добавления доступен спортсменам.')
            return HttpResponseRedirect(reverse('plans:list'))
        raw = request.POST.get('plan_id')
        if not raw or not str(raw).isdigit():
            messages.error(request, 'Некорректный план.')
            return HttpResponseRedirect(reverse('plans:list'))
        plan = get_object_or_404(TrainingPlan.objects.filter(is_public=True), pk=int(raw))
        with transaction.atomic():
            assignment, created = PlanAssignment.objects.get_or_create(
                plan=plan,
                athlete=request.user,
                defaults={'assigned_by': None, 'status': PlanAssignment.Status.ACTIVE},
            )
            if not created:
                if assignment.status != PlanAssignment.Status.ACTIVE:
                    assignment.status = PlanAssignment.Status.ACTIVE
                    assignment.save(update_fields=['status'])
                messages.info(request, 'Этот план уже в списке «Мои планы».')
            else:
                messages.success(request, f'План «{plan.name}» добавлен в «Мои планы».')
        next_url = (request.POST.get('next') or '').strip()
        if next_url.startswith('/plans/') and not next_url.startswith('//'):
            return HttpResponseRedirect(next_url)
        return HttpResponseRedirect(reverse('plans:list'))


class PlanDetailView(LoginRequiredMixin, ApprovedUserMixin, PlanAccessMixin, DetailView):
    model = TrainingPlan
    template_name = 'plans/plan_detail.html'
    context_object_name = 'plan'
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return TrainingPlan.objects.select_related('author').prefetch_related('plan_exercises__exercise', 'assignments__athlete').annotate(exercise_count=Count('plan_exercises', distinct=True))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav'] = 'plans'
        user = self.request.user
        ctx['is_author'] = self.object.author_id == user.id
        ctx['is_staff_elevated'] = user.is_elevated_staff()
        ctx['plan_exercises'] = self.object.plan_exercises.select_related('exercise').order_by('order', 'id')
        ctx['assignments'] = self.object.assignments.select_related('athlete').order_by('athlete__email')
        if user.role == Role.ATHLETE or not can_manage_plans(user):
            ctx['my_assignment'] = PlanAssignment.objects.filter(plan=self.object, athlete=user).first()
        ctx['show_catalog_add_self'] = bool(self.object.is_public and not can_manage_plans(user))
        return ctx


class PlanAssignAthletesApiView(LoginRequiredMixin, ApprovedUserMixin, View):
    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk, *args, **kwargs):
        plan = get_object_or_404(TrainingPlan.objects.select_related('author'), pk=pk)
        user = request.user
        if plan.author_id != user.id or not can_manage_plans(user):
            return JsonResponse({'error': 'forbidden'}, status=403)
        assigned_ids = set(PlanAssignment.objects.filter(plan=plan).values_list('athlete_id', flat=True))
        athlete_list: list[dict[str, object]] = []
        for a in confirmed_athletes_for_trainer(user):
            athlete_list.append({'id': a.pk, 'name': a.get_full_name() or a.email, 'email': a.email, 'assigned': a.pk in assigned_ids})
        return JsonResponse({'athletes': athlete_list})


class PlanAssignToggleView(LoginRequiredMixin, ApprovedUserMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, pk, *args, **kwargs):
        plan = get_object_or_404(TrainingPlan.objects.select_related('author'), pk=pk)
        user = request.user
        if plan.author_id != user.id or not can_manage_plans(user):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)
        raw_aid = body.get('athlete_id')
        try:
            athlete_id = int(raw_aid)
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'athlete_id'}, status=400)
        assign = bool(body.get('assign'))
        allowed = set(confirmed_athletes_for_trainer(user).values_list('pk', flat=True))
        if athlete_id not in allowed:
            return JsonResponse({'ok': False, 'error': 'not your athlete'}, status=400)
        athlete = get_object_or_404(CustomUser, pk=athlete_id, role=Role.ATHLETE)
        if assign:
            assignment, created = PlanAssignment.objects.get_or_create(plan=plan, athlete=athlete, defaults={'assigned_by': user, 'status': PlanAssignment.Status.ACTIVE})
            notify = created
            if not created and assignment.status != PlanAssignment.Status.ACTIVE:
                assignment.status = PlanAssignment.Status.ACTIVE
                assignment.assigned_by = user
                assignment.save(update_fields=['status', 'assigned_by'])
                notify = True
            if notify:
                Notification.objects.create(recipient=athlete, message=f'Вам назначен новый план: {plan.name}', link=reverse('plans:detail', kwargs={'pk': plan.pk}))
        else:
            PlanAssignment.objects.filter(plan=plan, athlete=athlete).delete()
        return JsonResponse({'ok': True, 'assigned': assign})


class PlanUpdateView(LoginRequiredMixin, ApprovedUserMixin, UserPassesTestMixin, UpdateView):
    model = TrainingPlan
    form_class = TrainingPlanMetaForm
    template_name = 'plans/plan_edit.html'
    context_object_name = 'plan'
    http_method_names = ['get', 'post', 'head', 'options']

    def test_func(self) -> bool:
        plan = get_object_or_404(TrainingPlan, pk=self.kwargs['pk'])
        user = self.request.user
        return plan.author_id == user.id and can_manage_plans(user)

    def handle_no_permission(self):
        messages.error(self.request, 'Редактирование доступно только автору.')
        return HttpResponseRedirect(reverse('plans:list'))

    def get_object(self, queryset=None):
        return get_object_or_404(TrainingPlan, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav'] = 'plans'
        ctx['exercises'] = Exercise.objects.all()[:300]
        ctx['plan_exercises'] = self.object.plan_exercises.select_related('exercise').order_by('order', 'id')
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.test_func():
            return self.handle_no_permission()
        form = TrainingPlanMetaForm(request.POST, instance=self.object)
        if not form.is_valid():
            for err in form.non_field_errors():
                messages.error(request, err)
            if not form.non_field_errors():
                messages.error(request, 'Проверьте поля плана.')
            return self.form_invalid(form)
        ex_ids = request.POST.getlist('exercise_id')
        sets_list = request.POST.getlist('target_sets')
        reps_list = request.POST.getlist('target_reps')
        weights = request.POST.getlist('target_weight_kg')
        if not ex_ids:
            messages.error(request, 'Нужна хотя бы одна строка упражнения.')
            return self.form_invalid(form)
        try:
            sets_vals = [int(s) for s in sets_list]
            reps_vals = [int(r) for r in reps_list]
        except ValueError:
            messages.error(request, 'Некорректные числа подходов или повторов.')
            return self.form_invalid(form)
        if not len(ex_ids) == len(sets_vals) == len(reps_vals):
            messages.error(request, 'Несовпадение полей упражнений.')
            return self.form_invalid(form)
        with transaction.atomic():
            plan = form.save()
            plan.plan_exercises.all().delete()
            for order, eid in enumerate(ex_ids):
                w = None
                if weights and len(weights) > order and (weights[order] or '').strip():
                    try:
                        w = Decimal(str(weights[order]).replace(',', '.'))
                    except Exception:
                        w = None
                PlanExercise.objects.create(plan=plan, exercise_id=int(eid), order=order, target_sets=max(1, sets_vals[order]), target_reps=max(1, reps_vals[order]), target_weight_kg=w)
        messages.success(request, 'План обновлён.')
        return HttpResponseRedirect(reverse('plans:detail', kwargs={'pk': plan.pk}))

class PlanDeleteView(LoginRequiredMixin, ApprovedUserMixin, UserPassesTestMixin, DeleteView):
    model = TrainingPlan
    success_url = reverse_lazy('plans:list')
    http_method_names = ['post', 'head', 'options']

    def test_func(self):
        plan = get_object_or_404(TrainingPlan, pk=self.kwargs['pk'])
        user = self.request.user
        if user.is_elevated_staff():
            return True
        return plan.author_id == user.id

    def handle_no_permission(self):
        messages.error(self.request, 'Удаление доступно только автору или персоналу.')
        return HttpResponseRedirect(reverse('plans:list'))
