# Task Management System

Full-stack task management app with a FastAPI backend and React + Vite frontend.

## Project Structure

```
Task_Management_System/
├── Backend/          # FastAPI app (Python)
├── Frontend/         # React + Vite app (Node/pnpm)
├── schema.sql        # PostgreSQL schema
└── .mcp.json         # MCP server config
```

## Backend

**Stack:** FastAPI · PostgreSQL (psycopg2) · JWT auth · Gemini AI

```
Backend/
├── main.py
├── controllers/      # Route handlers
├── services/         # Business logic
├── dao/              # Database access
├── queries/          # SQL strings
├── schemas/          # Pydantic models
├── core/             # Config, JWT, Gemini
├── database/         # DB session
├── utils/            # Security, dependencies
└── constants/        # Enums
```

### Run the backend

```powershell
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Environment variables (`Backend/.env`)

```
DATABASE_NAME=Task_Management_System_DB
DATABASE_USER=postgres
DATABASE_PASSWORD=<password>
DATABASE_HOST=localhost
DATABASE_PORT=5432
SECRET_KEY=<jwt-secret>
GEMINI_API_KEY=<gemini-key>
```

## Frontend

**Stack:** React 19 · Vite 7 · Tailwind CSS 4 · React Router 7 · Axios

```
Frontend/
├── src/
│   ├── pages/        # Login, Signup, Dashboard, Tasks, NotFound
│   ├── components/   # auth/, common/, dashboard/, tasks/
│   ├── context/      # AuthContext
│   ├── hooks/        # useAuth
│   ├── services/     # api.js, authService, taskService
│   ├── config/       # Axios instance with JWT interceptor
│   └── utils/        # helpers, constants
└── vite.config.js    # Dev server on :3000, proxy /api → :8000
```

### Run the frontend

```powershell
cd Frontend
pnpm install
pnpm dev        # http://localhost:3000
```

## Database

PostgreSQL. Apply the schema with:

```powershell
psql -U postgres -d Task_Management_System_DB -f schema.sql
```

**Tables:** `users`, `tasks`, `task_comments`

## Auth

JWT (HS256, 60-min expiry). Token stored in localStorage; injected via Axios interceptor.

Roles: `admin` | `user`

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register user |
| POST | `/login` | Login, returns JWT |
| GET/POST | `/tasks` | List / create tasks |
| GET/PUT/DELETE | `/tasks/{id}` | Task CRUD |
| GET | `/user/*` | User management (admin) |

## Common Commands

```powershell
# Backend
uvicorn main:app --reload --port 8000

# Frontend
pnpm dev

# Run both (two terminals)
```
