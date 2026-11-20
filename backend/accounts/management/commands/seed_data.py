from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, Department
from leaves.models import LeaveType, LeaveBalance
from workflows.models import Workflow, WorkflowStep


class Command(BaseCommand):
    help = "Seeds initial demo data including Departments, Roles, Users, LeaveTypes, Balances, and Multi-level Workflows."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting database seed..."))

        # 1. Create Departments
        eng_dept, _ = Department.objects.get_or_create(
            code="ENG",
            defaults={'name': "Engineering", 'description': "Software development and engineering"}
        )
        hr_dept, _ = Department.objects.get_or_create(
            code="HR",
            defaults={'name': "Human Resources", 'description': "People operations and HR administration"}
        )

        # 2. Create Workflow & Steps (Rule: > 5 days needs HR approval after Manager)
        workflow, _ = Workflow.objects.get_or_create(
            name="Standard Multi-Level Leave Approval Workflow",
            defaults={
                'description': "Tier 1: Direct Manager (All leaves). Tier 2: HR Admin (Leaves > 5 days).",
                'is_active': True
            }
        )

        # Step 1: Manager approval for all leaves (min_days = 0)
        WorkflowStep.objects.get_or_create(
            workflow=workflow,
            step_order=1,
            defaults={
                'name': "Direct Manager Review",
                'approver_role': WorkflowStep.ApproverRole.MANAGER,
                'min_days': 0,
                'max_days': None
            }
        )

        # Step 2: HR approval only for leaves longer than 5 days (min_days = 6)
        WorkflowStep.objects.get_or_create(
            workflow=workflow,
            step_order=2,
            defaults={
                'name': "HR Department Approval",
                'approver_role': WorkflowStep.ApproverRole.HR_ADMIN,
                'min_days': 6,
                'max_days': None
            }
        )

        # 3. Create Leave Types
        annual_leave, _ = LeaveType.objects.get_or_create(
            code="AL",
            defaults={
                'name': "Annual Leave",
                'default_days_per_year': Decimal('15.0'),
                'is_paid': True,
                'is_active': True
            }
        )
        casual_leave, _ = LeaveType.objects.get_or_create(
            code="CL",
            defaults={
                'name': "Casual Leave",
                'default_days_per_year': Decimal('10.0'),
                'is_paid': True,
                'is_active': True
            }
        )
        sick_leave, _ = LeaveType.objects.get_or_create(
            code="SL",
            defaults={
                'name': "Sick Leave",
                'default_days_per_year': Decimal('10.0'),
                'is_paid': True,
                'requires_attachment': True,
                'is_active': True
            }
        )

        # 4. Create Users for each Role
        # HR / Admin user
        hr_user, hr_created = User.objects.get_or_create(
            username="hr_admin",
            defaults={
                'email': "hr@company.com",
                'first_name': "Helen",
                'last_name': "Reed",
                'role': User.Role.HR_ADMIN,
                'department': hr_dept,
                'employee_id': "EMP-HR-001",
                'is_staff': True,
            }
        )
        if hr_created:
            hr_user.set_password("password123")
            hr_user.save()

        # Manager user
        mgr_user, mgr_created = User.objects.get_or_create(
            username="manager_john",
            defaults={
                'email': "john.mgr@company.com",
                'first_name': "John",
                'last_name': "Doe",
                'role': User.Role.MANAGER,
                'department': eng_dept,
                'employee_id': "EMP-MGR-002",
                'manager': hr_user,
            }
        )
        if mgr_created:
            mgr_user.set_password("password123")
            mgr_user.save()

        # Employee user
        emp_user, emp_created = User.objects.get_or_create(
            username="employee_alice",
            defaults={
                'email': "alice.emp@company.com",
                'first_name': "Alice",
                'last_name': "Smith",
                'role': User.Role.EMPLOYEE,
                'department': eng_dept,
                'employee_id': "EMP-DEV-003",
                'manager': mgr_user,  # Alice reports to John Doe!
            }
        )
        if emp_created:
            emp_user.set_password("password123")
            emp_user.save()

        # 5. Initialize Balances for Alice for current year
        current_year = timezone.now().year
        for lt in [annual_leave, casual_leave, sick_leave]:
            LeaveBalance.objects.get_or_create(
                employee=emp_user,
                leave_type=lt,
                year=current_year,
                defaults={
                    'allocated_days': lt.default_days_per_year,
                    'used_days': Decimal('0.0'),
                    'pending_days': Decimal('0.0'),
                }
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("""
Test Accounts (password: password123):
  1. Employee:   employee_alice  (reports to manager_john)
  2. Manager:    manager_john    (reports to hr_admin)
  3. HR / Admin: hr_admin
"""))
