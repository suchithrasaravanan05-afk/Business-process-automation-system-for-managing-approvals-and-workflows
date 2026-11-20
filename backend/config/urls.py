from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('leaves/', include('leaves.urls')),
    path('', lambda request: redirect('dashboard_redirect'), name='home_redirect'),
]
