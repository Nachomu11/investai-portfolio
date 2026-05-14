import json
import os
import uuid
from datetime import datetime
import pandas as pd

PORTFOLIOS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "portfolios.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(PORTFOLIOS_FILE), exist_ok=True)


def _load_all() -> list[dict]:
    _ensure_dir()
    if not os.path.exists(PORTFOLIOS_FILE):
        return []
    with open(PORTFOLIOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(portfolios: list[dict]) -> None:
    _ensure_dir()
    with open(PORTFOLIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolios, f, indent=2, default=_serializer, ensure_ascii=False)


def _serializer(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _holdings_to_records(holdings) -> list[dict]:
    if isinstance(holdings, pd.DataFrame):
        df = holdings.copy()
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].apply(lambda x: x if not isinstance(x, list) else x)
        return df.where(pd.notnull(df), None).to_dict(orient="records")
    return holdings or []


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    for col in ["reasons", "warnings"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])
    return df


def save_portfolio(portfolio: dict, profile: dict, name: str = "") -> str:
    portfolios = _load_all()
    pid = str(uuid.uuid4())[:8]
    if not name:
        risk = profile.get("risk_score", 5)
        if risk <= 3:
            risk_label = "Conservadora"
        elif risk <= 6:
            risk_label = "Moderada"
        else:
            risk_label = "Agresiva"
        name = f"Cartera {risk_label} — {datetime.now().strftime('%d/%m/%Y')}"

    holdings_records = _holdings_to_records(portfolio.get("holdings", pd.DataFrame()))

    entry = {
        "id": pid,
        "name": name,
        "created_at": datetime.now().isoformat(),
        "profile": profile,
        "portfolio_type": portfolio.get("type", "mixed"),
        "total_invested": portfolio.get("total_invested", 0),
        "total_expected_gain": portfolio.get("total_expected_gain", 0),
        "expected_return_pct": portfolio.get("expected_return_pct", 0),
        "portfolio_beta": portfolio.get("portfolio_beta", 1.0),
        "n_holdings": portfolio.get("n_holdings", 0),
        "holdings": holdings_records,
        "idx_allocation_pct": portfolio.get("idx_allocation_pct"),
        "stock_allocation_pct": portfolio.get("stock_allocation_pct"),
    }
    portfolios.append(entry)
    _save_all(portfolios)
    return pid


def load_portfolios() -> list[dict]:
    return _load_all()


def get_portfolio_by_id(pid: str) -> dict | None:
    for p in _load_all():
        if p["id"] == pid:
            raw = dict(p)
            raw["holdings"] = _records_to_df(raw.get("holdings", []))
            return raw
    return None


def delete_portfolio(pid: str) -> bool:
    portfolios = _load_all()
    new_list = [p for p in portfolios if p["id"] != pid]
    if len(new_list) == len(portfolios):
        return False
    _save_all(new_list)
    return True


def rename_portfolio(pid: str, new_name: str) -> bool:
    portfolios = _load_all()
    for p in portfolios:
        if p["id"] == pid:
            p["name"] = new_name
            _save_all(portfolios)
            return True
    return False


def duplicate_portfolio(pid: str) -> str | None:
    original = get_portfolio_by_id(pid)
    if not original:
        return None
    return save_portfolio(original, original.get("profile", {}),
                          name=f"{original.get('name', 'Cartera')} (copia)")
