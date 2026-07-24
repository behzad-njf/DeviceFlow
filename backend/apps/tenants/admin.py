from django.contrib import admin

from .models import Membership, Tenant, TenantInvite


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "is_active", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "tenant__name", "tenant__slug")
    autocomplete_fields = ("user", "tenant")


@admin.register(TenantInvite)
class TenantInviteAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "tenant", "expires_at", "accepted_at", "revoked_at")
    list_filter = ("role",)
    search_fields = ("email",)
