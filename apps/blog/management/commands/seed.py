import random
import time
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500
SEED_PASSWORD = "Password123!"

INACTIVE_USER_RATIO = 0.10
STAFF_USER_RATIO = 0.15
PUBLISHED_RATIO = 0.70
NO_CATEGORY_RATIO = 0.10
MAX_TAGS_PER_POST = 5
DAYS_BACK = 365
EDITED_POST_RATIO = 0.30
MIN_EDITED_DELAY_DAYS = 1
MAX_EDITED_DELAY_DAYS = 30

CATEGORIES_DATA = [
    "Python",
    "Django",
    "DevOps",
    "Frontend",
    "Backend",
    "Architecture",
    "Databases",
    "Security",
]

TAGS_DATA = [
    "api",
    "rest",
    "orm",
    "sql",
    "docker",
    "k8s",
    "aws",
    "ci-cd",
    "testing",
    "pytest",
    "git",
    "linux",
    "performance",
    "caching",
    "redis",
    "security",
    "async",
    "celery",
    "graphql",
    "microservices",
]


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        start_time = time.time()
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        if users_count < 0 or posts_count < 0 or comments_count < 0:
            raise CommandError("Number of users, posts or comments cannot be negative.")

        fake = Faker()

        if clear:
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write("Existing data cleared (except superusers).")

        # 1. Users
        created_users_count = 0
        used_emails = set(User.objects.values_list("email", flat=True))
        hashed_password = make_password(SEED_PASSWORD)
        new_users: list[Any] = []

        for _ in range(users_count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            clean_first = slugify(first_name) or "user"
            clean_last = slugify(last_name) or "author"
            domain = fake.free_email_domain()
            candidate_email = f"{clean_first}.{clean_last}@{domain}".lower()

            counter = 1
            while candidate_email in used_emails:
                candidate_email = (
                    f"{clean_first}.{clean_last}{counter}@{domain}".lower()
                )
                counter += 1

            used_emails.add(candidate_email)
            is_active = random.random() > INACTIVE_USER_RATIO
            is_staff = random.random() < STAFF_USER_RATIO

            new_users.append(
                User(
                    email=candidate_email,
                    first_name=first_name,
                    last_name=last_name,
                    password=hashed_password,
                    is_active=is_active,
                    is_staff=is_staff,
                )
            )

        if new_users:
            User.objects.bulk_create(new_users)
            created_users_count = len(new_users)

        all_users = list(User.objects.all())
        if (posts_count > 0 or comments_count > 0) and not all_users:
            raise CommandError(
                "Posts or comments requested, but there are no users in database."
            )

        # 2. Categories
        existing_categories = {c.slug: c for c in Category.objects.all()}
        categories_to_create: list[Category] = []
        for name in CATEGORIES_DATA:
            slug = slugify(name)
            if slug not in existing_categories:
                categories_to_create.append(Category(name=name, slug=slug))

        if categories_to_create:
            Category.objects.bulk_create(categories_to_create)

        all_categories = list(Category.objects.all())
        created_categories_count = len(categories_to_create)

        # 3. Tags
        existing_tags = {t.slug: t for t in Tag.objects.all()}
        tags_to_create: list[Tag] = []
        for name in TAGS_DATA:
            slug = slugify(name)
            if slug not in existing_tags:
                tags_to_create.append(Tag(name=name, slug=slug))

        if tags_to_create:
            Tag.objects.bulk_create(tags_to_create)

        all_tags = list(Tag.objects.all())
        created_tags_count = len(tags_to_create)

        # 4. Posts
        now = timezone.now()
        used_slugs = set(Post.objects.values_list("slug", flat=True))
        new_posts: list[Post] = []
        post_tags_map: list[list[Tag]] = []

        for _ in range(posts_count):
            author = random.choice(all_users)
            title = fake.sentence(nb_words=random.randint(4, 9)).rstrip(".")
            base_slug = slugify(title) or "post"
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)

            body = "\n\n".join(fake.paragraphs(nb=random.randint(3, 6)))

            category = None
            if all_categories and random.random() > NO_CATEGORY_RATIO:
                category = random.choice(all_categories)

            status = (
                Post.Status.PUBLISHED
                if random.random() < PUBLISHED_RATIO
                else Post.Status.DRAFT
            )

            post = Post(
                author=author,
                title=title,
                slug=slug,
                body=body,
                category=category,
                status=status,
            )
            new_posts.append(post)

            selected_tags = []
            if all_tags:
                tag_count = random.randint(0, min(MAX_TAGS_PER_POST, len(all_tags)))
                selected_tags = random.sample(all_tags, tag_count)
            post_tags_map.append(selected_tags)

        created_posts: list[Post] = []
        if new_posts:
            created_posts = Post.objects.bulk_create(new_posts)
            # Attach tags via through model in bulk
            through_model = Post.tags.through
            through_records: list[Any] = []
            for post_obj, tags in zip(created_posts, post_tags_map):
                for tag_obj in tags:
                    through_records.append(
                        through_model(post_id=post_obj.pk, tag_id=tag_obj.pk)
                    )
            if through_records:
                through_model.objects.bulk_create(through_records)

            # auto_now_add / auto_now overwrite dates in bulk_create,
            # so we set realistic dates afterwards with one bulk_update.
            max_age_seconds = int(timedelta(days=DAYS_BACK).total_seconds())
            for post_obj in created_posts:
                post_obj.created_at = now - timedelta(
                    seconds=random.randint(0, max_age_seconds)
                )
                post_obj.updated_at = post_obj.created_at
                if random.random() < EDITED_POST_RATIO:
                    edit_delay_days = random.randint(
                        MIN_EDITED_DELAY_DAYS, MAX_EDITED_DELAY_DAYS
                    )
                    post_obj.updated_at = min(
                        post_obj.created_at + timedelta(days=edit_delay_days), now
                    )
            Post.objects.bulk_update(created_posts, ["created_at", "updated_at"])

        created_posts_count = len(created_posts)

        # 5. Comments
        published_posts = [
            p for p in created_posts if p.status == Post.Status.PUBLISHED
        ] or list(Post.objects.filter(status=Post.Status.PUBLISHED))

        if comments_count > 0 and not published_posts:
            raise CommandError(
                "Comments were requested, but there are no published posts."
            )

        new_comments: list[Comment] = []
        comment_dates: list[datetime] = []
        for _ in range(comments_count):
            post = random.choice(published_posts)
            author = random.choice(all_users)
            sentence_count = random.randint(1, 3)
            body = " ".join(fake.sentences(nb=sentence_count))
            span_seconds = max(0, int((now - post.created_at).total_seconds()))
            created_at = post.created_at + timedelta(
                seconds=random.randint(0, span_seconds)
            )
            new_comments.append(
                Comment(
                    post=post,
                    author=author,
                    body=body,
                )
            )
            comment_dates.append(created_at)

        if new_comments:
            created_comments = Comment.objects.bulk_create(new_comments)
            for comment_obj, created_at in zip(created_comments, comment_dates):
                comment_obj.created_at = created_at
            Comment.objects.bulk_update(created_comments, ["created_at"])

        created_comments_count = len(new_comments)
        elapsed = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Users:      {created_users_count:>5} created\n"
                f"Categories: {created_categories_count:>5} created\n"
                f"Tags:       {created_tags_count:>5} created\n"
                f"Posts:      {created_posts_count:>5} created\n"
                f"Comments:   {created_comments_count:>5} created\n"
                f"Done in {elapsed:.2f} seconds"
            )
        )
