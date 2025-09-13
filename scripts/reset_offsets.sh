set -euo pipefail

BROKER="${BROKER:-localhost:9092}"
GROUP_ID="${1:-}"
TOPIC="${2:-}"
SHIFT="${3:---to-earliest}"
DATETIME="${4:-}"

if [[ -z "$GROUP_ID" || -z "$TOPIC" ]]; then
  echo "Uso: $0 <group_id> <topic> [--to-earliest|--to-latest|--to-datetime 'YYYY-MM-DDTHH:MM:SSZ']"
  exit 1
fi

CMD=(kafka-consumer-groups.sh --bootstrap-server "$BROKER" --group "$GROUP_ID" --topic "$TOPIC" --reset-offsets --execute)

case "$SHIFT" in
  --to-earliest)  "${CMD[@]}" --to-earliest ;;
  --to-latest)    "${CMD[@]}" --to-latest ;;
  --to-datetime)
      if [[ -z "$DATETIME" ]]; then
        echo "Falta datetime ISO para --to-datetime"
        exit 1
      fi
      "${CMD[@]}" --to-datetime "$DATETIME"
      ;;
  *)
      echo "Opción inválida: $SHIFT"
      exit 1
      ;;
esac

echo "Offsets reseteados para group=$GROUP_ID topic=$TOPIC"
