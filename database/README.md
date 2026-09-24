# Database

The application database schema is managed by Django migrations in each app's `migrations/` directory.

For Docker Compose, the `mysql` service creates the `MYSQL_DB` database automatically. The backend container runs `python manage.py migrate` at startup.

Real database dumps, media uploads, and backup zip files are intentionally ignored by Git because they may contain personal data, password hashes, sessions, or device credentials.
