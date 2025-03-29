# Default to Docker, allow override with DOCKER_TOOL=podman
DOCKER_TOOL ?= docker
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = wbor-rds-encoder
PROJECT_NAME = wbor-rds-encoder
COMPOSE_BAKE = true
export PODMAN_COMPOSE_SILENT = true

default: up logs

build:
	@echo "Building images..."
	COMPOSE_BAKE=$(COMPOSE_BAKE) $(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) build

up: down build
	@echo "Starting containers..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) up -d

down:
	@echo "Stopping and removing containers..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down

logs:
	@echo "Tailing logs for $(SERVICE_NAME)..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

restart: down up

watch:
	@echo "Watching for file changes and restarting containers..."
	while inotifywait -r -e modify,create,delete ./; do \
		$(MAKE) restart; \
	done