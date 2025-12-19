# Running Charts Server with Docker

This project has been containerized using Docker and `uv`.

## Prerequisites

- Docker and Docker Compose
- 50GB+ Free Disk Space (for charts)
- `make` (optional, for automation)

## Quick Start

1.  **Build the Containers**

    ```bash
    docker-compose build
    ```

2.  **Start the Services**

    ```bash
    docker-compose up -d
    ```

3.  **Verify Setup**
    - MapProxy Demo: [http://localhost:8080/demo/](http://localhost:8080/demo/)
    - KML Endpoint: [http://localhost:8080/kml/sec/0/0/0.kml](http://localhost:8080/kml/sec/0/0/0.kml)

## Data Management

The `mapserv/charts` directory is mounted into the container. You need to populate this with aviation data.

### Downloading Charts
Use the provided scripts (adapt paths as needed) or manually download from FAA specific chart cycles:

-   Sectional Charts: `mapserv/charts/sec/`
-   TAC Charts: `mapserv/charts/tac/`
-   Helicopter Charts: `mapserv/charts/hel/`
-   IFR Enroute: `mapserv/charts/enrl/`, `mapserv/charts/enrh/`

### Generating Mapfiles
After ensuring data is present, you may need to run the Perl scripts inside the container to update indexes (if you are following the legacy process):

```bash
docker-compose exec mapserver /root/bin/makemap3.pl
```

*Note: You might need to adjust paths in `makemap3.pl` to match the container structure `/charts/charts`.*

## Configuration

-   **MapProxy**: `mapproxy/chart/mapproxy.yaml`
    - Use `http://mapserver/mapserv` as the backend URL for WMS sources.
-   **MapServer**: `mapserv/mapfiles/`
    - Ensure `.map` files point to the correct data paths (`/charts/charts/...`).
