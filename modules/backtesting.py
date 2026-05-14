import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

BENCHMARK_SP500 = "SPY"
BENCHMARK_IBEX = "^IBEX"
RISK_FREE_RATE = 0.043  # aprox bono EE.UU. 10 años
# Mantener alias para compatibilidad interna
BENCHMARK = BENCHMARK_SP500


def _download_prices(tickers: list[str], start: datetime, end: datetime) -> pd.DataFrame:
    valid = [t for t in tickers if t and len(t) <= 8]
    if not valid:
        return pd.DataFrame()
    try:
        raw = yf.download(valid, start=start, end=end, progress=False, auto_adjust=True)
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.xs("Close", axis=1, level=0)
        else:
            closes = raw[["Close"]] if "Close" in raw.columns else raw
        # NO hacemos dropna global: cada ticker puede tener su propia fecha de
        # inicio (OPV posterior al start_date). Dejamos los NaN intactos para
        # que run_backtest los trate como retorno 0 (activo aún no cotizaba).
        # Solo eliminamos filas donde TODOS los valores son NaN (días sin mercado).
        return closes.dropna(how="all")
    except Exception:
        return pd.DataFrame()


def run_backtest(
    portfolio: dict,
    start_date: datetime,
    end_date: datetime,
    monthly_contribution: float = 0.0,
) -> dict:
    holdings = portfolio.get("holdings", pd.DataFrame())
    if holdings.empty:
        return {"error": "Cartera sin posiciones"}

    total_invested = portfolio.get("total_invested", 10000)

    # Solo acciones/ETFs con ticker corto (no índices de nombre largo)
    mask = holdings["ticker"].str.len() <= 8
    stock_holdings = holdings[mask].copy()

    if stock_holdings.empty:
        return {"error": "No hay tickers válidos para hacer backtesting"}

    tickers = stock_holdings["ticker"].tolist()
    weights_series = stock_holdings.set_index("ticker")["weight"] / 100

    # Precios históricos + benchmarks
    all_tickers = list(set(tickers + [BENCHMARK_SP500, BENCHMARK_IBEX]))
    prices = _download_prices(all_tickers, start_date, end_date)

    if prices.empty:
        return {"error": "No se pudieron descargar datos históricos"}

    # Alinear weights con columnas disponibles
    available = [t for t in tickers if t in prices.columns]
    if not available:
        return {"error": "No hay datos históricos para los tickers de tu cartera en ese período"}

    w = weights_series[available]
    w = w / w.sum()  # renormalizar si faltan tickers

    port_prices = prices[available]

    # Calcular retornos diarios. Los NaN (ticker aún no cotizaba en esa fecha)
    # se rellenan con 0: ese día el activo no existía en cartera, retorno neutro.
    # Esto preserva TODO el rango de fechas solicitado en lugar de recortarlo
    # al primer día en que TODOS los tickers tienen datos simultáneamente.
    port_returns = port_prices.pct_change()
    port_returns = port_returns.fillna(0)
    port_returns = port_returns.iloc[1:]  # eliminar solo la primera fila (NaN por el pct_change)

    # Reescalar pesos dinámicamente: si un ticker no tenía datos ese día,
    # su retorno es 0 pero su peso sigue siendo fijo — equivale a haber
    # esperado a que cotizara y empezar a invertir en él desde el primer día disponible.
    port_daily_ret = (port_returns * w).sum(axis=1)
    port_cumret = (1 + port_daily_ret).cumprod()
    port_value = port_cumret * total_invested

    # ── Simulación con aportaciones mensuales (DCA) ──────────────────────────
    port_value_dca = pd.Series(dtype=float)
    total_contributed_series = pd.Series(dtype=float)
    if monthly_contribution > 0:
        port_value_dca, total_contributed_series = _simulate_dca(
            port_daily_ret, total_invested, monthly_contribution
        )

    bench_ret = pd.Series(dtype=float)
    bench_cumret = pd.Series(dtype=float)
    bench_value = pd.Series(dtype=float)
    ibex_cumret = pd.Series(dtype=float)
    ibex_value = pd.Series(dtype=float)

    if BENCHMARK_SP500 in prices.columns:
        bench_daily = prices[BENCHMARK_SP500].pct_change().dropna()
        bench_daily = bench_daily.reindex(port_daily_ret.index).fillna(0)
        bench_cumret = (1 + bench_daily).cumprod()
        bench_value = bench_cumret * total_invested
        bench_ret = bench_daily

    if BENCHMARK_IBEX in prices.columns:
        ibex_daily = prices[BENCHMARK_IBEX].pct_change().dropna()
        ibex_daily = ibex_daily.reindex(port_daily_ret.index).fillna(0)
        ibex_cumret = (1 + ibex_daily).cumprod()
        ibex_value = ibex_cumret * total_invested

    metrics = _compute_metrics(port_daily_ret, bench_ret, total_invested)
    metrics_dca = {}
    if monthly_contribution > 0 and not port_value_dca.empty:
        metrics_dca = _compute_metrics_dca(
            port_value_dca, total_contributed_series, bench_ret, monthly_contribution
        )

    monthly_returns = _monthly_returns_table(port_daily_ret)
    drawdown_series = _drawdown_series(port_cumret)

    return {
        "portfolio_value": port_value,
        "portfolio_cumret": port_cumret,
        "bench_value": bench_value,
        "bench_cumret": bench_cumret,
        "port_daily_ret": port_daily_ret,
        "bench_daily_ret": bench_ret,
        "metrics": metrics,
        "monthly_returns": monthly_returns,
        "drawdown_series": drawdown_series,
        "available_tickers": available,
        "missing_tickers": [t for t in tickers if t not in available],
        "start_date": start_date,
        "end_date": end_date,
        "total_invested": total_invested,
        "monthly_contribution": monthly_contribution,
        "portfolio_value_dca": port_value_dca,
        "total_contributed_series": total_contributed_series,
        "metrics_dca": metrics_dca,
        "ibex_cumret": ibex_cumret,
        "ibex_value": ibex_value,
    }


def _simulate_dca(
    daily_ret: pd.Series,
    initial_capital: float,
    monthly_contribution: float,
) -> tuple[pd.Series, pd.Series]:
    """
    Simula una cartera con aportaciones mensuales reales.
    El primer día de cada mes se inyectan `monthly_contribution` euros
    distribuidos según los pesos de la cartera (equivale a comprar más participaciones).
    Devuelve (valor_total_diario, capital_invertido_acumulado).
    """
    dates = daily_ret.index
    # Número de unidades (shares normalizadas). Empezamos con 1 unidad = initial_capital
    # Modelamos la cartera como un fondo: shares * nav
    nav = pd.Series(index=dates, dtype=float)
    nav.iloc[0] = 1.0
    for i in range(1, len(dates)):
        nav.iloc[i] = nav.iloc[i - 1] * (1 + daily_ret.iloc[i])

    shares = initial_capital / nav.iloc[0]
    contributions_dates = set()
    last_month = dates[0].month

    for i, dt in enumerate(dates):
        if i == 0:
            continue
        if dt.month != last_month:
            # Primer día del nuevo mes: aportación
            new_shares = monthly_contribution / nav.iloc[i]
            shares += new_shares
            contributions_dates.add(dt)
            last_month = dt.month

    # Reconstruir las series día a día con acumulación real
    shares_series = pd.Series(index=dates, dtype=float)
    total_invested_series = pd.Series(index=dates, dtype=float)
    current_shares = initial_capital / nav.iloc[0]
    total_inv = initial_capital
    last_month = dates[0].month

    for i, dt in enumerate(dates):
        if i > 0 and dt.month != last_month:
            new_shares = monthly_contribution / nav.iloc[i]
            current_shares += new_shares
            total_inv += monthly_contribution
            last_month = dt.month
        shares_series.iloc[i] = current_shares
        total_invested_series.iloc[i] = total_inv

    port_value_dca = shares_series * nav
    return port_value_dca, total_invested_series


def _compute_metrics_dca(
    port_value_dca: pd.Series,
    total_contributed: pd.Series,
    bench_ret: pd.Series,
    monthly_contribution: float,
) -> dict:
    if port_value_dca.empty:
        return {}
    final_value = port_value_dca.iloc[-1]
    total_inv = total_contributed.iloc[-1]
    gain = final_value - total_inv
    gain_pct = (final_value / total_inv - 1) * 100 if total_inv > 0 else 0

    # Drawdown sobre la serie DCA
    rolling_max = port_value_dca.cummax()
    dd = (port_value_dca - rolling_max) / rolling_max
    max_dd = dd.min() * 100

    # Retorno diario implícito para Sharpe (aproximado)
    daily_ret_dca = port_value_dca.pct_change().dropna()
    n = len(daily_ret_dca)
    ann_vol = daily_ret_dca.std() * np.sqrt(252) * 100 if n > 5 else 0

    return {
        "final_value": round(final_value, 2),
        "total_contributed": round(total_inv, 2),
        "gain": round(gain, 2),
        "gain_pct": round(gain_pct, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "annualized_volatility_pct": round(ann_vol, 2),
        "monthly_contribution": monthly_contribution,
    }


def _compute_metrics(port_ret: pd.Series, bench_ret: pd.Series, capital: float) -> dict:
    n = len(port_ret)
    if n == 0:
        return {}

    total_ret = (1 + port_ret).prod() - 1
    ann_ret = (1 + total_ret) ** (252 / n) - 1 if n > 0 else 0
    ann_vol = port_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0

    neg_ret = port_ret[port_ret < 0]
    downside_vol = neg_ret.std() * np.sqrt(252) if len(neg_ret) > 0 else 0
    sortino = (ann_ret - RISK_FREE_RATE) / downside_vol if downside_vol > 0 else 0

    cumret = (1 + port_ret).cumprod()
    rolling_max = cumret.cummax()
    drawdown = (cumret - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    positive_days = (port_ret > 0).sum()
    win_rate = positive_days / n * 100

    # VaR 95%
    var_95 = np.percentile(port_ret, 5) * 100

    # Beta vs benchmark
    beta = np.nan
    alpha = np.nan
    if not bench_ret.empty and len(bench_ret) > 10:
        aligned = port_ret.align(bench_ret, join="inner")
        p_aligned, b_aligned = aligned
        if len(p_aligned) > 10 and b_aligned.std() > 0:
            cov = np.cov(p_aligned, b_aligned)
            beta = cov[0, 1] / cov[1, 1]
            bench_ann = (1 + b_aligned).prod() ** (252 / len(b_aligned)) - 1
            alpha = ann_ret - (RISK_FREE_RATE + beta * (bench_ann - RISK_FREE_RATE))

    final_value = capital * (1 + total_ret)
    profit = final_value - capital

    return {
        "total_return_pct": round(total_ret * 100, 2),
        "annualized_return_pct": round(ann_ret * 100, 2),
        "annualized_volatility_pct": round(ann_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "win_rate_pct": round(win_rate, 1),
        "var_95_pct": round(var_95, 2),
        "beta": round(beta, 3) if not np.isnan(beta) else None,
        "alpha_pct": round(alpha * 100, 2) if not np.isnan(alpha) else None,
        "final_value": round(final_value, 2),
        "profit": round(profit, 2),
        "n_trading_days": n,
    }


def _monthly_returns_table(daily_ret: pd.Series) -> pd.DataFrame:
    if daily_ret.empty:
        return pd.DataFrame()
    monthly = daily_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
    monthly.index = monthly.index.to_period("M")
    df = monthly.reset_index()
    df.columns = ["Period", "Return"]
    df["Year"] = df["Period"].dt.year
    df["Month"] = df["Period"].dt.month
    pivot = df.pivot(index="Year", columns="Month", values="Return")
    month_names = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                   7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
    pivot.columns = [month_names.get(c, c) for c in pivot.columns]
    pivot["Anual"] = (1 + pivot.fillna(0) / 100).prod(axis=1) ** (12 / pivot.notna().sum(axis=1)) - 1
    pivot["Anual"] = pivot["Anual"] * 100
    return pivot.round(2)


def _drawdown_series(cumret: pd.Series) -> pd.Series:
    rolling_max = cumret.cummax()
    return ((cumret - rolling_max) / rolling_max) * 100


# ── Plotly charts ────────────────────────────────────────────────────────────

def chart_portfolio_value(result: dict) -> go.Figure:
    fig = go.Figure()
    pv = result["portfolio_value"]
    bv = result["bench_value"]
    capital = result["total_invested"]
    pv_dca = result.get("portfolio_value_dca", pd.Series(dtype=float))
    contributed = result.get("total_contributed_series", pd.Series(dtype=float))

    fig.add_trace(go.Scatter(
        x=pv.index, y=pv.values,
        name="Mi cartera (sin aportaciones)",
        line=dict(color="#2d5a9f", width=2.5),
        fill="tozeroy", fillcolor="rgba(45,90,159,0.08)",
    ))
    if not pv_dca.empty:
        fig.add_trace(go.Scatter(
            x=pv_dca.index, y=pv_dca.values,
            name="Mi cartera (con aportaciones mensuales)",
            line=dict(color="#27ae60", width=2.5),
        ))
    if not contributed.empty:
        fig.add_trace(go.Scatter(
            x=contributed.index, y=contributed.values,
            name="Capital invertido total",
            line=dict(color="#f39c12", width=1.5, dash="dot"),
        ))
    if not bv.empty:
        fig.add_trace(go.Scatter(
            x=bv.index, y=bv.values,
            name="S&P 500 (referencia)",
            line=dict(color="#e74c3c", width=1.8, dash="dash"),
        ))
    ibex_v = result.get("ibex_value", pd.Series(dtype=float))
    if not ibex_v.empty:
        fig.add_trace(go.Scatter(
            x=ibex_v.index, y=ibex_v.values,
            name="IBEX 35 (referencia)",
            line=dict(color="#e67e22", width=1.8, dash="dashdot"),
        ))
    fig.add_hline(y=capital, line_dash="dash", line_color="#aaa",
                  annotation_text=f"Capital inicial €{capital:,.0f}")
    fig.update_layout(
        title=dict(text="Evolución del valor de la cartera", x=0, xanchor="left"),
        yaxis_title="Valor (€)",
    )
    return fig


def chart_dca_comparison(result: dict) -> go.Figure | None:
    """Gráfico dedicado a comparar escenario sin/con aportaciones."""
    pv = result["portfolio_value"]
    pv_dca = result.get("portfolio_value_dca", pd.Series(dtype=float))
    contributed = result.get("total_contributed_series", pd.Series(dtype=float))
    if pv_dca.empty:
        return None

    capital = result["total_invested"]
    monthly = result.get("monthly_contribution", 0)
    metrics_dca = result.get("metrics_dca", {})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pv.index, y=pv.values,
        name=f"Solo capital inicial (€{capital:,.0f})",
        line=dict(color="#2d5a9f", width=2),
        fill="tozeroy", fillcolor="rgba(45,90,159,0.07)",
    ))
    fig.add_trace(go.Scatter(
        x=pv_dca.index, y=pv_dca.values,
        name=f"+ €{monthly:,.0f}/mes (DCA)",
        line=dict(color="#27ae60", width=2.5),
        fill="tonexty", fillcolor="rgba(39,174,96,0.12)",
    ))
    fig.add_trace(go.Scatter(
        x=contributed.index, y=contributed.values,
        name="Capital invertido acumulado",
        line=dict(color="#f39c12", width=1.5, dash="dot"),
    ))

    if metrics_dca:
        final = metrics_dca.get("final_value", 0)
        gain = metrics_dca.get("gain", 0)
        gain_pct = metrics_dca.get("gain_pct", 0)
        fig.add_annotation(
            x=pv_dca.index[-1], y=final,
            text=f"€{final:,.0f} (+{gain_pct:.1f}%)",
            showarrow=True, arrowhead=2, bgcolor="#27ae60", font=dict(color="white"),
        )

    fig.update_layout(
        title=f"Impacto de las aportaciones mensuales de €{monthly:,.0f}",
        yaxis_title="Valor (€)",
    )
    return fig


def chart_returns_comparison(result: dict) -> go.Figure:
    pc = (result["portfolio_cumret"] - 1) * 100
    bc = (result["bench_cumret"] - 1) * 100 if not result["bench_cumret"].empty else None
    ibex_c = result.get("ibex_cumret", pd.Series(dtype=float))
    ibex_pct = (ibex_c - 1) * 100 if not ibex_c.empty else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pc.index, y=pc.values, name="Mi cartera",
                              line=dict(color="#2d5a9f", width=2.5)))
    if bc is not None:
        fig.add_trace(go.Scatter(x=bc.index, y=bc.values, name="S&P 500",
                                  line=dict(color="#e74c3c", width=1.8, dash="dot")))
    if ibex_pct is not None:
        fig.add_trace(go.Scatter(x=ibex_pct.index, y=ibex_pct.values, name="IBEX 35",
                                  line=dict(color="#e67e22", width=1.8, dash="dashdot")))
    fig.add_hline(y=0, line_color="#aaa", line_dash="dash")
    fig.update_layout(
        title=dict(text="Rentabilidad acumulada (%) — cartera vs S&P 500 vs IBEX 35", x=0, xanchor="left"),
        yaxis_title="%",
    )
    return fig


def chart_drawdown(result: dict) -> go.Figure:
    dd = result["drawdown_series"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy",
        fillcolor="rgba(231,76,60,0.25)",
        line=dict(color="#e74c3c", width=1.5),
        name="Drawdown",
    ))
    fig.update_layout(
        title="Drawdown (%)",
        yaxis_title="%",
        height=280,
        hovermode="x unified",
    )
    return fig


def chart_monthly_heatmap(result: dict) -> go.Figure | None:
    df = result["monthly_returns"]
    if df.empty:
        return None
    month_cols = [c for c in df.columns if c != "Anual"]
    z = df[month_cols].values
    fig = go.Figure(go.Heatmap(
        z=z,
        x=month_cols,
        y=[str(y) for y in df.index],
        colorscale=[[0, "#e74c3c"], [0.5, "#f8f9fa"], [1, "#27ae60"]],
        zmid=0,
        text=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in z],
        texttemplate="%{text}",
        showscale=True,
    ))
    fig.update_layout(
        title="Rentabilidad mensual (%)",
        height=max(180, 60 * len(df) + 80),
        margin=dict(t=40, b=20),
    )
    return fig


def chart_rolling_sharpe(result: dict, window: int = 63) -> go.Figure:
    ret = result["port_daily_ret"]
    if len(ret) < window + 5:
        return go.Figure()
    rolling_ret = ret.rolling(window).mean() * 252
    rolling_vol = ret.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = (rolling_ret - RISK_FREE_RATE) / rolling_vol.replace(0, np.nan)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values,
                              line=dict(color="#8e44ad", width=2), name=f"Sharpe móvil ({window}d)"))
    fig.add_hline(y=1, line_dash="dash", line_color="#27ae60", annotation_text="Sharpe = 1 (bueno)")
    fig.add_hline(y=0, line_dash="dot", line_color="#aaa")
    fig.update_layout(title=f"Sharpe ratio móvil ({window} días)", yaxis_title="Sharpe",
                      height=280, hovermode="x unified")
    return fig
