from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, Department
from audit.models import AuditLog
from leaves.models import LeaveType, LeaveBalance, LeaveRequest
from leaves.services import submit_leave_request, calculate_leave_days, ensure_default_workflow
from workflows.models import Workflow, WorkflowStep, ApprovalStepInstance


class LeaveWorkflowAndAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create department
        self.dept = Department.objects.create(name="Engineering", code="ENG")

        # Create users
        self.hr_user = User.objects.create_user(
            username="hr_test",
            password="testpassword",
            role=User.Role.HR_ADMIN,
            department=self.dept
        )
        self.mgr_user = User.objects.create_user(
            username="mgr_test",
            password="testpassword",
            role=User.Role.MANAGER,
            department=self.dept,
            manager=self.hr_user
        )
        self.emp_user = User.objects.create_user(
            username="emp_test",
            password="testpassword",
            role=User.Role.EMPLOYEE,
            department=self.dept,
            manager=self.mgr_user
        )

        # Ensure default workflow with data-driven steps
        self.workflow = ensure_default_workflow()

        # Create Leave Types
        self.annual_leave = LeaveType.objects.create(
            name="Annual Leave",
            code="AL",
            default_days_per_year=Decimal('15.0')
        )

        # Initialize balance
        self.balance = LeaveBalance.objects.create(
            employee=self.emp_user,
            leave_type=self.annual_leave,
            year=date.today().year,
            allocated_days=Decimal('15.0'),
            used_days=Decimal('0.0'),
            pending_days=Decimal('0.0')
        )

    def test_role_based_login_redirect(self):
        """Verify Employee, Manager, and HR each redirect to their respective dashboard."""
        # Test Employee Login
        self.client.login(username="emp_test", password="testpassword")
        res = self.client.get(reverse('dashboard_redirect'))
        self.assertRedirects(res, reverse('employee_dashboard'))
        self.client.logout()

        # Test Manager Login
        self.client.login(username="mgr_test", password="testpassword")
        res = self.client.get(reverse('dashboard_redirect'))
        self.assertRedirects(res, reverse('manager_dashboard'))
        self.client.logout()

        # Test HR Login
        self.client.login(username="hr_test", password="testpassword")
        res = self.client.get(reverse('dashboard_redirect'))
        self.assertRedirects(res, reverse('hr_dashboard'))
        self.client.logout()

    def test_leave_duration_calculation(self):
        """Test calculation of inclusive calendar days."""
        start = date(2026, 11, 23)
        end = date(2026, 11, 25)
        # Nov 23, 24, 25 = 3 days
        self.assertEqual(calculate_leave_days(start, end), Decimal('3'))

    def test_submission_short_leave_triggers_manager_only(self):
        """Leaves <= 5 days must trigger ONLY Step 1 (Manager approval)."""
        start = date(2026, 11, 23)
        end = date(2026, 11, 25) # 3 days

        req = submit_leave_request(
            employee=self.emp_user,
            leave_type=self.annual_leave,
            start_date=start,
            end_date=end,
            reason="Short personal leave",
            ip_address="127.0.0.1"
        )

        self.assertEqual(req.status, LeaveRequest.Status.SUBMITTED)
        self.assertEqual(req.total_days, Decimal('3'))

        # Check approval steps generated
        steps = req.approval_steps.all().order_by('step_order')
        self.assertEqual(steps.count(), 1)
        self.assertEqual(steps[0].step_order, 1)
        self.assertEqual(steps[0].approver_role, WorkflowStep.ApproverRole.MANAGER)
        self.assertEqual(steps[0].assigned_approver, self.mgr_user)
        self.assertEqual(steps[0].status, ApprovalStepInstance.StepStatus.PENDING)

        # Check Audit Log created
        audit_entry = AuditLog.objects.filter(leave_request=req).first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.action, "SUBMITTED")
        self.assertEqual(audit_entry.actor, self.emp_user)
        self.assertEqual(audit_entry.to_status, LeaveRequest.Status.SUBMITTED)

        # Check balance pending days updated
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.pending_days, Decimal('3'))

    def test_submission_long_leave_triggers_manager_and_hr(self):
        """Leaves > 5 days (e.g. 7 days) must trigger Step 1 (Manager) AND Step 2 (HR)."""
        start = date(2026, 11, 23)
        end = date(2026, 11, 29) # 7 days (> 5 days)

        req = submit_leave_request(
            employee=self.emp_user,
            leave_type=self.annual_leave,
            start_date=start,
            end_date=end,
            reason="Family vacation trip",
            ip_address="127.0.0.1"
        )

        self.assertEqual(req.status, LeaveRequest.Status.SUBMITTED)
        self.assertEqual(req.total_days, Decimal('7'))

        # Check approval steps generated
        steps = req.approval_steps.all().order_by('step_order')
        self.assertEqual(steps.count(), 2)

        # Step 1: Manager
        self.assertEqual(steps[0].step_order, 1)
        self.assertEqual(steps[0].approver_role, WorkflowStep.ApproverRole.MANAGER)
        self.assertEqual(steps[0].assigned_approver, self.mgr_user)

        # Step 2: HR Admin
        self.assertEqual(steps[1].step_order, 2)
        self.assertEqual(steps[1].approver_role, WorkflowStep.ApproverRole.HR_ADMIN)
        self.assertEqual(steps[1].assigned_approver, self.hr_user)

    def test_audit_log_append_only_immutability(self):
        """AuditLog must raise PermissionDenied when trying to update or delete."""
        start = date(2026, 11, 23)
        end = date(2026, 11, 24)

        req = submit_leave_request(
            employee=self.emp_user,
            leave_type=self.annual_leave,
            start_date=start,
            end_date=end,
            reason="Short leave"
        )

        audit_entry = AuditLog.objects.filter(leave_request=req).first()

        # Verify update is prohibited
        with self.assertRaises(PermissionDenied):
            audit_entry.action = "TAMPERED_ACTION"
            audit_entry.save()

        # Verify deletion is prohibited
        with self.assertRaises(PermissionDenied):
            audit_entry.delete()

    def test_apply_leave_via_http_post(self):
        """Test submitting the application via the web form view."""
        self.client.login(username="emp_test", password="testpassword")

        post_data = {
            'leave_type': self.annual_leave.id,
            'start_date': '2026-12-01',
            'end_date': '2026-12-04', # 4 days
            'reason': 'Attending a conference'
        }
        res = self.client.post(reverse('apply_leave'), post_data)
        self.assertRedirects(res, reverse('my_requests'))

        req = LeaveRequest.objects.filter(employee=self.emp_user, reason='Attending a conference').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.total_days, Decimal('4'))
        self.assertEqual(req.approval_steps.count(), 1) # <= 5 days -> 1 step

    def test_my_requests_view(self):
        """Test that the My Requests page renders successfully."""
        self.client.login(username="emp_test", password="testpassword")
        res = self.client.get(reverse('my_requests'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'leaves/my_requests.html')
