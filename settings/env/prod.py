from decouple import config

from settings.base import *

DEBUG = False

ALLOWED_HOSTS = config(
    "BLOG_ALLOWED_HOSTS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("BLOG_DB_NAME", default="blog_db"),
        "USER": config("BLOG_DB_USER", default="blog_user"),
        "PASSWORD": config("BLOG_DB_PASSWORD", default=""),
        "HOST": config("BLOG_DB_HOST", default="localhost"),
        "PORT": config("BLOG_DB_PORT", default="5432"),
    }
}
