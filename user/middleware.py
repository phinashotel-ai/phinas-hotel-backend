from django.shortcuts import redirect
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

class AdminLoginRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.path == '/admin/'
            and request.method == 'GET'
            and request.user.is_authenticated
            and request.session.get('just_logged_in')
        ):
            request.session.pop('just_logged_in', None)
            return response

        return response

@receiver(user_logged_in)
def set_login_flag(sender, request, user, **kwargs):
    request.session['just_logged_in'] = True
