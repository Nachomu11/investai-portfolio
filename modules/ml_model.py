import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from modules.data_fetcher import (
    get_company_info, get_momentum, get_sector_etf_performance,
    build_universe, is_esg_low, get_sp500_tickers
)

# ETFs de índices conocidos — nunca son "candidatos a entrar en un índice"
INDEX_ETFS = {"SPY", "URTH", "EEM", "QQQ", "FEZ", "EXW1.DE", "IVV", "VOO",
              "VTI", "AGG", "BND", "XLK", "XLV", "XLF", "XLE", "XLY",
              "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC"}

SECTOR_TRANSLATION = {
    "Technology": "Tecnología",
    "Information Technology": "Tecnología",
    "Health Care": "Salud",
    "Healthcare": "Salud",
    "Financials": "Finanzas",
    "Financial Services": "Finanzas",
    "Energy": "Energía",
    "Consumer Discretionary": "Consumo discrecional",
    "Consumer Staples": "Consumo básico",
    "Industrials": "Industria",
    "Materials": "Materiales",
    "Utilities": "Servicios públicos",
    "Real Estate": "Inmobiliario",
    "Communication Services": "Telecomunicaciones",
    "Semiconductors": "Semiconductores",
}

INDEX_INCLUSION_RULES = {
    "sp500": {
        "min_market_cap_b": 18,
        "require_profitable": True,
        "min_liquidity_days": 252,
    },
    "msci_world": {
        "min_market_cap_b": 2,
        "require_profitable": False,
        "min_liquidity_days": 126,
    },
}


def score_company(info: dict, momentum: dict, sector_perf: dict, profile: dict) -> dict:
    score = 0.0
    reasons = []
    warnings = []

    market_cap_b = (info.get("market_cap") or 0) / 1e9

    if market_cap_b >= 100:
        score += 25
    elif market_cap_b >= 30:
        score += 20
    elif market_cap_b >= 10:
        score += 12
    elif market_cap_b >= 2:
        score += 5
    else:
        score -= 5

    rev_growth = info.get("revenue_growth") or 0
    earn_growth = info.get("earnings_growth") or 0
    if rev_growth > 0.30:
        score += 20
        reasons.append(f"crecimiento de ingresos excepcional ({rev_growth:.0%})")
    elif rev_growth > 0.15:
        score += 14
        reasons.append(f"sólido crecimiento de ingresos ({rev_growth:.0%})")
    elif rev_growth > 0.05:
        score += 8
    elif rev_growth < 0:
        score -= 8
        warnings.append(f"ingresos decrecientes ({rev_growth:.0%})")

    if earn_growth and earn_growth > 0.25:
        score += 15
        reasons.append(f"fuerte crecimiento de beneficios ({earn_growth:.0%})")
    elif earn_growth and earn_growth > 0.10:
        score += 8

    mom_12 = momentum.get("mom_12m") or 0
    mom_3 = momentum.get("mom_3m") or 0
    mom_1 = momentum.get("mom_1m") or 0
    if mom_12 > 30:
        score += 18
        reasons.append(f"momentum de 12 meses muy fuerte (+{mom_12:.1f}%)")
    elif mom_12 > 15:
        score += 12
        reasons.append(f"momentum de 12 meses positivo (+{mom_12:.1f}%)")
    elif mom_12 > 0:
        score += 5
    else:
        score -= 5
        warnings.append(f"momentum negativo a 12 meses ({mom_12:.1f}%)")

    if mom_3 > 10:
        score += 8
    elif mom_3 < -10:
        score -= 6

    profit_margin = info.get("profit_margin") or 0
    if profit_margin > 0.20:
        score += 12
        reasons.append(f"margen neto elevado ({profit_margin:.0%})")
    elif profit_margin > 0.10:
        score += 6
    elif profit_margin < 0:
        score -= 10
        warnings.append("empresa sin beneficios actuales")

    pe = info.get("pe_ratio") or 0
    fwd_pe = info.get("forward_pe") or 0
    if 0 < fwd_pe < 15:
        score += 10
        reasons.append("valoración atractiva (PER forward bajo)")
    elif 0 < fwd_pe < 25:
        score += 5
    elif fwd_pe > 60:
        score -= 5
        warnings.append("valoración elevada (PER forward alto)")

    sector_yf = info.get("sector", "")
    if sector_yf in sector_perf:
        sp = sector_perf[sector_yf]
        if sp > 10:
            score += 10
            reasons.append(f"sector en tendencia alcista (+{sp:.1f}%)")
        elif sp > 0:
            score += 4
        elif sp < -10:
            score -= 8
            warnings.append(f"sector bajo presión ({sp:.1f}%)")

    preferred_sectors = profile.get("preferred_sectors", [])
    if preferred_sectors:
        sector_es = SECTOR_TRANSLATION.get(sector_yf, sector_yf)
        if sector_es in preferred_sectors or sector_yf in preferred_sectors:
            score += 15
            reasons.append("coincide con tus sectores preferidos")

    beta = info.get("beta") or 1.0
    risk_score = profile.get("risk_score", 5)
    if risk_score <= 3 and beta > 1.5:
        score -= 12
        warnings.append(f"alta volatilidad (beta={beta:.1f}) para tu perfil conservador")
    elif risk_score >= 7 and beta > 1.5:
        score += 5

    div_yield = info.get("dividend_yield") or 0
    if risk_score <= 4 and div_yield > 0.02:
        score += 8
        reasons.append(f"dividendo estable ({div_yield:.1%})")

    horizon = profile.get("horizon_years", 2)
    if horizon >= 5 and mom_12 > 0 and rev_growth > 0.10:
        score += 5
        reasons.append("perfil adecuado para inversión a largo plazo")

    return {
        "score": round(score, 1),
        "reasons": reasons,
        "warnings": warnings,
        "momentum": momentum,
    }


def compute_index_inclusion_probability(info: dict, momentum: dict) -> dict:
    market_cap_b = (info.get("market_cap") or 0) / 1e9
    profitable = (info.get("profit_margin") or 0) > 0
    mom_12 = momentum.get("mom_12m") or 0

    sp500_prob = 0.0
    if market_cap_b >= 18 and profitable:
        sp500_prob = min(0.85, 0.30 + (market_cap_b / 200) * 0.30 + max(0, mom_12 / 100) * 0.25)
    elif market_cap_b >= 10:
        sp500_prob = 0.15
    elif market_cap_b >= 3:
        sp500_prob = 0.05

    msci_prob = 0.0
    if market_cap_b >= 2:
        msci_prob = min(0.90, 0.40 + (market_cap_b / 100) * 0.30 + max(0, mom_12 / 100) * 0.20)
    elif market_cap_b >= 0.5:
        msci_prob = 0.10

    return {
        "sp500_inclusion_prob": round(sp500_prob * 100, 1),
        "msci_inclusion_prob": round(msci_prob * 100, 1),
    }


def analyze_universe(profile: dict, progress_callback=None) -> pd.DataFrame:
    tickers = build_universe(profile)
    sector_perf = get_sector_etf_performance()

    # Cargamos la lista actual del S&P 500 una sola vez para marcar membresía
    sp500_members = set(get_sp500_tickers())

    records = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i / total, f"Analizando {ticker}...")

        info = get_company_info(ticker)
        mom = get_momentum(ticker)
        score_data = score_company(info, mom, sector_perf, profile)

        esg_flag = is_esg_low(ticker)
        if profile.get("esg") == "strict" and esg_flag:
            continue

        # Membresía actual en índices
        is_sp500_member = ticker.upper() in sp500_members
        is_etf = ticker.upper() in INDEX_ETFS

        # Solo calculamos probabilidad de ENTRADA para empresas que AÚN no están en el índice
        if is_sp500_member or is_etf:
            sp500_prob = None    # ya está dentro — no tiene sentido mostrar probabilidad
            msci_prob  = None
        else:
            inclusion  = compute_index_inclusion_probability(info, mom)
            sp500_prob = inclusion["sp500_inclusion_prob"]
            msci_prob  = inclusion["msci_inclusion_prob"]

        records.append({
            "ticker": ticker,
            "name": info.get("name", ticker),
            "sector_en": info.get("sector", "Unknown"),
            "sector": SECTOR_TRANSLATION.get(info.get("sector", ""), info.get("sector", "Unknown")),
            "country": info.get("country", "Unknown"),
            "market_cap_b": round((info.get("market_cap") or 0) / 1e9, 2),
            "revenue_growth": round((info.get("revenue_growth") or 0) * 100, 1),
            "profit_margin": round((info.get("profit_margin") or 0) * 100, 1),
            "beta": info.get("beta") or 1.0,
            "dividend_yield": round((info.get("dividend_yield") or 0) * 100, 2),
            "pe_ratio": info.get("pe_ratio"),
            "mom_1m": mom.get("mom_1m"),
            "mom_3m": mom.get("mom_3m"),
            "mom_6m": mom.get("mom_6m"),
            "mom_12m": mom.get("mom_12m"),
            "score": score_data["score"],
            "reasons": score_data["reasons"],
            "warnings": score_data["warnings"],
            "sp500_member": is_sp500_member,
            "sp500_inclusion_prob": sp500_prob,   # None si ya es miembro
            "msci_inclusion_prob": msci_prob,
            "esg_concern": esg_flag,
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    numeric_cols = ["score", "market_cap_b", "mom_12m", "revenue_growth", "profit_margin"]
    existing = [c for c in numeric_cols if c in df.columns]
    scaler = MinMaxScaler()
    df_norm = pd.DataFrame(scaler.fit_transform(df[existing].fillna(0)), columns=existing)

    weights = {"score": 0.50, "mom_12m": 0.20, "revenue_growth": 0.15, "profit_margin": 0.10, "market_cap_b": 0.05}
    df["composite_score"] = sum(df_norm[c] * w for c, w in weights.items() if c in df_norm.columns)
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)

    if progress_callback:
        progress_callback(1.0, "Análisis completado")

    return df
