import uuid
from typing import Dict, Any

TRACE_KEY = "trace_id"

def ensure_trace(event: Dict[str, Any]) -> Dict[str, Any]:
    """Añade trace_id si no existe; devuelve una copia con trace_id."""
    out = dict(event)
    if TRACE_KEY not in out or not out[TRACE_KEY]:
        out[TRACE_KEY] = str(uuid.uuid4())
    return out

def propagate_trace(parent_event: Dict[str, Any], child_event: Dict[str, Any]) -> Dict[str, Any]:
    """Copia el trace_id del evento padre al hijo (si existe)."""
    out = dict(child_event)
    if TRACE_KEY in parent_event:
        out[TRACE_KEY] = parent_event[TRACE_KEY]
    elif TRACE_KEY not in out:
        out[TRACE_KEY] = str(uuid.uuid4())
    return out
