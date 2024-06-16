#!/bin/sh

if [ -d /var/log/podfeed ]; then
    ACCESS_LOG_OPT="--access-logfile /var/log/podfeed/gunicorn_access.log"
else
    ACCESS_LOG_OPT=""
fi


cd /app
gunicorn --log-level=info $ACCESS_LOG_OPT -b 0.0.0.0:8152 server:app
