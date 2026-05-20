import numpy as np
import pandas as pd
from scipy.optimize import minimize
from modules.data_fetcher import get_price_history, get_index_etf_info


def compute_dca_projection(
    initial_capital: float,
    monthly_contribution: float,
    annual_return: float,
    years: float,
) -> dict:
    """
    Proyección con aportaciones mensuales (DCA).
    Devuelve tanto el escenario sin aportaciones como con ellas,
    más una serie mensual para graficar.
    """
    months = int(years * 12)
    r_monthly = (1 + annual_return) ** (1 / 12) - 1

    # Serie mes a mes
    values_with = []
    values_without = []
    capital_invested = []
    capital = initial_capital

    for m in range(months + 1):
        # Sin aportaciones
        val_without = initial_capital * (1 + r_monthly) ** m
        # Con aportaciones: capital inicial compuesto + renta fija de aportaciones
        if r_monthly > 0:
            val_with = (
                initial_capital * (1 + r_monthly) ** m
                + monthly_contribution * ((1 + r_monthly) ** m - 1) / r_monthly
            )
        else:
            val_with = initial_capital + monthly_contribution * m
        total_invested = initial_capital + monthly_contribution * m

        values_with.append(val_with)
        values_without.append(val_without)
        capital_invested.append(total_invested)

    final_with = values_with[-1]
    final_without = values_without[-1]
    total_contributed = initial_capital + monthly_contribution * months

    return {
        "months": list(range(months + 1)),
        "values_with": values_with,
        "values_without": values_without,
        "capital_invested": capital_invested,
        "final_with_contributions": round(final_with, 2),
        "final_without_contributions": round(final_without, 2),
        "total_contributed": round(total_contributed, 2),
        "gain_with": round(final_with - total_contributed, 2),
        "gain_without": round(final_without - initial_capital, 2),
        "gain_pct_with": round((final_with / total_contributed - 1) * 100, 2),
        "gain_pct_without": round((final_without / initial_capital - 1) * 100, 2),
        "extra_gain": round(final_with - final_without, 2),
    }

INDEX_TICKERS = {
    "S&P 500 (EE.UU., grandes empresas)": "SPY",
    "MSCI World (global, mercados desarrollados)": "URTH",
    "MSCI Emerging Markets (mercados emergentes)": "EEM",
    "NASDAQ 100 (tecnología EE.UU.)": "QQQ",
    "Euro Stoxx 50 (Europa)": "FEZ",
    "IBEX 35 (España)": "EWP",
}

EXPECTED_RETURN_MAP = {
    "SPY": 0.105, "URTH": 0.095, "EEM": 0.11,
    "QQQ": 0.13, "FEZ": 0.09, "EWP": 0.085,
}


def _portfolio_stats(weights: np.ndarray, returns: pd.DataFrame) -> tuple[float, float, float]:
    port_return = np.dot(weights, returns.mean()) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = port_return / port_vol if port_vol > 0 else 0
    return port_return, port_vol, sharpe


def _optimize_weights(returns: pd.DataFrame, risk_score: int, min_w: float = 0.02, max_w: float = 0.35) -> np.ndarray:
    n = len(returns.columns)
    init_w = np.array([1 / n] * n)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(min_w, max_w)] * n

    def neg_sharpe(w):
        _, _, s = _portfolio_stats(w, returns)
        return -s

    def min_volatility(w):
        _, v, _ = _portfolio_stats(w, returns)
        return v

    objective = neg_sharpe if risk_score >= 6 else min_volatility
    result = minimize(objective, init_w, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"maxiter": 500, "ftol": 1e-9})
    if result.success:
        return result.x
    return init_w


# ── Modelo de retornos por régimen de mercado ─────────────────────────────────
#
# Los tres escenarios NO son base ± spread arbitrario.
# Se basan en regímenes históricos reales del mercado de renta variable:
#
#   PESIMISTA — año de mercado bajista (bear market):
#     Referencia histórica: S&P 500 2022 (-19%), 2008 (-37%), 2000-02 (-45%).
#     Carteras diversificadas pierden entre un 8% y un 35% según el perfil.
#     El escenario pesimista SIEMPRE es negativo para perfiles agresivos
#     y ligeramente negativo o cero para perfiles conservadores.
#
#   BASE — año de mercado normal (histórico largo plazo):
#     S&P 500: ~10% nominal anual desde 1928.
#     Bonos Investment Grade: ~4-5%.
#     Cartera mixta 60/40: ~7-8%.
#
#   OPTIMISTA — año de mercado alcista fuerte:
#     Referencia: S&P 500 2019 (+31%), 2023 (+26%), 2021 (+27%).
#     Acciones individuales growth pueden superar ese rango.
#
# El beta del activo amplifica AMBOS extremos de forma asimétrica
# (las pérdidas en bear markets se amplifican más que las ganancias en bull).
#
# El scoring ML selecciona qué empresas entran en cartera.
# Estas tablas calibran cuánto puede ganar o perder esa cartera.

# (bear_annual, base_annual, bull_annual) según perfil de riesgo
_REGIME_BY_RISK = {
    # Conservador: bonos + blue chips estables
    "conservative": (-0.05,  0.055, 0.10),
    # Moderado: cartera diversificada 60/40 o similar
    "moderate":     (-0.13,  0.082, 0.17),
    # Agresivo: renta variable pura, alta concentración en growth
    "aggressive":   (-0.24,  0.105, 0.28),
}

_DEFAULT_BASE = 0.09


def _realistic_return(
    mom_12: float, rev_growth: float, beta: float, risk_score: int
) -> tuple[float, float, float]:
    """
    Devuelve (base, pesimista, optimista) de rentabilidad anual.

    - Los tres escenarios parten de regímenes históricos de mercado reales.
    - Beta amplifica asimétricamente: más en bear (-) que en bull (+).
    - Calidad fundamental (crecimiento de ingresos) ajusta ligeramente el base.
    - Momentum pasado: señal muy débil (±1.5 pp máx.), no predictor directo.
    """
    if risk_score <= 3:
        bear, base, bull = _REGIME_BY_RISK["conservative"]
    elif risk_score <= 6:
        bear, base, bull = _REGIME_BY_RISK["moderate"]
    else:
        bear, base, bull = _REGIME_BY_RISK["aggressive"]

    # Beta: ajuste asimétrico. Beta alto amplifica pérdidas en bear más que ganancias en bull.
    b = max(0.3, min(float(beta or 1.0), 2.8))
    beta_excess = b - 1.0
    bear = bear + beta_excess * (-0.08)   # beta=2 → bear empeora ~8 pp más
    bull = bull + beta_excess * 0.05      # beta=2 → bull mejora ~5 pp más
    base = base + beta_excess * 0.01

    # Calidad fundamental: ajuste pequeño sobre el base
    rev = (rev_growth or 0) / 100
    if rev > 0.25:
        base += 0.015
    elif rev > 0.10:
        base += 0.007
    elif rev < -0.05:
        base -= 0.010

    # Momentum pasado: señal muy débil sobre el base (no sobre los extremos)
    mom_signal = np.clip(((mom_12 or 0) / 100) * 0.04, -0.015, 0.015)
    base += mom_signal

    # Límites absolutos por perfil (no recortar el pesimista en positivo)
    if risk_score <= 3:
        bear = np.clip(bear, -0.15, -0.01)   # conservador siempre pierde algo en bear
        base = np.clip(base,  0.02,  0.09)
        bull = np.clip(bull,  0.07,  0.13)
    elif risk_score <= 6:
        bear = np.clip(bear, -0.28, -0.04)
        base = np.clip(base,  0.04,  0.13)
        bull = np.clip(bull,  0.12,  0.22)
    else:
        bear = np.clip(bear, -0.45, -0.08)   # agresivo: pérdidas severas en bear
        base = np.clip(base,  0.06,  0.18)
        bull = np.clip(bull,  0.18,  0.40)

    return round(base, 4), round(bear, 4), round(bull, 4)


def _portfolio_scenarios(portfolio_df: pd.DataFrame, amount: float, horizon: float) -> dict:
    """
    Calcula los tres escenarios a nivel de cartera.
    La rentabilidad anual por posicion ya viene de _realistic_return (regímenes de mercado).
    Aqui simplemente se compone por el horizonte real del inversor.
    """
    # En horizontes largos, el escenario pesimista anual se suaviza por reversión
    # a la media: mercados en caída sostenida más de 2-3 años son históricamante raros.
    # Referencia: peor período 3 años S&P500 ≈ -14%/año; peor 5 años ≈ -7%/año;
    # peor 7 años ≈ -1%/año (siempre ha recuperado en plazos > 7 años).
    def _bear_horizon_adj(ann_bear: float) -> float:
        if horizon <= 1:
            return ann_bear                          # año único: el bear completo
        elif horizon <= 2:
            return ann_bear * 0.65                   # mezcla de un año malo y uno neutro
        elif horizon <= 3:
            return ann_bear * 0.45                   # referencia: 2000-2002
        elif horizon <= 5:
            return ann_bear * 0.28                   # referencia: peor quinquenio
        else:
            return max(ann_bear * 0.12, -0.03)       # >7 años: históricamente casi siempre positivo

    def _total_gain(col_ann: str) -> float:
        total = 0.0
        is_bear = col_ann == "expected_return_annual_min"
        for _, row in portfolio_df.iterrows():
            w = row["weight"] / 100
            ann_raw = row.get(col_ann, row["expected_return_annual"]) / 100
            ann = _bear_horizon_adj(ann_raw) if is_bear else ann_raw
            total += amount * w * ((1 + ann) ** horizon - 1)
        return round(total, 2)

    def _ann_avg(col: str) -> float:
        vals = portfolio_df[col] if col in portfolio_df.columns else portfolio_df["expected_return_annual"]
        weights = portfolio_df["weight"] / 100
        return round((vals * weights).sum(), 2)

    gain_base = _total_gain("expected_return_annual")
    gain_min  = _total_gain("expected_return_annual_min")
    gain_max  = _total_gain("expected_return_annual_max")

    # Descripciones contextuales segun horizonte
    if horizon <= 1:
        bear_desc = "Año de caída de mercado (ej. 2022, 2008). En el corto plazo el riesgo de pérdida es elevado y no hay tiempo de recuperación."
        base_desc = "Año de mercado en linea con la media historica. No garantiza rentabilidad positiva en periodos cortos."
        bull_desc = "Año de mercado alcista fuerte (ej. 2023, 2019). Requiere condiciones macro favorables."
    elif horizon <= 3:
        bear_desc = "Periodo con uno o mas años bajistas. Probabilidad relevante a 1-3 años según ciclos historicos."
        base_desc = "Rentabilidad media historica compuesta para el horizonte seleccionado."
        bull_desc = "Periodo con mercado predominantemente alcista y factores macro favorables."
    else:
        bear_desc = "Periodo que incluye una recesion o crisis de mercado. A largo plazo el mercado tiende a recuperarse."
        base_desc = "Rentabilidad media historica compuesta a largo plazo. La diversificacion reduce el riesgo con el tiempo."
        bull_desc = "Periodo de expansion economica sostenida con multiples años alcistas consecutivos."

    return {
        "pessimistic": {
            "label": "Escenario pesimista",
            "gain": gain_min,
            "gain_pct": round(gain_min / amount * 100, 2),
            "final_value": round(amount + gain_min, 2),
            "annual_avg": _ann_avg("expected_return_annual_min"),
            "description": bear_desc,
        },
        "base": {
            "label": "Escenario base",
            "gain": gain_base,
            "gain_pct": round(gain_base / amount * 100, 2),
            "final_value": round(amount + gain_base, 2),
            "annual_avg": _ann_avg("expected_return_annual"),
            "description": base_desc,
        },
        "optimistic": {
            "label": "Escenario optimista",
            "gain": gain_max,
            "gain_pct": round(gain_max / amount * 100, 2),
            "final_value": round(amount + gain_max, 2),
            "annual_avg": _ann_avg("expected_return_annual_max"),
            "description": "Viento de cola sectorial, mercado alcista y buen comportamiento relativo de la cartera.",
        },
    }


def build_stock_portfolio(df_scored: pd.DataFrame, profile: dict) -> dict:
    risk = profile.get("risk_score", 5)
    horizon = profile.get("horizon_years", 2)
    amount = profile.get("amount", 10000)

    if risk <= 3:
        n_stocks = 8
        max_w = 0.20
    elif risk <= 6:
        n_stocks = 12
        max_w = 0.25
    else:
        n_stocks = 15
        max_w = 0.35

    preferred_sectors = profile.get("preferred_sectors", [])
    specific = []
    for s in profile.get("specific_stocks", []):
        if "(" in s:
            specific.append(s.split("(")[1].rstrip(")"))

    # ETFs de índice conocidos — excluirlos del universo de empresas individuales
    INDEX_ETF_TICKERS = {"SPY","URTH","EEM","QQQ","FEZ","IVV","VOO","VTI",
                         "AGG","BND","XLK","XLV","XLF","XLE","XLY","XLP",
                         "XLI","XLB","XLU","XLRE","XLC","EXW1.DE"}
    df = df_scored[~df_scored["ticker"].str.upper().isin(INDEX_ETF_TICKERS)].copy()

    if preferred_sectors:
        preferred_mask = df["sector"].isin(preferred_sectors)
        n_preferred = min(int(n_stocks * 0.6), preferred_mask.sum())
        n_other = n_stocks - n_preferred
        top_preferred = df[preferred_mask].head(n_preferred)
        top_other = df[~preferred_mask].head(n_other)
        candidates = pd.concat([top_preferred, top_other]).drop_duplicates("ticker")
    else:
        candidates = df.head(n_stocks)

    for s in specific:
        if s not in candidates["ticker"].values and s in df["ticker"].values:
            row = df[df["ticker"] == s]
            candidates = pd.concat([candidates, row]).drop_duplicates("ticker")

    candidates = candidates.head(n_stocks + len(specific))
    tickers = candidates["ticker"].tolist()

    price_data = {}
    for t in tickers:
        hist = get_price_history(t, years=2)
        if not hist.empty:
            price_data[t] = hist[hist.columns[0]]

    if len(price_data) < 2:
        weights_arr = np.array([1 / len(tickers)] * len(tickers))
        valid_tickers = tickers
    else:
        prices_df = pd.DataFrame(price_data).dropna(thresh=int(len(price_data) * 0.7))
        prices_df = prices_df.ffill()
        valid_tickers = prices_df.columns.tolist()
        returns_df = prices_df.pct_change().dropna()
        if len(returns_df) < 30 or len(valid_tickers) < 2:
            weights_arr = np.array([1 / len(valid_tickers)] * len(valid_tickers))
        else:
            weights_arr = _optimize_weights(returns_df, risk)

    weights_arr = weights_arr / weights_arr.sum()

    result_rows = []
    for t, w in zip(valid_tickers, weights_arr):
        row = candidates[candidates["ticker"] == t]
        if row.empty:
            continue
        r = row.iloc[0]
        invested = amount * w
        mom_12 = r.get("mom_12m", 0) or 0
        rev_g = r.get("revenue_growth", 0) or 0
        beta = r.get("beta", 1.0) or 1.0
        base_ret, ret_min, ret_max = _realistic_return(mom_12, rev_g, beta, risk)

        expected_horizon      = invested * ((1 + base_ret) ** horizon - 1)
        expected_horizon_min  = invested * ((1 + ret_min)  ** horizon - 1)
        expected_horizon_max  = invested * ((1 + ret_max)  ** horizon - 1)

        reasons = r.get("reasons", [])
        warnings = r.get("warnings", [])
        result_rows.append({
            "ticker": t,
            "name": r.get("name", t),
            "sector": r.get("sector", ""),
            "country": r.get("country", ""),
            "weight": round(w * 100, 2),
            "invested_eur": round(invested, 2),
            "expected_return_annual": round(base_ret * 100, 1),
            "expected_return_annual_min": round(ret_min * 100, 1),
            "expected_return_annual_max": round(ret_max * 100, 1),
            "expected_gain_horizon": round(expected_horizon, 2),
            "expected_gain_horizon_min": round(expected_horizon_min, 2),
            "expected_gain_horizon_max": round(expected_horizon_max, 2),
            "score": r.get("score", 0),
            "sp500_inclusion_prob": r.get("sp500_inclusion_prob", 0),
            "msci_inclusion_prob": r.get("msci_inclusion_prob", 0),
            "beta": beta,
            "dividend_yield": r.get("dividend_yield", 0),
            "esg_concern": r.get("esg_concern", False),
            "reasons": reasons,
            "warnings": warnings,
            "mom_12m": mom_12,
            "revenue_growth": rev_g,
        })

    portfolio_df = pd.DataFrame(result_rows).sort_values("weight", ascending=False)
    port_beta = (portfolio_df["weight"] * portfolio_df["beta"]).sum() / 100

    scenarios = _portfolio_scenarios(portfolio_df, amount, horizon)

    return {
        "type": "stocks",
        "holdings": portfolio_df,
        "total_invested": amount,
        "total_expected_gain": scenarios["base"]["gain"],
        "expected_return_pct": scenarios["base"]["gain_pct"],
        "portfolio_beta": round(port_beta, 2),
        "n_holdings": len(portfolio_df),
        "scenarios": scenarios,
    }


def build_index_portfolio(profile: dict) -> dict:
    preferred_indices = profile.get("preferred_indices", [])
    risk = profile.get("risk_score", 5)
    amount = profile.get("amount", 10000)
    horizon = profile.get("horizon_years", 2)

    if preferred_indices:
        selected = {k: v for k, v in INDEX_TICKERS.items() if k in preferred_indices}
        # Si ninguna preferencia coincide con el diccionario de tickers, usar selección por riesgo
        if not selected:
            preferred_indices = []
    if not preferred_indices:
        if risk <= 3:
            selected = {"S&P 500 (EE.UU., grandes empresas)": "SPY",
                        "MSCI World (global, mercados desarrollados)": "URTH"}
        elif risk <= 6:
            selected = {k: v for k, v in INDEX_TICKERS.items() if k != "MSCI Emerging Markets (mercados emergentes)"}
        else:
            selected = INDEX_TICKERS

    if risk <= 3:
        weights = [0.50, 0.30] + [0.10] * (len(selected) - 2) if len(selected) > 2 else [0.60, 0.40]
    elif risk <= 6:
        weights = [1 / len(selected)] * len(selected)
    else:
        em_boost = 0.05
        base = 1 / len(selected)
        weights = [base + em_boost if "Emerging" in k else base for k in selected]

    weights = np.array(weights[:len(selected)])
    weights = weights / weights.sum()

    # Límites realistas por perfil para índices (menos volatilidad que acciones sueltas)
    if risk <= 3:
        cap_base, spread_down, spread_up = 0.08, 0.05, 0.03
    elif risk <= 6:
        cap_base, spread_down, spread_up = 0.12, 0.07, 0.05
    else:
        cap_base, spread_down, spread_up = 0.15, 0.09, 0.06

    rows = []
    for (idx_name, ticker), w in zip(selected.items(), weights):
        exp_ret = min(EXPECTED_RETURN_MAP.get(ticker, 0.09), cap_base)
        ret_min = max(-0.10, exp_ret - spread_down)
        ret_max = min(0.20,  exp_ret + spread_up)
        invested = amount * w

        rows.append({
            "ticker": ticker,
            "name": idx_name,
            "sector": "Diversificado",
            "country": "Global",
            "weight": round(w * 100, 2),
            "invested_eur": round(invested, 2),
            "expected_return_annual": round(exp_ret * 100, 1),
            "expected_return_annual_min": round(ret_min * 100, 1),
            "expected_return_annual_max": round(ret_max * 100, 1),
            "expected_gain_horizon": round(invested * ((1 + exp_ret) ** horizon - 1), 2),
            "expected_gain_horizon_min": round(invested * ((1 + ret_min) ** horizon - 1), 2),
            "expected_gain_horizon_max": round(invested * ((1 + ret_max) ** horizon - 1), 2),
            "score": 70,
            "beta": 1.0,
            "reasons": ["Diversificación global amplia", "Costes reducidos (ETF)", "Seguimiento de índice principal"],
            "warnings": [],
        })

    portfolio_df = pd.DataFrame(rows)
    scenarios = _portfolio_scenarios(portfolio_df, amount, horizon)

    return {
        "type": "indices",
        "holdings": portfolio_df,
        "total_invested": amount,
        "total_expected_gain": scenarios["base"]["gain"],
        "expected_return_pct": scenarios["base"]["gain_pct"],
        "portfolio_beta": 1.0,
        "n_holdings": len(portfolio_df),
        "scenarios": scenarios,
    }


def build_mixed_portfolio(df_scored: pd.DataFrame, profile: dict) -> dict:
    risk = profile.get("risk_score", 5)
    amount = profile.get("amount", 10000)

    custom_stock_pct = profile.get("custom_stock_pct")
    if custom_stock_pct is not None:
        idx_pct = 1.0 - (custom_stock_pct / 100.0)
    elif risk <= 3:
        idx_pct = 0.70
    elif risk <= 6:
        idx_pct = 0.50
    else:
        idx_pct = 0.30

    idx_profile = {**profile, "amount": amount * idx_pct}
    stock_profile = {**profile, "amount": amount * (1 - idx_pct)}

    idx_port = build_index_portfolio(idx_profile)
    stock_port = build_stock_portfolio(df_scored, stock_profile)

    idx_df = idx_port["holdings"].copy()
    stock_df = stock_port["holdings"].copy()

    idx_df["weight"] = idx_df["weight"] * idx_pct
    stock_df["weight"] = stock_df["weight"] * (1 - idx_pct)

    combined = pd.concat([idx_df, stock_df]).reset_index(drop=True)
    horizon = profile.get("horizon_years", 2)
    scenarios = _portfolio_scenarios(combined, amount, horizon)

    return {
        "type": "mixed",
        "holdings": combined,
        "total_invested": amount,
        "total_expected_gain": scenarios["base"]["gain"],
        "expected_return_pct": scenarios["base"]["gain_pct"],
        "portfolio_beta": round((idx_pct * 1.0 + (1 - idx_pct) * stock_port["portfolio_beta"]), 2),
        "n_holdings": len(combined),
        "idx_allocation_pct": round(idx_pct * 100),
        "stock_allocation_pct": round((1 - idx_pct) * 100),
        "scenarios": scenarios,
    }


def generate_portfolio(df_scored: pd.DataFrame, profile: dict) -> dict:
    inv_type = profile.get("investment_type", "Combinación de ambas")
    if "Índices" in inv_type:
        return build_index_portfolio(profile)
    elif "empresas individuales" in inv_type:
        return build_stock_portfolio(df_scored, profile)
    else:
        return build_mixed_portfolio(df_scored, profile)
