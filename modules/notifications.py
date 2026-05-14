import json
import os
from datetime import datetime
import pandas as pd
from modules.data_fetcher import get_price_history

NOTIF_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "notifications.json")


def _load_notifications() -> list[dict]:
    if os.path.exists(NOTIF_FILE):
        with open(NOTIF_FILE) as f:
            return json.load(f)
    return []


def _save_notifications(notifs: list[dict]) -> None:
    os.makedirs(os.path.dirname(NOTIF_FILE), exist_ok=True)
    with open(NOTIF_FILE, "w") as f:
        json.dump(notifs, f, indent=2, default=str)


def add_notification(title: str, message: str, level: str = "info") -> None:
    notifs = _load_notifications()
    notifs.insert(0, {
        "id": len(notifs) + 1,
        "title": title,
        "message": message,
        "level": level,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    })
    _save_notifications(notifs[:50])


def get_notifications(unread_only: bool = False) -> list[dict]:
    notifs = _load_notifications()
    if unread_only:
        return [n for n in notifs if not n["read"]]
    return notifs


def mark_all_read() -> None:
    notifs = _load_notifications()
    for n in notifs:
        n["read"] = True
    _save_notifications(notifs)


def clear_notifications() -> None:
    _save_notifications([])


def check_portfolio_alerts(portfolio: dict, thresholds: dict | None = None) -> list[dict]:
    if thresholds is None:
        thresholds = {"drop_alert": -5.0, "gain_alert": 10.0}

    alerts = []
    holdings = portfolio.get("holdings", pd.DataFrame())
    if holdings.empty:
        return alerts

    for _, row in holdings.iterrows():
        ticker = row.get("ticker", "")
        if not ticker or len(ticker) > 6:
            continue
        hist = get_price_history(ticker, years=0.1)
        if hist.empty or len(hist) < 5:
            continue
        col = hist.columns[0]
        current = hist[col].iloc[-1]
        week_ago = hist[col].iloc[-5] if len(hist) >= 5 else current
        change_pct = (current / week_ago - 1) * 100

        if change_pct <= thresholds["drop_alert"]:
            alerts.append({
                "ticker": ticker,
                "name": row.get("name", ticker),
                "change_pct": round(change_pct, 2),
                "type": "drop",
                "message": f"{row.get('name', ticker)} ha caido {abs(change_pct):.1f}% esta semana. Revisa si el contexto ha cambiado.",
            })
        elif change_pct >= thresholds["gain_alert"]:
            alerts.append({
                "ticker": ticker,
                "name": row.get("name", ticker),
                "change_pct": round(change_pct, 2),
                "type": "gain",
                "message": f"{row.get('name', ticker)} ha subido {change_pct:.1f}% esta semana. Considera si rebalancear.",
            })

    for alert in alerts:
        level = "warning" if alert["type"] == "drop" else "success"
        add_notification(
            title=f"Alerta de cartera — {alert['ticker']}",
            message=alert["message"],
            level=level,
        )

    return alerts


def generate_periodic_advice(portfolio: dict, profile: dict) -> list[str]:
    advice = []
    horizon = profile.get("horizon_years", 2)
    risk = profile.get("risk_score", 5)
    amount = profile.get("amount", 10000)

    if horizon >= 5:
        advice.append("Recuerda que tu horizonte es a largo plazo. Las correcciones del mercado son normales y no deben provocar cambios precipitados.")

    if risk <= 3:
        advice.append("Como inversor conservador, considera mantener un 10-15% de liquidez para aprovechar oportunidades en correcciones.")

    if risk >= 7:
        advice.append("Con un perfil agresivo, monitoriza tu beta de cartera. Una beta > 1.5 amplifica tanto subidas como bajadas.")

    if amount >= 50000:
        advice.append("Con un capital elevado, considera la fiscalidad. Las plusvalias a mas de 1 ano suelen tener mejor tratamiento fiscal.")

    advice.append("El rebalanceo trimestral de la cartera ayuda a mantener el perfil de riesgo objetivo.")
    advice.append("Diversifica en el tiempo mediante aportaciones periodicas para reducir el impacto de la volatilidad (dollar-cost averaging).")

    return advice
