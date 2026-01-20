# Changelog

## 2026-01-19 - Production Deployment Readiness

### Added

**Docker Compose Production Configuration**
- Added `restart: unless-stopped` policy to `mapproxy` and `mapserver` services
- Added resource limits and reservations:
  - MapProxy: 2 CPU / 2GB memory limit, 0.5 CPU / 512MB reservation
  - MapServer: 2 CPU / 4GB memory limit, 0.5 CPU / 1GB reservation
- Added volume mounts for persistent logs (`./logs/mapserv:/var/log/mapserv`)
- Added volume mounts for temp files (`./tmp/mapserv:/var/www/ms_tmp`)
- Made environment variables configurable with defaults (e.g., `${MAPPROXY_PROCESSES:-4}`)

**Environment Configuration**
- Added `WMS_BASE_URL` variable for configuring external service URL
- Added `BREF_DIR` variable for KML chart boundary generation
- Expanded `.env.example` with comprehensive documentation and deployment instructions

**Documentation**
- Added `docs/PROXMOX_VM_SETUP.md` - comprehensive step-by-step guide for deploying to Proxmox

### Fixed

**KML Charts Script (`mapserv/bin/kmlcharts.py`)**
- Replaced hardcoded macOS path with environment variable `BREF_DIR`
- Now defaults to container path `/home/mapserv/charts/bref`

---

## 2026-01-19 - Bug Fixes and Code Quality Improvements

### Fixed

**MapServer Configuration (12 files)**
- Fixed placeholder `wms_onlineresource` URLs in all map files
- Changed from `http://wms.example.com/...` to `http://localhost/cgi-bin/mapserv?map=/home/mapserv/mapfiles/<mapfile>.map`
- Affected files: `map1.map`, `map_sec.map`, `map_tac.map`, `map_hel.map`, `map_enrl.map`, `map_enrh.map`, `map_enra.map`, `map_4326.map`, `map_4326j.map`, `map_secj.map`, `map_grids.map`, `map_basegrid.map`

**Perl Build File (`mapserv/Makefile.pl`)**
- Removed invalid Module::Install methods: `ack_xxx`, `readme_from`, `version_check`
- These undefined methods would cause build failures

**Chart Processing (`mapserv/bin/makemap3.pl`)**
- Fixed cropper fallback path - `$thecropper2_path` now correctly points to `thecropper.pl` instead of duplicating `thecropperblah.pl`
- This ensures proper fallback behavior when primary cropper fails

**Orchestrator (`scripts/orchestrator.py`)**
- Fixed `run_command()` to return actual success/failure status based on return code
- Previously always returned `True` when `check=False`, masking failed commands
- Health checks and tile index updates now properly report failures

**Docker Configuration (`mapproxy/Dockerfile`)**
- Changed cache directory permissions from `777` (world-writable) to `755`
- Reduces security exposure in multi-user/multi-tenant scenarios

**Chart Downloader (`download_charts.py`)**
- Replaced `os.remove()` with `Path.unlink()` for consistency with pathlib usage
- Improved exception handling in `.aref` file generation
- Changed from bare `except Exception:` to specific exceptions (`IOError`, `OSError`, `ValueError`)
- Added warning messages when `.aref` generation fails

### Added

**Environment Configuration**
- Created `.env.example` as a template for environment configuration
- Documents all available environment variables with descriptions

### Notes

- The shell injection concern in `orchestrator.py` (using `shell=True`) was not addressed per user request, as this is a personal-use tool
