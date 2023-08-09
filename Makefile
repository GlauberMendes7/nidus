
# ------------------------------------------------------------------------------

.PHONY: format
format:
	.venv/bin/isort **/*.py
	.venv/bin/black **/*.py

# ------------------------------------------------------------------------------

.PHONY: test
test:
	.venv/bin/python -m unittest discover


# ------------------------------------------------------------------------------

.PHONY: init
init:
	@echo '>> dist'
	rm -rf .venv
	python3 -m venv .venv
	pip install -r requirements.txt

	
# ------------------------------------------------------------------------------

.PHONY: build
build:
	@echo '>> build'
	docker compose -f docker-compose.yml build

# ------------------------------------------------------------------------------

.PHONY: start
start:
	docker compose -f docker-compose.yml up -d

# ------------------------------------------------------------------------------

.PHONY: stop
stop:
	@echo '>> stop'
	docker compose -f docker-compose.yml down

# ------------------------------------------------------------------------------

.PHONY: clean
clean: stop
	@echo '>> clean'
	docker volume rm --force `docker volume ls --quiet --filter dangling=true` 2>/dev/null || true

# ------------------------------------------------------------------------------

.PHONY: prune
prune: clean
	@echo '>> prune'
	docker builder prune --force
	docker system prune --all --force

# ------------------------------------------------------------------------------

.PHONY: refresh
refresh: clean build start
	@echo '>> refresh'

# ------------------------------------------------------------------------------

.DEFAULT_GOAL := refresh

# ------------------------------------------------------------------------------
