#! /bin/bash

GUNICORN_TIMEOUT=300  # request timeout
GUNICORN_WORKERS=3  # number of workers
GUNICORN_PORT=8000  # port to listen on
GUNICORN_LOGLEVEL=debug  # log level
GUNICORN_LOGFILE=/var/log/gms-pdf.log  # log file

source .venv/bin/activate
gunicorn --timeout=$GUNICORN_TIMEOUT --workers=$GUNICORN_WORKERS \
         --bind=0.0.0.0:$GUNICORN_PORT --log-level=$GUNICORN_LOGLEVEL \
         --log-file=$GUNICORN_LOGFILE app:app

