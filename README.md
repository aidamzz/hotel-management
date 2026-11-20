# Hotel room booking

Django REST API for managing hotel rooms and booking an available room by bed count, view, and stay dates.

## Setup

### Prerequisites

- Python 3.13
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone https://github.com/aidamzz/hotel-management.git
cd hotel-management
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the PostgreSQL database

Make sure PostgreSQL is running. Open a PostgreSQL shell (for example, `psql -U postgres`) and execute:

```sql
CREATE ROLE hotel_user WITH LOGIN PASSWORD 'change-me' CREATEDB;
CREATE DATABASE hotel_booking OWNER hotel_user;
```

You can replace the username, database name, and password with your own values.

### 5. Configure environment variables

Create your local `.env` file from the example file.

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**Windows (Command Prompt):**

```cmd
copy .env.example .env
```

Open `.env` and configure the values:

```dotenv
SECRET_KEY=your-generated-secret-key
POSTGRES_DB=hotel_booking
POSTGRES_USER=hotel_user
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use the generated value for `SECRET_KEY`.

Do not commit your `.env` file. It is excluded through `.gitignore`.

### 6. Apply database migrations

```bash
python manage.py migrate
```

The PostgreSQL-specific migration creates the `btree_gist` extension and adds a database constraint to prevent overlapping bookings for the same room.

Make sure your PostgreSQL database user has permission to create this extension.

### 7. Run the application

```bash
python manage.py runserver
```

The API is available at:

http://127.0.0.1:8000/api/

### Run tests

```bash
python manage.py test
```

The test suite should be run against PostgreSQL because the project uses PostgreSQL-specific database behavior.

There is no authentication. `user_identifier` on a booking is an opaque string; this project does not manage user accounts.

## Rooms

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/rooms/` | List rooms |
| `POST` | `/api/rooms/` | Create a room |
| `GET` | `/api/rooms/{id}/` | Retrieve a room |
| `PUT` | `/api/rooms/{id}/` | Replace a room |
| `PATCH` | `/api/rooms/{id}/` | Update part of a room |
| `DELETE` | `/api/rooms/{id}/` | Delete a room |

```bash
curl -X POST http://127.0.0.1:8000/api/rooms/ ^
  -H "Content-Type: application/json" ^
  -d "{\"label\": \"204\", \"beds\": 2, \"view\": \"sea\"}"
```

`label` is unique. `beds` is an integer from 1 to 5. `view` is `sea`, `mountain`, or `yard` (any letter case). Invalid input returns `400`. Deleting a room that already has bookings returns `409`.

## Bookings

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/bookings/` | Book a matching available room |
| `GET` | `/api/bookings/` | List bookings |
| `GET` | `/api/bookings/{id}/` | Retrieve a booking |
| `PUT` | `/api/bookings/{id}/` | Replace a booking and reassign a room if needed |
| `PATCH` | `/api/bookings/{id}/` | Update part of a booking and reassign a room if needed |

```bash
curl -X POST http://127.0.0.1:8000/api/bookings/ ^
  -H "Content-Type: application/json" ^
  -d "{\"user_identifier\": \"user-42\", \"beds\": 2, \"view\": \"sea\", \"check_in\": \"2026-12-01T15:00:00Z\", \"check_out\": \"2026-12-05T11:00:00Z\"}"
```

A successful booking returns `201` with the booking and the assigned room. The assigned room is the lowest `id` among rooms that match the requested bed count and view and are free for the whole stay. If none are free, the response is `409`.

`PUT` and `PATCH` use the same body. The current room stays assigned when it still matches the new beds, view, and dates. Otherwise the booking moves to the lowest-id free match. If no room fits, the response is `409` and the booking is left unchanged.

Matching rooms are locked for the transaction, so two concurrent requests cannot both take the same room. On PostgreSQL, migration `0002_booking_no_overlap` also adds an exclusion constraint: the database rejects a second overlapping stay on that room. Run `migrate` after the database settings point at PostgreSQL.

Send check-in and check-out as ISO-8601 timestamps. Check-out must be later than check-in.

**Exact feature match.** A request for 2 beds and a sea view is assigned only a room with exactly those features, not a larger room.

**Half-open stays.** A booking occupies `[check_in, check_out)`. A later stay may start at the earlier stay's check-out time. Overlap is `existing.check_in < requested.check_out` and `existing.check_out > requested.check_in`.

**Delete protection.** Bookings use `on_delete=PROTECT`, so a room with history cannot be removed through the API.

