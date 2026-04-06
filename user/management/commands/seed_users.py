from django.core.management.base import BaseCommand
from user.models import CustomUser

class Command(BaseCommand):
    help = 'Create default admin and user accounts'

    def handle(self, *args, **kwargs):
        if not CustomUser.objects.filter(email='admin@gmail.com').exists():
            CustomUser.objects.create_user(
                email='admin@gmail.com',
                username='admin',
                password='Admin@123',
                first_name='Admin',
                last_name='User',
                contact='1234567890',
                address='Admin Address',
                gender='Male',
                role='admin',
            )
            self.stdout.write(self.style.SUCCESS('Admin created: admin@gmail.com / Admin@123'))
        
        if not CustomUser.objects.filter(email='user@gmail.com').exists():
            CustomUser.objects.create_user(
                email='user@gmail.com',
                username='user',
                password='User@123',
                first_name='Regular',
                last_name='User',
                contact='0987654321',
                address='User Address',
                gender='Male'
            )
            self.stdout.write(self.style.SUCCESS('User created: user@gmail.com / User@123'))
