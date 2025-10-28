export type UploadedRow = { id: string; timestamp: string | number | Date; var: number };
export type PredRow = { ts: string | number | Date; value: number };
export type Aligned = { t: number; var?: number | null; prediction?: number | null };

// Devuelve epoch ms, corrigiendo formatos ambiguos
export function parseRawTimestamp(x: string | number | Date): number {
  if (x instanceof Date) return x.getTime();

  if (typeof x === "number") {
    // si parece seconds -> ms
    return x > 1e12 ? x : x * 1000;
  }

  const s = String(x).trim();

  // Caso solo hora: HH:MM o HH:MM:SS  → combínalo con HOY en UTC
  const hhmm = /^(\d{2}):(\d{2})(?::(\d{2}))?$/;
  const m1 = s.match(hhmm);
  if (m1) {
    const h = Number(m1[1]);
    const m = Number(m1[2]);
    const sec = m1[3] ? Number(m1[3]) : 0;
    const now = new Date();
    const t = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), h, m, sec);
    return t;
  }

  // Caso fecha sin zona: "YYYY-MM-DD HH:MM:SS" o "YYYY-MM-DDTHH:MM:SS"
  const ymd_hms = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})$/;
  const m2 = s.match(ymd_hms);
  if (m2) {
    // Trátalo como UTC explícito
    const iso = `${m2[1]}T${m2[2]}Z`;
    const d = new Date(iso);
    return d.getTime();
  }

  // ISO normal (con o sin Z): deja que el motor resuelva
  const d = new Date(s);
  return d.getTime();
}

export function toEpochMs(x: string | number | Date): number {
  return parseRawTimestamp(x);
}

export function alignSeries(uploaded: UploadedRow[], predicted: PredRow[]): Aligned[] {
  const m = new Map<number, Aligned>();

  for (const r of uploaded || []) {
    const t = parseRawTimestamp(r.timestamp);
    if (Number.isNaN(t)) continue;
    const row = m.get(t) ?? { t };
    row.var = typeof r.var === "number" ? r.var : null;
    m.set(t, row);
  }

  for (const p of predicted || []) {
    const t = parseRawTimestamp(p.ts);
    if (Number.isNaN(t)) continue;
    const row = m.get(t) ?? { t };
    row.prediction = typeof p.value === "number" ? p.value : null;
    m.set(t, row);
  }

  // Dedup y orden estable por tiempo
  return [...m.values()].sort((a, b) => a.t - b.t);
}
