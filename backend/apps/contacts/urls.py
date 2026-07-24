from django.urls import path

from .views import (
    AutoReplyDetailView,
    AutoReplyListCreateView,
    ContactDetailView,
    ContactGroupDetailView,
    ContactGroupListCreateView,
    ContactImportConfirmView,
    ContactImportPreviewView,
    ContactListCreateView,
    ConversationDetailView,
    ConversationListView,
)

urlpatterns = [
    path("contacts/", ContactListCreateView.as_view(), name="contacts-list"),
    path(
        "contacts/import/preview/",
        ContactImportPreviewView.as_view(),
        name="contacts-import-preview",
    ),
    path(
        "contacts/import/",
        ContactImportConfirmView.as_view(),
        name="contacts-import",
    ),
    path("contacts/<uuid:contact_id>/", ContactDetailView.as_view(), name="contacts-detail"),
    path("contact-groups/", ContactGroupListCreateView.as_view(), name="contact-groups-list"),
    path(
        "contact-groups/<uuid:group_id>/",
        ContactGroupDetailView.as_view(),
        name="contact-groups-detail",
    ),
    path("conversations/", ConversationListView.as_view(), name="conversations-list"),
    path(
        "conversations/<uuid:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversations-detail",
    ),
    path("auto-replies/", AutoReplyListCreateView.as_view(), name="auto-replies-list"),
    path(
        "auto-replies/<uuid:rule_id>/",
        AutoReplyDetailView.as_view(),
        name="auto-replies-detail",
    ),
]
