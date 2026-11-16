from datetime import date, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.db.models import Value

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()
NEWEST_POSTS_LIMIT = 5
POSTS_PAGE_SIZE = 10
HOUR = timedelta(hours=1)
UNCATEGORIZED = "Uncategorized"
TOP_AUTHORS_LIMIT = 5
POPULARITY_HOT_THRESHOLD = 10
POPULARITY_NORMAL_THRESHOLD = 3
FEED_LIMIT = 50
TAGGED_POSTS_LIMIT = 20


def categories_by_name() -> QuerySet[Category]:
    """Return all categories ordered alphabetically."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Return published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """Return the newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Return a post by slug, or None when it does not exist."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Count active non-staff users."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """Return whether any draft posts exist."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return one page of published posts, ten per page."""
    start = (page - 1) * POSTS_PAGE_SIZE
    return published_posts()[start : start + POSTS_PAGE_SIZE]


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Return posts whose title contains the word, ignoring case."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Return users whose email ends with the requested domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Return posts without a category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Return categories whose slugs are in the supplied list."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Return posts created in the specified month and year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Return posts created during the last number of days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Return posts created on either endpoint date or between them."""
    return Post.objects.filter(created_at__date__range=(start, end))


def author_published_posts(email: str) -> QuerySet[Post]:
    """Return published posts by the author with this email."""
    return published_posts().filter(author__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Return posts with the specified tag."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Return comments on posts in the specified category."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Return each user with at least one published post."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Return posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Return users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Return posts carrying both specified tags."""
    return published_posts().filter(tags__slug=first_slug).filter(tags__slug=second_slug)


def search_posts(text: str) -> QuerySet[Post]:
    """Search post titles and bodies, ignoring case."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Return published posts without a category or without tags."""
    return published_posts().filter(Q(category__isnull=True) | Q(tags__isnull=True)).distinct()


def edited_posts() -> QuerySet[Post]:
    """Return posts edited more than an hour after creation."""
    return Post.objects.filter(updated_at__gt=F("created_at") + HOUR)


def comments_by_post_author() -> QuerySet[Comment]:
    """Return comments written by the author of their post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """Return comments created before their post."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


def published_authors_emails() -> list[str]:
    """Return unique published-post author emails in alphabetical order."""
    return list(
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .order_by("email")
        .values_list("email", flat=True)
        .distinct()
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """Return the required title, author email, and category name for each published post."""
    return list(
        published_posts().annotate(
            author_email=F("author__email"),
            category_name=Coalesce("category__name", Value(UNCATEGORIZED)),
        ).values("title", "author_email", "category_name")
    )


def posts_stats() -> dict[str, Any]:
    """Return post counts and first/last creation dates in one query."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Return the average comments per published post, including posts with none."""
    average = published_posts().annotate(comment_count=Count("comments")).aggregate(
        average=Avg("comment_count")
    )["average"]
    return round(average, 2) if average is not None else 0.0


def categories_with_post_count() -> QuerySet[Category]:
    """Return categories annotated with total post counts."""
    return Category.objects.annotate(post_count=Count("posts")).order_by("-post_count", "name")


def categories_with_published_count() -> QuerySet[Category]:
    """Return categories annotated with their published post counts."""
    return Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "name")


def top_authors() -> QuerySet[User]:
    """Return the five users with the most published posts."""
    return User.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Return tags used by at least min_posts posts, with their post counts."""
    return Tag.objects.annotate(post_count=Count("posts")).filter(
        post_count__gte=min_posts
    ).order_by("-post_count", "name")


def posts_per_status() -> list[dict[str, Any]]:
    """Return the number of posts in each status."""
    return list(Post.objects.values("status").annotate(count=Count("id")).order_by("status"))


def users_activity() -> QuerySet[User]:
    """Return every user with correct post and comment counts."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    ).order_by("-post_count", "-comment_count", "email")


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Return users whose combined first and last name contains text."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(" "), "last_name")
    ).filter(full_name__icontains=text).order_by("first_name", "last_name")


def published_posts_per_month() -> list[dict[str, Any]]:
    """Return published post counts grouped by creation month."""
    return list(
        published_posts().annotate(month=TruncMonth("created_at"))
        .values("month").annotate(count=Count("id")).order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Return all posts with comment_count and a popularity label."""
    return Post.objects.annotate(comment_count=Count("comments")).annotate(
        popularity=Case(
            When(comment_count__gte=POPULARITY_HOT_THRESHOLD, then=Value("hot")),
            When(comment_count__gte=POPULARITY_NORMAL_THRESHOLD, then=Value("normal")),
            default=Value("quiet"),
        )
    ).order_by("-comment_count", "-created_at")


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Find or create a tag using its normalized unique slug."""
    from django.utils.text import slugify

    slug = slugify(name)
    return Tag.objects.get_or_create(slug=slug, defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """Publish drafts older than the given number of days and update their timestamps."""
    cutoff = timezone.now() - timedelta(days=days)
    drafts = Post.objects.filter(status=Post.Status.DRAFT, created_at__lt=cutoff)
    return drafts.update(status=Post.Status.PUBLISHED, updated_at=timezone.now())


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Attach a tag to every post in the category and return the category post count."""
    posts = Post.objects.filter(category__slug=category_slug)
    tag = Tag.objects.get(slug=tag_slug)
    post_ids = list(posts.values_list("pk", flat=True))
    through = Post.tags.through
    existing_ids = set(through.objects.filter(post_id__in=post_ids, tag_id=tag.pk).values_list("post_id", flat=True))
    through.objects.bulk_create(
        [through(post_id=pk, tag_id=tag.pk) for pk in post_ids if pk not in existing_ids],
        ignore_conflicts=True,
    )
    return len(post_ids)


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move source category posts to target and delete the source category."""
    if source_slug == target_slug:
        return 0
    try:
        source = Category.objects.get(slug=source_slug)
        target = Category.objects.get(slug=target_slug)
    except Category.DoesNotExist:
        return 0
    moved = Post.objects.filter(category=source).update(category=target)
    source.delete()
    return moved


def delete_inactive_users_comments() -> int:
    """Delete comments written by inactive users and return the deleted comment count."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


def published_feed() -> list[str]:
    """Return the newest published posts as title, author, and category lines."""
    posts = published_posts().select_related("author", "category")[:FEED_LIMIT]
    return [f"{p.title} | {p.author.email} | {p.category.name if p.category else UNCATEGORIZED}" for p in posts]


def newest_posts_with_tags() -> list[str]:
    """Return the newest posts with their tags in at most two queries."""
    posts = Post.objects.order_by("-created_at").prefetch_related("tags")[:TAGGED_POSTS_LIMIT]
    return [f"{p.title}: {', '.join(tag.name for tag in p.tags.all())}" for p in posts]


def categories_with_published_posts() -> dict[str, list[str]]:
    """Return each category and its published post titles, newest first."""
    post_qs = Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")
    categories = Category.objects.prefetch_related(Prefetch("posts", queryset=post_qs, to_attr="published_posts"))
    return {category.name: [post.title for post in category.published_posts] for category in categories}


def posts_with_last_comment() -> QuerySet[Post]:
    """Return published posts with the body of their newest comment, if any."""
    latest_comment = Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at", "-pk")
    return published_posts().annotate(last_comment=Subquery(latest_comment.values("body")[:1]))


def posts_with_staff_comments() -> QuerySet[Post]:
    """Return posts with at least one comment by a staff user."""
    staff_comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Return users whose newest post is a draft, annotated with its status."""
    latest_post = Post.objects.filter(author=OuterRef("pk")).order_by("-created_at", "-pk")
    return User.objects.annotate(
        latest_post_status=Subquery(latest_post.values("status")[:1])
    ).filter(latest_post_status=Post.Status.DRAFT)


QUERIES = {
    1: categories_by_name, 2: published_posts, 3: newest_published_posts,
    4: post_by_slug, 5: active_users_count, 6: has_drafts,
    7: published_posts_page, 8: posts_with_word_in_title, 9: users_with_email_domain,
    10: posts_without_category, 11: categories_by_slugs, 12: posts_in_month,
    13: posts_last_days, 14: posts_between, 15: author_published_posts,
    16: posts_with_tag, 17: comments_in_category, 18: users_with_published_posts,
    19: posts_without_tags, 20: users_without_comments, 21: posts_with_both_tags,
    22: search_posts, 23: published_posts_missing_info, 24: edited_posts,
    25: comments_by_post_author, 26: comments_before_post,
    27: published_authors_emails, 28: published_posts_overview, 29: posts_stats,
    30: average_comments_per_post, 31: categories_with_post_count,
    32: categories_with_published_count, 33: top_authors, 34: popular_tags,
    35: posts_per_status, 36: users_activity, 37: search_users_by_full_name,
    38: published_posts_per_month, 39: posts_with_popularity, 40: get_or_create_tag,
    41: publish_old_drafts, 42: tag_category_posts, 43: merge_categories,
    44: delete_inactive_users_comments, 45: published_feed, 46: newest_posts_with_tags,
    47: categories_with_published_posts, 48: posts_with_last_comment,
    49: posts_with_staff_comments, 50: users_with_draft_as_latest_post,
}
