# Z-CMDB v0.6 Deployment Guide

> This document covers three deployment methods: Windows double-click launcher, Linux bare-metal, and Linux Docker.

---

## Important Warning

**The `./data` directory contains the SQLite database. NEVER place it on:**
- Network shares (NFS/SMB/CIFS)
- OneDrive / Dropbox / Google Drive or any sync directory
- Any remote filesystem that may cause WAL lock issues

SQLite WAL mode on these paths will cause lock errors or write loss. Always use local storage.

**Data backup**: Simply back up the `./data/cmdb.db` file (recommended while the service is stopped).

---

## 1. Windows Double-Click Launcher

### Prerequisites

- Windows 10/11 64-bit
- Dev machine: Python 3.12 (win_amd64) + pnpm + **internet access** (downloads embedded Python and dependencies)
- User machine: **No software installation required, no internet access needed**

### First Deployment (run on dev machine)

```cmd
cd z-cmdb
deploy\windows\build_bundle.bat
```

Output is in `dist\Z-CMDB\`, containing embedded Python + all dependencies + frontend + launcher (~160MB, build takes a few minutes).

> <b><font color="red">⚠️ build_bundle.bat will clear the entire dist\ directory! On first build this is fine, but for upgrades, back up dist\Z-CMDB\data\cmdb.db first, or use the "Incremental Update" method below.</font></b>

Copy the `dist\Z-CMDB\` folder to the target machine and double-click `start.bat`.

### Usage

1. Double-click `start.bat`
2. Browser opens automatically at `http://127.0.0.1:8000`
3. Log in with default account `admin` — initial password is in `data\INITIAL_ADMIN_PASSWORD.txt` (auto-generated on first start; deleted automatically after password change)

**Change port**: `start.bat 9000` (pass port as argument)

**Move folder**: The entire `Z-CMDB` folder is fully portable — data follows the folder.

### Upgrade (Recommended: Incremental Update)

When GitHub has a new version, only overwrite the code area — **keep embedded Python and dependencies untouched**:

> <b><font color="red">⚠️ Only overwrite app\, alembic\, static\, and alembic.ini. Do NOT touch data\ or .env — otherwise the database and secret key will be lost!</font></b>

```cmd
:: 1. Stop the service (close the start.bat window)

:: 2. Rebuild frontend on dev machine
cd z-cmdb
deploy\windows\build_bundle.bat

:: 3. Copy these folders from dist\Z-CMDB\ to the target machine (keep data\ and .env)
::    app\          ← backend code
::    alembic\      ← database migrations
::    static\       ← frontend build output
::    alembic.ini

:: 4. Double-click start.bat (runs new migrations automatically)
```

> **Note**: `start.bat` automatically runs `alembic upgrade head` on startup — no manual migration needed.

### Upgrade (Alternative: Full Rebuild)

If dependency versions changed, or you need a complete rebuild:

> <b><font color="red">⚠️ Full rebuild will delete the entire dist\ directory. You MUST back up data\cmdb.db first! Otherwise all asset data, user accounts, and audit logs will be permanently lost.</font></b>

```cmd
:: 1. Stop the service

:: 2. Back up data
copy dist\Z-CMDB\data\cmdb.db  C:\backup\cmdb.db

:: 3. Full rebuild
deploy\windows\build_bundle.bat

:: 4. Restore data
mkdir dist\Z-CMDB\data
copy C:\backup\cmdb.db  dist\Z-CMDB\data\cmdb.db

:: 5. Double-click start.bat
```

---

## 2. Linux Bare-Metal

### Prerequisites

- Python 3.12+
- Frontend already built (`cd frontend && pnpm build`), output copied to `backend/static/`

### Steps

```bash
cd z-cmdb/deploy/linux
chmod +x start.sh
./start.sh
```

The script automatically:
1. Creates `.venv` (first run only)
2. Installs dependencies (using Tsinghua mirror; override with `PIP_MIRROR` env var)
3. Generates `.env` (first run only, with random JWT_SECRET)
4. Runs database migrations
5. Starts uvicorn (listening on `0.0.0.0:8000`)

**Re-run**: Will not reinstall dependencies, overwrite `.env`, or lose data.

**First login**: Username `admin`, initial password in `data/INITIAL_ADMIN_PASSWORD.txt` (auto-generated on first start; deleted automatically after password change).

### systemd Service (optional)

```bash
# Create dedicated user
sudo useradd -r -s /sbin/nologin cmdb

# Deploy code
sudo cp -r z-cmdb /opt/z-cmdb
sudo chown -R cmdb:cmdb /opt/z-cmdb

# Install service
sudo cp deploy/linux/z-cmdb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now z-cmdb

# View logs
sudo journalctl -u z-cmdb -f
```

### Upgrade

```bash
sudo systemctl stop z-cmdb
sudo cp -r /opt/z-cmdb/backend/data /tmp/z-cmdb-backup  # backup
# Overwrite code (keep data/ and .env)
sudo systemctl start z-cmdb
```

---

## 3. Linux Docker

### Prerequisites

- Docker 20.10+
- Docker Compose v2
- Frontend already built (`cd frontend && pnpm build`)

### One-Click Deploy

```bash
cd z-cmdb/deploy/docker
export JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
./release.sh
```

The script automatically:
1. Builds base image `z-cmdb-base:0.6` (heavy deps, rebuild rarely)
2. Builds app image `z-cmdb-app:0.6` (COPY only, instant rebuild)
3. Creates `./data` directory
4. Starts the container

Access at `http://localhost:8000`.

**First login**: Username `admin`, initial password in host `./data/INITIAL_ADMIN_PASSWORD.txt` (auto-generated on first start; deleted automatically after password change).

### Offline Distribution

```bash
OFFLINE=1 ./release.sh
# Output: z-cmdb-base-0.6.tar.gz
# On target machine: docker load < z-cmdb-base-0.6.tar.gz
```

### Data Persistence

Database is bind-mounted to host `./data` directory:
```bash
docker compose down
docker compose up -d
# Data still in ./data/cmdb.db
```

### Upgrade

```bash
# Backup
cp data/cmdb.db data/cmdb.db.bak

# Rebuild (app layer only, instant)
docker compose up -d --build
```

---

## Configuration

All environments share these `.env` settings:

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Runtime environment | `production` |
| `DATABASE_URL` | Database connection | `sqlite:///./data/cmdb.db` |
| `JWT_SECRET` | JWT signing key (≥32 chars) | Auto-generated |
| `CORS_ORIGINS` | Allowed frontend origins | Auto-generated per deployment |
| `PORT` | Service port | `8000` |

**Production secret validation**: If `APP_ENV=production` and `JWT_SECRET` is default or <32 chars, the service refuses to start.

---

## FAQ

**Q: Forgot admin password?**
A: Delete `data/cmdb.db` (all data will be lost). Restart to generate a new `data/INITIAL_ADMIN_PASSWORD.txt`. Default account `admin`; the file is deleted automatically after password change.

**Q: Port already in use?**
A: Windows: `start.bat 9000`; Linux: `PORT=9000 ./start.sh`. Note: after first run, `CORS_ORIGINS` in `.env` is locked to the original port. To change the port, also delete `.env` to regenerate it.

**Q: Will data survive container restart?**
A: Yes. Database is bind-mounted to host `./data`. Container deletion does not affect data.

---

*Z-CMDB v0.6.0 | 2026-06-27*
