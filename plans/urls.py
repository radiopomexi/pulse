from django.urls import path
from . import views
app_name = 'plans'
urlpatterns = [
    path('', views.PlanListView.as_view(), name='list'),
    path('catalog/add-self/', views.PlanCatalogSelfAddView.as_view(), name='catalog_add_self'),
    path('catalog/', views.PlanCatalogView.as_view(), name='catalog'),
    path('assignments/<int:pk>/remove/', views.PlanAssignmentRemoveView.as_view(), name='assignment_remove'),
    path('user/<int:user_id>/plans/', views.PlanUserPlansStaffView.as_view(), name='user_plans_staff'),
    path('<int:pk>/assign/athletes/', views.PlanAssignAthletesApiView.as_view(), name='assign_athletes_api'),
    path('<int:pk>/assign/toggle/', views.PlanAssignToggleView.as_view(), name='assign_toggle'),
    path('<int:pk>/', views.PlanDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PlanUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.PlanDeleteView.as_view(), name='delete'),
]
