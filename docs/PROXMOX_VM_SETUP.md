# FAA Charts VM Setup Guide for Proxmox

This guide walks through creating an Ubuntu VM on Proxmox to host the FAA Charts system for Google Earth.

---

## Prerequisites

- Proxmox VE installed and accessible
- Ubuntu Server 22.04 ISO uploaded to Proxmox storage
- Network access to your Proxmox host

---

## Part 1: Create the VM in Proxmox

### Step 1: Download Ubuntu ISO (if not already uploaded)

1. Log into Proxmox web UI (`https://<proxmox-ip>:8006`)
2. Select your storage (e.g., `local`) in the left panel
3. Click **ISO Images** tab
4. Click **Download from URL**
5. Enter: `https://releases.ubuntu.com/22.04/ubuntu-22.04.5-live-server-amd64.iso`
6. Click **Query URL** then **Download**

### Step 2: Create New VM

1. Click **Create VM** button (top right)

2. **General tab**:
   - Node: (your proxmox node)
   - VM ID: `110` (or next available)
   - Name: `charts`
   - Click **Next**

3. **OS tab**:
   - Use CD/DVD disc image file (iso)
   - Storage: `local`
   - ISO image: Select the Ubuntu 22.04 ISO
   - Guest OS Type: `Linux`
   - Version: `6.x - 2.6 Kernel`
   - Click **Next**

4. **System tab**:
   - Graphics card: `Default`
   - Machine: `q35`
   - BIOS: `OVMF (UEFI)`
   - Add EFI Disk: ✅ checked
   - EFI Storage: `local-lvm`
   - SCSI Controller: `VirtIO SCSI single`
   - Qemu Agent: ✅ checked
   - Click **Next**

5. **Disks tab**:
   - Bus/Device: `SCSI` / `0`
   - Storage: `local-lvm`
   - Disk size: `64` GB (adjust based on how many chart types you want)
   - Cache: `Write back`
   - Discard: ✅ checked
   - Click **Next**

6. **CPU tab**:
   - Sockets: `1`
   - Cores: `4`
   - Type: `host`
   - Click **Next**

7. **Memory tab**:
   - Memory: `8192` MB (8 GB)
   - Click **Next**

8. **Network tab**:
   - Bridge: `vmbr0`
   - Model: `VirtIO (paravirtualized)`
   - Firewall: ✅ checked (optional)
   - Click **Next**

9. **Confirm tab**:
   - Review settings
   - ✅ Start after created (optional)
   - Click **Finish**

---

## Part 2: Install Ubuntu Server

### Step 3: Start VM and Open Console

1. Select your new VM (`110 (charts)`) in the left panel
2. Click **Start** button
3. Click **Console** button to open the terminal

### Step 4: Ubuntu Installation

1. Select **Try or Install Ubuntu Server**
2. Choose your language (English)
3. Select **Continue without updating** (if prompted)
4. Keyboard: Select your layout, then **Done**
5. Installation type: **Ubuntu Server** (not minimized), **Done**

6. **Network configuration**:
   - Note the interface name (usually `ens18`)
   - Select the interface → **Edit IPv4**
   - Change from `Automatic (DHCP)` to `Manual`
   - Enter:
     ```
     Subnet: 192.168.1.0/24
     Address: 192.168.1.110
     Gateway: 192.168.1.1
     Name servers: 192.168.1.100
     ```
   - **Save** → **Done**

7. **Proxy**: Leave blank, **Done**

8. **Mirror**: Keep default, **Done**

9. **Storage**:
   - Use an entire disk: ✅
   - Set up this disk as an LVM group: ✅
   - **Done** → **Done** → **Continue**

10. **Profile setup**:
    ```
    Your name: Tanner
    Server name: charts
    Username: tanner
    Password: (your password)
    Confirm: (your password)
    ```
    **Done**

11. **Upgrade to Ubuntu Pro**: Skip for now → **Continue**

12. **SSH Setup**:
    - Install OpenSSH server: ✅
    - Import SSH identity: (optional - No)
    - **Done**

13. **Featured Server Snaps**: Don't select any, **Done**

14. Wait for installation to complete...

15. When done, select **Reboot Now**

16. If prompted about removing installation medium, just press **Enter**

---

## Part 3: Initial Ubuntu Configuration

### Step 5: First Login

1. Wait for the VM to boot (you'll see the login prompt)
2. Log in with your username and password

### Step 6: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 7: Install QEMU Guest Agent

```bash
sudo apt install -y qemu-guest-agent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent
```

### Step 8: Set Timezone

```bash
sudo timedatectl set-timezone America/New_York
```
(Replace with your timezone - use `timedatectl list-timezones` to see options)

### Step 9: Reboot

```bash
sudo reboot
```

---

## Part 4: Install Docker

### Step 10: Install Docker Engine

```bash
# Install prerequisites
sudo apt install -y ca-certificates curl gnupg

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Step 11: Add User to Docker Group

```bash
sudo usermod -aG docker $USER
```

### Step 12: Log Out and Back In

```bash
exit
```
Then log back in for the group change to take effect.

### Step 13: Verify Docker Works

```bash
docker run hello-world
```

You should see "Hello from Docker!" message.

---

## Part 5: Set Up the Charts Project

### Step 14: Install Git

```bash
sudo apt install -y git
```

### Step 15: Clone the Repository

```bash
cd ~
git clone https://github.com/chartbundle/charts.git
cd charts
```

(Or use your own repo URL)

### Step 16: Create Environment File

```bash
cp .env.example .env
nano .env
```

Update the `WMS_BASE_URL` line to use your VM's IP:
```
WMS_BASE_URL=http://192.168.1.110:8080
```

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

### Step 17: Create Required Directories

```bash
mkdir -p logs/mapserv tmp/mapserv
```

### Step 18: Build and Start Services

```bash
docker compose build
docker compose up -d
```

This will take a few minutes on first run.

### Step 19: Check Services Are Running

```bash
docker compose ps
```

You should see both `mapproxy` and `mapserver` with status `Up (healthy)`.

### Step 20: Download Chart Data

```bash
docker compose run --rm updater
```

This downloads sectional charts from the FAA (~2-3 GB). Takes a while.

---

## Part 6: Add DNS Entry in Pi-hole (Optional)

### Step 21: Create Local DNS Record

1. Open Pi-hole admin: `http://192.168.1.100/admin`
2. Go to **Local DNS** → **DNS Records**
3. Add:
   - Domain: `charts.local`
   - IP Address: `192.168.1.110`
4. Click **Add**

Now you can access the service at `http://charts.local:8080`

---

## Part 7: Connect Google Earth

### Step 22: Add WMS to Google Earth Pro

1. Open **Google Earth Pro**
2. Go to **Add** → **Image Overlay** (or press `Ctrl+Shift+O`)
3. In the dialog:
   - Name: `FAA Sectional Charts`
   - Click **Refresh** tab
   - Click **WMS Parameters** button
4. In WMS Parameters:
   - Service URL: `http://192.168.1.110:8080/service?`
   - Click **Get Layers**
   - Select `sec` (Sectional Charts)
   - Click **Add Selected Layer(s)**
5. Click **OK** twice

### Alternative: Add KML Network Link

1. Go to **Add** → **Network Link**
2. Enter:
   - Name: `FAA Sectionals`
   - Link: `http://192.168.1.110:8080/kml/sec/0/0/0.kml`
3. Click **OK**

---

## Part 8: Set Up Automatic Updates (Optional)

### Step 23: Create Weekly Update Cron Job

```bash
crontab -e
```

Add this line (runs every Sunday at 3 AM):
```
0 3 * * 0 cd /home/tanner/charts && docker compose run --rm updater >> /home/tanner/charts/logs/update.log 2>&1
```

Save and exit.

---

## Verification Checklist

- [ ] VM boots and has IP `192.168.1.110`
- [ ] Can SSH to VM: `ssh tanner@192.168.1.110`
- [ ] Docker is running: `docker ps`
- [ ] Services are healthy: `docker compose ps`
- [ ] Web UI accessible: `http://192.168.1.110:8080/demo/`
- [ ] WMS works: `http://192.168.1.110:8080/service?SERVICE=WMS&REQUEST=GetCapabilities`
- [ ] Google Earth shows charts

---

## Troubleshooting

### Services won't start
```bash
docker compose logs -f
```

### Check disk space
```bash
df -h
```

### Restart services
```bash
docker compose restart
```

### Rebuild after changes
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### View MapServer logs
```bash
cat logs/mapserv/mapserv.log
```

---

## Resource Usage Notes

| Resource | Expected Usage |
|----------|---------------|
| Disk | ~10-15 GB for sectionals only, ~50+ GB for all chart types |
| RAM | ~2-4 GB under normal load |
| CPU | Low idle, spikes during tile generation |

---

## Quick Reference

| Service | URL |
|---------|-----|
| Demo/Test Page | `http://192.168.1.110:8080/demo/` |
| WMS Capabilities | `http://192.168.1.110:8080/service?SERVICE=WMS&REQUEST=GetCapabilities` |
| KML (for Google Earth) | `http://192.168.1.110:8080/kml/sec/0/0/0.kml` |
| TMS Tiles | `http://192.168.1.110:8080/tms/1.0.0/sec/` |
