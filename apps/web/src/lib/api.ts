export class ApiConnectionError extends Error {
  readonly isNetworkError = true;
  readonly targetUrl: string;

  constructor(targetUrl: string, causeMessage?: string) {
    super(
      `FastAPI-Backend unter ${targetUrl} ist nicht erreichbar${
        causeMessage ? ` (${causeMessage})` : ""
      }. Bitte mit "pnpm.cmd --dir apps/web start" (inkl. Auto-API) oder im zweiten Terminal mit "uv run uvicorn lexaudit_api.main:app --host 127.0.0.1 --port 8010" starten.`
    );
    this.name = "ApiConnectionError";
    this.targetUrl = targetUrl;
  }
}

export function apiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8010";
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    // Immer IPv4 127.0.0.1 verwenden, weil localhost unter Windows teils auf IPv6 ::1 auflöst
    if (host === "127.0.0.1" || host === "localhost" || host === "[::1]" || host === "::1") {
      return `http://127.0.0.1:8010${path}`;
    }
    return path;
  }
  return `${base}${path}`;
}

export function formatApiError(err: unknown): string {
  if (err instanceof ApiConnectionError) {
    return err.message;
  }
  if (err instanceof TypeError) {
    return new ApiConnectionError(apiUrl(""), err.message).message;
  }
  if (err instanceof Error) {
    if (err.message.toLowerCase().includes("failed to fetch")) {
      return new ApiConnectionError(apiUrl(""), err.message).message;
    }
    return err.message;
  }
  return "Unbekannter API-Fehler.";
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = apiUrl(path);
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : undefined;
    throw new ApiConnectionError(url, msg);
  }

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
