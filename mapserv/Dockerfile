FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    mapserver-bin \
    cgi-mapserver \
    apache2 \
    libapache2-mod-wsgi-py3 \
    gdal-bin \
    libgdal-perl \
    libgdal-dev \
    proj-bin \
    proj-data \
    libproj-dev \
    perl \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/mapserv

COPY mapserv/mapserv.conf /etc/apache2/sites-available/charts.conf
RUN a2ensite charts.conf
RUN a2enmod cgi rewrite headers && a2dissite 000-default.conf
RUN chmod +x /home/mapserv/bin/*.pl || true

VOLUME /home/mapserv/charts
EXPOSE 80
CMD ["apachectl", "-D", "FOREGROUND"]
