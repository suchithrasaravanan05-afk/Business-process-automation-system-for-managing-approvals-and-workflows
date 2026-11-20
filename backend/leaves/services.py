from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from audit.models import AuditLog
from workflows.models import Workflow, WorkflowStep, ApprovalStepInstance
from .models import LeaveType, LeaveBalance, LeaveRequest, Notification


def calculate_leave_days(start_date, end_date) -> Decimal:
    """
    Calculates the total number of calendar days (inclusive) between start_date and end_date.
    Validates that start_date does not exceed end_date.
    """
    if not start_date or not end_date:
        raise ValidationError("Both start date and end date are required.")
    if start_date > end_date:
        raise ValidationError("End date cannot be earlier than start date.")
    
    total = (end_date - start_date).days + 1
    return Decimal(total)


def ensure_default_workflow() -> Workflow:
    """
    Ensures that a default multi-level workflow exists in the database.
    Stores the business rules as configurable data in WorkflowStep:
      - Step 1: Direct Manager (min_days=0, applies to all leaves)
      - Step 2: HR / Admin (min_days=6, applies only to leaves longer than 5 days)
    """
    workflow, _ = Workflow.objects.get_or_create(
        name="Standard Multi-Level Leave Approval Workflow",
        defaults={
            'description': "Tier 1: Direct Manager (All leaves). Tier 2: HR Admin (Leaves > 5 days).",
            'is_active': True
        }
    )

    # Step 1: Manager approval for all leaves
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

    return workflow


def get_applicable_workflow_steps(total_days: Decimal, workflow: Workflow = None):
    """
    Queries WorkflowStep data to find which approval levels apply for the given duration.
    Evaluates min_days and max_days dynamically from database rows.
    """
    if not workflow:
        workflow = Workflow.objects.filter(is_active=True).first()
        if not workflow:
            workflow = ensure_default_workflow()

    # Query steps where min_days <= total_days and (max_days is None or max_days >= total_days)
    steps = (
        workflow.steps
        .filter(min_days__lte=int(total_days))
        .filter(models.Q(max_days__gte=int(total_days)) | models.Q(max_days__isnull=True))
        .order_by('step_order')
    )
    return steps, workflow


@transaction.atomic
def submit_leave_request(
    employee: User,
    leave_type: LeaveType,
    start_date,
    end_date,
    reason: str,
    ip_address: str = None
) -> LeaveRequest:
    """
    Encapsulates the complete business logic for submitting a leave application:
      1. Calculates total days automatically and validates date logic.
      2. Validates and holds pending balance for the employee.
      3. Retrieves the active workflow and determines the applicable WorkflowSteps based on min_days.
      4. Creates the LeaveRequest in 'SUBMITTED' status.
      5. Instantiates ApprovalStepInstance records for each applicable tier.
      6. Writes an immutable record to AuditLog.
      7. Dispatches in-app notifications to the employee and designated approver.
    """
    # 1. Calculate duration
    total_days = calculate_leave_days(start_date, end_date)

    # 2. Check / update employee's leave balance
    current_year = start_date.year
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=current_year,
        defaults={
            'allocated_days': leave_type.default_days_per_year,
            'used_days': Decimal('0.0'),
            'pending_days': Decimal('0.0')
        }
    )

    # Update pending days in balance
    balance.pending_days += total_days
    balance.save(update_fields=['pending_days'])

    # 3. Resolve workflow and steps based on min_days data
    steps, workflow = get_applicable_workflow_steps(total_days)

    if not steps.exists():
        raise ValidationError("No valid approval workflow step configured for this leave duration.")

    # 4. Create the LeaveRequest with status 'SUBMITTED'
    leave_request = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason.strip(),
        status=LeaveRequest.Status.SUBMITTED,
        workflow=workflow,
        current_step_order=steps.first().step_order
    )

    # 5. Create ApprovalStepInstance records for each applicable step
    assigned_tier1_approver = None
    for step in steps:
        # Determine assigned approver
        assigned_user = None
        if step.approver_role == WorkflowStep.ApproverRole.MANAGER:
            # Route to the employee's direct manager
            assigned_user = employee.manager
            if step.step_order == 1:
                assigned_tier1_approver = assigned_user
        elif step.approver_role == WorkflowStep.ApproverRole.HR_ADMIN:
            # Assigned to HR Admin pool (or first HR user if available)
            hr_user = User.objects.filter(role=User.Role.HR_ADMIN, is_active=True).first()
            assigned_user = hr_user

        ApprovalStepInstance.objects.create(
            leave_request=leave_request,
            workflow_step=step,
            step_order=step.step_order,
            approver_role=step.approver_role,
            assigned_approver=assigned_user,
            status=ApprovalStepInstance.StepStatus.PENDING
        )

    # 6. Record append-only entry in AuditLog
    step_summary = " -> ".join([s.name for s in steps])
    remarks = (
        f"Submitted leave request for {total_days} day(s). "
        f"Workflow assigned: {workflow.name}. Approval pipeline: [{step_summary}]."
    )
    AuditLog.objects.create(
        leave_request=leave_request,
        actor=employee,
        action="SUBMITTED",
        from_status="DRAFT",
        to_status=LeaveRequest.Status.SUBMITTED,
        remarks=remarks,
        ip_address=ip_address
    )

    # 7. Create notifications
    # Notification for the employee
    Notification.objects.create(
        recipient=employee,
        message=f"Your {leave_type.name} request (#{leave_request.id}) for {total_days} day(s) was submitted successfully.",
        related_leave_request=leave_request
    )

    # Notification for the first approver
    if assigned_tier1_approver:
        Notification.objects.create(
            recipient=assigned_tier1_approver,
            message=(
                f"New leave request (#{leave_request.id}) submitted by {employee.get_full_name() or employee.username} "
                f"for {total_days} day(s). Awaiting your approval."
            ),
            related_leave_request=leave_request
        )

    return leave_request
