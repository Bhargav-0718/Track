# Track — Adaptive AI Fitness Memory

> A fitness tracker that gets smarter the more you use it. Natural-language food logging, workout tracking, progress checkpoints, and daily AI-generated insights — across Android and web.

---

## Overview

Track is a full-stack fitness application built around an **adaptive memory system**. Instead of manually searching a food database, you describe what you ate in plain text and the AI estimates the nutrition. Over time, the system remembers your personal foods, portion sizes, and habits so estimates get faster and more accurate.

```
"2 rotis with dal and sabzi"  →  AI estimates macros  →  saved to your history
Next time → pulls from memory, skips the AI call entirely
```

---

## Architecture

```
Track/
├── backend/      FastAPI · MongoDB Atlas · Beanie ODM · OpenAI GPT-4o
├── frontend/     Next.js 14 · TypeScript · Tailwind CSS
└── mobile/       Flutter · Riverpod · Android Health Connect
```

All three share the same REST API at `/api/v1/`.

---

## Features

### Food Logging
- **Natural language input** — describe a meal in any format, AI parses and estimates nutrition
- **Three-tier estimation pipeline**: memory lookup → nutrition DB (1,014-entry Indian food dataset) → GPT-4o fallback
- **Confidence scoring** — every log is tagged `confirmed`, `estimated`, or `uncertain` with a numeric score
- **Adaptive memory** — OpenAI embeddings + cosine similarity retrieves your personal foods semantically
- **Meal types** — breakfast, lunch, dinner, snack, pre/post-workout

### Workout Tracking
- Log workouts with title, type, duration, and per-exercise sets/reps
- **MET-based calorie estimation** — auto-calculated from workout type, intensity, and your body weight if no manual entry
- Exercise autocomplete from your history
- **Daily step tracking** — log daily steps, view 7-day history and BMR-adjusted burn

### Progress & Insights
- **Progress checkpoints** — log weight, body fat %, notes, and photos
- **AI physique comparison** — GPT-4o Vision compares before/after photos with structured observations
- **Daily AI reports** — behavioural insights, motivational messages, calorie/macro summary
- **Streak tracking** — consecutive days logged, longest streak
- **Consistency scoring** — 7-day and 30-day breakdowns across logging, calories, protein, and workouts

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 + Uvicorn |
| Language | Python 3.11+ |
| ODM | Beanie 2.0 (async, Pydantic v2) |
| Driver | Motor 3.7 (async MongoDB) |
| Database | MongoDB Atlas (cloud-hosted) |
| AI | OpenAI GPT-4o (chat + vision), `text-embedding-3-small` |
| Vector search | Python cosine similarity over per-user food memories |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog |
| Image handling | Pillow + aiofiles |

### Frontend (Web)
| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS 3 |
| Components | Radix UI primitives |
| Animation | Framer Motion |
| Data fetching | SWR |
| State | Zustand |
| Charts | Recharts |

### Mobile (Android)
| Layer | Technology |
|---|---|
| Framework | Flutter 3.4+ |
| State | Riverpod 2 |
| Navigation | go_router |
| HTTP | Dio |
| Charts | fl_chart |
| Animation | flutter_animate |
| Health data | Android Health Connect (`health` plugin) |
| Secure storage | flutter_secure_storage |

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Flutter SDK 3.4+** (for mobile)
- A **MongoDB Atlas** account (free tier works — [cloud.mongodb.com](https://cloud.mongodb.com))
- An **OpenAI API key** (GPT-4o access)

> No Docker required for the database — MongoDB runs on Atlas (cloud).

---

### 1 — Backend

```bash
cd backend

# Copy and fill environment variables
cp .env.example .env
# Edit .env — set MONGODB_URL, OPENAI_API_KEY, and SECRET_KEY (see table below)

# Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -e ".[dev]"

# (Optional) Import Indian food nutrition dataset — 1,014 dishes
python scripts/import_nutrition_data.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API is now running at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

> MongoDB collections are created automatically by Beanie on first startup — no migration step needed.

#### Run with Docker Compose

```bash
cd backend
docker compose up --build
```

---

### 2 — Frontend (Web)

```bash
cd frontend

npm install

# Development server (hot reload)
npm run dev
```

App is running at **http://localhost:3000**

The frontend expects the backend at `http://localhost:8000`. If you change the backend port, update `frontend/lib/api/client.ts`.

Other commands:
```bash
npm run build       # Production build
npm run start       # Serve production build
npm run lint        # ESLint
npm run type-check  # TypeScript check (no emit)
```

---

### 3 — Mobile (Flutter)

```bash
cd mobile

flutter pub get

# Run on a connected Android device or emulator
flutter run

# Build release APK
flutter build apk --release
```

The app expects the backend at the IP configured in `mobile/lib/core/api/client.dart`. Update the `baseUrl` to your machine's local IP when running on a physical device.

> **Health Connect** — requires Android 9+ with Health Connect installed. Permissions are requested at runtime.

---

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers (food_logs, workout_logs, users, analytics, activity…)
│   ├── models/          # Beanie Document models (MongoDB collections)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── repositories/    # DB query layer (Beanie find/insert/update)
│   ├── services/        # Business logic
│   │   ├── ai/          # OpenAI client, LLM, embedding, vision, report services
│   │   └── storage/     # Local file storage for progress photos
│   └── core/            # Auth, exceptions, logging, portion helpers
├── data/                # Indian food nutrition CSV (INDB dataset)
├── scripts/             # Import scripts (import_nutrition_data.py)
└── tests/               # Pytest test suite (pytest-asyncio, session-scoped event loop)

frontend/
├── app/
│   ├── (app)/           # Authenticated pages (home, log, progress, insights, profile)
│   └── (auth)/          # Login / register
├── components/
│   ├── layout/          # BottomNav
│   └── shared/          # ProgressRing, AIInsightCard, MetricCard, ConfidenceBadge…
└── lib/
    ├── api/             # API clients (food, workout, analytics, checkpoints, reports)
    ├── store/           # Zustand auth store
    ├── types/           # Shared TypeScript types
    └── utils/           # Formatting helpers

mobile/
├── lib/
│   ├── core/
│   │   ├── api/         # Dio API clients (food, workout, analytics, health connect)
│   │   ├── models/      # Dart models
│   │   ├── services/    # Health Connect service
│   │   └── theme/       # App colours and text styles
│   ├── providers/       # Riverpod state providers
│   ├── screens/         # Home, Log (food+workout), Progress, Insights, Profile, Auth
│   └── widgets/         # Shared widgets (ProgressRing, AppShell, TrackLogo…)
└── android/             # Android-specific config (Health Connect permissions)
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Get JWT token |
| `GET/PUT` | `/users/me` | Get / update profile |
| `POST` | `/food-logs/` | Log food (natural language or manual) |
| `GET` | `/food-logs/daily` | Today's food summary + macro totals |
| `GET` | `/food-logs/recent` | Recent logged foods |
| `DELETE` | `/food-logs/{id}` | Delete a food log |
| `POST` | `/workout-logs/` | Log a workout |
| `GET` | `/workout-logs/` | List workouts (paginated, filterable) |
| `GET` | `/dashboard` | Full daily dashboard (food + workouts + step data) |
| `GET` | `/health-connect/sync` | Sync Android Health Connect data |
| `POST` | `/activity/steps` | Log daily step count |
| `GET` | `/activity/steps` | Step history (default 7 days, up to 90) |
| `GET` | `/analytics/streak` | Current and longest streak |
| `GET` | `/analytics/consistency` | 7d / 30d consistency scores |
| `GET` | `/analytics/trends` | Calorie and workout trend data |
| `POST` | `/checkpoints/` | Create progress checkpoint |
| `POST` | `/checkpoints/{id}/photos` | Upload progress photo |
| `POST` | `/checkpoints/compare` | AI physique comparison (GPT-4o Vision) |
| `POST` | `/reports/generate` | Generate daily AI report |

Full interactive docs: **http://localhost:8000/docs**

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret — use a random 32+ char string in production |
| `MONGODB_URL` | Atlas connection string: `mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/` |
| `MONGODB_DB_NAME` | Database name (default: `track_db`) |
| `OPENAI_API_KEY` | Your OpenAI API key (GPT-4o access required) |
| `OPENAI_CHAT_MODEL` | Default: `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Default: `text-embedding-3-small` |
| `CORS_ORIGINS` | Allowed frontend origins, e.g. `["http://localhost:3000"]` |
| `STORAGE_BACKEND` | `local` (default) — progress photos stored on disk |
| `ENVIRONMENT` | `development` \| `staging` \| `production` |

> **Never commit `.env`** — it's in `.gitignore`. Set `MONGODB_URL` only in your local `.env` and in your hosting provider's environment variable settings.

---

## Deployment

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import this repo
2. Vercel auto-detects `vercel.json` at the root
3. Add one **Environment Variable** in Project Settings:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://your-backend.up.railway.app` |

4. Hit **Deploy**.

---

### Backend → Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select this repo, set **Root Directory** to `backend/`
3. Railway detects `backend/railway.json` and builds from `Dockerfile`
4. Set these **Environment Variables** in Railway:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | A random 32+ character string |
   | `MONGODB_URL` | Your Atlas connection string |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `ENVIRONMENT` | `production` |
   | `CORS_ORIGINS` | `["https://your-app.vercel.app"]` |
   | `LOG_LEVEL` | `INFO` |

5. After first deploy, seed the nutrition dataset via the Railway shell:
   ```bash
   python scripts/import_nutrition_data.py
   ```

> No database plugin needed — the backend connects directly to MongoDB Atlas via `MONGODB_URL`.

---

## Running Tests

```bash
cd backend

# Ensure .env has a valid MONGODB_URL
# Tests run against a separate `track_test_db` database — dropped after the session

pytest
pytest --cov=app       # with coverage report
pytest -v              # verbose per-test output
```

The test suite uses a session-scoped event loop (Motor requirement) and drops the test database on teardown — production data is never touched.

---

## Roadmap

- [ ] S3 / cloud storage backend for progress photos
- [ ] Push notifications for streak reminders
- [ ] Barcode scanner for packaged foods
- [ ] Apple HealthKit integration (iOS)
- [ ] Web-based progress photo comparison
- [ ] Export data as CSV / JSON

---

## License

MIT
