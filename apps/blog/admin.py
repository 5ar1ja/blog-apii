from typing import Any

from django.contrib import admin
from django.db import models
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_BODY_MAX_PREVIEW = 50


class PostTableSection(TableSection):
    verbose_name = "Posts"
    related_name = "posts"
    fields = ["title", "status", "created_at"]


class CommentTableSection(TableSection):
    verbose_name = "Comments"
    related_name = "comments"
    fields = ["author", "body", "created_at"]


class CommentInline(TabularInline):
    model = Comment
    tab = True
    per_page = 10
    extra = 0
    autocomplete_fields = ("author",)
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [PostTableSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("posts")
            .annotate(posts_count=Count("posts"))
        )

    @display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: Category) -> int:
        return obj.posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: Tag) -> int:
        return obj.posts_count


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "shortened_body", "created_at")
    list_filter_submit = True
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    list_select_related = ("post", "author")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Comment]:
        return super().get_queryset(request).select_related("post", "author")

    @display(description="Post", ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Body")
    def shortened_body(self, obj: Comment) -> str:
        if len(obj.body) > COMMENT_BODY_MAX_PREVIEW:
            return f"{obj.body[:COMMENT_BODY_MAX_PREVIEW]}..."
        return obj.body


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = (
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    )
    list_filter_submit = True
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    search_fields = ("title", "body", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    warn_unsaved_form = True

    inlines = [CommentInline]
    list_sections = [CommentTableSection]
    list_select_related = ("author", "category")

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
    }

    fieldsets = (
        (
            "Content",
            {
                "classes": ["tab"],
                "fields": ("title", "slug", "body"),
            },
        ),
        (
            "Classification",
            {
                "classes": ["tab"],
                "fields": ("category", "tags", "status"),
            },
        ),
        (
            "Meta",
            {
                "classes": ["tab"],
                "fields": ("author", "created_at", "updated_at"),
            },
        ),
    )

    actions = ["publish_selected", "move_to_drafts"]
    actions_row = ["toggle_publish"]
    actions_list = ["publish_all_drafts"]
    actions_detail = ["open_post_comments"]
    actions_submit_line = ["save_and_publish"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related("tags", "comments", "comments__author")
            .annotate(comments_count=Count("comments"))
        )

    @display(description="Post", header=True)
    def post_header(self, obj: Post) -> list[str]:
        return [obj.title, obj.author.email]

    @display(description="Status", label={"published": "success", "draft": "warning"})
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> list[str]:
        return [t.name for t in obj.tags.all()]

    @display(description="Comments", ordering="comments_count")
    def comments_count(self, obj: Post) -> int:
        return obj.comments_count

    # Actions
    @action(description="Publish selected")
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"{updated} posts published.")

    @action(description="Move to drafts")
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f"{updated} posts moved to drafts.")

    @action(description="Publish / Unpublish", url_path="toggle-publish")
    def toggle_publish(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post = self.get_object(request, object_id)
        if post:
            if post.status == Post.Status.PUBLISHED:
                post.status = Post.Status.DRAFT
                self.message_user(request, f"Post '{post.title}' moved to drafts.")
            else:
                post.status = Post.Status.PUBLISHED
                self.message_user(request, f"Post '{post.title}' published.")
            post.save()
        return redirect(reverse("admin:blog_post_changelist"))

    @action(description="Publish all drafts", url_path="publish-all-drafts")
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        updated = Post.objects.filter(status=Post.Status.DRAFT).update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"All {updated} drafts published.")
        return redirect(reverse("admin:blog_post_changelist"))

    @action(description="Open post comments", url_path="open-comments")
    def open_post_comments(self, request: HttpRequest, object_id: int) -> HttpResponse:
        return redirect(f"{reverse('admin:blog_comment_changelist')}?post__id__exact={object_id}")

    @action(description="Save & publish")
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save()
        self.message_user(request, f"Post '{obj.title}' saved and published.")
