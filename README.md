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

### Deployment

Z-CMDB supports three deployment methods: **Windows double-click launcher** (zero-install, embedded Python), **Linux bare-metal** (venv + systemd), and **Docker** (layered images, bind-mounted database). All methods use single-port FastAPI hosting with auto-generated JWT secrets.

| Method | Best For | Docs |
|---|---|---|
| 🪟 Windows Launcher | End users, air-gapped machines | [`deploy/DEPLOY_EN.md §1`](deploy/DEPLOY_EN.md#1-windows-double-click-launcher) |
| 🐧 Linux Bare-Metal | Small servers, VMs | [`deploy/DEPLOY_EN.md §2`](deploy/DEPLOY_EN.md#2-linux-bare-metal) |
| 🐳 Docker | CI/CD, containerized environments | [`deploy/DEPLOY_EN.md §3`](deploy/DEPLOY_EN.md#3-linux-docker) |

> **Full deployment guide**: [deploy/DEPLOY_EN.md](deploy/DEPLOY_EN.md) (English) | [deploy/DEPLOY.md](deploy/DEPLOY.md) (中文)

---

## ⚠️ Upgrade Notice

> ### V0.6.5 — Database Encryption Upgrade
>
> V0.6.5 introduces static encryption. **Existing plaintext databases must be migrated** before starting the new version:
>
> ```bash
> # 1. Stop the service
> # 2. Back up
> cp data/cmdb.db data/cmdb.db.bak
>
> # 3. Encrypt the database
> cd backend
> PYTHONPATH=. python tools/encrypt_existing_db.py \
>     --password '<your-admin-password>'
>
> # 4. Save the recovery code (one-time!)
> # 5. Restart → unlock via browser
> ```
>
> **Do NOT skip this step.** Starting V0.6.5 without migrating will result in a LOCKED state with no existing data accessible. See the [V0.6.5 section](#v065--database-static-encryption-at-rest) for full details.
>
> ---
>
> ### V0.5.1 — Migrations
>
> After pulling V0.5.1, run database migrations before starting:
>
> ```bash
> # If using a virtual environment, activate it first:
> # Windows:   cd backend && .venv\Scripts\activate
> # Linux/Mac: cd backend && source .venv/bin/activate
>
> cd backend && alembic upgrade head
> ```
>
> Docker users: no action needed — migrations run automatically on container startup.
>
> This applies two new migrations:
> - `e9f0a1b2c3d4` — adds `token_version` column to `users` table (for token revocation on password change / account disable)
> - `f0a1b2c3d4e5` — adds index on `scan_snapshot_items.ip_address` (performance optimization)
>
> **Without running this command, the application will fail to start.**

---

## V0.6.5 — Database Static Encryption (At-Rest)

V0.6.5 adds **at-rest encryption** to Z-CMDB's SQLite database. A stolen `.db` file can no longer be opened by any SQLite tool — it appears as random bytes and requires an admin passphrase or recovery code, entered through the application, to unlock.

### Envelope Encryption Design

| Layer | Role |
|---|---|
| **DEK** (Data Encryption Key) | 32-byte random key, the actual SQLCipher/MC key. Never persisted in plaintext; held in memory only after unlock |
| **KEK** (Key Encryption Key) | Derived from admin passphrase via Argon2id (per-user salt). Used to wrap/unwrap the DEK |
| **keystore.json** | Stores wrapped DEK + salt + nonce (all ciphertext). Safe to back up; harmless if leaked without the passphrase |

- KDF: Argon2id (`memory=64MB, time=3, parallelism=4`)
- Wrap: AES-256-GCM (12-byte random nonce per wrap)

### Application State Machine

The application starts in **LOCKED** state (DB engine not initialized). After setup or unlock, it transitions to **UNLOCKED** with the DEK in memory.

| Action | Effect |
|---|---|
| **Setup** (first run) | Generate DEK → create admin → generate one-time recovery code → encrypt DB → unlock |
| **Unlock (passphrase)** | Derive KEK → unwrap DEK → init engine → run migrations → issue JWT (single-passphrase UX) |
| **Unlock (recovery code)** | Same as above, but does **not** auto-login (requires separate admin login after) |
| **Change password** | Re-wrap DEK with new KEK; database untouched |
| **Add admin** | Wrap DEK with new admin's KEK → add keystore record |
| **Remove admin** | Remove keystore record → passphrase immediately invalidated |

### Deployment Changes

- **Startup scripts no longer run `alembic upgrade head`**. Migrations run automatically after vault unlock/setup (encrypted DB cannot be migrated without the DEK).
- **Windows/Linux/Docker** all support encryption. Unattended mode via `CMDB_UNLOCK_PASSWORD` environment variable (injected at runtime, never written to `.env`).
- **One-time migration tool** for existing plaintext databases: `python tools/encrypt_existing_db.py --password '<admin-password>'`

### ⚠️ Important

- **Recovery code**: Generated once during setup, shown only once. It is the **only** way to recover if all admin passwords are lost. **Store it offline immediately** (paper, password manager).
- **Backup**: Always back up both `cmdb.db` **and** `keystore.json`. Losing the keystore without a recovery code means **permanent data loss**.
- **Defended**: Stolen `.db` file / stolen `.db` + `keystore.json` (no passphrase) / full disk image (app not running).
- **Not defended**: Process memory dump while running / compromised host with keylogger (see PRD §1 non-goals).

### Migration

```bash
# 1. Stop the service
# 2. Back up
cp data/cmdb.db data/cmdb.db.bak

# 3. Run one-time encryption migration
cd backend
PYTHONPATH=. python tools/encrypt_existing_db.py \
    --password '<new-admin-password>'

# 4. Save the recovery code printed to console (one-time!)
# 5. Restart → unlock via browser
```

The migration encrypts all tables (including views/indexes), verifies row counts, updates the admin password hash, and securely overwrites the plaintext original.

---

## V0.6 — Project Perspective & Consumption-Driven Billing

V0.6 introduces a **project perspective** alongside the existing asset view, upgrading Z-CMDB from "record resources" to "let configuration data be continuously consumed by operations scenarios." It adds deterministic cost apportionment, interactive topology visualization, and project-aware dashboards.

### Project Management (`/projects`)

- **Project list**: create, search, filter by business unit / owner / **department**, billing mode toggle per project, **delete with name confirmation**
- **Project architecture page**: interactive Vue Flow topology graph with deterministic template layout
  - Hosts arranged left-to-right by dependency topology order; units stacked vertically within each host group
  - Dependency edges (HTTP / SQL / cache / mq) with smoothstep arrows and type labels
  - Shared hosts highlighted in orange with per-project allocation percentages
  - Component cards with colored left bars by type (K8S / Docker / VM / Process)
  - "Manage Dependencies" dialog in the component table for declaring unit-to-unit relations
- **Project billing tab**: frozen bill snapshots per period, 7-column cost breakdown table, shared host allocation explanation with full arithmetic formulas and conservation checks

### Department Management (`/departments`)

- **Full CRUD**: create, edit, delete departments (super_admin only)
- **Project association**: projects can be linked to a department via dropdown selection (data sourced from the department registry)
- **Department filter**: project list supports filtering by department
- Reuses the existing `departments` table from V0.4 cost accounting module

### Project Cost Summary (`/projects/billing/departments`)

- Aggregates project billing costs grouped by department
- KPI cards: total cost, department count, total projects
- Pie chart showing cost distribution by department
- Summary table: department / project count / billing-enabled count / total cost

### Excel Asset Import

- **Template download**: standard .xlsx template with 19 columns (IP, MAC, hostname, OS, asset type, network zone, location, owner, business system, importance, CPU, memory, disk, purchase date, warranty expiry, port, protocol, service name, remark), headers include field descriptions
- **Upload & parse**: Excel files are parsed into the same `ParsedHost` structure as nmap scans, reusing the entire scan batch pipeline (diff computation → confirmation page → asset creation)
- **Row/column-level validation**: errors are collected with precise row number and column name (IP format, enum values, port range, numeric fields)
- **Confirmation page reuse**: Excel imports go through the same scan batch confirmation page, with data source marked as "Excel Import"; supplementary fields (CPU, memory, disk, etc.) are pre-populated from the Excel data
- **IP-based dedup**: existing assets matched by IP are flagged as duplicates; new assets are created with `source="excel"`
- **Remark preservation**: all three remark mapping scenarios (structured → corresponding field, free text → remark field, multi-line → merged text) are supported

### Deterministic Apportion Engine

- Pure function: host monthly cost × memory share = allocated amount per unit
- Supports `allocatable` or `sum_requests` denominator, `mem` / `cpu` / `weighted` / `max` weight modes
- Conservation assertion (tolerance 1e-6) — shares on every host sum to exactly 1.0
- Idle / unallocated costs go to a separate bucket (not forced onto projects)

### Data Model

- 6 new tables: `project`, `consuming_unit`, `placement`, `unit_relation`, `billing_policy`, `bill_snapshot`
- `host_resource` extended with `ip_address` column
- `project` extended with `department` column
- `scan_batches` extended with `source` column (`scan` / `excel`)
- `assets.source` CHECK constraint extended to include `excel`
- Bill snapshots are frozen after generation — changing the billing policy does not alter historical periods

### Dashboard Enhancements

- KPI row expanded with 5 project-dimension cards: Projects, Consuming Units, Attribution Coverage, Monthly Project Cost, Global Unallocated Bucket
- Asset distribution donut chart gains a 5th tab: "By Project"
- Project summary module aggregated from `bill_snapshot` data, served through the existing dashboard cache

### Removed

- **AI project summary**: removed the LLM-generated summary panel from the architecture page, the `/api/projects/{id}/summary` endpoints, and `engine/summary.py`. Topology is now fully deterministic.

### Migration

- New Alembic migrations: `a2b3c4d5e6f7` (v0.6 project tables), `b7c8d9e0f1a2` (summary cache columns — later removed), `c8d9e0f1a2b3` (host ip_address), `d1e2f3a4b5c6` (remove summary columns), `e2f3a4b5c6d7` (project department), `f1a2b3c4d5e6` (excel source support)
- **Version bumped to V0.6.0**

---

## V0.5.1 — Security Hardening & Bug Fixes

V0.5.1 is a security-focused patch that addresses findings from a full codebase audit. No new features; all changes improve security posture, robustness, and data integrity.

### Security Fixes

- **Initial admin password file auto-cleanup**: `INITIAL_ADMIN_PASSWORD.txt` is now automatically deleted after the admin changes their password; a startup warning is logged if the file still exists
- **Production JWT secret guard**: the app now refuses to start with the default `JWT_SECRET` when `APP_ENV=production`
- **Bulk update enum validation**: `PATCH /api/assets/bulk` now validates `status`, `importance`, and `network_zone` values against allowed enums
- **Upload filename sanitization**: nmap XML upload filenames are stripped of HTML/control characters to prevent stored XSS
- **Removed deprecated `X-XSS-Protection` header**
- **ClaudeProvider retry logic**: Claude API calls now retry 3 times with exponential backoff (matching OpenAIProvider behavior)
- **Frontend error messages i18n**: hardcoded Chinese error strings replaced with vue-i18n translation keys
- **`decrypt_value` error handling**: decryption failures now log a warning and return empty string instead of silently returning raw ciphertext
- **Config API masking**: non-super_admin users now see `****` for all API key fields (super_admin retains partial masking)
- **CORS startup warning**: logs a warning if `CORS_ORIGINS` contains `*` or HTTP origins in production

### Token Revocation (New)

- **`token_version` mechanism**: added to the `users` table — when a user changes their password or is disabled, all existing JWT tokens are immediately invalidated
- Backward compatible: tokens issued before this update (without `tv` claim) continue to work until the user changes their password

### Performance

- **IP address index** on `scan_snapshot_items` table for faster scan history queries
- **LLM log prompt truncation** reduced from 500 to 200 characters

### Bug Fixes

- **Asset list default sort**: changed from IP address to asset number (`asset_no`)
- **403 error display**: now shows the actual backend error message (e.g., "Feature not enabled") instead of a generic "Permission denied"
- **Cost feature toggle**: added error handling — if the toggle API fails, the user now sees an error message instead of a silent failure

### Migration

- New Alembic migration: `e9f0a1b2c3d4` (token_version), `f0a1b2c3d4e5` (ip index)
- **Version bumped to V0.5.1**

---

## V0.5 Highlights

V0.5 adds an **Import Preset** system to eliminate repetitive data entry during scan import, manual asset creation, and batch editing. It also improves the scan workflow with upload progress indicators and batch processing feedback.

### Import Presets (`/import-presets`)

- New settings page under "Scan Import" in the sidebar — two-column layout (category list + preset table)
- Three preset categories: Physical Location, Owner, Business System
- Full CRUD: add, edit, delete, search, sort order, remarks
- One default value per category (DB-enforced via partial unique index)
- **Sync from Assets**: one-click extract distinct values from existing assets into the preset library
- Presets are team-global, not per-user; deleting a preset does not affect existing asset values

### PresetSelect Component

- Reusable dropdown (`PresetSelect`) shared across three scenes: scan confirm, manual create, batch edit
- Filterable `el-select` with clearable selection
- **Inline add**: footer slot with input field — add a new preset value directly from any dropdown without leaving the page
- Default value auto-fill when creating new assets or importing scans

### Scan Confirm Page Improvements

- Location / Owner / Business System fields replaced with `PresetSelect` (was plain text input)
- **Batch Preset Toolbar**: field selector + value selector + scope (selected rows / all rows) + apply button — batch-set values across hundreds of rows in one click
- **Step loading indicator**: shows "Loading presets..." → "Computing diff..." with animated dots instead of blank spinner
- **Import overlay**: full-screen overlay with spinner during confirm submission, prevents double-click

### Asset Form & Asset List

- **Manual create/edit**: Location, Owner, Business System fields now use `PresetSelect` with default pre-fill
- **Batch edit**: asset list gets checkbox multi-select + batch edit dialog — select assets, choose field (owner / business system / location), pick preset value, apply

### Upload Progress Bar

- XML upload now shows a real progress bar with percentage (XHR `upload.onprogress`)
- After file transfer completes, switches to indeterminate pulse animation ("Processing scan data...")
- Axios timeout for scan APIs increased from 30s to 120s

### Other Changes

- Global scrollbar style updated to 10px solid (was 4px visible with transparent border trick)
- New database table: `import_preset` (category, value, is_default, sort_order, remark)
- New Alembic migration: `c7d8e9f0a1b2`
- New API endpoints: 7 endpoints under `/api/import-presets`
- `PATCH /api/assets/bulk` now supports `location` field
- Full i18n: all new UI strings bilingual (English + Chinese)
- **Version bumped to V0.5.0**

---

## V0.4 Highlights

V0.4 adds an **opt-in Asset Cost Accounting** module to Z-CMDB Lite, covering hardware depreciation, department billing, and cost governance. The feature is off by default — when disabled, the system behaves exactly as V0.3.

### Cost Overview (`/cost/overview`)

- 6 KPI cards (Monthly Total, Annualized, CapEx/OpEx Ratio, New Cost Assets, Missing Data)
- 4 charts: Department Ranking, Asset Type Distribution, Cloud vs On-Prem, Cost Trend
- Cost Governance list (Shadow Cost / Low Utilization / Depreciation Expiring / Missing Data)
- Period selector with recent 12 months, CSV export

| KPI Strip & Charts |
|--------------------|
| ![Cost KPI](img/v04-cost-kpi.png)  |

### Department Billing (`/cost/billing`)

- Two-column layout: searchable department list + billing content
- Period summary (Day/Month/Year/Custom) with 3 KPIs
- Resource detail table + Cost Type donut + Resource Ranking bar chart
- CSV export with full billing detail

| Summary  |
|---------|
| ![Billing Summary](img/v04-billing-summary.png)  |

### Asset Cost Panel (Asset Detail → Cost Breakdown tab)

- 3 KPI cards: Full-Loaded Monthly Cost, Net Value, Remaining Depreciation Months
- Cost distribution donut + detail list with progress bars
- Depreciation info section with progress bar
- Expiry warning banner with strategy selection

### Cost Rate Settings (`/cost/rates`)

- Depreciation table (6 asset types × years/residual/method/strategy)
- Power, bandwidth, datacenter parameters
- Resource Price Book with enable toggles
- Allocation drivers per asset type
- Currency selector (CNY/USD) — all displays switch automatically

### System Config — Feature Toggle

- Hero-style toggle card to enable/disable the entire cost module
- Super_admin only, confirmation dialog when disabling
- Quick-access links when enabled

### Other Changes

- **Asset list sorting**: all 10 columns support click-to-sort
- **Timezone-aware display**: timestamps switch between Asia/Shanghai and America/New_York by UI language
- **Currency-aware display**: amounts switch between ¥/CNY and $/USD by cost rate settings
- **GoatCounter analytics**: privacy-friendly page visit tracking
- **Version bumped to V0.4.0**

---

## V0.3 Highlights

V0.3 brings **full internationalization (i18n)** to Z-CMDB Lite, adding English/Chinese bilingual support across the entire frontend. The default language is now English, with one-click switching available from any page via the topbar toggle or System Config. The README documentation is also split into separate English and Chinese editions.

![Language Switching](img/i18n-preview.png)

### Bilingual UI

- **Complete English translation** of all 16 pages and 3 shared components — every button, label, tooltip, validation message, and chart title is localized
- **Topbar language toggle** (EN/中) for instant switching from any page without navigating to settings

| English | Chinese |
|---------|---------|
| ![Dashboard EN](img/i18n-dashboard-en.png) | ![Dashboard ZH](img/i18n-dashboard-zh.png) |
| ![Settings EN](img/i18n-settings-en.png) | ![Settings ZH](img/i18n-settings-zh.png) |

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

### V0.6 (2026-06-25)

> **Upgrade note**: After pulling V0.6, run `alembic upgrade head` in the `backend/` directory. This applies 6 migrations: project tables, host ip_address, summary columns (added then removed), project department, and Excel source support.

**Project Management**
- New `/projects` route with project list, per-project architecture page (Vue Flow topology), and billing tab
- 6 new database tables: `project`, `consuming_unit`, `placement`, `unit_relation`, `billing_policy`, `bill_snapshot`
- `host_resource` extended with `ip_address`
- **Project delete**: delete button with name-confirmation dialog (type exact project name to confirm)
- **Department field**: `project` table extended with `department` column; project list supports department filter; project create/edit uses department dropdown

**Department Management (`/departments`)**
- New admin page for full CRUD of departments (create / edit / delete)
- Reuses existing `departments` table from V0.4 cost module
- Sidebar entry under "System Admin" group

**Project Cost Summary (`/projects/billing/departments`)**
- New page aggregating project billing costs grouped by department
- KPI cards (total cost, department count, total projects) + pie chart + summary table
- API endpoint: `GET /api/projects/billing/department-summary?period=YYYY-MM`

**Excel Asset Import**
- Template download: `GET /api/scans/template/excel` — standard .xlsx with 19 columns, headers include field descriptions
- Upload endpoint: `POST /api/scans/upload-excel` — parses Excel into `ParsedHost`, reuses entire scan batch pipeline
- Row/column-level validation with precise error location (row number + column name)
- Confirmation page reuses scan batch confirmation; supplementary fields (CPU, memory, disk, etc.) pre-populated from Excel
- IP-based dedup: existing assets flagged as duplicates, new assets created with `source="excel"`
- `scan_batches` table extended with `source` column (`scan` / `excel`)
- `assets.source` CHECK constraint extended to include `'excel'`
- New dependency: `openpyxl>=3.1.0`

**Topology (Vue Flow)**
- Replaced HTML/CSS topology with Vue Flow interactive canvas
- Deterministic template layout: hosts sorted by dependency topology order, units stacked vertically per host
- Custom node components: `HostGroupNode` (shared host orange highlight), `UnitNode` (type-colored left bar)
- Dependency edges: smoothstep arrows with rel_type labels, cycle detection (dashed orange)
- "Manage Dependencies" dialog in component table (create / delete `unit_relation`)

**Billing**
- On-read freeze pattern: bill generated from apportion engine on first read, then frozen
- Enriched bill response: unit/host names, host monthly cost, memory ratio (absolute + percentage), host details, previous period comparison
- 7-column cost breakdown table, shared host allocation explanation module with conservation checks
- Root cause fix: populated `monthly_cost` / `cpu_total` / `mem_total` on all `host_resource` records

**Dashboard**
- 5 new project-dimension KPI cards (Projects, Consuming Units, Attribution Coverage, Monthly Project Cost, Global Unallocated)
- New `_build_project_summary()` aggregation in dashboard service (reads from `bill_snapshot`, same TTL cache)
- Asset distribution pie chart gains "By Project" tab (5th dimension)
- Unified KPI grid with separator, scrollable legend with text truncation

**Removed**
- AI project summary: deleted `engine/summary.py`, `/api/projects/{id}/summary` endpoints, `Project` model summary cache columns, related i18n keys and PRD sections

**Migrations**
- `a2b3c4d5e6f7` — v0.6 project tables
- `b7c8d9e0f1a2` — summary cache columns (added then removed in same release)
- `c8d9e0f1a2b3` — host ip_address
- `d1e2f3a4b5c6` — remove summary columns
- `e2f3a4b5c6d7` — project department column
- `f1a2b3c4d5e6` — Excel source support (scan_batches.source + assets CHECK)

### V0.5 (2026-06-23)

> **Upgrade note**: After pulling V0.5, run `alembic upgrade head` in the `backend/` directory to create the new `import_preset` table. Without this step the application will fail to start.

**Import Presets**
- New `/import-presets` settings page under "Scan Import" sidebar group, two-column layout (category list + preset table)
- Three preset categories: `location`, `owner`, `business_system` — full CRUD with search, sort order, remarks
- One default value per category enforced by partial unique index (`ix_preset_one_default`)
- "Sync from Assets" button: extracts distinct non-empty values from existing assets, deduplicates against existing presets
- New database table `import_preset` with Alembic migration `c7d8e9f0a1b2`
- 7 new API endpoints under `/api/import-presets` (list, categories, create, update, set-default, delete, sync-from-assets)
- All write operations logged to audit via `audit_service.log_from_request`

**PresetSelect Component**
- Reusable `el-select` component with `filterable` + `clearable` + footer slot for inline add
- Shared across scan confirm, manual asset create, and batch edit
- Backed by Pinia store (`useImportPresetStore`) with lazy-loading and per-category cache

**Scan Confirm Page**
- Location / Owner / Business System fields replaced with `PresetSelect` (was `el-input`)
- Default values auto-filled from preset library on page load
- Batch Preset Toolbar: field + value + scope (selected/all) + apply — pure frontend operation
- Step loading indicator: "Loading presets..." → "Computing diff..." with animated dots
- Full-screen import overlay during confirm submission (prevents double-click)

**Asset Form & Asset List**
- Asset create/edit form: Location, Owner, Business System replaced with `PresetSelect`, defaults pre-filled for new assets
- Asset list: new checkbox selection column + batch edit dialog with `PresetSelect`
- `PATCH /api/assets/bulk` extended to support `location` field

**Scan Upload Progress**
- Upload uses `XMLHttpRequest.upload.onprogress` for real percentage display (0–100%)
- After file transfer, switches to indeterminate pulse animation during server-side processing
- Axios timeout for scan upload/diff/confirm APIs increased from 30s to 120s

**Other**
- Global scrollbar width increased to 10px solid (was 4px effective with transparent border)
- All new UI strings fully bilingual (English + Chinese) via vue-i18n

### V0.4 (2026-06-21)

**Asset Cost Accounting (opt-in)**
- Added `feature_cost_accounting_enabled` feature flag in System Config (default OFF, super_admin only)
- Cost Overview dashboard (`/cost/overview`): 6 KPIs, 4 ECharts (dept ranking, type donut, cloud vs local, trend), governance list with tabs
- Department Billing (`/cost/billing`): searchable dept list, period selector (day/month/year), resource detail table, cost type donut + resource ranking bar, CSV export
- Asset Detail → Cost Breakdown tab: 3 KPIs (full-loaded monthly, net value, remaining months), cost distribution donut, depreciation progress bar, expiry warning
- Cost Rate Settings (`/cost/rates`): depreciation params per asset type, power/bandwidth/datacenter params, resource Price Book (vCPU/mem/storage/bandwidth/IP), allocation drivers, currency selector (CNY/USD)
- Asset Form → Section 04 cost fields (purchase price, depreciation months, residual rate, method, strategy, billing mode, responsible department)
- 5 new database tables: departments, asset_cost_items, asset_relations, asset_dept_assignments, cost_rates
- Asset table extended with 10 cost fields (purchase_price, depreciation_months, residual_rate, etc.)
- Pure computation engine: straight-line depreciation, revalue strategy, shared cost allocation (by driver/even split), conservation check
- All cost APIs guarded by centralized `require_cost_feature` dependency; feature off → 403

**Asset List Sorting**
- All 10 columns (asset_no, IP, hostname, type, zone, business system, OS, importance, status, owner) now support click-to-sort ascending/descending via Element Plus `sortable`

**Timezone & Currency**
- All timestamps switch timezone by UI language: zh → Asia/Shanghai (UTC+8), en → America/New_York
- Cost amounts switch currency symbol by rate settings: CNY → ¥, USD → $
- New `useTimeFormat` and `useCostCurrency` composables centralize all display logic

**i18n**
- Added `cost.ts` locale module (en + zh) with 200+ keys covering all cost pages, forms, charts, CSV exports
- Fixed `[intlify] Not found` warnings: array values use `tm()`, null-safe guards on all label functions
- Fixed `el-pagination` `small` prop deprecation → `size="small"`

**Analytics**
- Integrated GoatCounter page visit tracking (privacy-friendly, async)
- `allow_local: true` enables localhost/dev tracking
- Fallback script injection in Login.vue in case index.html script is removed

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
