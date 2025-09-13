set -e
b=kafka:9092
topics=("telemetry.raw" "telemetry.agent.in" "telemetry.agent.out" "telemetry.processed")
for t in "${topics[@]}"; do
  docker exec kafka kafka-topics.sh --bootstrap-server $b --create --if-not-exists --topic $t --partitions 1 --replication-factor 1
done
docker exec kafka kafka-topics.sh --bootstrap-server $b --list
