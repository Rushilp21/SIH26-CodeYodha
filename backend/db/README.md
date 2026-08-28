# Database (Developer 4)

## Purpose
PostGIS schema, Alembic migrations, sessions, and demo seed data.

## Owner
Developer 4 only. Do not edit from other ownership folders.

## Inputs
- `DATABASE_URL` from `.env`
- Geometry always stored as **EPSG:4326**

## Outputs
- Tables listed in `docs/architecture.md`
- Seeded demo project for tomorrow's UI walkthrough

## How to migrate
From repo root (PYTHONPATH = repo root):

```
cd backend/db
alembic upgrade head
```

Or:

```
python -m alembic -c backend/db/alembic.ini upgrade head
```

## How to seed

```
python backend/db/seed/seed_demo.py
```

Requires Postgres+PostGIS running (see Docker).

## Tests
Placeholder tests live under `backend/api/tests` until Dev 4 adds DB-specific tests here.
