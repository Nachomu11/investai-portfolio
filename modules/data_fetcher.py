import os
import json
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(CACHE_DIR, exist_ok=True)

SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

MSCI_WORLD_ETF = "URTH"
MSCI_EM_ETF = "EEM"
NASDAQ100_ETF = "QQQ"
EUROSTOXX_ETF = "EXW1.DE"

CANDIDATE_LARGE_CAPS = [
    "PLTR", "CRWD", "SNOW", "DDOG", "MDB", "NET", "ZS", "HUBS",
    "SHOP", "MELI", "SE", "BIDU", "JD", "NIO", "XPEV",
    "ARM", "SMCI", "VST", "CEG", "WDAY",
    "UBER", "LYFT", "ABNB", "DASH",
    "RIVN", "LCID", "JOBY",
    "IONQ", "RGTI",
    "SAP", "ASML", "NVO", "NOVO-B.CO",
    "RDDT", "HOOD", "COIN", "RBLX",
]

IBEX35_TICKERS = [
    "SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC", "REP.MC",
    "TEF.MC", "AMS.MC", "CABK.MC", "BKT.MC", "SAB.MC",
    "ELE.MC", "ENG.MC", "FER.MC", "ACS.MC", "ANA.MC",
    "AENA.MC", "CLNX.MC", "GRF.MC", "IAG.MC", "IDR.MC",
    "LOG.MC", "MAP.MC", "MRL.MC", "NTGY.MC", "PHM.MC",
    "RED.MC", "SCYR.MC", "SOL.MC", "UNI.MC", "VIS.MC",
    "ACX.MC", "COL.MC", "FDR.MC", "MEL.MC", "ALM.MC",
]

NASDAQ100_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
    "NFLX", "AMD", "ADBE", "QCOM", "INTC", "CSCO", "AMAT", "TXN", "MU", "INTU",
    "ISRG", "BKNG", "LRCX", "REGN", "PANW", "VRTX", "ADI", "KLAC", "SNPS", "CDNS",
    "CRWD", "FTNT", "MRVL", "ADP", "DXCM", "ABNB", "BIIB", "IDXX", "GILD", "NXPI",
    "MNST", "ORLY", "PYPL", "WDAY", "DDOG", "TEAM", "ZS", "PCAR", "FAST", "ROST",
    "PAYX", "ODFL", "CTAS", "VRSK", "ANSS", "CPRT", "MRNA", "LULU", "CTSH", "GEHC",
    "ON", "WBD", "TTD", "ILMN", "SPLK", "SIRI", "FSLR", "CEG", "ARM", "SMCI",
]

EUROSTOXX50_TICKERS = [
    "ASML.AS", "MC.PA", "SAP.DE", "SIE.DE", "TTE.PA", "ENEL.MI",
    "BNP.PA", "AXA.PA", "SU.PA", "AIR.PA", "DTE.DE", "ALV.DE",
    "AI.PA", "OR.PA", "PHIA.AS", "IBE.MC", "SAN.MC", "RMS.PA",
    "MBG.DE", "MUV2.DE", "ING.AS", "BAYN.DE", "BAS.DE", "BMW.DE",
    "IFX.DE", "ADS.DE", "ENI.MI", "MRK.DE", "DB1.DE", "PRX.AS",
    "SGO.PA", "AD.AS", "ISP.MI", "SAFE.PA", "KER.PA", "VOW3.DE",
    "URW.AS", "CRH.I", "DBK.DE", "NOKIA.HE",
]

ESG_LOW_SCORE = {"XOM", "CVX", "COP", "MPC", "VLO", "PSX", "HAL", "SLB",
                 "BTI", "MO", "PM", "LMT", "RTX", "NOC", "GD", "BA",
                 "MP", "ALB"}


def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}.json")


def _load_cache(name: str, max_age_hours: int = 12) -> dict | None:
    path = _cache_path(name)
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    if time.time() - mtime > max_age_hours * 3600:
        return None
    with open(path) as f:
        return json.load(f)


def _save_cache(name: str, data: dict) -> None:
    with open(_cache_path(name), "w") as f:
        json.dump(data, f)


def get_sp500_tickers() -> list[str]:
    cached = _load_cache("sp500_tickers")
    if cached:
        return cached["tickers"]
    try:
        tables = pd.read_html(SP500_WIKI)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        _save_cache("sp500_tickers", {"tickers": tickers})
        return tickers
    except Exception:
        return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "V"]


def get_company_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "country": info.get("country", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", np.nan),
            "forward_pe": info.get("forwardPE", np.nan),
            "revenue_growth": info.get("revenueGrowth", np.nan),
            "earnings_growth": info.get("earningsGrowth", np.nan),
            "profit_margin": info.get("profitMargins", np.nan),
            "beta": info.get("beta", 1.0),
            "dividend_yield": info.get("dividendYield", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", np.nan),
            "52w_low": info.get("fiftyTwoWeekLow", np.nan),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", ""),
        }
    except Exception:
        return {"ticker": ticker, "name": ticker, "sector": "Unknown",
                "industry": "Unknown", "country": "Unknown", "market_cap": 0,
                "pe_ratio": np.nan, "forward_pe": np.nan, "revenue_growth": np.nan,
                "earnings_growth": np.nan, "profit_margin": np.nan, "beta": 1.0,
                "dividend_yield": 0, "currency": "USD", "exchange": "", "website": "", "summary": ""}


def get_price_history(ticker: str, years: float = 2) -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=int(years * 365))
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Close"]].rename(columns={"Close": ticker})
    except Exception:
        return pd.DataFrame()


def get_momentum(ticker: str) -> dict:
    df = get_price_history(ticker, years=1.1)
    if df.empty or len(df) < 20:
        return {"mom_1m": np.nan, "mom_3m": np.nan, "mom_6m": np.nan, "mom_12m": np.nan}
    col = df.columns[0]
    last = df[col].iloc[-1]
    def pct(days):
        if len(df) > days:
            return (last / df[col].iloc[-days] - 1) * 100
        return np.nan
    return {
        "mom_1m": pct(21),
        "mom_3m": pct(63),
        "mom_6m": pct(126),
        "mom_12m": pct(252),
    }


def get_sector_etf_performance() -> dict[str, float]:
    sector_etfs = {
        "Technology": "XLK",
        "Health Care": "XLV",
        "Financials": "XLF",
        "Energy": "XLE",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
    }
    perf = {}
    for sector, etf in sector_etfs.items():
        hist = get_price_history(etf, years=0.3)
        if not hist.empty and len(hist) > 5:
            col = hist.columns[0]
            ret = (hist[col].iloc[-1] / hist[col].iloc[0] - 1) * 100
            perf[sector] = round(ret, 2)
        else:
            perf[sector] = 0.0
    return perf


def get_index_etf_info() -> dict:
    etfs = {
        "S&P 500": "SPY",
        "MSCI World": "URTH",
        "MSCI Emerging Markets": "EEM",
        "NASDAQ 100": "QQQ",
        "Euro Stoxx 50": "FEZ",
    }
    result = {}
    for name, ticker in etfs.items():
        hist = get_price_history(ticker, years=2)
        info = get_company_info(ticker)
        if not hist.empty:
            col = hist.columns[0]
            ret_1y = (hist[col].iloc[-1] / hist[col].iloc[-min(252, len(hist))] - 1) * 100
            ret_ytd = (hist[col].iloc[-1] / hist[col].iloc[0] - 1) * 100
        else:
            ret_1y = ret_ytd = np.nan
        result[name] = {
            "ticker": ticker,
            "price": hist[hist.columns[0]].iloc[-1] if not hist.empty else np.nan,
            "return_1y": round(ret_1y, 2),
            "return_ytd": round(ret_ytd, 2),
            "beta": info.get("beta", 1.0),
            "expense_ratio": info.get("pe_ratio", np.nan),
            "history": hist,
        }
    return result


def build_universe(profile: dict, max_stocks: int = 80) -> list[str]:
    market_filter = profile.get("stock_market_filter", [])
    # Eliminar el sentinel "Cualquier mercado" para obtener los mercados activos
    active_markets = [m for m in market_filter if "Cualquier" not in m]

    if not active_markets:
        # Comportamiento por defecto: S&P 500 + candidatos globales
        sp500 = get_sp500_tickers()
        universe = list(set(sp500[:150] + CANDIDATE_LARGE_CAPS))
    else:
        universe_set = set()
        if any("S&P 500" in m for m in active_markets):
            universe_set.update(get_sp500_tickers())
        if any("IBEX" in m for m in active_markets):
            universe_set.update(IBEX35_TICKERS)
        if any("NASDAQ" in m for m in active_markets):
            universe_set.update(NASDAQ100_TICKERS)
        if any("Euro Stoxx" in m for m in active_markets):
            universe_set.update(EUROSTOXX50_TICKERS)
        universe = list(universe_set)

    # Siempre añadir empresas específicas seleccionadas por el usuario
    for s in profile.get("specific_stocks", []):
        if "(" in s:
            ticker = s.split("(")[1].rstrip(")")
            if ticker not in universe:
                universe.append(ticker)

    return universe[:max_stocks]


def is_esg_low(ticker: str) -> bool:
    return ticker.upper() in ESG_LOW_SCORE


def get_live_portfolio_performance(
    holdings: pd.DataFrame,
    created_at: str,
    total_invested: float,
) -> dict:
    """
    Descarga precios reales desde la fecha de creacion de la cartera hasta hoy
    y calcula el valor de la cartera dia a dia.
    Devuelve series temporales y metricas de rendimiento en vivo.
    """
    from datetime import datetime as dt

    try:
        start = dt.fromisoformat(created_at[:10])
    except Exception:
        start = dt.today() - timedelta(days=30)

    end = dt.today()
    days_since = (end - start).days

    tickers = [t for t in holdings["ticker"].tolist() if t and len(t) <= 8]
    weights  = holdings[holdings["ticker"].isin(tickers)].set_index("ticker")["weight"] / 100

    if not tickers or days_since < 1:
        return {"error": "La cartera fue creada hoy — vuelve manana para ver el rendimiento en vivo.", "days": days_since}

    try:
        raw = yf.download(tickers, start=start, end=end + timedelta(days=1),
                          progress=False, auto_adjust=True)
        if raw.empty:
            return {"error": "No se pudieron descargar precios para esta cartera."}

        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]] if "Close" in raw.columns else raw

        prices = prices.dropna(how="all")
    except Exception as e:
        return {"error": f"Error al descargar datos: {e}"}

    available = [t for t in tickers if t in prices.columns]
    if not available:
        return {"error": "No hay datos de precios para los tickers de esta cartera."}

    w = weights[available]
    w = w / w.sum()

    port_prices  = prices[available]
    port_returns = port_prices.pct_change().fillna(0).iloc[1:]

    port_daily_ret = (port_returns * w).sum(axis=1)
    port_cumret    = (1 + port_daily_ret).cumprod()
    port_value     = port_cumret * total_invested

    total_ret  = (port_cumret.iloc[-1] - 1) * 100 if not port_cumret.empty else 0
    current_val = port_value.iloc[-1] if not port_value.empty else total_invested
    profit      = current_val - total_invested

    best_day  = port_daily_ret.max() * 100
    worst_day = port_daily_ret.min() * 100
    pos_days  = (port_daily_ret > 0).sum()

    return {
        "port_value":    port_value,
        "port_cumret":   port_cumret,
        "port_daily_ret": port_daily_ret,
        "total_return_pct": round(total_ret, 2),
        "current_value":    round(current_val, 2),
        "profit":           round(profit, 2),
        "best_day_pct":     round(best_day, 2),
        "worst_day_pct":    round(worst_day, 2),
        "positive_days":    int(pos_days),
        "total_days":       len(port_daily_ret),
        "start_date":       start,
        "days_tracked":     days_since,
    }
