# Hotel room booking

Django REST API for managing hotel rooms and booking an available room by bed count, view, and stay dates.

## Setup

Requires Python 3.13.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
copy  .env
python manage.py migrate
python manage.py runserver
```

macOS and Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp  .env
python manage.py migrate
python manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/`. Tests:

```bash
python manage.py test
```

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

```bash
curl -X POST http://127.0.0.1:8000/api/bookings/ ^
  -H "Content-Type: application/json" ^
  -d "{\"user_identifier\": \"user-42\", \"beds\": 2, \"view\": \"sea\", \"check_in\": \"2026-12-01T15:00:00Z\", \"check_out\": \"2026-12-05T11:00:00Z\"}"
```

A successful booking returns `201` with the booking and the assigned room. The assigned room is the lowest `id` among rooms that match the requested bed count and view and are free for the whole stay. If none are free, the response is `409`.

Send check-in and check-out as ISO-8601 timestamps. Check-out must be later than check-in.

**Exact feature match.** A request for 2 beds and a sea view is assigned only a room with exactly those features, not a larger room.

**Half-open stays.** A booking occupies `[check_in, check_out)`. A later stay may start at the earlier stay's check-out time. Overlap is `existing.check_in < requested.check_out` and `existing.check_out > requested.check_in`.

**Delete protection.** Bookings use `on_delete=PROTECT`, so a room with history cannot be removed through the API.

