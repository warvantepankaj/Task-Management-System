# Deployment Guide

Free-tier deployment of the Task Management System: **Cloudflare Pages** (frontend) + **AWS EC2** (backend) + **AWS RDS** (PostgreSQL), with a **GitHub Actions** pipeline that lints PRs and auto-deploys `main` to EC2.

**Total monthly cost in AWS free tier**: $0 for the first 12 months. After that ~$10/mo if you stay on the same shapes.

---

## 1. Architecture

```
                                          ┌────────────────────────┐
   ┌──────────┐   HTTPS                    │  Cloudflare Pages      │
   │ Browser  │ ─────────────────────────► │  (static React build)  │
   └────┬─────┘                            └────────────────────────┘
        │
        │ /api/*    HTTPS
        │ /ws/tasks WSS
        ▼
   ┌─────────────────────┐
   │ nginx (TLS, EC2)    │ ──► uvicorn :8000 (FastAPI, websockets)
   │ Let's Encrypt cert  │
   └──────────┬──────────┘
              │ libpq, 5432
              ▼
   ┌─────────────────────┐
   │ RDS PostgreSQL      │
   │ db.t4g.micro        │
   └─────────────────────┘
```

CI/CD:

```
PR  ─► GitHub Actions ─► lint + build (backend, frontend)
push main ─► GitHub Actions ─► SSH into EC2 → pull, install, restart systemd unit
push main ─► Cloudflare Pages (its own GitHub integration) → build + deploy frontend
```

---

## 2. Code changes you need before first deploy

These were flagged in the audit; commit them once before deploying.

### 2.1 `Backend/core/config.py` — stop hardcoding the `.env` path

```diff
- from dotenv import load_dotenv
- load_dotenv(r"C:\Pankaj's Space\Projects\FAST-API\Task_Management_System\Backend\.env")
+ from pathlib import Path
+ from dotenv import load_dotenv
+ load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

### 2.2 `Backend/main.py` — env-driven CORS

```diff
- app.add_middleware(
-     CORSMiddleware,
-     allow_origins=["http://localhost:3000"],
-     allow_credentials=True,
-     allow_methods=["*"],
-     allow_headers=["*"],
- )
+ import os
+ origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
+ app.add_middleware(
+     CORSMiddleware,
+     allow_origins=origins,
+     allow_credentials=True,
+     allow_methods=["*"],
+     allow_headers=["*"],
+ )
```

### 2.3 `Frontend/src/utils/constants.js` — env-driven API base URL

```diff
- export const API_BASE_URL = 'http://localhost:8000';
+ export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

`useTaskSocket.js` already reads `import.meta.env.VITE_WS_URL` — no change needed; just set the env at build time.

### 2.4 `Frontend/.env.production` (new)

```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

---

## 3. Database — Amazon RDS (free tier)

| Setting | Value |
|---|---|
| Engine | PostgreSQL 16 |
| Template | **Free tier** |
| Instance class | `db.t4g.micro` |
| Storage | 20 GB gp3, autoscaling **off** |
| Multi-AZ | **No** |
| Public access | Yes (will restrict via security group) |
| Backup retention | 7 days |
| Master user | `postgres` |
| Master password | *generate and save* |
| Initial DB name | `task_management_system_db` |

**Security group inbound rule**: PostgreSQL/5432 from the EC2 security group only (not 0.0.0.0/0).

Once it's up, apply the schema from your laptop:

```powershell
psql -h <rds-endpoint> -U postgres -d task_management_system_db -f schema.sql
```

---

## 4. Backend — AWS EC2 (free tier)

### 4.1 Launch the instance

| Setting | Value |
|---|---|
| AMI | Amazon Linux 2023 |
| Instance type | `t3.micro` (or `t2.micro` if t3 unavailable) |
| Key pair | Create a new one, save the `.pem` locally — you'll need it for SSH + GitHub Actions |
| Network | Default VPC, public IP **enabled** |
| Storage | 8 GB gp3 (free tier limit is 30 GB total) |
| Security group | Allow inbound 22/SSH (your IP only), 80/HTTP, 443/HTTPS (0.0.0.0/0) |

Then allocate and associate an **Elastic IP** so the public IP survives reboots.

### 4.2 First-time server setup

SSH in:

```powershell
ssh -i taskmgmt.pem ec2-user@<elastic-ip>
```

Install runtime + nginx + certbot:

```bash
sudo dnf update -y
sudo dnf install -y git nginx python3.11 python3.11-pip
python3.11 -m ensurepip --upgrade
sudo dnf install -y python3.11-devel postgresql15
sudo dnf install -y certbot python3-certbot-nginx
sudo systemctl enable --now nginx
```

Clone and bootstrap the app:

```bash
cd /opt
sudo git clone https://github.com/<your-org>/Task-Management-System.git taskmgmt
sudo chown -R ec2-user:ec2-user taskmgmt
cd taskmgmt/Backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `Backend/.env` with production values:

```bash
cat > /opt/taskmgmt/Backend/.env <<'EOF'
DATABASE_HOST=<rds-endpoint>
DATABASE_PORT=5432
DATABASE_NAME=task_management_system_db
DATABASE_USER=postgres
DATABASE_PASSWORD=<rds-master-password>

JWT_SECRET=<paste output of: python -c "import secrets; print(secrets.token_urlsafe(64))">
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=14

CORS_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com

# Optional — leave SMTP empty in dev; logs reset link to stdout
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
MAIL_FROM=no-reply@yourdomain.com
RESET_TOKEN_TTL_MIN=60
EOF
chmod 600 /opt/taskmgmt/Backend/.env
```

### 4.3 systemd unit

```bash
sudo tee /etc/systemd/system/taskmgmt.service > /dev/null <<'EOF'
[Unit]
Description=Task Management uvicorn
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/taskmgmt/Backend
ExecStart=/opt/taskmgmt/Backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now taskmgmt
sudo systemctl status taskmgmt
```

> **`--workers 1` is intentional.** WebSocket connections are stored in an in-memory `ConnectionManager`. Multiple workers each hold their own map; cross-worker broadcasts don't happen. To scale beyond one worker, swap the manager for Redis pub/sub (out of scope here).

### 4.4 nginx + TLS

```bash
sudo tee /etc/nginx/conf.d/taskmgmt.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket upgrade for /ws/tasks
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
EOF
sudo nginx -t && sudo systemctl reload nginx
```

Point your DNS `api.yourdomain.com` → EC2 Elastic IP, then:

```bash
sudo certbot --nginx -d api.yourdomain.com --redirect --agree-tos -m you@yourdomain.com -n
```

Certbot installs a cron job for renewal; you don't have to touch it again.

> **No domain?** Use a free `*.nip.io` host like `api.<elastic-ip>.nip.io`, or a Cloudflare-managed subdomain you already own.

### 4.5 Verify

```bash
curl https://api.yourdomain.com/docs            # FastAPI OpenAPI UI
```

Open a browser, log in, watch the EC2 log:

```bash
sudo journalctl -u taskmgmt -f
```

---

## 5. Frontend — Cloudflare Pages

1. Push your code (already done).
2. Cloudflare dashboard → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git** → pick the repo.
3. Build configuration:
   - Framework preset: **Vite**
   - Build command: `pnpm install --frozen-lockfile && pnpm build`
   - Build output directory: `Frontend/dist`
   - Root directory: `Frontend`
4. Environment variables (Pages → Settings → Environment variables, Production):
   - `VITE_API_BASE_URL` → `https://api.yourdomain.com`
   - `VITE_WS_URL` → `wss://api.yourdomain.com`
5. First deploy runs automatically; subsequent pushes to `main` redeploy.

Map a custom domain (Pages → Custom domains) and Cloudflare handles TLS automatically.

---

## 6. GitHub Actions pipeline

Two workflows go under `.github/workflows/`:

### 6.1 `ci.yml` — runs on every PR

```yaml
name: ci

on:
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        working-directory: Backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Import-check
        working-directory: Backend
        env:
          JWT_SECRET: ci-placeholder-secret-not-used
          DATABASE_HOST: localhost
          DATABASE_PORT: '5432'
          DATABASE_NAME: ci
          DATABASE_USER: ci
          DATABASE_PASSWORD: ci
        run: python -c "from main import app; print('routes:', len(app.routes))"

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          cache-dependency-path: Frontend/pnpm-lock.yaml
      - name: Install
        working-directory: Frontend
        run: pnpm install --frozen-lockfile
      - name: Build
        working-directory: Frontend
        env:
          VITE_API_BASE_URL: https://api.example.com
          VITE_WS_URL: wss://api.example.com
        run: pnpm build
```

### 6.2 `deploy-backend.yml` — SSH-deploys on push to `main`

```yaml
name: deploy-backend

on:
  push:
    branches: [main]
    paths:
      - 'Backend/**'
      - '.github/workflows/deploy-backend.yml'

concurrency:
  group: deploy-backend
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            set -euo pipefail
            cd /opt/taskmgmt
            git fetch --all
            git reset --hard origin/main
            cd Backend
            source .venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            sudo systemctl restart taskmgmt
            sleep 3
            sudo systemctl is-active taskmgmt
```

### 6.3 Secrets to add (GitHub → Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `EC2_HOST` | Elastic IP or `api.yourdomain.com` |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | Contents of your `.pem` file (the **private** key) |

Cloudflare Pages doesn't need GitHub Actions secrets — its GitHub App authenticates directly.

---

## 7. Smoke test the full deploy

1. **Health**: `curl https://api.yourdomain.com/docs` → returns the FastAPI Swagger HTML.
2. **CORS**: `https://yourdomain.com/login` in browser → submit credentials → DevTools Network shows `200` on `/login` and a JSON body with `access_token` + `refresh_token`.
3. **WebSocket**: open the board in two tabs; drag a card in tab A; tab B shows the ghost following A's cursor.
4. **Password reset**: `/forgot-password` → check the EC2 log; you should see the reset link printed there (SMTP unset = stdout fallback). Click the link in a fresh browser, set a new password, log back in.

---

## 8. Going-not-free upgrade paths

| Need | Next step | Cost |
|---|---|---|
| More than one worker | Add Redis (ElastiCache or Upstash free) and rewrite `ConnectionManager` to use pub/sub. | ~$0–5/mo |
| Real email | Brevo / Resend / SES with verified domain. | Free at low volume |
| Higher uptime | EC2 Auto Scaling Group of 2 + ALB; pair sockets to a single instance with sticky sessions or use Redis. | ~$15/mo |
| Cheaper DB long-term | Switch RDS → Neon (Postgres, free tier is forever, 0.5 GB). | $0 |
| Skip server ops | Replace EC2 with Render / Fly / Koyeb. Free tiers idle-sleep, which will disconnect WS. | $0–7/mo |

---

## 9. Common failure modes (and what fixes them)

| Symptom | Cause | Fix |
|---|---|---|
| `/ws/tasks` 404 from prod | `websockets` not installed in the venv used to start uvicorn | `Backend/.venv/bin/pip install websockets` then restart `taskmgmt.service` |
| `/ws/tasks` 502 from nginx | `Upgrade` headers missing in nginx | See §4.4 — must include `proxy_http_version 1.1; proxy_set_header Upgrade ...` |
| CORS error in browser | `CORS_ORIGINS` env not set to your prod frontend URL | Set in `Backend/.env`, restart |
| `JWT_SECRET is not set` at startup | env not loaded | Confirm `.env` exists at `/opt/taskmgmt/Backend/.env`; recheck the patched config loader |
| Login works but `/auth/refresh` 401s after 15 min | Frontend on stale build that doesn't include the refresh interceptor | Hard-refresh Pages; verify `Network → Fetch/XHR → /auth/refresh` 200 happens automatically when the access token expires |
| Reset email never arrives | SMTP unset → link only goes to stdout. | Either check `journalctl -u taskmgmt` for the link, or configure SMTP |
