from __future__ import annotations
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from plans.models import TrainingPlan
from users.models import Role, TrainerProfile

User = get_user_model()


def pulse_is_admin(user) -> bool:
    return bool(user.is_superuser or user.role == Role.ADMIN)


class StaffRequiredMixin(UserPassesTestMixin):

    def test_func(self) -> bool:
        u = self.request.user
        return bool(u.is_authenticated and u.is_staff)

    def handle_no_permission(self):
        messages.error(self.request, 'Доступ к панели персонала только у сотрудников.')
        return HttpResponseRedirect(reverse('dashboard:landing'))


class StaffElevatedMixin(UserPassesTestMixin):
    """Администратор или модератор Pulse."""

    def test_func(self) -> bool:
        u = self.request.user
        return bool(u.is_authenticated and u.is_elevated_staff())

    def handle_no_permission(self):
        messages.error(self.request, 'Недостаточно прав.')
        return HttpResponseRedirect(reverse('dashboard:landing'))


@transaction.atomic
def _apply_user_role_change(target, new_role: str) -> None:
    old = target.role
    if old == Role.TRAINER and new_role != Role.TRAINER:
        TrainerProfile.objects.filter(user=target).delete()
    target.role = new_role
    target.is_staff = new_role in (Role.ADMIN, Role.MODERATOR)
    if new_role == Role.TRAINER:
        target.trainer_verified = True
    target.save()
    if new_role == Role.TRAINER:
        TrainerProfile.objects.get_or_create(user=target)


class StaffDashboardView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'staff/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav_staff'] = 'home'
        ctx['stat_users'] = User.objects.count()
        ctx['stat_trainers'] = User.objects.filter(role=Role.TRAINER).count()
        ctx['stat_plans'] = TrainingPlan.objects.count()
        return ctx


class StaffUserProfileView(LoginRequiredMixin, StaffElevatedMixin, TemplateView):
    template_name = 'staff/user_profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = get_object_or_404(User, pk=self.kwargs['pk'])
        ctx['nav_staff'] = 'users'
        ctx['profile_user'] = u
        ctx['initials'] = (u.first_name[:1] + u.last_name[:1]).upper() if u.first_name else u.email[:2].upper()
        return ctx


class StaffUsersView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'staff/users.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav_staff'] = 'users'
        qs = User.objects.all().order_by('-date_joined')
        role = (self.request.GET.get('role') or '').strip()
        if role in {Role.ATHLETE, Role.TRAINER, Role.ADMIN, Role.MODERATOR}:
            qs = qs.filter(role=role)
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(username__icontains=q))
        ctx['users_list'] = qs[:500]
        ctx['filter_role'] = role
        ctx['search_q'] = q
        ctx['role_choices'] = Role.choices
        ctx['staff_is_admin'] = pulse_is_admin(self.request.user)
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        uid = request.POST.get('user_id')
        if not uid or not str(uid).isdigit():
            messages.error(request, 'Некорректный запрос.')
            return HttpResponseRedirect(reverse('dashboard:staff_users'))
        target = get_object_or_404(User, pk=int(uid))

        if action == 'confirm_trainer':
            if not request.user.is_elevated_staff():
                messages.error(request, 'Недостаточно прав.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            if target.role != Role.TRAINER:
                messages.error(request, 'Подтверждение только для роли «Тренер».')
            elif target.trainer_verified:
                messages.info(request, 'Тренер уже подтверждён.')
            else:
                target.trainer_verified = True
                target.save(update_fields=['trainer_verified'])
                messages.success(request, f'Тренер {target.email} подтверждён.')
            return HttpResponseRedirect(reverse('dashboard:staff_users'))

        if action == 'toggle_active':
            if not pulse_is_admin(request.user):
                messages.error(request, 'Блокировка доступна только администратору.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            if target.pk == request.user.pk:
                messages.error(request, 'Нельзя изменить статус своей учётной записи.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            state = 'разблокирован' if target.is_active else 'заблокирован'
            messages.success(request, f'Пользователь {target.email} {state}.')
            return HttpResponseRedirect(reverse('dashboard:staff_users'))

        if action == 'update_role':
            if not pulse_is_admin(request.user):
                messages.error(request, 'Смена роли доступна только администратору.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            if target.pk == request.user.pk:
                messages.error(request, 'Нельзя изменить свою роль через эту форму.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            new_role = (request.POST.get('role') or '').strip()
            if new_role not in {Role.ADMIN, Role.MODERATOR, Role.TRAINER, Role.ATHLETE}:
                messages.error(request, 'Некорректная роль.')
                return HttpResponseRedirect(reverse('dashboard:staff_users'))
            _apply_user_role_change(target, new_role)
            messages.success(request, f'Роль пользователя {target.email} обновлена.')
            return HttpResponseRedirect(reverse('dashboard:staff_users'))

        messages.error(request, 'Неизвестное действие.')
        return HttpResponseRedirect(reverse('dashboard:staff_users'))


class StaffPlansView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'staff/plans.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav_staff'] = 'plans'
        plans = (
            TrainingPlan.objects.select_related('author')
            .annotate(exercise_count=Count('plan_exercises'))
            .order_by('-updated_at')
        )
        q = (self.request.GET.get('q') or '').strip()
        public_raw = (self.request.GET.get('public') or '').strip()

        raw_uid = (self.request.GET.get('user') or '').strip()
        filter_user = None
        if raw_uid.isdigit():
            filter_user = User.objects.filter(pk=int(raw_uid)).first()
            if filter_user:
                plans = plans.filter(
                    Q(author_id=filter_user.pk) | Q(assignments__athlete_id=filter_user.pk)
                ).distinct()

        if q:
            plans = plans.filter(
                Q(name__icontains=q)
                | Q(author__email__icontains=q)
                | Q(author__username__icontains=q)
            )

        filter_public = ''
        if public_raw == '1':
            plans = plans.filter(is_public=True)
            filter_public = '1'
        elif public_raw == '0':
            plans = plans.filter(is_public=False)
            filter_public = '0'

        ctx['plans_list'] = plans[:500]
        ctx['filter_user'] = filter_user
        ctx['search_q'] = q
        ctx['filter_public'] = filter_public
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('action') != 'delete_plan':
            return HttpResponseRedirect(reverse('dashboard:staff_plans'))
        pid = request.POST.get('plan_id')
        if not pid or not pid.isdigit():
            messages.error(request, 'Некорректный идентификатор плана.')
            return HttpResponseRedirect(reverse('dashboard:staff_plans'))
        plan = get_object_or_404(TrainingPlan, pk=int(pid))
        name = plan.name
        with transaction.atomic():
            plan.delete()
        messages.success(request, f'План «{name}» удалён.')
        fu = (request.POST.get('filter_user') or '').strip()
        pres_q = (request.POST.get('pres_q') or '').strip()
        pres_pub = (request.POST.get('pres_public') or '').strip()
        query = {}
        if fu.isdigit():
            query['user'] = int(fu)
        if pres_q:
            query['q'] = pres_q
        if pres_pub in ('0', '1'):
            query['public'] = pres_pub
        base = reverse('dashboard:staff_plans')
        if query:
            return HttpResponseRedirect(f'{base}?{urlencode(query)}')
        return HttpResponseRedirect(base)


class StaffPlanDetailView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'staff/plan_detail.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nav_staff'] = 'plans'
        plan = get_object_or_404(
            TrainingPlan.objects.select_related('author').prefetch_related(
                'plan_exercises__exercise',
                'assignments__athlete',
                'assignments__assigned_by',
            ),
            pk=self.kwargs['pk'],
        )
        ctx['plan'] = plan
        ctx['plan_exercises'] = plan.plan_exercises.select_related('exercise').order_by('order', 'id')
        ctx['assignments'] = plan.assignments.select_related('athlete', 'assigned_by').order_by('athlete__email')
        return ctx
