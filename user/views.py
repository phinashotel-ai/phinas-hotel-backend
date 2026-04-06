from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, ContactMessage
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .serializers import (
    UserSerializer,
    LoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    PasswordResetSerializer,
    ContactMessageSerializer,
    AdminUserManageSerializer,
    validate_password_strength,
    PASSWORD_RULE_TEXT,
)


def _send_staff_account_email(user, plain_password):
    try:
        send_mail(
            subject="Your Phinas Hotel Staff Account",
            message=(
                f"Hello {user.first_name},\n\n"
                "A staff account has been created for you at Phinas Hotel.\n\n"
                f"Login email: {user.email}\n"
                f"Temporary password: {plain_password}\n\n"
                "Please log in and change your password after your first sign-in.\n\n"
                "Regards,\nPhinas Hotel"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass


def _send_staff_password_email(user, plain_password):
    try:
        send_mail(
            subject="Your Phinas Hotel Staff Password Has Been Updated",
            message=(
                f"Hello {user.first_name},\n\n"
                "Your staff account password has been updated by an administrator.\n\n"
                f"Login email: {user.email}\n"
                f"New password: {plain_password}\n\n"
                "Please log in and change your password if needed.\n\n"
                "Regards,\nPhinas Hotel"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass


class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "User registered successfully!",
                "user": UserProfileSerializer(user).data,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(request.user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        total_users  = CustomUser.objects.filter(role="user").count()
        total_staff  = CustomUser.objects.filter(role="staff").count()
        total_admins = CustomUser.objects.filter(role="admin").count()
        users = CustomUser.objects.all()
        return Response({
            'total_users':  total_users,
            'total_staff':  total_staff,
            'total_admins': total_admins,
            'users': UserProfileSerializer(users, many=True).data
        }, status=status.HTTP_200_OK)


class AdminUserListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        users = CustomUser.objects.all().order_by("id")
        return Response(UserProfileSerializer(users, many=True).data)

    def post(self, request):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        data["role"] = "staff"
        plain_password = data.get("password", "").strip()
        serializer = AdminUserManageSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            _send_staff_account_email(user, plain_password)
            return Response({
                "message": f"Staff account created. Password sent to {user.email}.",
                "user": UserProfileSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserManageSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response(UserProfileSerializer(updated_user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        if user.pk == request.user.pk:
            return Response({"error": "Cannot delete yourself"}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({"message": "User deleted"}, status=status.HTTP_204_NO_CONTENT)


class AdminSetPasswordView(APIView):
    """Admin: set a new password for any user (staff or user)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        new_password     = request.data.get("new_password", "").strip()
        confirm_password = request.data.get("confirm_password", "").strip()
        try:
            validate_password_strength(new_password)
        except Exception:
            return Response({"error": PASSWORD_RULE_TEXT}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        if user.role == "staff":
            _send_staff_password_email(user, new_password)
        return Response({"message": f"Password updated for {user.username} and sent to email."}, status=status.HTTP_200_OK)


class StaffDashboardView(APIView):
    """Staff: overview stats"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        from hotelroom.models import Booking, Room
        return Response({
            "total_bookings":  Booking.objects.count(),
            "pending_bookings": Booking.objects.filter(status="pending").count(),
            "confirmed_bookings": Booking.objects.filter(status="confirmed").count(),
            "total_rooms":     Room.objects.count(),
            "available_rooms": Room.objects.filter(status="available").count(),
            "total_users":     CustomUser.objects.filter(role="user").count(),
            "unread_messages": ContactMessage.objects.filter(status="unread").count(),
        }, status=status.HTTP_200_OK)


class UserDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'user': UserProfileSerializer(request.user).data,
            'message': 'Welcome to your dashboard'
        }, status=status.HTTP_200_OK)


class ContactMessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Message sent successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserContactMessagesView(APIView):
    """Regular users: fetch their own contact messages (matched by email)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = ContactMessage.objects.filter(email=request.user.email)
        return Response(ContactMessageSerializer(messages, many=True).data)


class ContactMessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        messages = ContactMessage.objects.all()
        return Response(ContactMessageSerializer(messages, many=True).data)

    def patch(self, request, pk):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            msg = ContactMessage.objects.get(pk=pk)
        except ContactMessage.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        update_data = request.data.copy()
        if "reply" in update_data:
            update_data["status"] = "replied"
            msg.replied_at = timezone.now()
            msg.replied_by = request.user
        elif update_data.get("status") == "replied" and not msg.reply:
            return Response({"error": "Reply text is required before marking as replied."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ContactMessageSerializer(msg, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save(replied_at=msg.replied_at, replied_by=msg.replied_by)
            # Send email notification when a reply is saved
            if "reply" in update_data and update_data["reply"]:
                try:
                    send_mail(
                        subject=f"Re: {msg.subject} – Phinas Hotel",
                        message=(
                            f"Dear {msg.name},\n\n"
                            f"Thank you for contacting Phinas Hotel. Here is our reply:\n\n"
                            f"{update_data['reply']}\n\n"
                            f"Best regards,\nPhinas Hotel Team\ninfo@phinashotel.com"
                        ),
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[msg.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            msg = ContactMessage.objects.get(pk=pk)
            msg.delete()
            return Response({"message": "Deleted"}, status=status.HTTP_204_NO_CONTENT)
        except ContactMessage.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
