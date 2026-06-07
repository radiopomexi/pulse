from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect


class ApprovedUserMixin(UserPassesTestMixin):

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (not u.is_blocked_trainer())

    def handle_no_permission(self):
        if self.request.user.is_authenticated and self.request.user.is_blocked_trainer():
            return redirect('users:trainer_pending')
        return redirect('users:login')


class ApprovedUserJsonMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Как ApprovedUserMixin, но для JSON API: без HTML-редиректа (fetch не ломается)."""

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (not u.is_blocked_trainer())

    def handle_no_permission(self):
        return JsonResponse({'error': 'forbidden'}, status=403)
