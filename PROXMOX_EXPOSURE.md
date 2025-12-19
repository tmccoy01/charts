# Exposing Charts Server via Proxmox

This guide details how to expose your internal Docker-based Charts Server to outside networks using a Proxmox environment.

## Strategy Overview

Since Proxmox is a virtualization platform, "exposing" usually means routing traffic from the WAN or a separate network to the VM/Container running the charts service.

**Recommended Approach:** Reverse Proxy (Nginx/Traefik) or VPN (Tailscale/WireGuard).

## Option 1: Reverse Proxy (Public Exposure)

If you want the world (or a specific IP range) to access the maps without a VPN.

1.  **VM/CT Setup**: Ensure the VM running Docker has a static IP (e.g., `192.168.1.50`).
2.  **Reverse Proxy**: Set up a Reverse Proxy (like Nginx Proxy Manager or Traefik) in a separate LXC container on Proxmox.
    *   Point a domain (e.g., `maps.yourdomain.com`) to your home/static IP.
    *   Configure the Reverse Proxy to forward `maps.yourdomain.com` -> `192.168.1.50:8080`.
3.  **Security**:
    *   **Port Forwarding**: On your router, forward ports 80/443 to the Proxmox Reverse Proxy IP, NOT the Docker VM directly.
    *   **SSL**: Use Let's Encrypt in the Reverse Proxy to handle HTTPS. MapProxy sends KMLs with HTTP links by default, so you may need to configure `globals` in `mapproxy.yaml` to force HTTPS links if you go this route.

## Option 2: VPN (Private Exposure)

Safest method. Only authenticated devices can see the server.

1.  **Tailscale/WireGuard**: Install Tailscale on the Proxmox Host or a dedicated LXC container (acting as a subnet router) or directly on the Docker VM.
2.  **Access**: Any device on your Tailnet can access `http://192.168.1.50:8080` (or the MagicDNS name) as if they were on the LAN.
3.  **Google Earth**: Connect your iPad/Laptop to Tailscale, then add the Network Link in Google Earth.

## Google Earth Integration

MapProxy's KML service produces NetworkLinks.

1.  **Local Access**: Open Google Earth.
2.  **Add Network Link**:
    *   Name: `Charts`
    *   Link: `http://<SERVER_IP>:8080/kml/sec/0/0/0.kml` (This is the root KML for the Sectional charts).
    *   Fly To: Any US location to see the tiles load.

## SuperOverlays

The current configuration includes `kml` service. Ensure your `mapproxy.yaml` defines the layers correctly. The root KML will dynamically fetch tiles as you zoom (SuperOverlays).
