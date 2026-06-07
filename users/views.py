from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, TemplateView
from .forms import EmailLoginForm, RegisterForm
from .models import CustomUser, Role

class PulseLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        user = self.request.user
        if user.is_blocked_trainer():
            return reverse('users:trainer_pending')
        return resolve_url(settings.LOGIN_REDIRECT_URL)

class PulseLogoutView(LogoutView):
    next_page = reverse_lazy('dashboard:landing')

class RegisterView(CreateView):
    model = CustomUser
    form_class = RegisterForm
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('dashboard:home'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object, backend='django.contrib.auth.backends.ModelBackend')
        if self.object.role == Role.TRAINER and (not self.object.trainer_verified):
            messages.info(self.request, 'Аккаунт тренера создан. Дождитесь подтверждения администратором.')
        else:
            messages.success(self.request, 'Добро пожаловать в Pulse.')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        user = self.object
        if user.role == Role.TRAINER and (not user.trainer_verified):
            return reverse('users:trainer_pending')
        return reverse('dashboard:home')

class TrainerPendingView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/trainer_pending.html'

    def test_func(self):
        return self.request.user.is_blocked_trainer()

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('dashboard:home'))
