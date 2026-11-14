from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import (
    UserChangeForm as UnfoldUserChangeForm,
    UserCreationForm as UnfoldUserCreationForm,
)

from apps.auths.models import User

# Unregister default Group and re-register with Unfold
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class UserCreationForm(UnfoldUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(UnfoldUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "user_header",
        "is_active_label",
        "is_staff_label",
        "posts_count",
    )
    list_filter = (
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (
            "Personal info",
            {
                "classes": ["tab"],
                "fields": ("email", "first_name", "last_name", "password"),
            },
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {
                "classes": ["tab"],
                "fields": ("last_login",),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ["wide"],
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    actions = ["activate_users", "deactivate_users"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="User", header=True)
    def user_header(self, obj: User) -> list[str]:
        full_name = f"{obj.first_name} {obj.last_name}".strip() or "Unnamed"
        return [full_name, obj.email]

    @display(description="Active", label={True: "success", False: "danger"})
    def is_active_label(self, obj: User) -> bool:
        return obj.is_active

    @display(description="Staff", label={True: "info", False: "warning"})
    def is_staff_label(self, obj: User) -> bool:
        return obj.is_staff

    @display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: User) -> int:
        return obj.posts_count

    @action(description="Activate selected users")
    def activate_users(
        self, request: HttpRequest, queryset: QuerySet[User]
    ) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users activated.")

    @action(description="Deactivate selected users")
    def deactivate_users(
        self, request: HttpRequest, queryset: QuerySet[User]
    ) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users deactivated.")
