FROM debian:bullseye
COPY bin/ /root/bin/
COPY perl/ /root/perl/
RUN apt update && apt install -y --no-install-recommends \
    proj-bin \
    proj-data \
    gdal-bin \
    libgdal-perl \
    && rm -rf /var/lib/apt/lists \
    && rm -rf /var/cache/apt
VOLUME /charts