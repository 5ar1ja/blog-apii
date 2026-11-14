from pathlib import Path
from decouple import Config, RepositoryEnv, config

ENV_FILE = Path(__file__).resolve().parent / ".env"
if ENV_FILE.exists():
    env_config = Config(RepositoryEnv(str(ENV_FILE)))
else:
    env_config = config

SECRET_KEY = env_config("BLOG_SECRET_KEY", cast=str, default="django-insecure-dev-key")
ENV_ID = env_config("BLOG_ENV_ID", cast=str, default="local")