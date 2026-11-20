from django.contrib import admin
from .models import LeaveType, LeaveBalance, LeaveRequest, Notification


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_days_per_year', 'is_paid', 'requires_attachment', 'is_active')
    list_filter = ('is_paid', 'requires_attachment', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'year', 'allocated_days', 'used_days', 'pending_days', 'get_remaining')
    list_filter = ('year', 'leave_type')
    search_fields = ('employee__username', 'employee__employee_id', 'leave_type__name')
    ordering = ('employee', 'year')

    @admin.display(description="Remaining Days")
    def get_remaining(self, obj):
        return obj.remaining_days


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'current_step_order', 'created_at')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('employee__username', 'employee__employee_id', 'reason')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'is_read', 'related_leave_request', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('recipient__username', 'message')
    ordering = ('-created_at',)
