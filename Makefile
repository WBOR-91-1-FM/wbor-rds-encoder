IMAGE_NAME = wbor-rds-encoder-image
CONTAINER_NAME = wbor-rds-encoder
NETWORK_NAME = wbor-network
HOST_DIR = "/home/wbor/wbor-rds-encoder"

default: clean build run logsf

q: clean build run

exec:
	podman exec -it $(CONTAINER_NAME) /bin/bash

logsf:
	podman logs -f $(CONTAINER_NAME)

build:
	@echo "Building..."
	nice -n 10 podman build --quiet -t $(IMAGE_NAME) .

start: run

run: stop
	podman run -d --restart unless-stopped \
		--network $(NETWORK_NAME) \
		--name $(CONTAINER_NAME) \
		-v ${HOST_DIR}/logs:/app/logs \
		$(IMAGE_NAME)

stop:
	@echo "Checking if container $(CONTAINER_NAME) is running..."
	@if [ "$$(podman ps -a -q -f name=$(CONTAINER_NAME))" != "" ]; then \
		echo "Stopping $(CONTAINER_NAME)..."; \
		podman stop $(CONTAINER_NAME) > /dev/null; \
		echo "Removing the container $(CONTAINER_NAME)..."; \
		podman rm -f $(CONTAINER_NAME) > /dev/null; \
	else \
		echo "No running container with name $(CONTAINER_NAME) found."; \
	fi

clean: stop
	@IMAGE_ID=$$(podman images -q $(IMAGE_NAME)); \
	if [ "$$IMAGE_ID" ]; then \
		echo "Removing image $(IMAGE_NAME) with ID $$IMAGE_ID..."; \
		podman rmi $$IMAGE_ID > /dev/null; \
	else \
		echo "No image found with name $(IMAGE_NAME)."; \
	fi