from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'department', 'is_active', 'is_staff')
    list_filter = ('role', 'department', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        (_('Warehouse info'), {'fields': ('role', 'department', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Warehouse info'), {'fields': ('role', 'department', 'phone')}),
    )
