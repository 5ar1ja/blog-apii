import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpRequest

from apps.blog.models import Category, Comment, Post
from settings.conf import ENV_ID

User = get_user_model()


def environment_callback(request: HttpRequest) -> list[str]:
    """Return badge text and badge color type based on environment."""
    if ENV_ID == "prod":
        return ["Production", "danger"]
    return ["Local", "warning"]


def drafts_badge(request: HttpRequest) -> int:
    """Return number of draft posts for sidebar badge."""
    return Post.objects.filter(status=Post.Status.DRAFT).count()


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Provide data for the admin dashboard."""
    total_users = User.objects.count()
    published_posts = Post.objects.filter(status=Post.Status.PUBLISHED).count()
    draft_posts = Post.objects.filter(status=Post.Status.DRAFT).count()
    total_comments = Comment.objects.count()
    total_posts = published_posts + draft_posts

    # Bar chart: posts per category
    categories = Category.objects.annotate(posts_count=Count("posts")).order_by("name")
    chart_labels = [c.name for c in categories]
    chart_values = [c.posts_count for c in categories]
    chart_data = {
        "labels": chart_labels,
        "datasets": [
            {
                "label": "Posts",
                "data": chart_values,
                "backgroundColor": "rgba(16, 185, 129, 0.8)",
                "borderColor": "rgb(16, 185, 129)",
                "borderWidth": 1,
            }
        ],
    }

    # Table: top 5 authors by posts count
    top_authors = (
        User.objects.annotate(posts_count=Count("posts"))
        .filter(posts_count__gt=0)
        .order_by("-posts_count")[:5]
    )
    authors_table = {
        "headers": ["Author", "Email", "Posts"],
        "rows": [
            [f"{author.first_name} {author.last_name}".strip() or "Anonymous", author.email, author.posts_count]
            for author in top_authors
        ],
    }

    # Progress: share of published vs draft posts
    if total_posts > 0:
        published_pct = round((published_posts / total_posts) * 100)
        draft_pct = 100 - published_pct
    else:
        published_pct = 0
        draft_pct = 0

    progress_items = [
        {"title": "Published", "value": published_pct, "progress_class": "bg-emerald-500"},
        {"title": "Draft", "value": draft_pct, "progress_class": "bg-amber-500"},
    ]

    context.update(
        {
            "kpi_total_users": total_users,
            "kpi_published_posts": published_posts,
            "kpi_draft_posts": draft_posts,
            "kpi_total_comments": total_comments,
            "category_chart_json": json.dumps(chart_data),
            "top_authors_table": authors_table,
            "posts_progress_items": progress_items,
            "published_pct": published_pct,
            "draft_pct": draft_pct,
        }
    )
    return context
