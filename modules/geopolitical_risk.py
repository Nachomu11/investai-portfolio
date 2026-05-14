import xml.etree.ElementTree as ET
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
REQUEST_TIMEOUT = 6
MAX_WORKERS = 8

# Palabras que suben el riesgo geopolítico
HIGH_RISK = [
    "war", "conflict", "sanctions", "crisis", "attack", "tension", "threat",
    "escalation", "military", "nuclear", "shutdown", "embargo", "ban",
    "recession", "default", "collapse", "protest", "coup", "missile",
    "terrorism", "shortage", "tariff", "inflation surge", "invasion",
    "strike", "blockade", "hostility", "unrest", "instability",
]
# Palabras que bajan el riesgo
LOW_RISK = [
    "peace", "agreement", "deal", "growth", "recovery", "stability",
    "cooperation", "accord", "ceasefire", "summit", "partnership",
    "trade deal", "investment", "expansion",
]

SECTOR_QUERIES = {
    "Tecnología":            "technology sanctions chip export ban AI regulation",
    "Energía":               "oil supply OPEC energy crisis natural gas",
    "Finanzas":              "banking crisis financial sanctions credit default",
    "Salud":                 "pandemic drug shortage healthcare reform",
    "Industria":             "supply chain disruption tariffs manufacturing",
    "Consumo discrecional":  "consumer recession inflation spending",
    "Materiales":            "mining sanctions rare earth commodity shortage",
    "Telecomunicaciones":    "telecom ban internet shutdown censorship",
    "Energías renovables":   "green energy climate policy renewable subsidy",
    "Defensa & Aeroespacial":"military conflict arms embargo defense spending",
    "Semiconductores":       "semiconductor chip ban export control TSMC",
    "Inmobiliario":          "real estate crash interest rates housing market",
    "Consumo básico":        "food supply inflation consumer goods shortage",
}

REGION_QUERIES = {
    "EE.UU.":        "United States trade war federal reserve economy risk",
    "Europa":        "European Union recession ECB Russia sanctions",
    "China":         "China Taiwan conflict trade ban export economy",
    "Rusia":         "Russia Ukraine war sanctions military conflict",
    "Oriente Medio": "Middle East Israel Iran oil war conflict",
    "Asia Emergente":"India Korea Southeast Asia instability export",
}

RISK_LEVEL_MAP = {
    0: ("Muy bajo",  "#2a7d4f"),
    1: ("Bajo",      "#3a9e6a"),
    2: ("Moderado",  "#b8966e"),
    3: ("Elevado",   "#b85c1a"),
    4: ("Alto",      "#8b2635"),
    5: ("Critico",   "#5a1a6e"),
}


def _fetch_google_news(query: str, max_items: int = 5) -> list[dict]:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    resp = requests.get(GOOGLE_NEWS_RSS, params=params, headers=headers,
                        timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = item.findtext("title", "").strip()
        # Google News wraps titles with source: "Headline - Source Name"
        title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
        link  = item.findtext("link", "").strip()
        pub   = item.findtext("pubDate", "")[:16] if item.findtext("pubDate") else ""
        if title:
            items.append({"title": title, "url": link, "date": pub})
    return items


def _score_from_headlines(headlines: list[dict]) -> float:
    if not headlines:
        return 2.0
    text = " ".join(h["title"].lower() for h in headlines)
    high = sum(1 for w in HIGH_RISK if w in text)
    low  = sum(1 for w in LOW_RISK  if w in text)
    # Base 1.0, sube con menciones de riesgo, baja con señales positivas
    score = 1.0 + high * 0.45 - low * 0.3
    return round(max(0.0, min(5.0, score)), 1)


def _build_result(name: str, headlines: list[dict], key: str = "sector") -> dict:
    risk_level = _score_from_headlines(headlines)
    label, color = RISK_LEVEL_MAP.get(min(int(risk_level), 5), ("Moderado", "#b8966e"))
    return {
        key:         name,
        "risk_level": risk_level,
        "risk_label": label,
        "color":      color,
        "headlines":  headlines[:4],
        "updated":    datetime.now().strftime("%H:%M"),
    }


def _fetch_and_score(name: str, query: str, key: str) -> dict:
    headlines = _fetch_google_news(query, max_items=5)
    return _build_result(name, headlines, key)


def get_portfolio_geopolitical_impact(portfolio_df, profile: dict) -> dict:
    sectors = []
    if hasattr(portfolio_df, "columns") and "sector" in portfolio_df.columns:
        sectors = portfolio_df["sector"].dropna().unique().tolist()[:5]

    if not sectors:
        return {
            "sector_risks":       {},
            "overall_risk_level": 2.0,
            "overall_risk_label": "Moderado",
            "overall_color":      "#b8966e",
            "recommendation":     "No se identificaron sectores en la cartera.",
        }

    sector_risks = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(
                _fetch_and_score,
                s,
                SECTOR_QUERIES.get(s, s + " geopolitical risk economy"),
                "sector",
            ): s
            for s in sectors
        }
        for fut in as_completed(futures, timeout=9):
            s = futures[fut]
            try:
                sector_risks[s] = fut.result()
            except Exception:
                sector_risks[s] = _build_result(s, [], "sector")

    for s in sectors:
        if s not in sector_risks:
            sector_risks[s] = _build_result(s, [], "sector")

    avg_risk = (
        sum(v["risk_level"] for v in sector_risks.values()) / len(sector_risks)
        if sector_risks else 2.0
    )
    label, color = RISK_LEVEL_MAP.get(min(int(avg_risk), 5), ("Moderado", "#b8966e"))

    return {
        "sector_risks":       sector_risks,
        "overall_risk_level": round(avg_risk, 1),
        "overall_risk_label": label,
        "overall_color":      color,
        "recommendation":     _risk_recommendation(avg_risk, profile),
    }


def get_global_risk_map() -> dict:
    region_risks = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(_fetch_and_score, r, q, "region"): r
            for r, q in REGION_QUERIES.items()
        }
        for fut in as_completed(futures, timeout=9):
            r = futures[fut]
            try:
                region_risks[r] = fut.result()
            except Exception:
                region_risks[r] = _build_result(r, [], "region")

    for r in REGION_QUERIES:
        if r not in region_risks:
            region_risks[r] = _build_result(r, [], "region")

    return region_risks


def _risk_recommendation(avg_risk: float, profile: dict) -> str:
    risk_score = profile.get("risk_score", 5)
    if avg_risk >= 4 and risk_score <= 4:
        return (
            "El riesgo geopolitico detectado es alto y tu perfil es conservador. "
            "Revisa la exposicion a los sectores mas afectados y considera reducir posiciones."
        )
    elif avg_risk >= 4:
        return (
            "El riesgo geopolitico es elevado. Mantén la posicion pero monitoriza "
            "los desarrollos. Considera cobertura si el horizonte es corto."
        )
    elif avg_risk >= 2.5:
        return (
            "Riesgo geopolitico moderado. Situacion bajo control pero con focos "
            "de incertidumbre activos. Revision mensual recomendada."
        )
    return (
        "Entorno geopolitico estable. Las condiciones son favorables "
        "para mantener la estrategia de inversion actual."
    )
