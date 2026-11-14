# Blog API

A blog REST API built with Django.

## Entity-Relationship Diagram (ERD)

![ERD Diagram](docs/erd.svg)

```mermaid
erDiagram
    User ||--o{ Post : "writes"
    User ||--o{ Comment : "authors"
    Category ||--o{ Post : "categorizes"
    Post ||--o{ Comment : "has"
    Post }o--o{ Tag : "tagged with"

    User {
        int id PK
        string email UK
        string first_name
        string last_name
        boolean is_active
        boolean is_staff
    }

    Category {
        int id PK
        string name UK
        string slug UK
    }

    Tag {
        int id PK
        string name UK
        string slug UK
    }

    Post {
        int id PK
        int author_id FK
        string title
        string slug UK
        text body
        int category_id FK
        string status
        datetime created_at
        datetime updated_at
    }

    Comment {
        int id PK
        int post_id FK
        int author_id FK
        text body
        datetime created_at
    }
```

## Project Structure

```text
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── logs/
├── apps/
│   ├── auths/
│   └── blog/
├── settings/
│   ├── .env
│   ├── .env.example
│   ├── conf.py
│   ├── base.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── env/
│       ├── local.py
│       └── prod.py
└── docs/
    └── erd.svg
```

## Setup & Local Run

1. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements/dev.txt
   ```

3. Configure environment variables in `settings/.env`:
   ```bash
   cp settings/.env.example settings/.env
   ```

4. Apply migrations:
   ```bash
   python manage.py migrate
   ```

5. Run development server:
   ```bash
   python manage.py runserver
   ```
