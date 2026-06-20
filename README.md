**English** | [中文](README_zh.md)

# Z-CMDB Lite

> Accuracy-first, zero-barrier, lightweight CMDB for small and medium teams

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## Introduction

Z-CMDB Lite is designed for IT operations and security engineers in **small-to-medium teams (5–50 people)**. It manages intranet / office network / IDC / cloud assets via nmap scan uploads, for:

- Daily operations asset ledger
- Security audit & compliance readiness
- HVV / Red-Blue exercise asset inventory
- Port exposure analysis

**Core design principles**: SQLite single-file, zero middleware dependency, all write operations are auditable, sensitive data stays on-premises.

---

## V0.3 Highlights

V0.3 brings **full internationalization (i18n)** to Z-CMDB Lite, adding English/Chinese bilingual support across the entire frontend. The default language is now English, with one-click switching available from any page via the topbar toggle or System Config. The README documentation is also split into separate English and Chinese editions.

![Language Switching](img/i18n-preview.png)

### Bilingual UI

- **Complete English translation** of all 16 pages and 3 shared components — every button, label, tooltip, validation message, and chart title is localized
- **Topbar language toggle** (EN/中) for instant switching from any page without navigating to settings
- **System Config language selector** (section 00) with dropdown for English / Chinese
- **Persistent preference** saved to `localStorage` — language choice survives browser refresh and restarts
- **Element Plus locale sync** — pagination text, date pickers, table empty states, and all built-in component labels switch dynamically via `ElConfigProvider`
- **ECharts chart re-rendering** — dashboard charts (topology, distribution, port exposure) automatically re-render with localized labels on language switch

### README Split

- `README.md` (English, default) and `README_zh.md` (Chinese) with mutual language toggle links at the top of each file
- Both editions stay in sync with identical structure and screenshots

---

## V0.2 Highlights

V0.2 introduces the **Asset Overview** (`/dashboard`) as the default homepage after login, aggregating key metrics previously scattered across reports and asset lists into a single view, enabling operations and security engineers to grasp the overall asset security posture at a glance. This release also includes a round of frontend engineering quality improvements.

![Asset Overview](img/dashboard-overview.png)

### Asset Overview

All page data is provided by the backend aggregation endpoint `GET /api/reports/dashboard-summary` in a single request (SQL aggregation + 30s TTL cache, full page refresh triggers only one request). The page consists of 5 modules:

**KPI Cards (8 metrics)**
Total Assets · Online · Offline · Decommissioned · Dangerous Ports · Shadow Assets · Monthly Changes · Scan Coverage. Numbers animate with a flip effect on page entry; "Online / Offline / Decommissioned" cards are clickable, linking directly to the asset list with pre-applied status filters.

**Network Zone Topology**
ECharts force-directed layout, aggregated by `network_zone`, node size reflects asset count; zones with core assets are highlighted with red borders, supports drag and zoom exploration.

**Asset Distribution Donut Chart**
Center displays total asset count, top tabs switch between four dimensions: Network Zone / Asset Type / Importance / OS.

**Port Exposure**
Left side: Top 10 open ports horizontal bar chart (dangerous ports auto-highlighted in red); right side: donut chart showing distribution by network zone.

**Dangerous Port Alert Scrolling List**
Scrolling broadcast of dangerous port details (IP / Port / Service / Zone / Level), color-coded by severity (high-risk with pulse animation), auto-pauses on mouse hover for inspection.

### Engineering Improvements

- **Removed deprecated large-screen code**: Cleaned up the unused fixed-resolution large-screen implementation (`panels/*`, `ScreenContainer`, `registry`), unified as the responsive Asset Overview page as the sole implementation, eliminating dual code paths and inconsistent color schemes
- **Performance**: Backend cache hit on first load (only "Refresh Data" button forces refresh), window `resize` debounce, ECharts instances use `shallowRef`, removed redundant `deep` watchers
- **Responsive**: Added desktop / laptop / tablet breakpoints, KPI cards adapt from 8 → 4 → 2 columns, dual-column cards auto-stack to single column on narrow screens
- **UX**: Loading skeleton screens replace blank pages, clickable KPIs add hover feedback, dangerous port list auto-pauses scrolling when page is backgrounded (fixes background idle and timer leaks)
- **Accessibility**: Number flip, high-risk pulse, and auto-scroll respect system "Reduce Motion" (`prefers-reduced-motion`) settings
- **Maintainability**: Zone colors / dangerous ports / zone mapping constants extracted as single source (`constants/dashboard.ts`), KPI icons extracted as independent components

> Full changelog at the end of this document: [Changelog](#changelog).

---

## Feature Overview

### Asset Management

![Asset List](img/001.png)

- Supports five asset types: Physical Server, Virtual Machine, **Cloud Server**, Network Device, Other
- When Cloud Server is selected, network zone auto-switches to cloud provider (Alibaba Cloud / Tencent Cloud / Huawei Cloud / AWS / Azure / GCP)
- Multi-dimension filtering: Network Zone, Asset Type, Importance, Status
- Full-text search: IP, Hostname, Asset Number, Business System, **Application Name** (e.g., nginx, mysql)
- Batch operations: Batch modify Owner, Business System, Importance, Network Zone
- Export: Standard CSV + Threat Hunting Assistant compatible format

### Asset Detail

![Asset Detail](img/003.png)

Three tabs for one-stop viewing:

| Tab | Content |
|-----|---------|
| Basic Info | Asset Number, IP/MAC/Hostname, OS, Ownership, Hardware, Procurement & Warranty |
| Ports | Open ports discovered by scan, including service name, version, status |
| Applications | Manually registered or scan-extracted application list, including version, port, install path |

**Port-Application bidirectional sync**: When manually adding an application with ports, it auto-writes to the ports table; when confirming nmap scan import, ports with `service_name` automatically generate application records.

### Scan Batches

![Scan Batches](img/005.png)
![Diff Confirmation](img/006.png)

1. Run nmap on a jump host to generate an XML report
2. Upload to the platform, auto-parse and perform diff analysis against existing assets
3. Diffs are categorized into four types: **New Discovery** / **Change** / **Disappearance** / **Recovery**
4. Manually review each host's port change details before confirming import
5. Disappeared hosts are not immediately deleted; `missing_count + 1`, marked offline only after exceeding the threshold

### Topology (AI-Generated)

![Topology](img/007.png)

- One-click LLM invocation to generate a draft drawio network topology diagram
- Supports DeepSeek / OpenRouter / Local Ollama
- Asset data is **auto-anonymized** before being sent to the LLM (IP → placeholder, business system → code name)
- Core assets can be configured to force local model usage; sensitive data stays on-premises
- After generation, manual adjustments can be made in the embedded drawio editor, with version management and rollback support

### Security Reports

![Security Reports](img/008.png)

- Asset distribution: Network Zone, Importance, OS, Asset Type
- Port exposure analysis: Top ports, dangerous port statistics
- Scan coverage: Recent scan time distribution
- Threat Hunting Assistant compatible export: Expanded by "Asset x Application", including environment / criticality / exposure_scope / vendor fields

### Audit Log

![Audit Log](img/009.png)

- Records all login, CRUD, export, and LLM call operations
- **Tamper-proof**: SQLite triggers at the database layer prevent UPDATE / DELETE
- Supports filtering by action type, user, target type

### Users & Permissions

![User Management](img/010.png)

Three roles with separation of duties:

| Role | Permissions |
|------|------------|
| `super_admin` | All operations + User management + System configuration |
| `admin` | Asset CRUD, Scan upload & confirm, Topology generation |
| `auditor` | Read-only + Audit log viewing |

> The system requires at least one auditor account to be created before unlocking full functionality (compliance separation-of-duties requirement).

### System Configuration

- LLM Provider / API Key / Model / Base URL
- Core asset routing policy (whether to force local Ollama)
- Asset number prefix (default `CMDB`)
- Scan disappearance threshold (consecutive N scans without detection before marking offline)
- Upload file size limit

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend Language | Python 3.11+ |
| Web Framework | FastAPI |
| Database | SQLite 3 (WAL mode, single file) |
| ORM | SQLAlchemy 2.0 |
| Data Migration | Alembic |
| Frontend Framework | Vue 3 + Vite + TypeScript |
| UI Component Library | Element Plus |
| State Management | Pinia |
| Password Hashing | argon2id |
| Authentication | JWT (access + refresh token) |
| Deployment | Docker + docker-compose |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone the project
git clone https://github.com/Zer00n/z-cmdb.git
cd z-cmdb

# 2. Configure JWT secret
cp secrets/jwt_secret.txt.example secrets/jwt_secret.txt
# Edit secrets/jwt_secret.txt, enter a random string (recommended 32+ characters)

# 3. Start
docker compose -f docker/docker-compose.yml up --build -d

# 4. Access
# http://localhost:8080

# 5. Get initial password (auto-generated on first start)
# Method 1: View container logs
docker compose -f docker/docker-compose.yml logs backend | grep "密码"
# Method 2: Read password file
cat data/INITIAL_ADMIN_PASSWORD.txt
# Default account: admin, use the password obtained above to log in

# (Optional) Preset initial password, consistent for both Docker and Windows modes:
# Create a .env file in the repository root, write:
# CMDB_INITIAL_ADMIN_PASSWORD=YourPassword@123
# Then start with:
# docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

### Option 2: Local Development (Windows 11)

**One-click Start**

The project root provides Windows batch scripts, double-click to start both frontend and backend simultaneously:

```
dev-start.bat    # One-click start backend + frontend (auto-opens two terminal windows)
dev-stop.bat     # One-click stop all services
```

> Prerequisite: Complete the environment initialization below (venv + pnpm install + alembic upgrade head).

**Environment Initialization (First time only)**

```powershell
# Backend
cd backend
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
alembic upgrade head

# Frontend
cd ..\frontend
pnpm install
```

**Manual Start (for separate debugging)**

Backend:

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (new terminal):

```powershell
cd frontend
pnpm dev
```

Access http://localhost:5173
Initial password is in `backend/data/INITIAL_ADMIN_PASSWORD.txt` (auto-generated on first start).

---

## Project Structure

```
z-cmdb/
├── backend/
│   ├── app/
│   │   ├── cli.py            # Management CLI (init-db / reset-admin)
│   │   ├── core/           # Config, security, dependency injection, encryption
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic v2 Schemas
│   │   ├── routers/        # API routes
│   │   ├── services/       # Business logic
│   │   ├── repositories/   # Data access layer
│   │   └── utils/          # nmap parsing and other utilities
│   ├── alembic/            # Database migration scripts
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/          # Page components
│       ├── components/     # Shared components
│       ├── api/            # API wrappers
│       ├── stores/         # Pinia state
│       ├── styles/         # Global styles & Design Tokens
│       ├── types/          # TypeScript type definitions
│       └── constants/      # Enum constants (OS options, app categories, etc.)
├── docker/                 # Dockerfile & docker-compose
├── scripts/                # Operations scripts (password reset, audit export, etc.)
├── secrets/                # JWT secret (not committed, only .example files)
├── img/                    # Feature screenshots
└── README.md
```

---

## nmap Scan Reference

```bash
# Quick scan (common ports)
nmap -sV -T4 -oX scan_result.xml 192.168.1.0/24

# Full port scan
nmap -sV -p- -T4 -oX scan_full.xml 192.168.1.0/24

# Specific ports + OS detection
nmap -sV -O -p 22,80,443,3306,6379,8080 -oX scan_web.xml 192.168.1.0/24
```

After scanning, upload the `.xml` file to the "Scan Batches" page on the platform.

---

## Security Notes

- Passwords use argon2id hashing (memory=64MB, time=3, parallelism=4)
- JWT supports access token (short-lived) + refresh token (long-lived)
- Account auto-locks after exceeding failed login threshold
- All response headers include CSP / X-Content-Type-Options / X-Frame-Options
- Audit logs are tamper-proof via database triggers
- Asset data is anonymized before LLM calls; core assets can be forced to use local models

---

## Forgot Password / Reset Admin

**Docker environment:**

```bash
# Reset to random password (new password printed to terminal and written to data/INITIAL_ADMIN_PASSWORD.txt)
docker compose -f docker/docker-compose.yml exec backend python -m app.cli reset-admin

# Reset to a specific password
docker compose -f docker/docker-compose.yml exec backend python -m app.cli reset-admin --password 'YourNew@Pass1'
```

**Local development:**

```powershell
cd backend
.venv\Scripts\activate
python -m app.cli reset-admin
# Or specify a password:
python -m app.cli reset-admin --password 'YourNew@Pass1'
```

---

## Disclaimer

**This project is not recommended for production deployment.**

Z-CMDB Lite is designed as a local tool for individuals or small teams, suitable for the following usage patterns:

- Deployed on a **local machine or intranet workstation**, started on demand
- Shut down after use (`dev-stop.bat` or close terminal); do not leave it exposed on the network long-term
- **Do not expose the service port to the public internet**; if remote access is needed, use VPN or SSH tunnel
- Database is a single SQLite file (`backend/data/cmdb.db`); back up regularly
- Change the default admin password immediately after first login (system will enforce this)

If your use case involves concurrent writes from multiple users (>50 people), high availability, or public-facing services, please consider production-grade database solutions like PostgreSQL.

---

## Changelog

### V0.3 (2026-06-20)

**Internationalization (i18n)**
- Added full English/Chinese bilingual support via vue-i18n@9 (Composition API mode)
- Default language changed to English; all UI strings translated
- Language toggle button in topbar (EN/中) for quick switching from any page
- Language settings card in System Config page (section 00) with dropdown selector
- Language preference persisted to localStorage across sessions
- Element Plus component locale (pagination, date pickers, table empty text) dynamically switches via ElConfigProvider
- README split into English (`README.md`, default) and Chinese (`README_zh.md`) with mutual language toggle links
- Translation files organized by module: common, layout, router, login, dashboard, asset, scan, topology, report, audit, user, settings, help, components, constants
- Shared `useTranslatedLabels()` composable centralizes zoneLabel/importanceLabel/statusLabel/typeLabel/roleLabel functions

### V0.2 (2026-06-19)

**Asset Overview**
- Added `/dashboard` Asset Overview page as the default homepage after login
- 8 KPI metric cards (Total Assets, Online/Offline/Decommissioned, Dangerous Ports, Shadow Assets, Monthly Changes, Scan Coverage) with number flip animation
- Network Zone Topology (ECharts force-directed), aggregated by `network_zone`, core assets highlighted with red borders
- Asset Distribution donut chart, supporting Network Zone/Asset Type/Importance/OS dimension switching
- Port Exposure: Top 10 open ports horizontal bar chart + distribution by zone donut chart
- Dangerous Port Alert scrolling list, color-coded by severity (high-risk pulse animation), auto-pauses on hover
- Shadow Assets (missing fields + long-term offline) tab switching display
- Asset change timeline, audit & LLM activity stream scrolling broadcast
- Backend aggregation endpoint `GET /api/reports/dashboard-summary`, SQL aggregation + 30s TTL cache, single refresh triggers only one request
- Dangerous port list and high-risk zones migrated from hardcoded to `system_configs` configuration, reports and overview share the same judgment logic
- Layout persistence (personal layout + global default), `system_configs` KV storage

**Docker Deployment Fixes**
- Backend dependencies switched to `/opt/venv` virtual environment, fixing `import sqlalchemy` failure in `docker exec`
- Added in-app CLI `python -m app.cli` (`init-db` / `reset-admin`), no need to copy scripts into the container
- Initial password controllable: supports `CMDB_INITIAL_ADMIN_PASSWORD` environment variable preset, random generation and write to `data/INITIAL_ADMIN_PASSWORD.txt` if not set
- Added `COOKIE_SECURE` configuration, fixing refresh token cookie rejection by browsers under HTTP deployment
- Added `.env.example` environment variable template
- Local development scripts (`scripts/reset_admin.py`, `init_db.py`) path logic corrected, reusing CLI service layer

**Topology Improvements**
- Fixed routing to Ollama reusing OpenRouter model name causing 502 error
- Added Ollama availability detection, showing clear Chinese prompt when unavailable (instead of cryptic 502)
- Added `llm_ollama_model` independent configuration, Ollama routing uses dedicated model name
- LLM provider simplified to "Custom" and "Local" two options, custom supports any OpenAI-compatible API
- Topology page added "Generation Log" tab, showing LLM call process and details (provider/model/latency)
- Fixed config page saving masked values overwriting real API Key bug

**Other Improvements**
- Fixed change password 422 error: frontend password policy validation (>= 12 chars + uppercase/lowercase/digit/symbol) aligned with backend
- 422 Pydantic validation error messages correctly displayed (extracting `msg` from `detail` array)
- Backend `llm_service.get_provider()` no longer validates provider name, non-ollama always uses OpenAI-compatible interface

---

## License

[MIT](LICENSE)
