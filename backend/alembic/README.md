# Alembic Migrations

This directory contains Alembic migration scripts for the G-Drive database.

## Setup

### For Docker (Recommended)

The application runs in Docker, so all Alembic commands must be run inside the container.

1. Make sure your containers are running:
```bash
docker-compose up -d
```

2. Make sure your `DATABASE_URL` environment variable is set correctly in your `.env` file.

## Running Migrations in Docker

### Option 1: Using the helper script (Easiest)
```bash
# From the backend directory
./migrate.sh api current      # Check current status
./migrate.sh api upgrade      # Apply all migrations
./migrate.sh api history      # View history
./migrate.sh api downgrade    # Rollback one migration
```

### Option 2: Direct docker-compose commands

#### Check current migration status:
```bash
docker-compose exec api alembic current
```

#### View migration history:
```bash
docker-compose exec api alembic history
```

#### Apply all pending migrations:
```bash
docker-compose exec api alembic upgrade head
```

#### Apply a specific migration:
```bash
docker-compose exec api alembic upgrade <revision_id>
```

#### Rollback to previous migration:
```bash
docker-compose exec api alembic downgrade -1
```

#### Rollback to a specific revision:
```bash
docker-compose exec api alembic downgrade <revision_id>
```

### Option 3: Using docker exec
```bash
docker exec -it g-drive-api alembic current
docker exec -it g-drive-api alembic upgrade head
```

### For Local Development (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your `DATABASE_URL` environment variable is set correctly in your `.env` file.

3. Run migrations directly:
```bash
alembic current
alembic upgrade head
```

## Creating New Migrations

### In Docker:

#### Auto-generate migration from model changes:
```bash
# Using helper script
./migrate.sh api revision "description of changes"

# Or directly
docker-compose exec api alembic revision --autogenerate -m "description of changes"
```

#### Create empty migration script:
```bash
docker-compose exec api alembic revision -m "description of changes"
```

### Local Development:
```bash
alembic revision --autogenerate -m "description of changes"
alembic revision -m "description of changes"
```

## Important Notes

- **001_convert_ids_to_uuid**: This migration converts all Integer IDs to UUIDs. 
  - It preserves all existing data by creating new UUID columns, migrating data, then replacing the old columns.
  - **Backup your database** before running this migration if you have important data.
  - The downgrade function will lose UUID data and generate new sequential integer IDs.

## Migration Workflow

1. Make changes to your SQLAlchemy models
2. Generate a migration: 
   - Docker: `./migrate.sh api revision "description"` or `docker-compose exec api alembic revision --autogenerate -m "description"`
   - Local: `alembic revision --autogenerate -m "description"`
3. Review the generated migration file in `alembic/versions/`
4. Apply the migration:
   - Docker: `./migrate.sh api upgrade` or `docker-compose exec api alembic upgrade head`
   - Local: `alembic upgrade head`
5. Test your application

## First Time Setup

If this is your first time running migrations:

1. Start your Docker containers:
```bash
docker-compose up -d
```

2. Check if migrations are needed:
```bash
docker-compose exec api alembic current
```

3. Apply the UUID migration:
```bash
docker-compose exec api alembic upgrade head
```

This will convert all Integer IDs to UUIDs in your database.

