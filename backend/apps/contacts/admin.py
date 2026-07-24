from django.contrib import admin

from .models import AutoReplyRule, Contact, ContactGroup, Conversation


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "name", "is_blacklisted", "is_whitelisted", "tenant")
    search_fields = ("phone_number", "name")
    list_filter = ("is_blacklisted", "is_whitelisted")


@admin.register(ContactGroup)
class ContactGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant")
    search_fields = ("name",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "unread_count", "last_message_at", "tenant")
    search_fields = ("phone_number",)


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "keyword", "match_type", "enabled", "priority")
    list_filter = ("enabled", "match_type")
