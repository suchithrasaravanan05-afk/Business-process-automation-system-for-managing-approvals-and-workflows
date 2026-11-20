from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import LeaveApplicationForm
from .models import LeaveBalance, LeaveRequest
from .services import submit_leave_request


def get_client_ip(request):
    """Utility helper to capture user's IP for append-only audit logging."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def apply_leave_view(request):
    """
    View for employees to apply for leave.
    Collects leave parameters and delegates execution to the services.py layer.
    """
    current_year = timezone.now().year
    balances = LeaveBalance.objects.filter(employee=request.user, year=current_year).select_related('leave_type')

    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST)
        if form.is_valid():
            try:
                leave_request = submit_leave_request(
                    employee=request.user,
                    leave_type=form.cleaned_data['leave_type'],
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date'],
                    reason=form.cleaned_data['reason'],
                    ip_address=get_client_ip(request)
                )
                messages.success(
                    request,
                    f"Leave Request #{leave_request.id} for {leave_request.total_days} day(s) "
                    f"submitted successfully and routed to approval workflow!"
                )
                return redirect('my_requests')
            except ValidationError as ve:
                messages.error(request, f"Validation Error: {ve.message if hasattr(ve, 'message') else str(ve)}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while processing your request: {str(e)}")
    else:
        form = LeaveApplicationForm()

    context = {
        'form': form,
        'balances': balances,
        'current_year': current_year,
    }
    return render(request, 'leaves/apply.html', context)


@login_required
def my_requests_view(request):
    """
    Lists all leave requests submitted by the currently logged-in employee,
    including approval progress and step instances.
    """
    leave_requests = (
        LeaveRequest.objects.filter(employee=request.user)
        .select_related('leave_type', 'workflow')
        .prefetch_related('approval_steps', 'approval_steps__assigned_approver')
        .order_by('-created_at')
    )
    return render(request, 'leaves/my_requests.html', {'leave_requests': leave_requests})
