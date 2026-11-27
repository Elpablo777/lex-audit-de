export function apiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8010";
  if (typeof window !== "undefined") {
    // Direkter Zugriff auf FastAPI (CORS konfiguriert) verhindert Next.js-Rewrite-ECONNRESET bei Keep-Alive-Timeouts
    const host = window.location.hostname;
    if (host === "127.0.0.1" || host === "localhost") {
      return `http://${host}:8010${path}`;
    }
    return path;
  }
  return `${base}${path}`;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

export const CONFLICT_CLASS_LABELS: Record<number, string> = {
  1: "1 · Vertikale Normkollision",
  2: "2 · Gleichheits-/Prinzipienbruch",
  3: "3 · Horizontaler Schnittstellenbruch",
  4: "4 · Legistischer Qualitätsmangel",
  5: "5 · Rechtsprechungs-Divergenz",
};

export const LEVER_LABELS: Record<string, string> = {
  ovg_normenkontrolle_47_vwgo: "OVG-Normenkontrolle (§ 47 VwGO / § 75 NJG)",
  fachgericht_vorlage_art100: "Fachgericht → Vorlage (Art. 100 GG / Art. 267 AEUV)",
  bundestag_epetition: "Bundestag ePetition (petition.bundestag.de)",
  landtag_petition: "Niedersächsischer Landtag Online-Petition",
  abgeordneten_briefing: "Abgeordneten- & Fraktions-Dossier",
  verfassungsbeschwerde_ultima_ratio: "Verfassungsbeschwerde (Ultima Ratio · 1,12 %)",
};
