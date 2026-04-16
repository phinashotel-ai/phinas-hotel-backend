from django.urls import path
from .views import (
    RoomListView, RoomDetailView, RoomCapacityCheckView,
    BookingCreateView, BookingListView, BookingDetailView,
    AdminBookingListView, AdminBookingDetailView,
    RoomRatingView, MyRoomRatingsView, AdminRoomRatingsView, PromoCodeValidateView, AdminPromoCodeView, AdminRoomView,
)

urlpatterns = [
    path("rooms/",                       RoomListView.as_view(),           name="room-list"),
    path("rooms/<int:pk>/",              RoomDetailView.as_view(),         name="room-detail"),
    path("rooms/<int:pk>/check-capacity/", RoomCapacityCheckView.as_view(), name="room-capacity-check"),
    path("rooms/admin/",                 AdminRoomView.as_view(),          name="admin-room-list"),
    path("rooms/admin/<int:pk>/",        AdminRoomView.as_view(),          name="admin-room-detail"),
    path("bookings/",                    BookingCreateView.as_view(),      name="booking-create"),
    path("bookings/my/",                 BookingListView.as_view(),        name="booking-list"),
    path("bookings/<int:pk>/",           BookingDetailView.as_view(),      name="booking-detail"),
    path("bookings/admin/",              AdminBookingListView.as_view(),   name="admin-booking-list"),
    path("bookings/admin/<int:pk>/",     AdminBookingDetailView.as_view(), name="admin-booking-detail"),
    path("rooms/<int:room_id>/ratings/", RoomRatingView.as_view(),         name="room-ratings"),
    path("ratings/my/",                  MyRoomRatingsView.as_view(),      name="my-room-ratings"),
    path("ratings/admin/",               AdminRoomRatingsView.as_view(),   name="admin-room-ratings"),
    path("promo/validate/",              PromoCodeValidateView.as_view(),  name="promo-validate"),
    path("promo/",                       AdminPromoCodeView.as_view(),     name="promo-list"),
    path("promo/<int:pk>/",              AdminPromoCodeView.as_view(),     name="promo-detail"),
]
