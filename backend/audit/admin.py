from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'leave_request', 'actor', 'action', 'from_status', 'to_status', 'ip_address')
    list_filter = ('action', 'from_status', 'to_status', 'created_at')
    search_fields = ('leave_request__id', 'actor__username', 'action', 'remarks', 'ip_address')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    # Strict append-only protections in Django Admin:
    def has_add_permission(self, request):
        # Audit logs should only be generated automatically by application actions
        return False

    def has_change_permission(self, request, obj=None):
        # Prevent editing audit logs
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting audit logs
        return False
