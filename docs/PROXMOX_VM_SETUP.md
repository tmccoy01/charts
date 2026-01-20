# FAA Charts VM Setup Guide for Proxmox

> **Target Configuration**
> - Ubuntu Server 24.04 LTS
> - Static IP: `192.168.1.110`
> - Docker with FAA Charts system
> - Accessible from Google Earth

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Proxmox VE | Installed and accessible via web UI |
| Ubuntu ISO | `ubuntu-24.04.2-live-server-amd64.iso` uploaded to Proxmox storage |
| Network | Access to your `192.168.1.0/24` network |

---

# Part 1: Create the VM in Proxmox

## Step 1: Upload Ubuntu ISO

*Skip if you already have the ISO uploaded to Proxmox.*

1. Log into Proxmox web UI at `https://<proxmox-ip>:8006`
2. Select your storage (e.g., `local`) in the left panel
3. Click **ISO Images** tab
4. Click **Upload** and select `ubuntu-24.04.2-live-server-amd64.iso`

> **Alternative**: Click **Download from URL** and enter:
> ```
> https://releases.ubuntu.com/24.04/ubuntu-24.04.2-live-server-amd64.iso
> ```

---

## Step 2: Create New VM

Click **Create VM** (top right corner) and configure each tab:

### General

| Setting | Value |
|---------|-------|
| Node | *(your proxmox node)* |
| VM ID | `110` |
| Name | `charts` |

### OS

| Setting | Value |
|---------|-------|
| Use CD/DVD | Yes |
| Storage | `local` |
| ISO image | `ubuntu-24.04.2-live-server-amd64.iso` |
| Guest OS Type | `Linux` |
| Version | `6.x - 2.6 Kernel` |

### System

| Setting | Value |
|---------|-------|
| Machine | `q35` |
| BIOS | `OVMF (UEFI)` |
| Add EFI Disk | Yes |
| EFI Storage | `local-lvm` |
| SCSI Controller | `VirtIO SCSI single` |
| Qemu Agent | Yes |

### Disks

| Setting | Value |
|---------|-------|
| Bus/Device | `SCSI / 0` |
| Storage | `local-lvm` |
| Disk size | `64 GB` |
| Cache | `Write back` |
| Discard | Yes |

> **Note**: 64 GB is sufficient for sectional charts only. Increase to 100+ GB if you plan to download all chart types.

### CPU

| Setting | Value |
|---------|-------|
| Sockets | `1` |
| Cores | `4` |
| Type | `host` |

### Memory

| Setting | Value |
|---------|-------|
| Memory | `2048 MB` (2 GB) |

> **Note**: 2GB is minimal. The system will work but may be slow during tile generation. Consider adding swap space after install (see Part 3).

### Network

| Setting | Value |
|---------|-------|
| Bridge | `vmbr0` |
| Model | `VirtIO (paravirtualized)` |

### Confirm

Review settings and click **Finish**.

---

# Part 2: Install Ubuntu Server

## Step 3: Start VM and Open Console

1. Select VM `110 (charts)` in the left panel
2. Click **Start**
3. Click **Console** to open the terminal

---

## Step 4: Ubuntu Installation Wizard

### Language & Keyboard

- Select **Try or Install Ubuntu Server**
- Choose **English**
- Select **Continue without updating** if prompted
- Select your keyboard layout

### Installation Type

- Select **Ubuntu Server** (not minimized)

### Network Configuration

> **Important**: Configure a static IP to ensure consistent access.

1. Select your network interface (usually `ens18`)
2. Select **Edit IPv4**
3. Change from `Automatic (DHCP)` to **Manual**
4. Enter the following:

| Setting | Value |
|---------|-------|
| Subnet | `192.168.1.0/24` |
| Address | `192.168.1.110` |
| Gateway | `192.168.1.1` |
| Name servers | `192.168.1.100` |

5. Select **Save**, then **Done**

### Remaining Screens

| Screen | Action |
|--------|--------|
| Proxy | Leave blank, select **Done** |
| Mirror | Keep default, select **Done** |
| Storage | Use entire disk with LVM, select **Done** twice, then **Continue** |

### Profile Setup

| Field | Value |
|-------|-------|
| Your name | `Tanner` |
| Server name | `charts` |
| Username | `tanner` |
| Password | *(your secure password)* |

### Additional Options

| Screen | Action |
|--------|--------|
| Ubuntu Pro | Select **Skip for now**, then **Continue** |
| SSH Setup | Check **Install OpenSSH server**, then **Done** |
| Featured Snaps | Don't select any, select **Done** |

### Complete Installation

- Wait for installation to finish
- Select **Reboot Now**
- Press **Enter** if prompted about installation medium

---

# Part 3: Initial Ubuntu Configuration

## Step 5: First Login

Log in with your username and password at the console prompt.

---

## Step 6: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 7: Install QEMU Guest Agent

```bash
sudo apt install -y qemu-guest-agent
sudo systemctl start qemu-guest-agent
```

| Package | Purpose |
|---------|---------|
| `qemu-guest-agent` | Enables Proxmox to communicate with the VM - allows proper shutdown commands, displays IP in Proxmox UI, enables filesystem freeze for consistent backups |

> **Note**: The `enable` step isn't needed - the agent auto-starts when it detects a QEMU/KVM environment.

---

## Step 8: Set Timezone

```bash
sudo timedatectl set-timezone America/New_York
```

> **Tip**: Run `timedatectl list-timezones` to see all available options.

---

## Step 9: Add Swap Space

With only 2GB RAM, add swap to prevent out-of-memory issues:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify swap is active:

```bash
free -h
```

---

## Step 10: Reboot

```bash
sudo reboot
```

---

# Part 4: Install Docker

## Step 11: Install Docker Prerequisites

Run the following commands in sequence:

```bash
# Install prerequisites
sudo apt install -y ca-certificates curl gnupg
```

| Package | Purpose |
|---------|---------|
| `ca-certificates` | Root certificates to verify HTTPS connections (needed to download Docker GPG key and packages) |
| `curl` | Command-line tool to download files from URLs |
| `gnupg` | GPG encryption tools to verify package signatures |

```bash
# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

```bash
# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

| Package | Purpose |
|---------|---------|
| `docker-ce` | Docker Community Edition - the main container runtime engine |
| `docker-ce-cli` | Command-line interface (`docker` command) to interact with the engine |
| `containerd.io` | Industry-standard container runtime that Docker uses under the hood |
| `docker-buildx-plugin` | Extended build capabilities (multi-platform builds, better caching) |
| `docker-compose-plugin` | Enables `docker compose` command for multi-container applications |

---

## Step 12: Add User to Docker Group

```bash
sudo usermod -aG docker $USER
```

---

## Step 13: Apply Group Change

Log out and back in:

```bash
exit
```

Then reconnect via SSH or console.

---

## Step 14: Verify Docker

```bash
docker run hello-world
```

> **Expected Output**: "Hello from Docker!" message confirming installation.

---

# Part 5: Deploy the Charts Application

## Step 15: Install Git

*Part 5 begins here - you're now ready to deploy the application.*

```bash
sudo apt install -y git
```

| Package | Purpose |
|---------|---------|
| `git` | Version control system - needed to clone the charts repository from GitHub |

---

## Step 16: Clone Repository

```bash
cd ~
git clone https://github.com/chartbundle/charts.git
cd charts
```

---

## Step 17: Configure Environment

```bash
cp .env.example .env
nano .env
```

Find the `WMS_BASE_URL` line and update it:

```ini
# Change this line:
WMS_BASE_URL=http://localhost:8080

# To this:
WMS_BASE_URL=http://192.168.1.110:8080
```

Save and exit: Press `Ctrl+X`, then `Y`, then `Enter`

---

## Step 18: Create Required Directories

```bash
mkdir -p logs/mapserv tmp/mapserv
```

---

## Step 19: Build and Start Services

```bash
docker compose build
```

> **Note**: First build takes several minutes. Subsequent builds are faster.

```bash
docker compose up -d
```

---

## Step 20: Verify Services

```bash
docker compose ps
```

**Expected output:**

```
NAME        SERVICE     STATUS
charts-mapproxy-1   mapproxy    Up (healthy)
charts-mapserver-1  mapserver   Up (healthy)
```

> **Troubleshooting**: If status shows "starting" or "unhealthy", wait a minute and check again. View logs with `docker compose logs -f`

---

## Step 21: Download Chart Data

```bash
docker compose run --rm updater
```

| Chart Type | Approximate Size | Download Time |
|------------|------------------|---------------|
| Sectionals only | ~2-3 GB | 10-20 minutes |
| All chart types | ~15-20 GB | 1-2 hours |

---

# Part 6: Pi-hole DNS Entry

*Optional but recommended for easier access.*

## Step 22: Add Local DNS Record

1. Open Pi-hole admin panel: `http://192.168.1.100/admin`
2. Navigate to **Local DNS** > **DNS Records**
3. Add new record:

| Field | Value |
|-------|-------|
| Domain | `charts.local` |
| IP Address | `192.168.1.110` |

4. Click **Add**

You can now access the service at `http://charts.local:8080`

---

# Part 7: Google Earth Configuration

## Step 23: Option A - Add as WMS Layer

1. Open **Google Earth Pro**
2. Navigate to **Add** > **Image Overlay** (or `Ctrl+Shift+O`)
3. Enter a name: `FAA Sectional Charts`
4. Click the **Refresh** tab
5. Click **WMS Parameters**
6. Configure:

| Field | Value |
|-------|-------|
| Service URL | `http://192.168.1.110:8080/service?` |

7. Click **Get Layers**
8. Select `sec` (Sectional Charts)
9. Click **Add Selected Layer(s)**
10. Click **OK** twice

---

## Step 23: Option B - Add as KML Network Link

1. Open **Google Earth Pro**
2. Navigate to **Add** > **Network Link**
3. Configure:

| Field | Value |
|-------|-------|
| Name | `FAA Sectionals` |
| Link | `http://192.168.1.110:8080/kml/sec/0/0/0.kml` |

4. Click **OK**

---

# Part 8: Automatic Updates

## Step 24: Configure Weekly Cron Job

```bash
crontab -e
```

Select your preferred editor (nano is easiest), then add this line:

```cron
0 3 * * 0 cd /home/tanner/charts && docker compose run --rm updater >> /home/tanner/charts/logs/update.log 2>&1
```

> **Schedule**: Runs every Sunday at 3:00 AM

Save and exit.

---

# Verification Checklist

| Check | Command / Action | Expected Result |
|-------|------------------|-----------------|
| VM has correct IP | `ip addr show` | Shows `192.168.1.110` |
| SSH works | `ssh tanner@192.168.1.110` | Connects successfully |
| Docker running | `docker ps` | Shows running containers |
| Services healthy | `docker compose ps` | Both show `Up (healthy)` |
| Web UI accessible | Browser: `http://192.168.1.110:8080/demo/` | Shows MapProxy demo page |
| WMS works | Browser: `http://192.168.1.110:8080/service?SERVICE=WMS&REQUEST=GetCapabilities` | Returns XML |
| Google Earth | Add WMS or KML | Charts visible on map |

---

# Troubleshooting

## Services Won't Start

```bash
# View real-time logs
docker compose logs -f

# Check specific service
docker compose logs mapserver
docker compose logs mapproxy
```

## Disk Space Issues

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean unused Docker resources
docker system prune -a
```

## Restart Services

```bash
docker compose restart
```

## Full Rebuild

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Check MapServer Logs

```bash
cat logs/mapserv/mapserv.log
```

---

# Quick Reference

## Service URLs

| Service | URL |
|---------|-----|
| Demo Page | `http://192.168.1.110:8080/demo/` |
| WMS GetCapabilities | `http://192.168.1.110:8080/service?SERVICE=WMS&REQUEST=GetCapabilities` |
| KML for Google Earth | `http://192.168.1.110:8080/kml/sec/0/0/0.kml` |
| TMS Tiles | `http://192.168.1.110:8080/tms/1.0.0/sec/` |

## Common Commands

| Task | Command |
|------|---------|
| Start services | `docker compose up -d` |
| Stop services | `docker compose down` |
| View logs | `docker compose logs -f` |
| Restart | `docker compose restart` |
| Update charts | `docker compose run --rm updater` |
| Check status | `docker compose ps` |

## Resource Expectations

| Resource | Typical Usage |
|----------|---------------|
| Disk | 10-15 GB (sectionals only), 50+ GB (all charts) |
| RAM | 1-2 GB under normal load (with 2GB swap) |
| CPU | Low idle, spikes during tile generation |
