#!/bin/sh

if [ -z "$@" ]; then
	python3 ./manage.py migrate

	python3 ./manage.py collectstatic --no-input

	exec gunicorn packagearchive.wsgi:application --bind 0.0.0.0:8000
fi

exec $@
