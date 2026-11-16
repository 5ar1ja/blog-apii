from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Count
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.blog import queries

SAMPLE_ARGUMENTS: dict[int, dict[str, Any]] = {
    7: {"page": 1}, 13: {"days": 365}, 34: {"min_posts": 1},
    40: {"name": "query-command-tag"}, 41: {"days": 30},
}
READ_ONLY_QUERY_NUMBERS = set(range(1, 40)) | {48, 49, 50}
PREVIEW_ROWS = 5


class Command(BaseCommand):
    help = "Run the numbered blog ORM queries."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only this query number.")
        parser.add_argument("--sql", action="store_true", help="Print captured SQL statements.")

    def handle(self, *args: Any, **options: Any) -> None:
        number = options["number"]
        selected = [number] if number is not None else sorted(READ_ONLY_QUERY_NUMBERS)
        for query_number in selected:
            function = queries.QUERIES.get(query_number)
            if function is None:
                raise CommandError(f"Unknown query number: {query_number}")
            arguments = dict(SAMPLE_ARGUMENTS.get(query_number, {}))
            arguments.update(self._sample_arguments(query_number))

            with CaptureQueriesContext(connection) as context:
                result = function(**arguments)
                if hasattr(result, "query"):
                    result = list(result)
            self.stdout.write(f"#{query_number} {function.__name__} — {len(context.captured_queries)} SQL quer{'y' if len(context.captured_queries) == 1 else 'ies'}")
            if options["sql"]:
                for captured in context.captured_queries:
                    self.stdout.write(captured["sql"])
            if isinstance(result, list):
                for item in result[:PREVIEW_ROWS]:
                    self.stdout.write(f"  {self._format_item(item)}")
                self.stdout.write(f"  ({len(result)} rows)")
            else:
                self.stdout.write(f"  {self._format_item(result)}")

    @staticmethod
    def _format_item(item: Any) -> str:
        if hasattr(item, "_meta"):
            values = {"id": item.pk, "title": getattr(item, "title", None), "name": getattr(item, "name", None)}
            field_names = {field.attname for field in item._meta.concrete_fields}
            values.update({key: value for key, value in item.__dict__.items() if key not in field_names and key != "_state"})
            return repr({key: value for key, value in values.items() if value is not None})
        return repr(item)

    @staticmethod
    def _sample_arguments(number: int) -> dict[str, Any]:
        from django.contrib.auth import get_user_model

        from apps.blog.models import Category, Post, Tag

        User = get_user_model()
        if number == 4:
            return {"slug": Post.objects.values_list("slug", flat=True).first() or "missing"}
        if number == 8:
            title = Post.objects.values_list("title", flat=True).first() or "django"
            return {"word": title.split()[0]}
        if number == 9:
            email = User.objects.values_list("email", flat=True).first() or "user@example.com"
            return {"domain": email.rsplit("@", 1)[-1]}
        if number == 11:
            return {"slugs": list(Category.objects.values_list("slug", flat=True)[:2])}
        if number == 12:
            created = Post.objects.order_by("created_at").values_list("created_at", flat=True).first()
            created = created or timezone.now()
            return {"year": created.year, "month": created.month}
        if number == 14:
            dates = list(Post.objects.dates("created_at", "day", order="ASC"))
            if dates:
                return {"start": dates[0], "end": dates[-1]}
            from datetime import date
            today = date.today()
            return {"start": today, "end": today}
        if number == 15:
            email = User.objects.filter(posts__status=Post.Status.PUBLISHED).values_list("email", flat=True).first()
            return {"email": email or "missing@example.com"}
        if number == 16:
            slug = Tag.objects.filter(posts__isnull=False).values_list("slug", flat=True).first()
            return {"tag_slug": slug or "api"}
        if number == 17:
            slug = Category.objects.filter(posts__comments__isnull=False).values_list("slug", flat=True).first()
            return {"category_slug": slug or "django"}
        if number == 21:
            post = (
                Post.objects.filter(status=Post.Status.PUBLISHED)
                .annotate(tag_count=Count("tags"))
                .filter(tag_count__gte=2)
                .first()
            )
            if post:
                slugs = list(post.tags.values_list("slug", flat=True)[:2])
                return {"first_slug": slugs[0], "second_slug": slugs[1]}
            slugs = list(Tag.objects.values_list("slug", flat=True)[:2])
            return {"first_slug": slugs[0] if slugs else "api", "second_slug": slugs[1] if len(slugs) > 1 else "orm"}
        if number == 22:
            title = Post.objects.values_list("title", flat=True).first() or "django"
            return {"text": title.split()[0]}
        if number == 37:
            name = User.objects.values_list("first_name", flat=True).first() or "a"
            return {"text": name}
        if number == 42:
            category = (
                Category.objects.filter(posts__isnull=False)
                .values_list("slug", flat=True)
                .distinct()
                .first()
                or "django"
            )
            tag = Tag.objects.values_list("slug", flat=True).first() or "api"
            return {"category_slug": category, "tag_slug": tag}
        if number == 43:
            slugs = list(
                Category.objects.filter(posts__isnull=False)
                .values_list("slug", flat=True)
                .distinct()[:2]
            )
            return {"source_slug": slugs[0] if slugs else "", "target_slug": slugs[1] if len(slugs) > 1 else ""}
        return {}
