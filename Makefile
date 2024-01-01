network:
	docker network create --driver=bridge chat-net

build:
	docker compose build

up:
	docker compose up -d

build-up:
	docker compose up -d --build

restart:
	docker compose down && docker compose up -d

logs:
	docker logs -f chat-backend

down:
	docker compose down

test:
	docker exec -it chat-backend python -m pytest -svv $(target)

revision:
	docker exec -it chat-backend alembic revision --autogenerate -m "${m}"

upgrade:
	docker exec -it chat-backend alembic upgrade head

downgrade:
	docker exec -it chat-backend alembic downgrade -${last}

migration-history:
	docker exec -it chat-backend alembic history

web-bash:
	docker exec -it chat-backend bash

postgres-bash:
	docker exec -it chat-postgres bash

redis-cli:
	docker exec -it chat-redis redis-cli

show-envs:
	docker exec chat-backend env
