from django.urls import path

from .views import TenantListView, TenantMeView
from .views_users import (
    InviteAcceptView,
    MembershipDetailView,
    MembershipListView,
    UserInviteView,
)

urlpatterns = [
    path("tenants/me/", TenantMeView.as_view(), name="tenants-me"),
    path("tenants/", TenantListView.as_view(), name="tenants-list"),
    path("users/", MembershipListView.as_view(), name="users-list"),
    path("users/invite/", UserInviteView.as_view(), name="users-invite"),
    path("users/<uuid:membership_id>/", MembershipDetailView.as_view(), name="users-detail"),
    path("invites/accept/", InviteAcceptView.as_view(), name="invites-accept"),
]
