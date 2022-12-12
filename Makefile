.PHONY: deploy up down login-node login-ws login-events clean

deploy:
	@docker-compose -f docker/docker-compose.yml build --no-cache && \
	docker-compose -f docker/docker-compose.yml down && \
	docker-compose -f docker/docker-compose.yml up -d
up:
	@docker-compose -f docker/docker-compose.yml up -d
down:
	@docker-compose -f docker/docker-compose.yml down
login-node:
	@docker-compose -f docker/docker-compose.yml exec node /bin/bash
login-ws:
	@docker-compose -f docker/docker-compose.yml exec webserver /bin/bash
login-events:
	@docker-compose -f docker/docker-compose.yml exec events /bin/bash
clean:
	@docker-compose -f docker/docker-compose.yml down
	@docker rmi lamden
