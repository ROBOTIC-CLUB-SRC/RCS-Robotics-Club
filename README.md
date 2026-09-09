# RCS Robotics Club @ SRC SASTRA — Website + Club App

A full-stack starter for the RCS Robotics Club: a public robotics website plus a responsive, installable club-management web app.

## What is included

- Public site: Home, About, Members, Projects, Events, RCS Academy, Games, Quiz Arena, and "What should we conduct next?"
- Interactive flying robot hero that reacts to mouse and touch movement.
- Members/projects/events can show images.
- Robotics learning path from fundamentals → embedded → motors → control → kinematics → computer vision → ROS 2 → SLAM/autonomy → industrial robotics.
- Three mini-games: Sensor Sprint, PID Pilot, Warehouse Navigator.
- Quiz engine with instant explanations.
- Common login for Faculty + Members.
- Role-based account field (ready to extend for faculty-only actions).
- CRUD dashboard for members, projects, events, learning, quizzes and games.
- Website feedback/requests are stored in the same SQLite database and appear in the app.
- Image upload API is included; content forms currently accept image URLs for simplicity.
- PWA manifest so the app can be installed on a phone/desktop like an app.
- SQLite for a simple MVP; easy to migrate to PostgreSQL later.

## 1. Run locally

### Windows PowerShell

```powershell
cd rcs-robotics-club
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY="change-this-to-a-long-random-secret"
python app.py
```

Open:
- Public website: http://127.0.0.1:5000/
- Club app: http://127.0.0.1:5000/app
- Health check: http://127.0.0.1:5000/health

### Demo login

Faculty:
`faculty@rcs-sastra.org`

Member:
`member@rcs-sastra.org`

Password:
`RCS@2026`

**Change these credentials before deployment.** For a real club deployment, add a user-management screen and environment-based admin bootstrap.

## 2. How the sync works

Public pages call `GET /api/public/all`.

The app writes to the same SQLite tables through `/api/admin/...`.

Therefore:
Website → "What should RCS conduct?" → `feedback` table → App → Ideas & Requests.

And:
App → edit members/projects/events/etc. → database → Public website.

No manual copying is required.

## 3. GitHub

Create a new empty GitHub repository, then:

```bash
git init
git add .
git commit -m "Initial RCS Robotics Club website and app"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

Do **not** commit `.env`, `data/rcs.db`, or uploaded private material.

## 4. Deployment

For a simple deployment, this repo includes a `render.yaml` + `Procfile` for Render. It uses a small persistent disk for the SQLite `data/` directory, which is suitable for an MVP/demo. For a serious multi-editor club system, migrate to PostgreSQL.

Recommended production stack:
- Flask API
- PostgreSQL database
- Object storage for member/project images
- HTTPS
- Secret key stored as an environment variable
- A real email/password reset flow
- Backups

### Important SQLite note

SQLite is excellent for your first version and college demo. For multiple editors and production use, migrate to PostgreSQL.

## 5. Custom domain

Buy/choose a domain such as `rcsrobotics.in` or a SASTRA-approved club subdomain.

After deployment, your hosting provider gives you a URL. In your domain DNS:
- Add the provider's required CNAME/A record.
- Enable HTTPS.
- Set the app's canonical/public URL if you later add SEO metadata.

If the club is officially under SASTRA, get approval before using a SASTRA-owned subdomain or branding.

## 6. Suggested next upgrades

1. Faculty-only user management.
2. Real member registration/profile approval.
3. Rich-text event/project editor.
4. Direct image upload UI instead of image URLs.
5. Gallery + project detail pages.
6. Event registration database.
7. Quiz leaderboard and certificates.
8. More advanced games using Canvas/WebGL.
9. ROS 2 simulation lessons.
10. PostgreSQL + cloud storage + automated backups.
11. GitHub Actions for tests/deployment.
12. Wrap the PWA as an Android APK with Capacitor if a Play Store-style native app is required.

## Architecture

```text
Browser / Phone
      │
      ├── Public Website /
      │      └── GET /api/public/all
      │
      └── Club App /app
             ├── Login
             ├── CRUD content
             └── Feedback inbox
                     │
                     ▼
                 Flask API
                     │
                     ▼
                  SQLite
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 Public website               Club app
```

The uploaded RCS logo has been included as `static/assets/rcs-logo.jpg`. It is a crop from the supplied reference photo; replace it with the club's original high-resolution logo when available for a cleaner production result.
