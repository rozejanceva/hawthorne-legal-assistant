# AI Legal Office Assistant

Production-ready consultation scheduler: React booking site, FastAPI API, PostgreSQL in production, SQLite for local work, optional Google Calendar and SMTP.

## What it does

- Collects name, email, consultation type, and preferred time (office timezone).
- 30-minute Initial/Follow-up and 60-minute Detailed Case Consultation.
- Monday–Friday hours (09:00–17:00 by default) with a lunch break; back-to-back bookings allowed.
- Rechecks availability at confirmation, locks the slot, writes SQLite/Postgres, then creates the calendar event (and removes the event if storage fails).
- Chat widget answers scheduling questions and refuses legal advice.
- Office login at `/admin` lists appointments (HTTP-only cookie session).
- Demo calendar by default. Google Calendar in production after a one-time local OAuth.

## Run locally

1. `python -m venv .venv` then `.venv\Scripts\pip install -r requirements-dev.txt`
2. Copy `.env.example` to `.env`. Set `ADMIN_PASSWORD` and leave `APP_ENV=development`.
3. `uvicorn backend.main:app --reload`
4. In `frontend`: `npm install` then `npm run dev`
5. Site: `http://127.0.0.1:5173` — API docs: `http://127.0.0.1:8000/docs` — office login: `http://127.0.0.1:5173/admin`

The Vite dev server proxies `/api` to port 8000.

```bash
.venv\Scripts\pytest
```

## Connect Google Calendar

1. Google Cloud: enable Calendar API, create **Desktop** OAuth credentials, add yourself as a test user.
2. Save the JSON as `credentials.json` in the project root.
3. In `.env` set `CALENDAR_MODE=google` and `GOOGLE_ALLOW_BROWSER_OAUTH=true`.
4. Restart the backend and complete the browser consent. This writes `token.json`.
5. Set `GOOGLE_ALLOW_BROWSER_OAUTH=false` after that. Copy `credentials.json` and `token.json` onto the server; do not commit them.

## Production deploy

1. Copy `.env.production.example` to `.env` on the server. Set `SECRET_KEY`, `ADMIN_PASSWORD` (12+ characters), `POSTGRES_PASSWORD`, `CORS_ORIGINS`, and `TRUSTED_HOSTS` to your public hostname.
2. Put `credentials.json` and `token.json` next to `docker-compose.prod.yml` (Google mode). If you stay on demo calendar, create empty placeholder files or change the compose volume mounts.
3. Optional SMTP variables send a confirmation email after each booking.
4. Put TLS in front of port 80 (load balancer, Caddy, or Cloudflare) and set `SECURE_COOKIES=true` when the site is served over HTTPS.
5. Start:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The app is served at `http://<host>/`. Health check: `/healthz`. Appointments: `/admin`.

Production refuses to start with SQLite, a default secret, a weak admin password, or browser-based Google OAuth.

The production API also validates database readiness at `/healthz`, rejects past and off-grid appointment times, serializes overlapping booking decisions in PostgreSQL, hides API documentation, and adds browser security headers.

## Publish on GitHub and get a real URL

The easiest hosted setup is the included Render Blueprint. It deploys the React site and FastAPI API as one HTTPS service and creates a managed PostgreSQL database.

### 1. Create the GitHub repository

Create a new empty repository on GitHub named `hawthorne-legal-assistant`. Do not add a README, license, or `.gitignore on GitHub because this folder already contains them.

Run these commands in this project folder, replacing `YOUR_GITHUB_USERNAME`:

```powershell
git init
git add .
git commit -m "Production-ready legal scheduling assistant"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/hawthorne-legal-assistant.git
git push -u origin main
```

GitHub may open a browser for sign-in. The `.env`, database, tokens, dependencies, and log files are ignored and will not be uploaded.

### 2. Deploy the real website

1. Sign in to [Render](https://render.com) with GitHub.
2. Choose **New > Blueprint** and select the `hawthorne-legal-assistant` repository.
3. Render reads `render.yaml`. Enter a strong `ADMIN_PASSWORD` when prompted. `OPENAI_API_KEY` is optional; add it if you want AI-generated chat replies.
4. Approve the Blueprint and wait for both the web service and PostgreSQL database to become available.
5. Open the `onrender.com` URL shown by Render. The admin page is that URL followed by `/admin`.

If Render changes the service name because the preferred URL is already taken, the included trusted-host wildcard still allows the assigned `onrender.com` address. The frontend and API share that origin, so no separate API URL is needed.

### 3. Connect a custom domain (optional)

In the Render web service, open **Settings > Custom Domains**, add the domain you own, and copy the DNS records into your domain registrar. After HTTPS is active, update `CORS_ORIGINS` to the full `https://` URL and `TRUSTED_HOSTS` to the hostname only.

### Before a real client uses it

- Set `OPENAI_API_KEY` in Render; never put the key in GitHub or the React frontend.
- Configure Google Calendar and SMTP using the instructions above if the office needs calendar events and confirmation email.
- Replace the placeholder Hawthorne Legal name, contact details, privacy notice, and legal disclaimer with the client's approved content.
- Use a paid PostgreSQL/web plan for a real business. Free hosting can sleep, has operational limits, and should be treated as a demonstration environment.
- Rotate any database password or API key that has ever been pasted into chat, logs, screenshots, or a Git commit.
- Arrange managed database backups and test restoring one before accepting real appointments.
- Have the client approve the public wording, privacy notice, retention policy, booking workflow, office hours, and legal disclaimer.

## Security notes

- Calendar tokens never go to the browser.
- Public booking routes are rate-limited.
- Admin access uses a SameSite cookie, not Basic auth in the browser.
- Replace the single office password with your identity provider when you outgrow one-admin access.
