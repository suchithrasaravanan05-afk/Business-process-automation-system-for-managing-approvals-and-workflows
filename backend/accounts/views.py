from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import User
from leaves.models import LeaveBalance, LeaveRequest


def login_view(request):
    """
    Handles user login. If authenticated, redirects users to their role-specific dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Logs out the current user and redirects to login page.
    """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')


@login_required
def dashboard_redirect_view(request):
    """
    Dispatches logged-in users to their respective role-based dashboard:
      - Employee -> Employee Dashboard
      - Manager -> Manager Dashboard
      - HR / Admin -> HR / Admin Dashboard
    """
    role = request.user.role

    if role == User.Role.EMPLOYEE:
        return redirect('employee_dashboard')
    elif role == User.Role.MANAGER:
        return redirect('manager_dashboard')
    elif role == User.Role.HR_ADMIN:
        return redirect('hr_dashboard')
    else:
        # Default fallback for superuser / custom accounts
        return redirect('employee_dashboard')


@login_required
def employee_dashboard_view(request):
    """
    Dashboard landing view for Employee role.
    Displays annual leave quotas, quick statistics, and recent leave applications.
    """
    current_year = timezone.now().year
    balances = LeaveBalance.objects.filter(employee=request.user, year=current_year).select_related('leave_type')
    recent_requests = (
        LeaveRequest.objects.filter(employee=request.user)
        .select_related('leave_type')
        .prefetch_related('approval_steps')
        .order_by('-created_at')[:5]
    )

    stats = {
        'total': LeaveRequest.objects.filter(employee=request.user).count(),
        'pending': LeaveRequest.objects.filter(
            employee=request.user,
            status__in=[LeaveRequest.Status.SUBMITTED, LeaveRequest.Status.IN_REVIEW]
        ).count(),
        'approved': LeaveRequest.objects.filter(employee=request.user, status=LeaveRequest.Status.APPROVED).count(),
        'rejected': LeaveRequest.objects.filter(employee=request.user, status=LeaveRequest.Status.REJECTED).count(),
        'sent_back': LeaveRequest.objects.filter(employee=request.user, status=LeaveRequest.Status.SENT_BACK).count(),
    }

    context = {
        'balances': balances,
        'recent_requests': recent_requests,
        'stats': stats,
        'current_year': current_year,
    }
    return render(request, 'accounts/employee_dashboard.html', context)


@login_required
def manager_dashboard_view(request):
    """
    Landing dashboard for Managers.
    Lists direct reporting team members and prepares for Phase 2 approval screens.
    """
    subordinates = User.objects.filter(manager=request.user).select_related('department')
    return render(request, 'accounts/manager_dashboard.html', {'subordinates': subordinates})


@login_required
def hr_dashboard_view(request):
    """
    Landing dashboard for HR / Admin.
    Displays organization summary and prepares for Phase 2 approval & policy screens.
    """
    total_employees = User.objects.count()
    active_requests = LeaveRequest.objects.filter(
        status__in=[LeaveRequest.Status.SUBMITTED, LeaveRequest.Status.IN_REVIEW]
    ).count()

    context = {
        'total_employees': total_employees,
        'active_requests': active_requests,
    }
    return render(request, 'accounts/hr_dashboard.html', context)
