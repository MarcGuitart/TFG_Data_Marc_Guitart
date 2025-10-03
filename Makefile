SHELL := /bin/bash
COMPOSE := docker compose
ORCH_URL := http://localhost:8081
COLLECTOR_URL := http://localhost:8082

.PHONY: up build down ps logs logs-% restart-% topics trigger flush \
        tail-raw tail-in tail-out tail-proc tail-agent kafka-sh reset \
        test_pipeline query-influx reset-agent

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
	curl -s -X POST $(ORCH_URL)/api/run_window | jq .

flush:
	curl -s $(COLLECTOR_URL)/flush | jq .

tail-raw:
	$(COMPOSE) exec kafka kafka-console-consumer.sh \
		--bootstrap-server kafka:9092 \
		--topic telemetry.raw --from-beginning

tail-in:
	docker compose exec -T kafka kafka-console-consumer.sh \
		--bootstrap-server kafka:9092 \
		--topic telemetry.agent.in --from-beginning


tail-out:
	$(COMPOSE) exec kafka kafka-console-consumer.sh \
		--bootstrap-server kafka:9092 \
		--topic telemetry.agent.out --from-beginning

tail-proc:
	$(COMPOSE) exec kafka kafka-console-consumer.sh \
		--bootstrap-server kafka:9092 \
		--topic telemetry.processed --from-beginning

tail-agent:
	cd docker && $(COMPOSE) logs -f --tail=200 agent

kafka-sh:
	$(COMPOSE) exec kafka bash

reset:
	@ if [ -z "$(GROUP)" ] || [ -z "$(TOPIC)" ]; then \
		echo "Uso: make reset GROUP=<group> TOPIC=<topic> MODE=earliest|latest|datetime [WHEN=...]"; exit 1; fi
	@ if [ "$(MODE)" = "earliest" ]; then \
		$(COMPOSE) exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-earliest --execute; \
	elif [ "$(MODE)" = "latest" ]; then \
		$(COMPOSE) exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-latest --execute; \
	elif [ "$(MODE)" = "datetime" ]; then \
		if [ -z "$(WHEN)" ]; then echo "Falta WHEN=YYYY-MM-DDTHH:MM:SSZ"; exit 1; fi; \
		$(COMPOSE) exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group $(GROUP) --topic $(TOPIC) --reset-offsets --to-datetime $(WHEN) --execute; \
	else \
		echo "MODE inválido: $(MODE)"; exit 1; \
	fi

# Helper para resetear offsets del agent rápido
reset-agent:
	$(COMPOSE) exec kafka kafka-consumer-groups.sh \
		--bootstrap-server kafka:9092 \
		--group agent-v1 \
		--topic telemetry.agent.in \
		--reset-offsets --to-earliest --execute

test_pipeline:
	curl -s -X POST $(ORCH_URL)/api/upload_csv -F "file=@data/test_csvs/test_small.csv"
	curl -s -X POST $(ORCH_URL)/api/run_window | jq
	curl -s $(COLLECTOR_URL)/flush | jq

query-influx:
	$(COMPOSE) exec influxdb influx query \
		--org tfg \
		--token admin_token \
		'from(bucket:"pipeline") |> range(start:-5m) |> limit(n:10)'
