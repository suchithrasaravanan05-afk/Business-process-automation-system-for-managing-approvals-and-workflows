from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Workflow(models.Model):
    """
    Represents an approval workflow definition.
    Allows HR/Admins to configure approval chains without modifying backend code.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Workflow name (e.g., Default Company Leave Workflow)")
    description = models.TextField(blank=True, help_text="Summary of when this workflow applies")
    is_active = models.BooleanField(default=True, help_text="Whether this workflow is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status})"


class WorkflowStep(models.Model):
    """
    Defines an approval tier within a workflow.
    Rule parameters (such as minimum days for HR approval) are stored directly as data
    so admins can change policies dynamically via the admin interface without code changes.
    """
    class ApproverRole(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        HR_ADMIN = 'HR_ADMIN', 'HR / Admin'

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='steps',
        help_text="The parent workflow this approval step belongs to"
    )
    step_order = models.PositiveSmallIntegerField(
        default=1,
        help_text="Sequence order of this approval tier (1 for Tier 1, 2 for Tier 2, etc.)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Descriptive step title (e.g., 'Direct Manager Review', 'HR Admin Approval')"
    )
    approver_role = models.CharField(
        max_length=20,
        choices=ApproverRole.choices,
        default=ApproverRole.MANAGER,
        help_text="Role required to approve this step"
    )
    min_days = models.PositiveIntegerField(
        default=0,
        help_text="Minimum leave duration (in days) required to trigger this step. "
                  "E.g., set to 0 for Manager (all leaves), and set to 6 for HR approval (only leaves > 5 days)."
    )
    max_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional upper bound on leave duration (in days). Leave blank for unlimited."
    )

    class Meta:
        ordering = ['workflow', 'step_order']
        unique_together = [('workflow', 'step_order')]
        verbose_name = "Workflow Step"
        verbose_name_plural = "Workflow Steps"
        indexes = [
            models.Index(fields=['workflow', 'step_order']),
            models.Index(fields=['min_days']),
        ]

    def clean(self):
        super().clean()
        if self.max_days is not None and self.min_days > self.max_days:
            raise ValidationError({'max_days': "max_days cannot be less than min_days."})

    def applies_to_duration(self, duration_days):
        """
        Determines dynamically whether this step should be included
        in the approval pipeline for a given leave duration.
        """
        if duration_days < self.min_days:
            return False
        if self.max_days is not None and duration_days > self.max_days:
            return False
        return True

    def __str__(self):
        duration_info = f" (Days: {self.min_days}+)" if self.min_days > 0 else " (All durations)"
        return f"Step {self.step_order}: {self.name} [{self.get_approver_role_display()}]{duration_info}"


class ApprovalStepInstance(models.Model):
    """
    Represents an active or resolved approval step instance for a specific LeaveRequest.
    Created when a leave request is submitted according to the configured WorkflowSteps.
    """
    class StepStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SENT_BACK = 'SENT_BACK', 'Sent Back'
        SKIPPED = 'SKIPPED', 'Skipped'

    leave_request = models.ForeignKey(
        'leaves.LeaveRequest',
        on_delete=models.CASCADE,
        related_name='approval_steps',
        help_text="The leave request requiring this approval"
    )
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.PROTECT,
        related_name='step_instances',
        help_text="The blueprint workflow step from which this instance was generated"
    )
    step_order = models.PositiveSmallIntegerField(
        help_text="Order of execution in the workflow pipeline"
    )
    approver_role = models.CharField(
        max_length=20,
        choices=WorkflowStep.ApproverRole.choices,
        help_text="Required role for actioning this step"
    )
    assigned_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_approvals',
        help_text="Specific user assigned (e.g. employee's direct manager or HR officer)"
    )
    status = models.CharField(
        max_length=20,
        choices=StepStatus.choices,
        default=StepStatus.PENDING,
        help_text="Current state of this approval step"
    )
    comments = models.TextField(
        blank=True,
        help_text="Approver comments or rationale (mandatory on rejection or send-back)"
    )
    decision_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the decision was registered"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']
        unique_together = [('leave_request', 'step_order')]
        verbose_name = "Approval Step Instance"
        verbose_name_plural = "Approval Step Instances"
        indexes = [
            models.Index(fields=['leave_request', 'status']),
            models.Index(fields=['assigned_approver', 'status']),
        ]

    def __str__(self):
        return f"Request #{self.leave_request_id} - Step {self.step_order} [{self.get_status_display()}]"
