# Install weekly updater (Proxmox VM)

Run this on the VM that hosts the stack.

## Option A: cron.weekly (simple)
```bash
sudo ln -sf "$(pwd)/scripts/weekly_update.sh" /etc/cron.weekly/charts-update
sudo chmod +x /etc/cron.weekly/charts-update
```

## Option B: crontab (explicit schedule)
Every Sunday at 03:15 local time:
```bash
sudo crontab -e
```
Add:
```cron
15 3 * * 0 /path/to/your/repo/scripts/weekly_update.sh >> /var/log/charts-update.log 2>&1
```
