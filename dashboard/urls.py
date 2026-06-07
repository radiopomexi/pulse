from django.urls import path

from . import staff_views, views

app_name = "dashboard"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("notifications/api/list/", views.NotificationsListApiView.as_view(), name="notifications_api_list"),
    path("notifications/api/mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="notifications_mark_all_read"),
    path("notifications/api/<int:pk>/read/", views.NotificationMarkReadView.as_view(), name="notifications_mark_read"),
    path("dashboard/admin/", staff_views.StaffDashboardView.as_view(), name="staff_home"),
    path("dashboard/admin/users/", staff_views.StaffUsersView.as_view(), name="staff_users"),
    path("dashboard/admin/plans/<int:pk>/", staff_views.StaffPlanDetailView.as_view(), name="staff_plan_detail"),
    path("dashboard/admin/plans/", staff_views.StaffPlansView.as_view(), name="staff_plans"),
    path("dashboard/", views.DashboardView.as_view(), name="home"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("profile/weight/", views.WeightTrackingView.as_view(), name="profile_weight"),
    path("profile/<int:pk>/", staff_views.StaffUserProfileView.as_view(), name="user_profile"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("athlete/<int:pk>/", views.AthleteProfileView.as_view(), name="athlete_profile"),
    path("athlete/<int:pk>/weight/", views.AthleteWeightTrackingView.as_view(), name="athlete_weight"),
    path("calculator/", views.CalculatorView.as_view(), name="calculator"),
    path("api/plans/<int:pk>/data/", views.CalendarPlanDataApiView.as_view(), name="api_plan_data"),
    path("calendar/api/day/", views.CalendarDayApiView.as_view(), name="calendar_api_day"),
    path("calendar/api/plan-exercises/", views.CalendarPlanExercisesApiView.as_view(), name="calendar_api_plan_exercises"),
    path("calendar/api/session/save/", views.CalendarSessionSaveView.as_view(), name="calendar_session_save"),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
]
