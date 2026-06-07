from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, TrainerAthleteLink, TrainerProfile

class TrainerAthleteLinkInline(admin.TabularInline):
    model = TrainerAthleteLink
    extra = 0
    autocomplete_fields = ('athlete',)

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'trainer_verified', 'is_staff')
    list_filter = ('role', 'trainer_verified', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    fieldsets = ((None, {'fields': ('email', 'username', 'password')}), ('Персоналия', {'fields': ('first_name', 'last_name', 'avatar', 'role', 'trainer_verified')}), ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}), ('Даты', {'fields': ('last_login', 'date_joined')}))
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'username', 'password1', 'password2', 'role', 'trainer_verified')}),)

@admin.register(TrainerProfile)
class TrainerProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = [TrainerAthleteLinkInline]
