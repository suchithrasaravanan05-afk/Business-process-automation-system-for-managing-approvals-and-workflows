from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Department, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'employee_id', 'email', 'first_name', 'last_name', 'role', 'department', 'manager', 'is_staff')
    list_filter = ('role', 'department', 'is_staff', 'is_active')
    search_fields = ('username', 'employee_id', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Organization Profile', {
            'fields': ('role', 'department', 'manager', 'employee_id', 'phone_number')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Organization Profile', {
            'fields': ('role', 'department', 'manager', 'employee_id', 'phone_number')
        }),
    )
