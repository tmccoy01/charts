# WSGI module for use with Apache mod_wsgi or gunicorn
import os.path
from logging.config import fileConfig
from mapproxy.wsgiapp import make_wsgi_app

# Set path to config files relative to this script
crt_dir = os.path.dirname(os.path.abspath(__file__))
log_ini = os.path.join(crt_dir, 'log.ini')
yaml_config = os.path.join(crt_dir, 'mapproxy.yaml')

if os.path.exists(log_ini):
    fileConfig(log_ini, {'here': crt_dir})

application = make_wsgi_app(yaml_config)

