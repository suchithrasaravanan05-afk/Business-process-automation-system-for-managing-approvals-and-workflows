from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLog(models.Model):
    """
    Append-only security and compliance ledger.
    Every lifecycle transition and approval action is permanently recorded here.
    Updating or deleting rows is strictly blocked both at the ORM model level and in the admin.
    """
    leave_request = models.ForeignKey(
        'leaves.LeaveRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="The leave request affected by this action"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions',
        help_text="The user who performed this action (null if automated system action)"
    )
    action = models.CharField(
        max_length=60,
        help_text="The action verb (e.g. DRAFT_CREATED, SUBMITTED, MANAGER_APPROVED, HR_APPROVED, SENT_BACK, REJECTED, RESUBMITTED, CANCELLED)"
    )
    from_status = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text="Status of the leave request prior to this action"
    )
    to_status = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text="Status of the leave request resulting from this action"
    )
    remarks = models.TextField(
        blank=True,
        default='',
        help_text="Approver notes, user reason, or transition context"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address where action was initiated"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Immutable timestamp when the action occurred"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=['leave_request', 'created_at']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['action']),
        ]

    def save(self, *args, **kwargs):
        """
        Enforce append-only integrity: prohibit updating existing records.
        """
        if self.pk is not None:
            raise PermissionDenied("AuditLog entries are append-only and cannot be modified once written.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Enforce append-only integrity: prohibit deleting records.
        """
        raise PermissionDenied("AuditLog entries are append-only and cannot be deleted.")

    def __str__(self):
        req_ref = f"Req #{self.leave_request_id}" if self.leave_request_id else "Global"
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {req_ref} - {self.action} by {actor_name} ({self.from_status} -> {self.to_status})"
