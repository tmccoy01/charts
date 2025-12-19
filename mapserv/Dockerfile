FROM debian:bullseye-slim

# Install MapServer and dependencies
RUN apt-get update && apt-get install -y \
    mapserver-bin \
    cgi-mapserver \
    gdal-bin \
    libmapscript-perl \
    libgdal-perl \
    proj-bin \
    proj-data \
    apache2 \
    && rm -rf /var/lib/apt/lists/*

# Enable CGI module in Apache
RUN a2enmod cgi

# Configure Apache to serve MapServer
RUN echo '\
    ScriptAlias /mapserv /usr/lib/cgi-bin/mapserv\n\
    <Directory "/usr/lib/cgi-bin">\n\
    AllowOverride None\n\
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch\n\
    Require all granted\n\
    </Directory>\n\
    ' > /etc/apache2/conf-available/mapserver.conf && \
    a2enconf mapserver

# Set up working directory
WORKDIR /home/mapserv

# Copy bin and perl scripts to locations expected by legacy scripts or standard paths
COPY bin/ /home/mapserv/bin/
COPY perl/ /home/mapserv/perl/
COPY mapfiles/ /home/mapserv/mapfiles/

# Ensure permissions
RUN chmod +x /home/mapserv/bin/*.pl

# Charts data volume
VOLUME /home/mapserv/charts

# Environment variables
ENV MS_MAPFILE=/home/mapserv/mapfiles/global.map

# Symlink executables if needed by scripts
RUN ln -s /home/mapserv/bin /root/bin

EXPOSE 80

# Start Apache in foreground
CMD ["apachectl", "-D", "FOREGROUND"]
