from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class LeaveType(models.Model):
    """
    Defines the categories of leave supported by the organization.
    Stores policy details such as yearly entitlement quota and paid status.
    """
    name = models.CharField(max_length=60, unique=True, help_text="Descriptive leave title (e.g., Casual Leave, Sick Leave)")
    code = models.CharField(max_length=15, unique=True, help_text="Unique shorthand code (e.g., CL, SL, AL)")
    description = models.TextField(blank=True, help_text="Explanation of terms and conditions for this leave type")
    default_days_per_year = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=12.0,
        help_text="Standard annual quota allocated to an employee"
    )
    is_paid = models.BooleanField(default=True, help_text="Indicates whether this leave is compensated")
    requires_attachment = models.BooleanField(
        default=False,
        help_text="Whether supporting documents (e.g. medical certificates) are required"
    )
    is_active = models.BooleanField(default=True, help_text="Whether employees can currently apply for this type")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(models.Model):
    """
    Maintains annual leave quota and usage per employee, per leave type, per calendar year.
    Tracks pending leaves to prevent over-subscription while requests are in review.
    """
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_balances',
        help_text="The employee holding this balance"
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances',
        help_text="The leave category"
    )
    year = models.PositiveIntegerField(help_text="Calendar year for this quota (e.g., 2026)")
    allocated_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        help_text="Total days granted for this year"
    )
    used_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        help_text="Days consumed by approved leave requests"
    )
    pending_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        help_text="Days locked under active (Submitted/In Review) requests"
    )

    class Meta:
        ordering = ['employee', 'year', 'leave_type']
        unique_together = [('employee', 'leave_type', 'year')]
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        indexes = [
            models.Index(fields=['employee', 'year']),
            models.Index(fields=['leave_type', 'year']),
        ]

    @property
    def remaining_days(self):
        """Calculates available balance that can still be applied for."""
        return self.allocated_days - self.used_days - self.pending_days

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.code} ({self.year}): Rem: {self.remaining_days}d"


class LeaveRequest(models.Model):
    """
    Core record representing a time-off application.
    Tracks state transitions through Draft -> Submitted -> In Review -> Approved / Rejected / Sent Back.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        IN_REVIEW = 'IN_REVIEW', 'In Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SENT_BACK = 'SENT_BACK', 'Sent Back'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_requests',
        help_text="The employee requesting time off"
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests',
        help_text="Category of leave"
    )
    start_date = models.DateField(help_text="First day of leave (inclusive)")
    end_date = models.DateField(help_text="Last day of leave (inclusive)")
    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Total number of working days requested"
    )
    reason = models.TextField(help_text="Purpose or justification for time-off request")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Current state in the approval lifecycle"
    )
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests',
        help_text="Workflow definition governing this request"
    )
    current_step_order = models.PositiveSmallIntegerField(
        default=1,
        help_text="The approval tier currently required to act on this request"
    )
    attachment = models.FileField(
        upload_to='leave_attachments/%Y/%m/',
        null=True,
        blank=True,
        help_text="Supporting documentation (medical certificate, travel doc, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': "End date cannot be prior to start date."})
        if self.total_days is not None and self.total_days <= 0:
            raise ValidationError({'total_days': "Total days requested must be greater than zero."})

    def __str__(self):
        return f"REQ-{self.id} | {self.employee.username} ({self.total_days}d) - {self.get_status_display()}"


class Notification(models.Model):
    """
    Stores system and action alerts for users (e.g. approval notices, send-back alerts).
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user receiving this notification"
    )
    message = models.TextField(help_text="Notification alert message content")
    is_read = models.BooleanField(default=False, help_text="Whether the user has viewed this notification")
    created_at = models.DateTimeField(auto_now_add=True)
    related_leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="The leave request this notification pertains to (if any)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"To: {self.recipient.username} [{status}] - {self.message[:40]}"
