from django.urls import path
from . import views
app_name = 'users'
urlpatterns = [path('login/', views.PulseLoginView.as_view(), name='login'), path('logout/', views.PulseLogoutView.as_view(), name='logout'), path('register/', views.RegisterView.as_view(), name='register'), path('trainer-pending/', views.TrainerPendingView.as_view(), name='trainer_pending')]
