from django.urls import path
from .views import (
    UserRegisterView, UserLoginView, UserLogoutView, UserProfileView,
    AdminDashboardView, AdminUserListCreateView, AdminUserDetailView,
    AdminSetPasswordView, UserDashboardView, StaffDashboardView, PasswordResetView,
    ContactMessageView, ContactMessageListView, UserContactMessagesView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/',                    UserRegisterView.as_view(),        name='register'),
    path('login/',                       UserLoginView.as_view(),           name='login'),
    path('logout/',                      UserLogoutView.as_view(),          name='logout'),
    path('profile/',                     UserProfileView.as_view(),         name='profile'),
    path('password/reset/',              PasswordResetView.as_view(),       name='password_reset'),
    path('dashboard/admin/',             AdminDashboardView.as_view(),      name='admin_dashboard'),
    path('dashboard/user/',              UserDashboardView.as_view(),       name='user_dashboard'),
    path('dashboard/staff/',             StaffDashboardView.as_view(),      name='staff_dashboard'),
    path('token/refresh/',               TokenRefreshView.as_view(),        name='token_refresh'),
    path('contact/',                     ContactMessageView.as_view(),      name='contact'),
    path('contact/messages/',            ContactMessageListView.as_view(),  name='contact_messages'),
    path('contact/messages/<int:pk>/',   ContactMessageListView.as_view(),  name='contact_message_detail'),
    path('contact/my-messages/',         UserContactMessagesView.as_view(), name='user_contact_messages'),
    path('users/',                       AdminUserListCreateView.as_view(), name='admin_user_list_create'),
    path('users/<int:pk>/',              AdminUserDetailView.as_view(),     name='admin_user_detail'),
    path('users/<int:pk>/set-password/', AdminSetPasswordView.as_view(),    name='admin_set_password'),
]
