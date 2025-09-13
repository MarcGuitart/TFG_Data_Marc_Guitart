SHELL := /bin/bash
COMPOSE := docker compose
ORCH_URL := http://localhost:8080
COLLECTOR_URL := http://localhost:8082

.PHONY: up build down ps logs logs-% restart-% topics trigger flush tail-raw tail-in tail-out tail-proc kafka-sh reset

up:
	cd docker && $(COMPOSE) up -d --build

build:
	cd docker && $(COMPOSE) build

down:
	cd docker && $(COMPOSE) down -v

ps:
	cd docker && $(COMPOSE) ps

logs:
	cd docker && $(COMPOSE) logs -f --tail=200

logs-%:
	cd docker && $(COMPOSE) logs -f --tail=200 $*

restart-%:
	cd docker && $(COMPOSE) restart $*

topics:
	bash scripts/create_topics.sh

trigger:
	curl -s -X POST http://localhost:8080/trigger | jq .


flush:
	curl -s $(COLLECTOR_URL)/flush | jq .

tail-raw:
	docker exec -it kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic telemetry.raw --from-beginning
tail-in:
	docker exec -it kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic telemetry.agent.in --from-beginning
tail-out:
	docker exec -it kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic telemetry.agent.out --from-beginning
tail-proc:
	docker exec -it kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic telemetry.processed --from-beginning

kafka-sh:
	docker exec -it kafka bash

reset:
	@ if [ -z "$(GROUP)" ] || [ -z "$(TOPIC)" ]; then \
		echo "Uso: make reset GROUP=<group> TOPIC=<topic> MODE=earliest|latest|datetime [WHEN=...]"; exit 1; fi
	@ if [ "$(MODE)" = "earliest" ]; then \
		docker exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-earliest --execute; \
	elif [ "$(MODE)" = "latest" ]; then \
		docker exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-latest --execute; \
	elif [ "$(MODE)" = "datetime" ]; then \
		if [ -z "$(WHEN)" ]; then echo "Falta WHEN=YYYY-MM-DDTHH:MM:SSZ"; exit 1; fi; \
		docker exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-datetime $(WHEN) --execute; \
	else \
		echo "MODE inválido: $(MODE)"; exit 1; \
	fi
