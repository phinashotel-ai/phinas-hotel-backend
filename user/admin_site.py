import os

from django.contrib.admin import AdminSite
from django.shortcuts import redirect


FRONTEND_APP_URL = os.environ.get("FRONTEND_APP_URL", "http://localhost:3000").rstrip("/")

class CustomAdminSite(AdminSite):
    def login(self, request, extra_context=None):
        if request.method == 'POST' and request.user.is_authenticated:
            if request.user.is_staff and request.user.is_superuser:
                return redirect(f"{FRONTEND_APP_URL}/admin-dashboard")
            elif request.user.is_authenticated:
                return redirect(f"{FRONTEND_APP_URL}/user-dashboard")
        return super().login(request, extra_context)

admin_site = CustomAdminSite(name='custom_admin')
