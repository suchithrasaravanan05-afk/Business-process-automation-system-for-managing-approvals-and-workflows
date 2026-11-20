from django.contrib import admin
from .models import Workflow, WorkflowStep, ApprovalStepInstance


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1
    fields = ('step_order', 'name', 'approver_role', 'min_days', 'max_days')
    ordering = ('step_order',)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [WorkflowStepInline]


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'step_order', 'name', 'approver_role', 'min_days', 'max_days')
    list_filter = ('approver_role', 'workflow')
    search_fields = ('name', 'workflow__name')
    ordering = ('workflow', 'step_order')


@admin.register(ApprovalStepInstance)
class ApprovalStepInstanceAdmin(admin.ModelAdmin):
    list_display = ('leave_request', 'step_order', 'approver_role', 'assigned_approver', 'status', 'decision_at')
    list_filter = ('status', 'approver_role')
    search_fields = ('leave_request__id', 'assigned_approver__username', 'comments')
    ordering = ('-created_at',)
