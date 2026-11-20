from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.apply_leave_view, name='apply_leave'),
    path('my-requests/', views.my_requests_view, name='my_requests'),
]
