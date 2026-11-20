from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    """
    Represents an organizational department (e.g., Engineering, HR, Sales).
    Enables department-level grouping, managerial hierarchies, and reporting.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Department name (e.g., Engineering)")
    code = models.CharField(max_length=20, unique=True, help_text="Unique department abbreviation (e.g., ENG)")
    description = models.TextField(blank=True, help_text="Brief description of the department's scope")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    """
    Custom user model representing all organizational actors.
    Supports role-based authorization and reporting hierarchy via self-referencing manager foreign key.
    """
    class Role(models.TextChoices):
        EMPLOYEE = 'EMPLOYEE', 'Employee'
        MANAGER = 'MANAGER', 'Manager'
        HR_ADMIN = 'HR_ADMIN', 'HR / Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text="Role determining permissions and approval capabilities"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text="Department this user belongs to"
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        help_text="Direct reporting manager responsible for Tier-1 approvals"
    )
    employee_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique company employee ID (e.g., EMP-1001)"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact telephone or mobile number"
    )

    class Meta:
        ordering = ['username']
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['employee_id']),
        ]

    def clean(self):
        super().clean()
        # Prevent self-referential reporting loops
        if self.manager_id and self.pk and self.manager_id == self.pk:
            raise ValidationError({'manager': "A user cannot be their own reporting manager."})

    @property
    def is_leave_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_hr_admin(self):
        return self.role == self.Role.HR_ADMIN

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        return f"{display_name} ({self.get_role_display()})"
