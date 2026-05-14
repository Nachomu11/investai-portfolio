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
    "Ninguno en particular — prefiero empresas individuales",
]

SPECIFIC_STOCKS = [
    "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Amazon (AMZN)",
    "Alphabet (GOOGL)", "Meta (META)", "Tesla (TSLA)", "Berkshire Hathaway (BRK-B)",
    "LVMH (MC.PA)", "Novo Nordisk (NVO)", "ASML (ASML)", "Samsung (005930.KS)",
    "Taiwan Semiconductor (TSM)", "Eli Lilly (LLY)", "JPMorgan (JPM)",
    "Ninguna en particular",
]


def render_profile_form() -> dict | None:
    st.markdown("## Cuestionario de perfil de inversor")
    st.markdown(
        "Complete el siguiente cuestionario para que el sistema pueda generar "
        "una propuesta de cartera ajustada a sus objetivos y tolerancia al riesgo."
    )

    with st.form("investor_form", clear_on_submit=False):
        st.markdown("### 1. Datos generales de la inversión")
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "¿Cuánto dinero deseas invertir inicialmente? (€)",
                min_value=500,
                max_value=10_000_000,
                value=10_000,
                step=500,
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
            )

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

        st.markdown("### 2. Tolerancia al riesgo")
        risk_raw = st.slider(
            "¿Cómo describes tu tolerancia al riesgo?",
            min_value=1,
            max_value=10,
            value=5,
            help="1 = muy conservador (prefiero seguridad), 10 = muy agresivo (busco máxima rentabilidad)",
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

        st.markdown("### 3. Preferencias de inversión")
        investment_type = st.radio(
            "¿Cómo prefieres estructurar tu inversión?",
            [
                "Empresas individuales (selección activa)",
                "Índices / ETFs (diversificación pasiva)",
                "Combinación de ambas",
            ],
            index=2,
        )

        # Índices preferidos — solo si el usuario quiere índices
        preferred_indices = []
        if investment_type in ["Índices / ETFs (diversificación pasiva)", "Combinación de ambas"]:
            preferred_indices = st.multiselect(
                "¿Qué índices o ETFs quieres incluir? (deja vacío para incluir todos los disponibles)",
                INDICES,
                help="Si no seleccionas ninguno, el algoritmo elegirá los más adecuados a tu perfil.",
            )

        preferred_sectors = st.multiselect(
            "¿En qué sectores prefieres invertir? (deja vacío para cualquier sector)",
            SECTORS,
        )

        # Empresas concretas — solo si el usuario quiere empresas individuales
        specific_stocks = []
        if investment_type in ["Empresas individuales (selección activa)", "Combinación de ambas"]:
            specific_stocks = st.multiselect(
                "¿Hay alguna empresa en la que tengas especial interés?",
                SPECIFIC_STOCKS,
                default=["Ninguna en particular"],
            )
            if "Ninguna en particular" in specific_stocks:
                specific_stocks = [s for s in specific_stocks if s != "Ninguna en particular"]

        st.markdown("### 4. Criterios de sostenibilidad (ESG)")
        esg_pref = st.radio(
            "¿Quieres que tus inversiones tengan un enfoque sostenible / responsable?",
            [
                "Sí — excluir empresas con malas prácticas ESG (medioambiente, social, gobernanza)",
                "Preferentemente sí, pero no es excluyente",
                "No es un criterio relevante para mí",
            ],
            index=1,
        )

        st.markdown("### 5. Diversificación geográfica")
        geo_pref = st.multiselect(
            "¿En qué regiones te interesa invertir?",
            ["Global (sin restricción)", "EE.UU.", "Europa", "Asia-Pacífico", "Mercados emergentes"],
            default=["Global (sin restricción)"],
        )

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
        )

        st.markdown("---")
        submitted = st.form_submit_button("Generar mi cartera", use_container_width=True, type="primary")

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

    return (
        f"**Perfil {risk_label}** | "
        f"Horizonte: {profile['horizon_label']} | "
        f"Capital: €{profile['amount']:,.0f}{contrib_text} | "
        f"Sectores: {sectors} | "
        f"ESG: {esg_text[profile['esg']]}"
    )
