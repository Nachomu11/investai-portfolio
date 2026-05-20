import streamlit as st

SECTORS = [
    "Tecnología", "Salud", "Finanzas", "Energía", "Consumo discrecional",
    "Consumo básico", "Industria", "Materiales", "Servicios públicos",
    "Inmobiliario", "Telecomunicaciones", "Defensa & Aeroespacial",
    "Semiconductores", "Inteligencia Artificial", "Energías renovables",
]

INDICES = [
    "S&P 500 (EE.UU., grandes empresas)",
    "MSCI World (global, mercados desarrollados)",
    "MSCI Emerging Markets (mercados emergentes)",
    "NASDAQ 100 (tecnología EE.UU.)",
    "Euro Stoxx 50 (Europa)",
    "IBEX 35 (España)",
]

SPECIFIC_STOCKS = [
    "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Amazon (AMZN)",
    "Alphabet (GOOGL)", "Meta (META)", "Tesla (TSLA)", "Berkshire Hathaway (BRK-B)",
    "LVMH (MC.PA)", "Novo Nordisk (NVO)", "ASML (ASML)", "Samsung (005930.KS)",
    "Taiwan Semiconductor (TSM)", "Eli Lilly (LLY)", "JPMorgan (JPM)",
    "Ninguna en particular",
]

IBEX35_STOCKS = [
    "Banco Santander (SAN.MC)", "BBVA (BBVA.MC)", "Inditex (ITX.MC)",
    "Iberdrola (IBE.MC)", "Repsol (REP.MC)", "Telefónica (TEF.MC)",
    "Amadeus IT (AMS.MC)", "CaixaBank (CABK.MC)", "Bankinter (BKT.MC)",
    "Banco Sabadell (SAB.MC)", "Endesa (ELE.MC)", "Enagás (ENG.MC)",
    "Ferrovial (FER.MC)", "ACS (ACS.MC)", "Acciona (ANA.MC)",
    "AENA (AENA.MC)", "Cellnex Telecom (CLNX.MC)", "Grifols (GRF.MC)",
    "IAG (IAG.MC)", "Indra (IDR.MC)", "Logista (LOG.MC)",
    "Mapfre (MAP.MC)", "Merlin Properties (MRL.MC)", "Naturgy (NTGY.MC)",
    "PharmaMar (PHM.MC)", "Redeia (RED.MC)", "Sacyr (SCYR.MC)",
    "Solaria (SOL.MC)", "Unicaja (UNI.MC)", "Viscofan (VIS.MC)",
    "Acerinox (ACX.MC)", "Colonial (COL.MC)", "Fluidra (FDR.MC)",
    "Meliá Hotels (MEL.MC)", "Almirall (ALM.MC)",
    "Ninguna en particular",
]

SP500_STOCKS = [
    "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Amazon (AMZN)",
    "Alphabet (GOOGL)", "Meta (META)", "Tesla (TSLA)", "Berkshire Hathaway (BRK-B)",
    "JPMorgan (JPM)", "Eli Lilly (LLY)", "Exxon Mobil (XOM)", "UnitedHealth (UNH)",
    "Visa (V)", "Procter & Gamble (PG)", "Mastercard (MA)", "Johnson & Johnson (JNJ)",
    "Home Depot (HD)", "Chevron (CVX)", "Costco (COST)", "AbbVie (ABBV)",
    "Merck (MRK)", "Netflix (NFLX)", "Salesforce (CRM)", "Oracle (ORCL)",
    "Goldman Sachs (GS)", "Boeing (BA)", "Walt Disney (DIS)", "Caterpillar (CAT)",
    "AMD (AMD)", "Palantir (PLTR)",
    "Ninguna en particular",
]

NASDAQ100_STOCKS = [
    "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Amazon (AMZN)",
    "Alphabet (GOOGL)", "Meta (META)", "Tesla (TSLA)", "Broadcom (AVGO)",
    "Costco (COST)", "Netflix (NFLX)", "AMD (AMD)", "Adobe (ADBE)",
    "Qualcomm (QCOM)", "Intel (INTC)", "Cisco (CSCO)", "Texas Instruments (TXN)",
    "Micron Technology (MU)", "Intuit (INTU)", "Booking Holdings (BKNG)",
    "Palo Alto Networks (PANW)", "Vertex Pharma (VRTX)", "Lam Research (LRCX)",
    "CrowdStrike (CRWD)", "Fortinet (FTNT)", "ADP (ADP)", "Airbnb (ABNB)",
    "Workday (WDAY)", "Datadog (DDOG)", "Gilead Sciences (GILD)", "ARM Holdings (ARM)",
    "Ninguna en particular",
]

EUROSTOXX50_STOCKS = [
    "ASML (ASML.AS)", "LVMH (MC.PA)", "SAP (SAP.DE)", "Siemens (SIE.DE)",
    "TotalEnergies (TTE.PA)", "ENEL (ENEL.MI)", "BNP Paribas (BNP.PA)",
    "AXA (AXA.PA)", "Schneider Electric (SU.PA)", "Airbus (AIR.PA)",
    "Deutsche Telekom (DTE.DE)", "Allianz (ALV.DE)", "Air Liquide (AI.PA)",
    "L'Oréal (OR.PA)", "Philips (PHIA.AS)", "Hermès (RMS.PA)",
    "Mercedes-Benz (MBG.DE)", "Munich Re (MUV2.DE)", "ING (ING.AS)",
    "Bayer (BAYN.DE)", "BASF (BAS.DE)", "BMW (BMW.DE)",
    "Infineon (IFX.DE)", "Adidas (ADS.DE)", "ENI (ENI.MI)",
    "Merck KGaA (MRK.DE)", "Deutsche Börse (DB1.DE)", "Prosus (PRX.AS)",
    "Saint-Gobain (SGO.PA)", "Ahold Delhaize (AD.AS)",
    "Ninguna en particular",
]


def _stocks_for_markets(market_filter: list) -> list:
    """Devuelve la lista de empresas disponibles según los mercados seleccionados."""
    active = [m for m in market_filter if "Cualquier" not in m]
    if not active:
        return SPECIFIC_STOCKS

    pool = set()
    for m in active:
        if "IBEX" in m:
            pool.update(IBEX35_STOCKS)
        if "S&P 500" in m:
            pool.update(SP500_STOCKS)
        if "NASDAQ" in m:
            pool.update(NASDAQ100_STOCKS)
        if "Euro Stoxx" in m:
            pool.update(EUROSTOXX50_STOCKS)

    result = sorted(s for s in pool if s != "Ninguna en particular")
    result.append("Ninguna en particular")
    return result


def _info(label: str, content: str):
    with st.expander(f"ℹ️ {label}"):
        st.markdown(content)


def render_profile_form() -> dict | None:
    st.markdown("## Cuestionario de perfil de inversor")
    st.markdown(
        "Complete el siguiente cuestionario para que el sistema pueda generar "
        "una propuesta de cartera ajustada a sus objetivos y tolerancia al riesgo."
    )

    # ── 1. Datos generales ───────────────────────────────────────────────────────
    st.markdown("### 1. Datos generales de la inversión")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input(
            "¿Cuánto dinero deseas invertir inicialmente? (€)",
            min_value=500,
            max_value=10_000_000,
            value=10_000,
            step=500,
            key="pf_amount",
        )
    with col2:
        horizon = st.selectbox(
            "¿En qué plazo deseas ver resultados?",
            [
                "Corto plazo (< 1 año)",
                "Medio plazo (1-3 años)",
                "Largo plazo (3-7 años)",
                "Muy largo plazo (> 7 años)",
            ],
            index=1,
            key="pf_horizon",
        )

    _info("¿Cómo afecta el horizonte temporal?", """
**Corto plazo (< 1 año):** Mayor peso en activos defensivos y líquidos. El riesgo de pérdida es elevado ya que no hay tiempo de recuperación ante caídas del mercado.

**Medio plazo (1-3 años):** Equilibrio entre seguridad y crecimiento. Se pueden incluir acciones con menor volatilidad y algo de renta fija.

**Largo plazo (3-7 años):** La diversificación reduce el riesgo con el tiempo. Históricamente los mercados se recuperan de caídas en este período.

**Muy largo plazo (> 7 años):** Los mercados globales diversificados siempre han recuperado y superado sus máximos históricos en plazos largos. Mayor tolerancia a la volatilidad a corto plazo.
""")

    st.markdown("#### Aportaciones periódicas (opcional)")
    st.markdown(
        "Invertir una cantidad fija cada mes — conocido como *Dollar-Cost Averaging* (DCA) — "
        "reduce el impacto de la volatilidad y acelera el crecimiento de tu cartera a largo plazo. "
        "Escribe **0** si no quieres hacer aportaciones."
    )
    col3, col4 = st.columns([1, 2])
    with col3:
        monthly_contribution = st.number_input(
            "Aportación mensual (€)",
            min_value=0,
            max_value=100_000,
            value=200,
            step=50,
            help="Pon 0 si no quieres hacer aportaciones periódicas.",
            key="pf_monthly",
        )
    with col4:
        if monthly_contribution > 0:
            horizon_months_map = {
                "Corto plazo (< 1 año)": 6,
                "Medio plazo (1-3 años)": 24,
                "Largo plazo (3-7 años)": 60,
                "Muy largo plazo (> 7 años)": 120,
            }
            horizon_months = horizon_months_map.get(horizon, 24)
            yearly = monthly_contribution * 12
            total_horizon = monthly_contribution * horizon_months
            st.markdown("")
            st.markdown("")
            st.info(
                f"**€{monthly_contribution:,.0f}/mes** → €{yearly:,.0f}/año  \n"
                f"Total aportado en tu horizonte: **€{total_horizon:,.0f}**"
            )

    # ── 2. Tolerancia al riesgo ──────────────────────────────────────────────────
    st.markdown("### 2. Tolerancia al riesgo")
    risk_raw = st.slider(
        "¿Cómo describes tu tolerancia al riesgo?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 = muy conservador (prefiero seguridad), 10 = muy agresivo (busco máxima rentabilidad)",
        key="pf_risk",
    )
    risk_labels = {
        (1, 3): "Conservador — priorizas preservar el capital sobre crecer",
        (4, 6): "Moderado — aceptas cierta volatilidad a cambio de rentabilidad",
        (7, 9): "Agresivo — toleras pérdidas temporales buscando altos retornos",
        (10, 10): "Especulativo — dispuesto a asumir riesgo máximo",
    }
    for rng, label in risk_labels.items():
        if rng[0] <= risk_raw <= rng[1]:
            st.info(f"**Tu perfil:** {label}")

    _info("¿Qué significa la tolerancia al riesgo?", """
La tolerancia al riesgo indica cuánta volatilidad e incertidumbre puedes asumir en tu cartera.

| Nivel | Perfil | Pérdida posible en año malo | Rentabilidad esperada |
|-------|--------|-----------------------------|-----------------------|
| 1–3 | Conservador | −5 % a −10 % | 4–7 % anual |
| 4–6 | Moderado | −10 % a −20 % | 7–10 % anual |
| 7–9 | Agresivo | −20 % a −35 % | 10–15 %+ anual |
| 10 | Especulativo | Hasta −50 % | 15–25 %+ anual |

**Importante:** A mayor riesgo, mayor potencial de rentabilidad, pero también mayores pérdidas posibles a corto plazo. El horizonte temporal es clave: carteras de alto riesgo necesitan más tiempo para recuperarse de caídas.
""")

    # ── 3. Preferencias de inversión ─────────────────────────────────────────────
    st.markdown("### 3. Preferencias de inversión")
    investment_type = st.radio(
        "¿Cómo prefieres estructurar tu inversión?",
        [
            "Empresas individuales (selección activa)",
            "Índices / ETFs (diversificación pasiva)",
            "Combinación de ambas",
        ],
        index=2,
        key="pf_inv_type",
    )

    _info("¿Qué diferencia hay entre empresas, índices y combinación?", """
**Empresas individuales (selección activa):**
El sistema elige las mejores empresas para tu perfil usando inteligencia artificial y análisis cuantitativo. Mayor potencial de superar al mercado, pero también mayor concentración y riesgo específico.

**Índices / ETFs (diversificación pasiva):**
Inviertes en fondos que replican un índice completo (S&P 500, MSCI World…). Diversificación automática, costes muy bajos y sin necesidad de gestión activa. La rentabilidad se ajusta a la del mercado en conjunto.

**Combinación de ambas:**
Una parte de tu cartera en ETFs para dar base y estabilidad, y otra parte en empresas seleccionadas para buscar rentabilidad adicional. Tú decides la proporción.
""")

    # Índices — solo si el usuario quiere índices
    preferred_indices = []
    if investment_type in ["Índices / ETFs (diversificación pasiva)", "Combinación de ambas"]:
        preferred_indices = st.multiselect(
            "¿Qué índices o ETFs quieres incluir?",
            INDICES,
            help="Si no seleccionas ninguno, el algoritmo elegirá los más adecuados a tu perfil de riesgo.",
            key="pf_indices",
        )
        if not preferred_indices:
            st.caption("Sin selección: el sistema elegirá los índices más adecuados a tu perfil.")

    # Control de distribución — solo en modo combinado
    custom_stock_pct = None
    if investment_type == "Combinación de ambas":
        st.markdown("#### ¿Cómo quieres repartir tu cartera?")
        custom_stock_pct = st.slider(
            "Porcentaje en empresas individuales",
            min_value=10,
            max_value=90,
            value=50,
            step=10,
            format="%d%%",
            key="pf_mix_split",
        )
        idx_display = 100 - custom_stock_pct
        col_a, col_b = st.columns(2)
        col_a.metric("Empresas individuales", f"{custom_stock_pct}%")
        col_b.metric("Índices / ETFs", f"{idx_display}%")

    # Mercado de empresas — solo si el usuario quiere empresas individuales
    stock_market_filter = []
    if investment_type in ["Empresas individuales (selección activa)", "Combinación de ambas"]:
        st.markdown("#### ¿De qué mercado quieres las empresas?")
        stock_market_filter = st.multiselect(
            "Selecciona uno o varios mercados (deja vacío para universo global)",
            [
                "Cualquier mercado (universo global)",
                "S&P 500 (EE.UU., 500 mayores empresas)",
                "NASDAQ 100 (tecnología EE.UU.)",
                "IBEX 35 (España)",
                "Euro Stoxx 50 (Europa)",
            ],
            default=["Cualquier mercado (universo global)"],
            key="pf_market_filter",
            help="Restringe la selección de empresas a los componentes del índice elegido.",
        )

    preferred_sectors = st.multiselect(
        "¿En qué sectores prefieres invertir? (deja vacío para cualquier sector)",
        SECTORS,
        key="pf_sectors",
    )

    # Empresas concretas — solo si el usuario quiere empresas individuales
    specific_stocks = []
    if investment_type in ["Empresas individuales (selección activa)", "Combinación de ambas"]:
        available_stocks = _stocks_for_markets(stock_market_filter)

        # Limpiar selección anterior si el mercado cambió y hay valores que ya no están disponibles
        prev = st.session_state.get("pf_stocks", ["Ninguna en particular"])
        valid_prev = [s for s in prev if s in available_stocks]
        if set(valid_prev) != set(prev):
            st.session_state["pf_stocks"] = valid_prev if valid_prev else ["Ninguna en particular"]

        specific_stocks = st.multiselect(
            "¿Hay alguna empresa en la que tengas especial interés?",
            available_stocks,
            default=["Ninguna en particular"],
            key="pf_stocks",
        )
        if "Ninguna en particular" in specific_stocks:
            specific_stocks = [s for s in specific_stocks if s != "Ninguna en particular"]

    # ── 4. ESG ───────────────────────────────────────────────────────────────────
    st.markdown("### 4. Criterios de sostenibilidad (ESG)")
    esg_pref = st.radio(
        "¿Quieres que tus inversiones tengan un enfoque sostenible / responsable?",
        [
            "Sí — excluir empresas con malas prácticas ESG (medioambiente, social, gobernanza)",
            "Preferentemente sí, pero no es excluyente",
            "No es un criterio relevante para mí",
        ],
        index=1,
        key="pf_esg",
    )

    _info("¿Qué es ESG?", """
**ESG** son las siglas de *Environmental* (Medioambiente), *Social* y *Governance* (Gobernanza).

- **Medioambiente:** Impacto en el cambio climático, emisiones de CO₂, uso de recursos naturales.
- **Social:** Condiciones laborales, derechos humanos, relaciones con la comunidad.
- **Gobernanza:** Transparencia empresarial, ética en la gestión, diversidad en la dirección.

**Opciones disponibles:**
- **Excluir malas prácticas:** Se eliminan del universo de inversión empresas de combustibles fósiles, tabaco, armamento y con escándalos de gobernanza.
- **Preferencia ESG:** Las empresas con mejor puntuación ESG reciben puntuación adicional en el análisis, pero no se excluyen automáticamente.
- **Sin filtro ESG:** La selección se basa puramente en criterios financieros, sin considerar el impacto social o medioambiental.
""")

    # ── 5. Diversificación geográfica ────────────────────────────────────────────
    st.markdown("### 5. Diversificación geográfica")
    geo_pref = st.multiselect(
        "¿En qué regiones te interesa invertir?",
        ["Global (sin restricción)", "EE.UU.", "Europa", "Asia-Pacífico", "Mercados emergentes"],
        default=["Global (sin restricción)"],
        key="pf_geo",
    )

    # ── 6. Reacción ante caídas ──────────────────────────────────────────────────
    st.markdown("### 6. Situación ante caídas del mercado")
    drawdown_reaction = st.radio(
        "Si tu cartera cae un 20% en 3 meses, ¿qué harías?",
        [
            "Vendo todo — no puedo asumir esa pérdida",
            "Vendo una parte para reducir el riesgo",
            "No hago nada — es parte del ciclo",
            "Compro más — es una oportunidad de entrada",
        ],
        index=2,
        key="pf_drawdown",
    )

    _info("¿Por qué se pregunta sobre caídas del mercado?", """
Esta pregunta calibra tu **tolerancia real al riesgo** más allá del número del slider anterior.

Las caídas del 20 % son relativamente frecuentes en mercados de renta variable:
S&P 500 ha caído más del 20 % en: **2022, 2020, 2008–09, 2000–02, 1987...**

**Implicaciones de cada respuesta:**

- **Vender todo:** No tolerarías esa pérdida. El algoritmo reduce la exposición a activos volátiles y aumenta el peso en ETFs estables.
- **Vender parte:** Tolerancia media-baja. Cartera algo más defensiva pero con potencial de crecimiento.
- **No hacer nada:** Tolerancia normal. Mantienes la estrategia a largo plazo, que históricamente es lo más rentable.
- **Comprar más:** Alta convicción e inversión en valor. El algoritmo puede incluir activos de mayor beta y potencial de crecimiento.

Tu respuesta ajusta tu puntuación de riesgo en **±2 puntos** para calibrar mejor la composición de la cartera.
""")

    st.markdown("---")
    submitted = st.button("Generar mi cartera", use_container_width=True, type="primary", key="pf_submit")

    if submitted:
        horizon_map = {
            "Corto plazo (< 1 año)": 0.5,
            "Medio plazo (1-3 años)": 2,
            "Largo plazo (3-7 años)": 5,
            "Muy largo plazo (> 7 años)": 10,
        }
        esg_map = {
            "Sí — excluir empresas con malas prácticas ESG (medioambiente, social, gobernanza)": "strict",
            "Preferentemente sí, pero no es excluyente": "preferred",
            "No es un criterio relevante para mí": "none",
        }
        drawdown_map = {
            "Vendo todo — no puedo asumir esa pérdida": -2,
            "Vendo una parte para reducir el riesgo": -1,
            "No hago nada — es parte del ciclo": 0,
            "Compro más — es una oportunidad de entrada": +2,
        }
        risk_score = risk_raw + drawdown_map[drawdown_reaction]
        risk_score = max(1, min(10, risk_score))

        return {
            "amount": amount,
            "monthly_contribution": monthly_contribution,
            "horizon_label": horizon,
            "horizon_years": horizon_map[horizon],
            "risk_raw": risk_raw,
            "risk_score": risk_score,
            "investment_type": investment_type,
            "preferred_indices": preferred_indices,
            "preferred_sectors": preferred_sectors,
            "specific_stocks": specific_stocks,
            "esg": esg_map[esg_pref],
            "geo_pref": geo_pref,
            "drawdown_reaction": drawdown_reaction,
            "custom_stock_pct": custom_stock_pct,
            "stock_market_filter": stock_market_filter,
        }
    return None


def describe_profile(profile: dict) -> str:
    risk = profile["risk_score"]
    if risk <= 3:
        risk_label = "Conservador"
    elif risk <= 6:
        risk_label = "Moderado"
    elif risk <= 8:
        risk_label = "Agresivo"
    else:
        risk_label = "Especulativo"

    sectors = ", ".join(profile["preferred_sectors"]) if profile["preferred_sectors"] else "todos los sectores"
    esg_text = {"strict": "con criterios ESG estrictos", "preferred": "con preferencia ESG", "none": "sin filtro ESG"}
    monthly = profile.get("monthly_contribution", 0)
    contrib_text = f" + €{monthly:,.0f}/mes" if monthly else ""

    inv_type = profile.get("investment_type", "")
    custom_pct = profile.get("custom_stock_pct")
    if custom_pct is not None:
        inv_text = f"Mixta ({custom_pct}% empresas / {100 - custom_pct}% índices)"
    elif "Índices" in inv_type:
        inv_text = "Índices/ETFs"
    elif "individuales" in inv_type:
        inv_text = "Empresas individuales"
    else:
        inv_text = "Mixta"

    return (
        f"**Perfil {risk_label}** | "
        f"Horizonte: {profile['horizon_label']} | "
        f"Capital: €{profile['amount']:,.0f}{contrib_text} | "
        f"Inversión: {inv_text} | "
        f"Sectores: {sectors} | "
        f"ESG: {esg_text[profile['esg']]}"
    )
