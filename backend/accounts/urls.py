from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect_view, name='dashboard_redirect'),
    path('employee/dashboard/', views.employee_dashboard_view, name='employee_dashboard'),
    path('manager/dashboard/', views.manager_dashboard_view, name='manager_dashboard'),
    path('hr/dashboard/', views.hr_dashboard_view, name='hr_dashboard'),
]
