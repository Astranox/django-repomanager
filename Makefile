all:
	git pull
	podman-compose build
#	podman-compose push
run:
	podman-compose down
	sleep 1
	podman-compose up -d
	podman logs -f django-repomanager_packagearchive_1
