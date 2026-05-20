import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta

from modules.investor_profile import render_profile_form, describe_profile
from modules.ml_model import analyze_universe
from modules.portfolio_optimizer import generate_portfolio, compute_dca_projection
from modules.geopolitical_risk import get_portfolio_geopolitical_impact, get_global_risk_map
from modules.notifications import (
    get_notifications, mark_all_read, clear_notifications,
    check_portfolio_alerts, generate_periodic_advice, add_notification
)
from modules.data_fetcher import get_price_history, get_live_portfolio_performance
from modules.portfolio_manager import (
    save_portfolio, load_portfolios, get_portfolio_by_id,
    delete_portfolio, rename_portfolio, duplicate_portfolio
)
from modules.backtesting import (
    run_backtest, chart_portfolio_value, chart_returns_comparison,
    chart_drawdown, chart_monthly_heatmap, chart_rolling_sharpe, chart_dca_comparison
)

st.set_page_config(
    page_title="InvestAI — Portfolio Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
C_NAVY    = "#0d1b2a"
C_BLUE    = "#1b3a5c"
C_ACCENT  = "#2563a8"
C_GOLD    = "#b8966e"
C_GREEN   = "#1e6b45"
C_RED     = "#8b2635"
C_AMBER   = "#8b5e1a"
C_TEXT    = "#1a1a2e"
C_MUTED   = "#5c6475"
C_BORDER  = "#d8dce8"
C_BG_CARD = "#ffffff"
C_BG_PAGE = "#f4f6fb"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: {C_TEXT};
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {C_NAVY};
    border-right: 1px solid #1e2d40;
}}
[data-testid="stSidebar"] * {{
    color: #c8d0dc !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: transparent;
    color: #c8d0dc !important;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 8px 14px;
    font-size: 0.87rem;
    font-weight: 400;
    width: 100%;
    transition: background 0.15s;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.07);
    color: #ffffff !important;
}}

/* ── Page background ── */
.main .block-container {{
    background: {C_BG_PAGE};
    padding-top: 2rem;
    max-width: 1280px;
}}

/* ── Page title ── */
h1 {{
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: {C_NAVY} !important;
    letter-spacing: -0.3px;
    border-bottom: 2px solid {C_BORDER};
    padding-bottom: 0.6rem;
    margin-bottom: 1.4rem !important;
}}
h2 {{
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: {C_NAVY} !important;
    margin-top: 1.6rem !important;
}}
h3 {{
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: {C_BLUE} !important;
    margin-top: 1.2rem !important;
}}

/* ── Cards ── */
.inv-card {{
    background: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 20px 24px;
    margin: 0 0 12px 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}
.inv-card-accent {{
    border-left: 3px solid {C_ACCENT};
}}

/* ── Feature grid (home) ── */
.feature-block {{
    background: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-top: 3px solid {C_ACCENT};
    border-radius: 6px;
    padding: 20px;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.feature-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: {C_ACCENT};
    margin-bottom: 6px;
}}
.feature-title {{
    font-size: 1rem;
    font-weight: 600;
    color: {C_NAVY};
    margin-bottom: 6px;
}}
.feature-desc {{
    font-size: 0.83rem;
    color: {C_MUTED};
    line-height: 1.5;
}}

/* ── Scenario cards ── */
.scenario-card {{
    background: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}}
.scenario-card.bear {{ border-top: 3px solid {C_RED}; }}
.scenario-card.base {{ border-top: 3px solid {C_ACCENT}; background: #f5f8ff; }}
.scenario-card.bull {{ border-top: 3px solid {C_GREEN}; }}
.scenario-tag {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-bottom: 10px;
}}
.scenario-pct {{
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 8px;
}}
.scenario-detail {{
    font-size: 0.82rem;
    color: {C_MUTED};
    margin: 3px 0;
}}
.scenario-ann {{
    font-size: 0.75rem;
    color: {C_MUTED};
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid {C_BORDER};
}}
.scenario-desc {{
    font-size: 0.72rem;
    color: #8a95a8;
    margin-top: 6px;
    line-height: 1.4;
}}

/* ── Metric row ── */
.kpi-row {{
    display: flex;
    gap: 12px;
    margin: 16px 0;
    flex-wrap: wrap;
}}
.kpi-box {{
    flex: 1;
    min-width: 140px;
    background: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 14px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.kpi-label {{
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {C_MUTED};
    margin-bottom: 4px;
}}
.kpi-value {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {C_NAVY};
    line-height: 1.2;
}}
.kpi-value.pos {{ color: {C_GREEN}; }}
.kpi-value.neg {{ color: {C_RED}; }}
.kpi-value.neutral {{ color: {C_NAVY}; }}

/* ── Portfolio list card ── */
.port-card {{
    background: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.port-card.active {{ border-left: 3px solid {C_ACCENT}; }}
.port-name {{
    font-size: 1rem;
    font-weight: 600;
    color: {C_NAVY};
}}
.port-meta {{
    font-size: 0.8rem;
    color: {C_MUTED};
    margin-top: 4px;
}}

/* ── Badges ── */
.badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}
.badge-cons  {{ background: #e8f4ee; color: {C_GREEN}; }}
.badge-mod   {{ background: #fdf3e3; color: {C_AMBER}; }}
.badge-agg   {{ background: #fce8ea; color: {C_RED}; }}
.badge-active {{ background: #e8eef8; color: {C_ACCENT}; }}

/* ── Notif entry ── */
.notif-entry {{
    background: {C_BG_CARD};
    border-left: 3px solid {C_BORDER};
    border-radius: 0 6px 6px 0;
    padding: 10px 16px;
    margin: 6px 0;
    font-size: 0.87rem;
}}
.notif-entry.success {{ border-left-color: {C_GREEN}; }}
.notif-entry.warning {{ border-left-color: {C_AMBER}; }}
.notif-entry.error   {{ border-left-color: {C_RED}; }}
.notif-entry.info    {{ border-left-color: {C_ACCENT}; }}
.notif-ts {{
    font-size: 0.75rem;
    color: {C_MUTED};
    float: right;
}}

/* ── Disclaimer ── */
.disclaimer {{
    font-size: 0.75rem;
    color: {C_MUTED};
    border-top: 1px solid {C_BORDER};
    padding-top: 12px;
    margin-top: 24px;
    line-height: 1.6;
}}

/* ── Section separator ── */
.section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: {C_MUTED};
    margin: 20px 0 8px 0;
}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, color_class: str = "neutral") -> str:
    return (
        f'<div class="kpi-box">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value {color_class}">{value}</div>'
        f'</div>'
    )


def _apply_plotly_style(fig: go.Figure, height: int = 400) -> go.Figure:
    n_traces = len(fig.data)
    # Leyenda debajo solo cuando hay mas de 1 traza (evita espacio vacio innecesario)
    if n_traces > 1:
        legend_cfg = dict(
            orientation="h",
            yanchor="top", y=-0.22,
            xanchor="left", x=0,
            bgcolor="white", bordercolor=C_BORDER, borderwidth=1,
            font=dict(size=11),
        )
        bottom_margin = 100
    else:
        legend_cfg = dict(
            orientation="h",
            yanchor="top", y=-0.12,
            xanchor="left", x=0,
            bgcolor="white", bordercolor=C_BORDER, borderwidth=1,
            font=dict(size=11),
        )
        bottom_margin = 50

    fig.update_layout(
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=C_TEXT),
        paper_bgcolor="white",
        plot_bgcolor="#f9fafc",
        height=height,
        margin=dict(t=36, b=bottom_margin, l=10, r=10),
        hovermode="x unified",
        legend=legend_cfg,
    )
    fig.update_xaxes(gridcolor="#eaecf3", linecolor=C_BORDER, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#eaecf3", linecolor=C_BORDER, tickfont=dict(size=11))
    return fig


# ── Session state ─────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "page": "home",
        "profile": None,
        "df_scored": None,
        "portfolio": None,
        "portfolio_accepted": False,
        "analysis_done": False,
        "geo_risk": None,
        "active_portfolio_id": None,
        "backtest_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _sidebar():
    with st.sidebar:
        st.markdown(
            f'<div style="padding:20px 8px 12px;border-bottom:1px solid #1e2d40;margin-bottom:16px;">'
            f'<div style="font-size:1.1rem;font-weight:700;color:#e8edf4;letter-spacing:-0.2px;">InvestAI</div>'
            f'<div style="font-size:0.72rem;color:#7a8fa6;margin-top:2px;letter-spacing:0.5px;text-transform:uppercase;">Portfolio Intelligence</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        nav_items = [
            ("home",         "Inicio"),
            ("profile",      "Nuevo perfil"),
            ("analysis",     "Analisis de cartera"),
            ("my_portfolios","Mis carteras"),
            ("dashboard",    "Dashboard"),
            ("backtest",     "Backtesting"),
            ("geo",          "Riesgo geopolitico"),
            ("notifications","Notificaciones"),
        ]
        need_profile = {"analysis", "dashboard", "backtest", "geo"}

        st.markdown('<div style="margin-bottom:4px;font-size:0.65rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#4a5a6e;padding:0 8px;">Navegacion</div>', unsafe_allow_html=True)
        for key, label in nav_items:
            disabled = key in need_profile and not st.session_state.profile
            active = st.session_state.page == key
            btn_style = "background:rgba(255,255,255,0.1);color:#ffffff !important;" if active else ""
            if st.button(label, key=f"nav_{key}", use_container_width=True, disabled=disabled):
                st.session_state.page = key
                st.rerun()

        st.markdown('<div style="border-top:1px solid #1e2d40;margin:16px 0;"></div>', unsafe_allow_html=True)

        if st.session_state.profile:
            p = st.session_state.profile
            risk = p.get("risk_score", 5)
            risk_label = "Conservador" if risk <= 3 else "Moderado" if risk <= 6 else "Agresivo"
            monthly = p.get("monthly_contribution", 0)
            contrib = f" · +€{monthly:,.0f}/mes" if monthly else ""
            st.markdown(
                f'<div style="padding:10px 8px;font-size:0.78rem;color:#7a8fa6;">'
                f'<div style="color:#a8b8cc;font-weight:600;margin-bottom:4px;">Perfil activo</div>'
                f'{risk_label} · €{p.get("amount",0):,.0f}{contrib}<br>'
                f'{p.get("horizon_label","")}'
                f'</div>',
                unsafe_allow_html=True,
            )

        saved = load_portfolios()
        if saved:
            st.markdown(f'<div style="padding:0 8px;font-size:0.75rem;color:#4a5a6e;">{len(saved)} cartera(s) guardada(s)</div>', unsafe_allow_html=True)

        notifs = get_notifications(unread_only=True)
        if notifs:
            st.markdown(f'<div style="padding:8px;margin:8px 0;background:#1e2d40;border-radius:6px;font-size:0.78rem;color:#e0a96d;">{len(notifs)} notificacion(es) pendiente(s)</div>', unsafe_allow_html=True)


# ── Page: Home ────────────────────────────────────────────────────────────────

def page_home():
    st.markdown("# InvestAI — Portfolio Intelligence")
    st.markdown(
        '<div style="color:#5c6475;font-size:0.95rem;margin:-12px 0 24px;">Sistema de gestion activa de carteras basado en modelos de machine learning y analisis de indices globales.</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("Perfil de inversor", "Cuestionario estructurado sobre tolerancia al riesgo, horizonte temporal, preferencias sectoriales y criterios ESG."),
        ("Analisis de indices", "Modelos ML que analizan el flujo de empresas en S&P 500, MSCI World y Fortune Global 500 para identificar oportunidades."),
        ("Optimizacion de cartera", "Algoritmo de optimizacion media-varianza (Markowitz) con escenarios de rentabilidad pesimista, base y optimista."),
        ("Riesgo geopolitico", "Integracion con GDELT para monitorizar eventos geopoliticos en tiempo real y su impacto sectorial."),
    ]
    for col, (title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(
                f'<div class="feature-block">'
                f'<div class="feature-label">Modulo</div>'
                f'<div class="feature-title">{title}</div>'
                f'<div class="feature-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown('<div class="inv-card inv-card-accent">', unsafe_allow_html=True)
        st.markdown("**Nueva cartera**")
        st.markdown('<div style="font-size:0.85rem;color:#5c6475;margin-bottom:12px;">Define tu perfil de inversor y genera una propuesta de cartera personalizada en minutos.</div>', unsafe_allow_html=True)
        if st.button("Iniciar cuestionario de perfil", type="primary", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="inv-card">', unsafe_allow_html=True)
        st.markdown("**Mis carteras**")
        saved = load_portfolios()
        st.markdown(f'<div style="font-size:0.85rem;color:#5c6475;margin-bottom:12px;">Tienes {len(saved)} cartera(s) guardada(s). Accede, compara y realiza backtesting sobre periodos historicos.</div>', unsafe_allow_html=True)
        if st.button("Ver carteras guardadas", use_container_width=True):
            st.session_state.page = "my_portfolios"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="disclaimer">InvestAI proporciona informacion y analisis con fines educativos e informativos. '
        'No constituye asesoramiento financiero regulado ni oferta de compra o venta de valores. '
        'Las rentabilidades pasadas no garantizan resultados futuros. Toda inversion conlleva riesgo de perdida de capital.</div>',
        unsafe_allow_html=True,
    )


# ── Page: Profile ─────────────────────────────────────────────────────────────

def page_profile():
    profile = render_profile_form()
    if profile:
        st.session_state.profile = profile
        st.session_state.analysis_done = False
        st.session_state.df_scored = None
        st.session_state.portfolio = None
        st.session_state.portfolio_accepted = False
        st.session_state.backtest_result = None
        st.session_state.page = "analysis"
        add_notification("Perfil registrado", "Perfil de inversor guardado. Iniciando analisis de mercado.", "info")
        st.rerun()


# ── Page: Analysis ────────────────────────────────────────────────────────────

def page_analysis():
    profile = st.session_state.profile
    if not profile:
        st.warning("Es necesario completar el cuestionario de perfil antes de continuar.")
        return

    st.markdown("# Analisis y propuesta de cartera")
    st.markdown(
        f'<div class="inv-card" style="margin-bottom:16px;">'
        f'<span style="font-size:0.72rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{C_MUTED};">Perfil activo</span><br>'
        f'<span style="font-size:0.9rem;">{describe_profile(profile)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.analysis_done:
        st.markdown("**Procesando datos de mercado...**")
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_cb(pct, msg):
            progress_bar.progress(min(pct, 1.0))
            status_text.markdown(f'<span style="font-size:0.82rem;color:{C_MUTED};">{msg}</span>', unsafe_allow_html=True)

        with st.spinner("Descargando y procesando datos de mercado..."):
            df_scored = analyze_universe(profile, progress_callback=progress_cb)
            st.session_state.df_scored = df_scored

        with st.spinner("Optimizando cartera..."):
            portfolio = generate_portfolio(df_scored, profile)
            st.session_state.portfolio = portfolio

        progress_bar.progress(1.0)
        status_text.empty()
        st.session_state.analysis_done = True
        st.rerun()

    _render_portfolio_proposal(st.session_state.portfolio, profile, st.session_state.df_scored)


def _portfolio_rationale(portfolio: dict, profile: dict, n_universe: int = 0) -> str:
    holdings = portfolio["holdings"]
    n = len(holdings)
    beta = portfolio.get("portfolio_beta", 1.0)
    port_type = portfolio.get("type", "mixed")
    risk = profile.get("risk_score", 5)
    risk_label = "conservador" if risk <= 3 else "moderado" if risk <= 6 else "agresivo"
    pct_base = portfolio.get("expected_return_pct", 0)
    opt_method = "minimización de volatilidad" if risk <= 5 else "maximización del índice de Sharpe"

    # ── Sector dominante ──────────────────────────────────────────────────────
    if "sector" in holdings.columns:
        sw = holdings.groupby("sector")["weight"].sum().sort_values(ascending=False)
        top_sector, top_sector_pct = (sw.index[0], sw.iloc[0]) if not sw.empty else ("diversificado", 0)
    else:
        top_sector, top_sector_pct = "diversificado", 0

    # ── Cartera de índices ────────────────────────────────────────────────────
    if port_type == "indices":
        parts = []
        for _, r in holdings.iterrows():
            ret = r.get("expected_return_annual", 0)
            parts.append(f"{r['name']} (ticker: {r.get('ticker','')}, ret. histórico ~{ret:.1f}% anual)")
        names_str = "; ".join(parts)
        avg_ret = holdings["expected_return_annual"].mean() if "expected_return_annual" in holdings.columns else pct_base
        return (
            f"La cartera está compuesta por {n} ETF{'s' if n > 1 else ''} de gestión pasiva: {names_str}. "
            f"La estrategia de indexación ofrece exposición a miles de empresas simultáneamente con costes muy reducidos, "
            f"eliminando el riesgo específico de empresa. "
            f"La rentabilidad histórica media ponderada de estos índices es del {avg_ret:.1f}% anual "
            f"y la beta de cartera resultante es de {beta:.2f}, "
            f"{'ligeramente por debajo' if beta < 1 else 'alineada con' if abs(beta-1)<0.05 else 'por encima de'} "
            f"la referencia del mercado global."
        )

    # ── Métricas agregadas (acciones / mixta) ─────────────────────────────────
    w_col = holdings["weight"] / 100

    avg_mom   = (holdings["mom_12m"]       * w_col).sum() if "mom_12m"       in holdings.columns else 0
    avg_rev_g = (holdings["revenue_growth"] * w_col).sum() if "revenue_growth" in holdings.columns else 0
    avg_div   = (holdings["dividend_yield"] * w_col).sum() if "dividend_yield" in holdings.columns else 0
    pos_mom   = int((holdings["mom_12m"] > 0).sum())       if "mom_12m"       in holdings.columns else 0

    # ── Top 3 posiciones con métricas clave ───────────────────────────────────
    top3_parts = []
    for _, r in holdings.head(3).iterrows():
        name  = r.get("name", r.get("ticker", ""))
        w     = r.get("weight", 0)
        mom   = r.get("mom_12m", 0) or 0
        rev_g = r.get("revenue_growth", 0) or 0
        b     = r.get("beta", 1.0) or 1.0
        sign_mom = "+" if mom >= 0 else ""
        sign_rev = "+" if rev_g >= 0 else ""
        top3_parts.append(
            f"**{name}** ({w:.0f}% — mom. 12M: {sign_mom}{mom:.1f}%, "
            f"crec. ingresos: {sign_rev}{rev_g:.1f}%, β {b:.2f})"
        )
    top3_str = "; ".join(top3_parts)

    # ── Contexto de mercado y selección ──────────────────────────────────────
    market_filter = [m for m in profile.get("stock_market_filter", []) if "Cualquier" not in m]
    market_str = f" del {market_filter[0].split('(')[0].strip()}" if len(market_filter) == 1 else ""
    universe_str = f" analizó {n_universe} candidatos{market_str} y" if n_universe > 0 else f"{market_str}"

    sector_str = (
        f"concentra el {top_sector_pct:.0f}% en {top_sector}"
        if top_sector_pct > 35
        else f"distribuye el peso principal en {top_sector} ({top_sector_pct:.0f}%)"
    )

    # ── Nota sobre dividendo (perfil conservador) ─────────────────────────────
    div_note = f" La rentabilidad por dividendo media ponderada es del {avg_div:.1f}%." if risk <= 4 and avg_div > 0.5 else ""

    # ── Nota mixta ────────────────────────────────────────────────────────────
    idx_note = ""
    if port_type == "mixed":
        idx_pct = portfolio.get("idx_allocation_pct", 50)
        idx_note = f" El {idx_pct}% restante se asigna a ETFs de índice para reducir volatilidad y ampliar diversificación."

    sign_mom_avg = "+" if avg_mom >= 0 else ""
    sign_rev_avg = "+" if avg_rev_g >= 0 else ""

    return (
        f"El algoritmo{universe_str} seleccionó {n} posiciones mediante {opt_method} (Markowitz). "
        f"Las tres principales apuestas son: {top3_str}. "
        f"A nivel agregado, la cartera {sector_str}, presenta una beta ponderada de **{beta:.2f}** "
        f"({'por debajo' if beta < 1 else 'por encima'} del mercado), "
        f"un momentum medio a 12 meses del **{sign_mom_avg}{avg_mom:.1f}%** "
        f"y un crecimiento de ingresos ponderado del **{sign_rev_avg}{avg_rev_g:.1f}%** "
        f"({pos_mom} de {n} posiciones con momentum positivo).{div_note} "
        f"La rentabilidad base estimada es del **{pct_base:.1f}%** sobre el horizonte seleccionado.{idx_note}"
    )


def _render_portfolio_proposal(portfolio: dict, profile: dict, df_scored: pd.DataFrame):
    holdings = portfolio["holdings"]
    amount = portfolio["total_invested"]
    beta = portfolio.get("portfolio_beta", 1.0)
    scenarios = portfolio.get("scenarios", {})

    # ── KPI row ──────────────────────────────────────────────────────────────
    s_base = scenarios.get("base", {})
    gain_base = s_base.get("gain", 0)
    pct_base = s_base.get("gain_pct", 0)

    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Capital invertido", f"€{amount:,.0f}")}'
        f'{_kpi("Horizonte", profile["horizon_label"])}'
        f'{_kpi("Rentabilidad base esperada", f"+{pct_base:.1f}%", "pos" if pct_base >= 0 else "neg")}'
        f'{_kpi("Beta de cartera", f"{beta:.2f}")}'
        f'{_kpi("Posiciones", str(portfolio["n_holdings"]))}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tres escenarios ───────────────────────────────────────────────────────
    if scenarios:
        st.markdown("## Escenarios de rentabilidad")
        s_min  = scenarios.get("pessimistic", {})
        s_max  = scenarios.get("optimistic", {})

        col_min, col_base, col_max = st.columns(3)
        for col, sc, css_cls, tag_color in [
            (col_min,  s_min,  "bear", C_RED),
            (col_base, s_base, "base", C_ACCENT),
            (col_max,  s_max,  "bull", C_GREEN),
        ]:
            with col:
                gain = sc.get("gain", 0)
                pct  = sc.get("gain_pct", 0)
                final = sc.get("final_value", amount)
                ann  = sc.get("annual_avg", 0)
                label = sc.get("label", "")
                desc  = sc.get("description", "")
                sign  = "+" if pct >= 0 else ""
                st.markdown(
                    f'<div class="scenario-card {css_cls}">'
                    f'<div class="scenario-tag" style="color:{tag_color};">{label}</div>'
                    f'<div class="scenario-pct" style="color:{tag_color};">{sign}{pct:.1f}%</div>'
                    f'<div class="scenario-detail">Ganancia: <strong>€{gain:+,.0f}</strong></div>'
                    f'<div class="scenario-detail">Valor final: <strong>€{final:,.0f}</strong></div>'
                    f'<div class="scenario-ann">{ann:.1f}% anual medio estimado</div>'
                    f'<div class="scenario-desc">{desc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<div class="disclaimer" style="margin-top:8px;">Estimaciones basadas en rentabilidades historicas ajustadas por perfil de riesgo. '
            'No constituyen garantia de rendimiento futuro.</div>',
            unsafe_allow_html=True,
        )

    # ── Párrafo de justificación ──────────────────────────────────────────────
    n_universe = len(df_scored) if df_scored is not None and not df_scored.empty else 0
    rationale = _portfolio_rationale(portfolio, profile, n_universe)
    st.markdown(
        f'<div class="inv-card" style="margin:8px 0 20px;line-height:1.65;font-size:0.9rem;">'
        f'<span style="font-size:0.68rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;'
        f'color:{C_MUTED};display:block;margin-bottom:6px;">Por qué esta cartera</span>'
        f'{rationale}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("## Composicion de la cartera")
    col_chart, col_list = st.columns([1, 1])

    with col_chart:
        colors = ["#1b3a5c","#2563a8","#3d7dd4","#6aa3e0","#9dc4ec",
                  "#b8966e","#d4b896","#1e6b45","#3a9e6a","#5fcc8f"]
        fig = go.Figure(go.Pie(
            labels=holdings["name"], values=holdings["weight"],
            hole=0.45, textposition="inside", textinfo="percent+label",
            marker=dict(colors=colors, line=dict(color="white", width=1.5)),
        ))
        fig = _apply_plotly_style(fig, height=360)
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

        if "sector" in holdings.columns:
            sector_alloc = holdings.groupby("sector")["weight"].sum().reset_index().sort_values("weight")
            fig2 = go.Figure(go.Bar(
                x=sector_alloc["weight"], y=sector_alloc["sector"],
                orientation="h",
                marker=dict(color=C_ACCENT, opacity=0.85),
                text=sector_alloc["weight"].apply(lambda x: f"{x:.1f}%"),
                textposition="outside",
            ))
            fig2 = _apply_plotly_style(fig2, height=max(180, len(sector_alloc) * 32 + 40))
            fig2.update_layout(title="Distribucion sectorial", margin=dict(t=36, b=10, l=10, r=40))
            st.plotly_chart(fig2, use_container_width=True)

    with col_list:
        st.markdown("### Posiciones recomendadas")
        for _, row in holdings.iterrows():
            weight  = row.get("weight", 0)
            invested = row.get("invested_eur", amount * weight / 100)
            ret_base = row.get("expected_return_annual", 0)
            ret_min  = row.get("expected_return_annual_min", ret_base - 5)
            ret_max  = row.get("expected_return_annual_max", ret_base + 5)
            reasons  = row.get("reasons", [])
            warnings = row.get("warnings", [])
            sp_prob  = row.get("sp500_inclusion_prob", None)

            with st.expander(f"{row['name']} ({row.get('ticker','')})  —  {weight:.1f}%  ·  €{invested:,.0f}"):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:{C_MUTED};margin-bottom:8px;">'
                        f'Sector: <strong>{row.get("sector","—")}</strong> &nbsp;·&nbsp; Pais: <strong>{row.get("country","—")}</strong>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div style="font-size:0.85rem;margin-bottom:8px;">'
                        f'Rentabilidad anual estimada: '
                        f'<span style="color:{C_RED};font-weight:500;">{ret_min:.1f}%</span>'
                        f' &nbsp;/&nbsp; '
                        f'<span style="color:{C_ACCENT};font-weight:700;">{ret_base:.1f}%</span>'
                        f' &nbsp;/&nbsp; '
                        f'<span style="color:{C_GREEN};font-weight:500;">{ret_max:.1f}%</span>'
                        f'<span style="font-size:0.72rem;color:{C_MUTED};"> (pesimista / base / optimista)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    sp500_member = row.get("sp500_member", False)
                    if sp500_member:
                        st.markdown(f'<div style="font-size:0.82rem;margin-bottom:6px;color:{C_GREEN};">Actualmente en el S&P 500</div>', unsafe_allow_html=True)
                    elif sp_prob is not None and sp_prob > 0:
                        st.markdown(f'<div style="font-size:0.82rem;margin-bottom:6px;">Probabilidad de entrada en S&P 500: <strong>{sp_prob:.0f}%</strong></div>', unsafe_allow_html=True)
                    if reasons:
                        st.markdown(f'<div style="font-size:0.78rem;font-weight:600;color:{C_MUTED};margin-bottom:3px;text-transform:uppercase;letter-spacing:0.6px;">Fundamento</div>', unsafe_allow_html=True)
                        for r in reasons[:3]:
                            st.markdown(f'<div style="font-size:0.82rem;color:{C_TEXT};">— {r}</div>', unsafe_allow_html=True)
                    if warnings:
                        st.markdown(f'<div style="font-size:0.78rem;font-weight:600;color:{C_MUTED};margin:6px 0 3px;text-transform:uppercase;letter-spacing:0.6px;">Consideraciones</div>', unsafe_allow_html=True)
                        for w in warnings[:2]:
                            st.markdown(f'<div style="font-size:0.82rem;color:{C_AMBER};">— {w}</div>', unsafe_allow_html=True)
                with cols[1]:
                    st.metric("Peso", f"{weight:.1f}%")
                    st.metric("Beta", f"{row.get('beta', 1.0):.2f}")

    # ── Proyeccion DCA ────────────────────────────────────────────────────────
    monthly = profile.get("monthly_contribution", 0)
    if monthly and monthly > 0:
        st.markdown("## Proyeccion con aportaciones mensuales")
        ann_ret_est = scenarios.get("base", {}).get("annual_avg", 9) / 100 if scenarios else 0.09
        dca = compute_dca_projection(amount, monthly, ann_ret_est, profile["horizon_years"])

        v_without = f"€{dca['final_without_contributions']:,.0f}"
        v_with    = f"€{dca['final_with_contributions']:,.0f}"
        v_contrib = f"€{dca['total_contributed']:,.0f}"
        v_extra   = f"€{dca['extra_gain']:,.0f}"
        lbl_with  = f"Valor final con +€{monthly:,.0f}/mes"
        st.markdown(
            f'<div class="kpi-row">'
            f'{_kpi("Valor final sin aportaciones", v_without)}'
            f'{_kpi(lbl_with, v_with, "pos")}'
            f'{_kpi("Capital total aportado", v_contrib)}'
            f'{_kpi("Ganancia adicional por DCA", v_extra, "pos")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        months_list = dca["months"]
        fig_dca = go.Figure()
        fig_dca.add_trace(go.Scatter(
            x=months_list, y=dca["values_with"],
            name=f"Con €{monthly:,.0f}/mes",
            line=dict(color=C_GREEN, width=2.5),
            fill="tozeroy", fillcolor="rgba(30,107,69,0.07)",
        ))
        fig_dca.add_trace(go.Scatter(
            x=months_list, y=dca["values_without"],
            name="Solo capital inicial",
            line=dict(color=C_ACCENT, width=2),
        ))
        fig_dca.add_trace(go.Scatter(
            x=months_list, y=dca["capital_invested"],
            name="Capital aportado acumulado",
            line=dict(color=C_GOLD, width=1.5, dash="dot"),
        ))
        fig_dca = _apply_plotly_style(fig_dca, height=360)
        fig_dca.update_layout(
            title=f"Proyeccion a {profile['horizon_label']} — rentabilidad estimada {ann_ret_est*100:.1f}% anual",
            xaxis_title="Meses",
            yaxis_title="Valor (€)",
        )
        st.plotly_chart(fig_dca, use_container_width=True)
        st.markdown(
            f'<div class="disclaimer">Proyeccion orientativa con rentabilidad anual del {ann_ret_est*100:.1f}%. Los resultados reales dependeran de las condiciones de mercado.</div>',
            unsafe_allow_html=True,
        )

    # ── Acciones ─────────────────────────────────────────────────────────────
    st.markdown("## Guardar propuesta")
    col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
    with col_a:
        port_name = st.text_input("Nombre de la cartera", placeholder="p.ej. Cartera tecnologia 2025", label_visibility="collapsed")
    with col_b:
        if st.button("Guardar cartera", type="primary", use_container_width=True):
            pid = save_portfolio(portfolio, profile, name=port_name or "")
            st.session_state.portfolio_accepted = True
            st.session_state.active_portfolio_id = pid
            add_notification("Cartera guardada", f"Cartera guardada con {portfolio['n_holdings']} posiciones (ID: {pid}).", "success")
            st.success(f"Cartera guardada correctamente.")
    with col_c:
        if st.button("Nueva propuesta", use_container_width=True):
            st.session_state.analysis_done = False
            st.rerun()
    with col_d:
        if st.button("Editar perfil", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()

    # ── Tabla de analisis ────────────────────────────────────────────────────
    if not df_scored.empty:
        st.markdown("## Universo analizado — top 20")
        cols_show = ["ticker", "name", "sector", "market_cap_b", "mom_12m",
                     "revenue_growth", "sp500_inclusion_prob", "score"]
        cols_show = [c for c in cols_show if c in df_scored.columns]
        st.dataframe(
            df_scored[cols_show].head(20).rename(columns={
                "ticker": "Ticker", "name": "Empresa", "sector": "Sector",
                "market_cap_b": "Cap. mkt (B€)", "mom_12m": "Mom. 12M (%)",
                "revenue_growth": "Crec. ingresos (%)",
                "sp500_inclusion_prob": "P(S&P 500) %", "score": "Score ML",
            }),
            use_container_width=True, hide_index=True,
        )


# ── Page: Mis carteras ────────────────────────────────────────────────────────

def page_my_portfolios():
    st.markdown("# Mis carteras")

    portfolios = load_portfolios()
    col_new, col_ref = st.columns([3, 1])
    with col_new:
        if st.button("Nueva cartera", type="primary"):
            st.session_state.profile = None
            st.session_state.analysis_done = False
            st.session_state.portfolio = None
            st.session_state.page = "profile"
            st.rerun()
    with col_ref:
        if st.button("Actualizar"):
            st.rerun()

    if not portfolios:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:40px;">No hay carteras guardadas. Crea una nueva a traves del cuestionario de perfil.</div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div class="section-label">{len(portfolios)} cartera(s) guardada(s)</div>', unsafe_allow_html=True)

    for p in reversed(portfolios):
        pid = p["id"]
        name = p.get("name", pid)
        created = p.get("created_at", "")[:10]
        total = p.get("total_invested", 0)
        gain_pct = p.get("expected_return_pct", 0)
        n_hold = p.get("n_holdings", 0)
        risk = p.get("profile", {}).get("risk_score", 5)
        horizon = p.get("profile", {}).get("horizon_label", "")
        port_type = {"stocks": "Acciones", "indices": "Indices", "mixed": "Mixta"}.get(p.get("portfolio_type", ""), "")
        active = st.session_state.active_portfolio_id == pid

        if risk <= 3:
            badge = '<span class="badge badge-cons">Conservadora</span>'
        elif risk <= 6:
            badge = '<span class="badge badge-mod">Moderada</span>'
        else:
            badge = '<span class="badge badge-agg">Agresiva</span>'
        active_badge = '<span class="badge badge-active" style="margin-left:8px;">Activa</span>' if active else ""

        st.markdown(
            f'<div class="port-card {"active" if active else ""}">'
            f'<div class="port-name">{name} {badge}{active_badge}</div>'
            f'<div class="port-meta">'
            f'Creada {created} &nbsp;·&nbsp; {n_hold} posiciones &nbsp;·&nbsp; '
            f'Capital €{total:,.0f} &nbsp;·&nbsp; Rent. base +{gain_pct:.1f}% &nbsp;·&nbsp; '
            f'{port_type} &nbsp;·&nbsp; {horizon}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        with col1:
            new_name = st.text_input("", value=name, key=f"rename_{pid}", label_visibility="collapsed", placeholder="Renombrar...")
            if new_name != name and st.button("Guardar nombre", key=f"save_name_{pid}"):
                rename_portfolio(pid, new_name)
                st.rerun()
        with col2:
            if st.button("Dashboard", key=f"load_{pid}", use_container_width=True):
                full = get_portfolio_by_id(pid)
                if full:
                    st.session_state.portfolio = full
                    st.session_state.profile = full.get("profile", {})
                    st.session_state.active_portfolio_id = pid
                    st.session_state.backtest_result = None
                    st.session_state.page = "dashboard"
                    st.rerun()
        with col3:
            if st.button("Backtesting", key=f"bt_{pid}", use_container_width=True):
                full = get_portfolio_by_id(pid)
                if full:
                    st.session_state.portfolio = full
                    st.session_state.profile = full.get("profile", {})
                    st.session_state.active_portfolio_id = pid
                    st.session_state.backtest_result = None
                    st.session_state.page = "backtest"
                    st.rerun()
        with col4:
            if st.button("Duplicar", key=f"dup_{pid}", use_container_width=True):
                duplicate_portfolio(pid)
                st.rerun()
        with col5:
            if st.button("Eliminar", key=f"del_{pid}", use_container_width=True):
                st.session_state[f"confirm_del_{pid}"] = True

        if st.session_state.get(f"confirm_del_{pid}"):
            st.warning(f"Confirmar eliminacion de '{name}'. Esta accion no se puede deshacer.")
            ca, cb = st.columns(2)
            with ca:
                if st.button("Confirmar eliminacion", key=f"yes_{pid}", type="primary"):
                    delete_portfolio(pid)
                    if st.session_state.active_portfolio_id == pid:
                        st.session_state.active_portfolio_id = None
                        st.session_state.portfolio = None
                    st.session_state.pop(f"confirm_del_{pid}", None)
                    st.rerun()
            with cb:
                if st.button("Cancelar", key=f"no_{pid}"):
                    st.session_state.pop(f"confirm_del_{pid}", None)
                    st.rerun()

        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)


# ── Page: Backtesting ─────────────────────────────────────────────────────────

def page_backtest():
    portfolio = st.session_state.portfolio
    profile   = st.session_state.profile

    if portfolio is None:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:40px;">Carga una cartera desde "Mis carteras" para ejecutar el backtesting.</div>', unsafe_allow_html=True)
        if st.button("Ir a Mis carteras"):
            st.session_state.page = "my_portfolios"
            st.rerun()
        return

    port_name = "Cartera activa"
    if st.session_state.active_portfolio_id:
        match = next((p for p in load_portfolios() if p["id"] == st.session_state.active_portfolio_id), None)
        if match:
            port_name = match.get("name", port_name)

    st.markdown(f"# Backtesting — {port_name}")
    st.markdown('<div style="color:#5c6475;font-size:0.9rem;margin:-12px 0 20px;">Simulacion historica del rendimiento de la cartera sobre datos de mercado reales.</div>', unsafe_allow_html=True)

    st.markdown("### Parametros del analisis")
    col1, col2, col3 = st.columns(3)
    today = date.today()
    presets = {
        "Ultimo ano":          (today - timedelta(days=365),  today),
        "Ultimos 2 anos":      (today - timedelta(days=730),  today),
        "Ultimos 3 anos":      (today - timedelta(days=1095), today),
        "Ultimos 5 anos":      (today - timedelta(days=1825), today),
        "Desde 2020 (COVID)":  (date(2020, 1, 1),             today),
        "Personalizado":       None,
    }
    with col1:
        preset = st.selectbox("Periodo", list(presets.keys()), index=0)

    if preset == "Personalizado":
        with col2:
            start_date = st.date_input("Inicio", value=today - timedelta(days=730), max_value=today - timedelta(days=60))
        with col3:
            end_date = st.date_input("Fin", value=today, max_value=today)
    else:
        start_date, end_date = presets[preset]
        with col2:
            st.date_input("Inicio", value=start_date, disabled=True)
        with col3:
            st.date_input("Fin", value=end_date, disabled=True)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date,   datetime.min.time())

    monthly_from_profile = profile.get("monthly_contribution", 0) if profile else 0
    st.markdown("### Aportaciones periodicas (DCA)")
    col_t, col_n = st.columns([1, 2])
    with col_t:
        use_dca = st.toggle("Incluir aportaciones mensuales", value=bool(monthly_from_profile))
    bt_monthly = 0
    if use_dca:
        with col_n:
            bt_monthly = st.number_input(
                "Aportacion mensual (€)",
                min_value=50, max_value=100_000,
                value=int(monthly_from_profile) if monthly_from_profile else 200,
                step=50, label_visibility="collapsed",
            )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if st.button("Ejecutar backtesting", type="primary", use_container_width=True):
        with st.spinner("Descargando datos historicos y calculando metricas..."):
            result = run_backtest(portfolio, start_dt, end_dt, monthly_contribution=bt_monthly)
            st.session_state.backtest_result = result

    result = st.session_state.backtest_result
    if result is None:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:32px;">Configure los parametros y ejecute el backtesting.</div>', unsafe_allow_html=True)
        return
    if "error" in result:
        st.error(result["error"])
        return

    _render_backtest_results(result, portfolio)


def _render_backtest_results(result: dict, portfolio: dict):
    metrics = result["metrics"]
    capital = result["total_invested"]
    missing = result.get("missing_tickers", [])
    available = result.get("available_tickers", [])

    if missing:
        st.info(f"Sin datos para: {', '.join(missing)}. El analisis utiliza los {len(available)} tickers disponibles.")

    m = metrics
    total_ret = m.get("total_return_pct", 0)
    ann_ret   = m.get("annualized_return_pct", 0)
    ann_vol   = m.get("annualized_volatility_pct", 0)
    sharpe    = m.get("sharpe_ratio", 0)
    sortino   = m.get("sortino_ratio", 0)
    max_dd    = m.get("max_drawdown_pct", 0)
    win_rate  = m.get("win_rate_pct", 0)
    var95     = m.get("var_95_pct", 0)
    final_val = m.get("final_value", capital)
    profit    = m.get("profit", 0)
    beta      = m.get("beta")
    alpha     = m.get("alpha_pct")

    st.markdown("## Resultados del periodo")
    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Rentabilidad total", f"{total_ret:+.2f}%", "pos" if total_ret >= 0 else "neg")}'
        f'{_kpi("Rentabilidad anualizada", f"{ann_ret:+.2f}%", "pos" if ann_ret >= 0 else "neg")}'
        f'{_kpi("Valor final", f"€{final_val:,.0f}")}'
        f'{_kpi("Ganancia / Perdida", f"€{profit:+,.0f}", "pos" if profit >= 0 else "neg")}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Sharpe ratio", f"{sharpe:.2f}", "pos" if sharpe >= 1 else "neutral" if sharpe >= 0.5 else "neg")}'
        f'{_kpi("Max. Drawdown", f"{max_dd:.1f}%", "neg" if max_dd < -20 else "neutral" if max_dd < -10 else "pos")}'
        f'{_kpi("Volatilidad anualizada", f"{ann_vol:.1f}%")}'
        f'{_kpi("Dias positivos", f"{win_rate:.0f}%")}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if beta is not None or alpha is not None:
        row = ""
        if beta is not None:
            row += _kpi("Beta vs S&P 500", f"{beta:.2f}")
        if alpha is not None:
            row += _kpi("Alpha anualizado", f"{alpha:+.2f}%", "pos" if alpha >= 0 else "neg")
        row += _kpi("Sortino ratio", f"{sortino:.2f}")
        row += _kpi("VaR diario 95%", f"{var95:.2f}%")
        st.markdown(f'<div class="kpi-row">{row}</div>', unsafe_allow_html=True)

    _render_backtest_interpretation(metrics)

    st.markdown("## Graficos de rendimiento")
    has_dca = result.get("monthly_contribution", 0) > 0
    tab_names = ["Evolucion del valor", "Rentabilidad acumulada", "Drawdown", "Calendario mensual", "Sharpe movil"]
    if has_dca:
        tab_names.insert(1, "Analisis DCA")
    tabs = st.tabs(tab_names)
    idx = 0

    with tabs[idx]:
        fig = chart_portfolio_value(result)
        fig = _apply_plotly_style(fig, height=420)
        st.plotly_chart(fig, use_container_width=True)
    idx += 1

    if has_dca:
        with tabs[idx]:
            _render_dca_backtest_tab(result)
        idx += 1

    with tabs[idx]:
        fig = chart_returns_comparison(result)
        fig = _apply_plotly_style(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)
    idx += 1

    with tabs[idx]:
        fig = chart_drawdown(result)
        fig = _apply_plotly_style(fig, height=280)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f'<div style="font-size:0.8rem;color:{C_MUTED};">Caida maxima: {max_dd:.1f}%  ·  {m.get("n_trading_days",0)} dias de cotizacion analizados</div>', unsafe_allow_html=True)
    idx += 1

    with tabs[idx]:
        fig = chart_monthly_heatmap(result)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requiere al menos un mes de datos para generar el calendario.")
    idx += 1

    with tabs[idx]:
        fig = chart_rolling_sharpe(result)
        if fig.data:
            fig = _apply_plotly_style(fig, height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Se requieren al menos 3 meses de datos para el Sharpe movil.")


def _render_dca_backtest_tab(result: dict):
    md = result.get("metrics_dca", {})
    mb = result.get("metrics", {})
    monthly = result.get("monthly_contribution", 0)
    capital = result.get("total_invested", 0)

    if not md:
        st.info("No hay datos de aportaciones disponibles.")
        return

    st.markdown(f"### Sin aportaciones vs. con €{monthly:,.0f}/mes")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="section-label">Sin aportaciones</div>', unsafe_allow_html=True)
        st.metric("Capital inicial", f"€{capital:,.0f}")
        st.metric("Valor final", f"€{mb.get('final_value', 0):,.0f}")
        st.metric("Ganancia", f"€{mb.get('profit', 0):+,.0f}", delta=f"{mb.get('total_return_pct', 0):+.2f}%")
        st.metric("Max. Drawdown", f"{mb.get('max_drawdown_pct', 0):.1f}%")
    with col2:
        st.markdown(f'<div class="section-label">Con +€{monthly:,.0f}/mes (DCA)</div>', unsafe_allow_html=True)
        st.metric("Capital total aportado", f"€{md.get('total_contributed', 0):,.0f}")
        st.metric("Valor final", f"€{md.get('final_value', 0):,.0f}")
        gain = md.get("gain", 0)
        gain_pct = md.get("gain_pct", 0)
        st.metric("Ganancia sobre lo invertido", f"€{gain:+,.0f}", delta=f"{gain_pct:+.2f}%")
        st.metric("Max. Drawdown", f"{md.get('max_drawdown_pct', 0):.1f}%")

    extra = md.get("final_value", 0) - mb.get("final_value", 0)
    n_days = result.get("metrics", {}).get("n_trading_days", 252)
    pure_contrib = monthly * (n_days / 21)
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Valor adicional gracias al DCA", f"€{extra:,.0f}", "pos" if extra >= 0 else "neg")}'
        f'{_kpi("Rentabilidad de las aportaciones", f"€{(extra - pure_contrib):+,.0f}", "pos" if extra > pure_contrib else "neutral")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    fig = chart_dca_comparison(result)
    if fig:
        fig = _apply_plotly_style(fig, height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'<div class="disclaimer">Las aportaciones de €{monthly:,.0f}/mes habrian generado €{gain:,.0f} de ganancia '
        f'sobre el total invertido ({gain_pct:.1f}%). La inversion periodica reduce el impacto de la volatilidad '
        f'al promediar el precio de compra a lo largo del tiempo.</div>',
        unsafe_allow_html=True,
    )


def _render_backtest_interpretation(metrics: dict):
    total_ret = metrics.get("total_return_pct", 0)
    sharpe    = metrics.get("sharpe_ratio", 0)
    max_dd    = metrics.get("max_drawdown_pct", 0)
    alpha     = metrics.get("alpha_pct")

    lines = []
    if total_ret >= 20:
        lines.append(f"La cartera habria registrado un rendimiento de {total_ret:.1f}% en el periodo analizado, situandose por encima de la media historica del mercado.")
    elif total_ret >= 5:
        lines.append(f"La cartera habria generado una rentabilidad positiva del {total_ret:.1f}% en el periodo seleccionado.")
    elif total_ret >= 0:
        lines.append(f"La cartera habria terminado el periodo con una rentabilidad marginal del {total_ret:.1f}%.")
    else:
        lines.append(f"La cartera habria registrado una perdida del {abs(total_ret):.1f}% en este periodo.")

    if sharpe >= 1.5:
        lines.append(f"El Sharpe ratio de {sharpe:.2f} es destacado, indicando una solida compensacion del riesgo asumido.")
    elif sharpe >= 0.8:
        lines.append(f"El Sharpe ratio de {sharpe:.2f} es razonable, con una relacion riesgo-rentabilidad aceptable.")
    elif sharpe >= 0:
        lines.append(f"El Sharpe ratio de {sharpe:.2f} es bajo. La rentabilidad no compensa suficientemente el riesgo.")
    else:
        lines.append(f"El Sharpe ratio negativo ({sharpe:.2f}) indica que la cartera habria rendido por debajo del activo libre de riesgo.")

    if max_dd > -10:
        lines.append(f"La caida maxima registrada ({max_dd:.1f}%) es moderada y dentro de parametros controlados.")
    elif max_dd > -25:
        lines.append(f"La caida maxima de {max_dd:.1f}% es relevante. En ese punto, el inversor habria experimentado una reduccion significativa del capital.")
    else:
        lines.append(f"La caida maxima de {max_dd:.1f}% es severa, lo que habria requerido una tolerancia al riesgo elevada para mantener la inversion.")

    if alpha is not None:
        if alpha > 3:
            lines.append(f"El alpha de +{alpha:.1f}% anual confirma que la cartera habria superado al S&P 500 ajustado por riesgo.")
        elif alpha > 0:
            lines.append(f"La cartera habria generado un alpha positivo ({alpha:+.1f}%), batiendo ligeramente al mercado de referencia.")
        else:
            lines.append(f"El alpha negativo ({alpha:.1f}%) indica que el S&P 500 habria superado a esta cartera en terminos ajustados por riesgo.")

    with st.expander("Interpretacion del analisis", expanded=True):
        for line in lines:
            st.markdown(f'<div style="font-size:0.87rem;color:{C_TEXT};padding:3px 0;border-bottom:1px solid {C_BORDER};margin-bottom:6px;">— {line}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="disclaimer" style="margin-top:8px;">El rendimiento historico no garantiza resultados futuros. '
            f'El backtesting refleja como habria evolucionado la cartera bajo condiciones de mercado ya conocidas.</div>',
            unsafe_allow_html=True,
        )


def _render_live_chart(portfolio: dict, portfolio_meta: dict):
    """
    Grafico de seguimiento en vivo desde la fecha de creacion de la cartera.
    Descarga precios reales y calcula el valor actual de la cartera.
    """
    created_at  = portfolio_meta.get("created_at", "")
    amount      = portfolio.get("total_invested", 0)
    holdings    = portfolio.get("holdings", pd.DataFrame())

    if holdings.empty or not created_at:
        st.info("No hay datos suficientes para mostrar el seguimiento en vivo.")
        return

    with st.spinner("Descargando precios actuales..."):
        live = get_live_portfolio_performance(holdings, created_at, amount)

    if "error" in live:
        days = live.get("days", 0)
        if days < 1:
            st.markdown(
                f'<div class="inv-card" style="text-align:center;padding:32px;color:{C_MUTED};">'
                f'<div style="font-size:1rem;font-weight:600;color:{C_NAVY};margin-bottom:8px;">Cartera creada hoy</div>'
                f'<div style="font-size:0.87rem;">Vuelve manana para ver el rendimiento en vivo. '
                f'El mercado necesita al menos una sesion de cotizacion para generar datos.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.error(live["error"])
        return

    total_ret  = live["total_return_pct"]
    profit     = live["profit"]
    current    = live["current_value"]
    days       = live["days_tracked"]
    best_day   = live["best_day_pct"]
    worst_day  = live["worst_day_pct"]
    pos_days   = live["positive_days"]
    total_days = live["total_days"]
    start_date = live["start_date"]

    # KPIs
    ret_cls = "pos" if total_ret >= 0 else "neg"
    pnl_cls = "pos" if profit >= 0 else "neg"
    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Valor actual", f"€{current:,.0f}", ret_cls)}'
        f'{_kpi("Ganancia / Perdida", f"€{profit:+,.0f}", pnl_cls)}'
        f'{_kpi("Rentabilidad acumulada", f"{total_ret:+.2f}%", ret_cls)}'
        f'{_kpi("Dias seguidos", str(days))}'
        f'{_kpi("Mejor sesion", f"{best_day:+.2f}%", "pos")}'
        f'{_kpi("Peor sesion", f"{worst_day:+.2f}%", "neg")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Grafico de valor en vivo
    pv = live["port_value"]
    if not pv.empty and len(pv) > 1:
        color_line = "#1e6b45" if total_ret >= 0 else "#8b2635"
        fill_color = "rgba(30,107,69,0.07)" if total_ret >= 0 else "rgba(139,38,53,0.07)"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pv.index, y=pv.values,
            name="Mi cartera",
            line=dict(color=color_line, width=2.5),
            fill="tozeroy", fillcolor=fill_color,
        ))
        fig.add_hline(
            y=amount, line_dash="dash", line_color="#aaa", line_width=1,
            annotation_text=f"Capital inicial €{amount:,.0f}",
            annotation_position="bottom right",
        )
        fig = _apply_plotly_style(fig, height=380)
        fig.update_layout(
            title=dict(
                text=f"Rendimiento en vivo desde {start_date.strftime('%d/%m/%Y')}",
                x=0, xanchor="left",
            ),
            yaxis_title="Valor (€)",
            showlegend=False,
            margin=dict(t=40, b=30, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Grafico de retorno diario
        dr = live["port_daily_ret"] * 100
        bar_colors = [("#1e6b45" if v >= 0 else "#8b2635") for v in dr.values]
        fig2 = go.Figure(go.Bar(
            x=dr.index, y=dr.values,
            marker_color=bar_colors,
            name="Retorno diario",
        ))
        fig2 = _apply_plotly_style(fig2, height=200)
        fig2.update_layout(
            title=dict(text="Retorno diario (%)", x=0, xanchor="left"),
            yaxis_title="%",
            showlegend=False,
            margin=dict(t=36, b=20, l=10, r=10),
        )
        fig2.add_hline(y=0, line_color="#aaa", line_width=1)
        st.plotly_chart(fig2, use_container_width=True)

        win_rate = pos_days / total_days * 100 if total_days > 0 else 0
        st.markdown(
            f'<div class="disclaimer">'
            f'Seguimiento desde {start_date.strftime("%d/%m/%Y")} · '
            f'{total_days} sesiones de mercado · '
            f'{pos_days} dias positivos ({win_rate:.0f}% del total) · '
            f'Datos con retraso habitual de mercado.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No hay suficientes sesiones de mercado para mostrar el grafico. Vuelve en uno o dos dias habiles.")


# ── Page: Dashboard ───────────────────────────────────────────────────────────

def page_dashboard():
    portfolio = st.session_state.portfolio
    profile   = st.session_state.profile

    if portfolio is None or profile is None:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:40px;">Carga una cartera desde "Mis carteras" para acceder al dashboard.</div>', unsafe_allow_html=True)
        if st.button("Ir a Mis carteras"):
            st.session_state.page = "my_portfolios"
            st.rerun()
        return

    holdings = portfolio["holdings"]
    amount   = portfolio["total_invested"]
    port_name = "Cartera activa"
    if st.session_state.active_portfolio_id:
        match = next((p for p in load_portfolios() if p["id"] == st.session_state.active_portfolio_id), None)
        if match:
            port_name = match.get("name", port_name)

    st.markdown(f"# Dashboard — {port_name}")

    gain_str = f"€{portfolio['total_expected_gain']:,.0f}"
    ret_str  = f"+{portfolio['expected_return_pct']:.1f}%"
    n_str    = str(portfolio['n_holdings'])
    st.markdown(
        f'<div class="kpi-row">'
        f'{_kpi("Capital invertido", f"€{amount:,.0f}")}'
        f'{_kpi("Ganancia base esperada", gain_str, "pos")}'
        f'{_kpi("Rentabilidad base", ret_str, "pos")}'
        f'{_kpi("Posiciones", n_str)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    tickers = [t for t in holdings["ticker"].tolist() if t and len(t) <= 6][:6]
    if tickers:
        st.markdown("## Evolucion relativa — ultimos 12 meses")
        price_data = {}
        for t in tickers:
            hist = get_price_history(t, years=1)
            if not hist.empty:
                col = hist.columns[0]
                price_data[t] = hist[col] / hist[col].iloc[0] * 100

        if price_data:
            palette = [C_ACCENT, C_GREEN, C_GOLD, "#6aa3e4", "#9b59b6", "#e67e22"]
            fig = go.Figure()
            for i, (t, series) in enumerate(price_data.items()):
                name_row = holdings[holdings["ticker"] == t]
                display  = name_row.iloc[0]["name"] if not name_row.empty else t
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values, name=display, mode="lines",
                    line=dict(color=palette[i % len(palette)], width=1.8),
                ))
            fig.add_hline(y=100, line_dash="dash", line_color=C_BORDER, line_width=1)
            fig = _apply_plotly_style(fig, height=400)
            fig.update_layout(title="Rendimiento relativo (base 100)", yaxis_title="Indice (base 100)")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("## Posiciones actuales")
    show_cols = ["ticker", "name", "sector", "weight", "invested_eur", "expected_return_annual", "beta"]
    show_cols = [c for c in show_cols if c in holdings.columns]
    st.dataframe(
        holdings[show_cols].rename(columns={
            "ticker": "Ticker", "name": "Empresa", "sector": "Sector",
            "weight": "Peso (%)", "invested_eur": "Capital (€)",
            "expected_return_annual": "Rent. base anual (%)", "beta": "Beta",
        }),
        use_container_width=True, hide_index=True,
    )

    # ── Seguimiento en vivo ───────────────────────────────────────────────────
    st.markdown("## Seguimiento en vivo")
    st.markdown(
        f'<div style="font-size:0.85rem;color:{C_MUTED};margin:-8px 0 16px;">'
        f'Rendimiento real de la cartera desde su fecha de creacion, basado en precios de mercado actuales.'
        f'</div>',
        unsafe_allow_html=True,
    )

    portfolio_meta = {}
    if st.session_state.active_portfolio_id:
        all_saved = load_portfolios()
        portfolio_meta = next((p for p in all_saved if p["id"] == st.session_state.active_portfolio_id), {})

    if portfolio_meta:
        col_ref, _ = st.columns([1, 3])
        with col_ref:
            if st.button("Actualizar datos en vivo", use_container_width=True):
                st.rerun()
        _render_live_chart(portfolio, portfolio_meta)
    else:
        st.info("Guarda la cartera en 'Mis carteras' para activar el seguimiento en vivo.")

    st.divider()
    col_bt, col_geo = st.columns(2)
    with col_bt:
        if st.button("Ir a Backtesting", use_container_width=True):
            st.session_state.backtest_result = None
            st.session_state.page = "backtest"
            st.rerun()
    with col_geo:
        if st.button("Ver riesgo geopolitico", use_container_width=True):
            st.session_state.page = "geo"
            st.rerun()

    st.markdown("## Notas del gestor")
    for tip in generate_periodic_advice(portfolio, profile):
        st.markdown(
            f'<div class="notif-entry info" style="border-left-color:{C_ACCENT};">{tip}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("## Alertas de mercado")
    if st.button("Verificar alertas ahora", use_container_width=True):
        with st.spinner("Consultando precios recientes..."):
            alerts = check_portfolio_alerts(portfolio)
        if alerts:
            for a in alerts:
                level_color = C_RED if a["type"] == "drop" else C_GREEN
                direction = "Caida" if a["type"] == "drop" else "Subida"
                st.markdown(
                    f'<div class="notif-entry {"warning" if a["type"]=="drop" else "success"}">'
                    f'<strong>{direction} relevante — {a["name"]}</strong><br>'
                    f'<span style="font-size:0.85rem;">{a["message"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No se detectan alertas significativas en las posiciones actuales.")


# ── Page: Geo ─────────────────────────────────────────────────────────────────

def page_geo():
    portfolio = st.session_state.portfolio
    profile   = st.session_state.profile

    if portfolio is None:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:40px;">Carga una cartera para analizar el riesgo geopolitico.</div>', unsafe_allow_html=True)
        return

    st.markdown("# Riesgo Geopolitico")
    st.markdown('<div style="color:#5c6475;font-size:0.9rem;margin:-12px 0 20px;">Analisis en tiempo real del impacto de eventos geopoliticos sobre tu cartera, basado en la base de datos GDELT.</div>', unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_geo = st.button("Actualizar analisis", type="primary", use_container_width=True)
    with col_info:
        st.markdown(
            f'<div style="font-size:0.8rem;color:{C_MUTED};padding-top:8px;">'
            f'Tiempo estimado: 5-8 segundos. Titulares en tiempo real de Google News.'
            f'</div>',
            unsafe_allow_html=True,
        )

    if run_geo:
        with st.spinner("Consultando fuentes de noticias globales en paralelo..."):
            geo_data   = get_portfolio_geopolitical_impact(portfolio["holdings"], profile)
            global_map = get_global_risk_map()
            st.session_state.geo_risk = {"portfolio": geo_data, "global": global_map}

    if st.session_state.geo_risk:
        geo_data   = st.session_state.geo_risk["portfolio"]
        global_map = st.session_state.geo_risk.get("global", {})


        col1, col2 = st.columns([1, 2])
        with col1:
            risk_level = geo_data["overall_risk_level"]
            risk_label = geo_data["overall_risk_label"]
            color      = geo_data["overall_color"]
            st.markdown(
                f'<div style="background:{color};padding:24px;border-radius:8px;text-align:center;color:white;">'
                f'<div style="font-size:0.7rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;opacity:0.85;margin-bottom:8px;">Riesgo global de cartera</div>'
                f'<div style="font-size:2rem;font-weight:700;">{risk_label}</div>'
                f'<div style="font-size:0.85rem;opacity:0.85;margin-top:4px;">Nivel {risk_level:.1f} / 5</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="inv-card" style="font-size:0.85rem;line-height:1.6;">{geo_data.get("recommendation","")}</div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown("### Exposicion sectorial al riesgo")
            for sector, data in geo_data.get("sector_risks", {}).items():
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f'<div style="font-size:0.87rem;font-weight:600;color:{C_NAVY};">{sector}</div>', unsafe_allow_html=True)
                    headlines = data.get("headlines", [])
                    if headlines:
                        st.markdown(f'<div style="font-size:0.77rem;color:{C_MUTED};">{headlines[0]["title"][:110]}</div>', unsafe_allow_html=True)
                with col_b:
                    c = data.get("color", "#95a5a6")
                    l = data.get("risk_label", "N/D")
                    st.markdown(f'<div style="background:{c};color:white;padding:3px 10px;border-radius:4px;font-size:0.72rem;font-weight:600;text-align:center;margin-top:2px;">{l}</div>', unsafe_allow_html=True)
                st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

        if global_map:
            st.markdown("## Riesgo por region geografica")
            regions    = list(global_map.keys())
            risk_vals  = [global_map[r]["risk_level"] for r in regions]
            risk_colors = [global_map[r]["color"] for r in regions]
            fig = go.Figure(go.Bar(
                x=regions, y=risk_vals,
                marker_color=risk_colors,
                text=[global_map[r]["risk_label"] for r in regions],
                textposition="outside",
            ))
            fig = _apply_plotly_style(fig, height=320)
            fig.update_layout(
                title="Nivel de riesgo geopolitico por region (0 = minimo · 5 = critico)",
                yaxis=dict(range=[0, 6]),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:32px;">Haz clic en "Actualizar analisis" para obtener datos en tiempo real.</div>', unsafe_allow_html=True)


# ── Page: Notifications ───────────────────────────────────────────────────────

def page_notifications():
    st.markdown("# Centro de notificaciones")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Marcar todas como leidas"):
            mark_all_read()
            st.rerun()
    with col2:
        if st.button("Eliminar todas", type="secondary"):
            clear_notifications()
            st.rerun()

    notifs = get_notifications()
    if not notifs:
        st.markdown('<div class="inv-card" style="text-align:center;color:#5c6475;padding:40px;">No hay notificaciones.</div>', unsafe_allow_html=True)
        return

    unread_count = sum(1 for n in notifs if not n["read"])
    if unread_count:
        st.markdown(f'<div style="font-size:0.82rem;color:{C_MUTED};margin-bottom:8px;">{unread_count} sin leer &nbsp;·&nbsp; {len(notifs)} en total</div>', unsafe_allow_html=True)

    for n in notifs:
        lvl  = n.get("level", "info")
        ts   = n.get("timestamp", "")[:16].replace("T", " ")
        bold = "font-weight:600;" if not n["read"] else ""
        st.markdown(
            f'<div class="notif-entry {lvl}">'
            f'<span class="notif-ts">{ts}</span>'
            f'<div style="{bold}font-size:0.87rem;margin-bottom:3px;">{n["title"]}</div>'
            f'<div style="font-size:0.82rem;color:{C_MUTED};">{n["message"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    _init_state()
    _sidebar()

    page = st.session_state.page
    dispatch = {
        "home":         page_home,
        "profile":      page_profile,
        "analysis":     page_analysis,
        "my_portfolios":page_my_portfolios,
        "backtest":     page_backtest,
        "dashboard":    page_dashboard,
        "geo":          page_geo,
        "notifications":page_notifications,
    }
    dispatch.get(page, page_home)()


if __name__ == "__main__":
    main()
