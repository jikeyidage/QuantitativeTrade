"""
OKX交易所封装
实现统一的交易接口函数
"""
from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import hmac
import json
from typing import Dict, List, Optional

import requests

_CONFIG_PATH = "Executor/exchanges/config.json"
_BASE_URL = "https://www.okx.com"
_TD_MODE = "cross"

with open(_CONFIG_PATH, "r", encoding="utf-8") as _conf_file:
    _API_CFG = json.load(_conf_file)["okx"]

_API_KEY = _API_CFG.get("api_key", "")
_API_SECRET = _API_CFG.get("api_secret", "")
_API_PASSPHRASE = _API_CFG.get("passphrase", "")


def _ensure_credentials() -> None:
    if not all([_API_KEY, _API_SECRET, _API_PASSPHRASE]):
        raise RuntimeError("OKX API 配置缺失，请在 config.json 中填写 api_key/api_secret/passphrase")


def _utc_timestamp() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sign(message: str) -> str:
    mac = hmac.new(_API_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")


def _format_decimal(value: float) -> str:
    formatted = f"{value:.12f}".rstrip("0").rstrip(".")
    return formatted or "0"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _request(method: str, path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict:
    _ensure_credentials()
    method_upper = method.upper()
    params = params or {}
    body = body or {}

    query = ""
    if params:
        query = "?" + "&".join(f"{k}={v}" for k, v in params.items())

    request_path = f"{path}{query}"
    body_str = json.dumps(body) if body and method_upper != "GET" else ""

    timestamp = _utc_timestamp()
    prehash = f"{timestamp}{method_upper}{request_path}{body_str}"
    signature = _sign(prehash)

    headers = {
        "OK-ACCESS-KEY": _API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": _API_PASSPHRASE,
        "Content-Type": "application/json",
    }

    url = f"{_BASE_URL}{path}"

    try:
        if method_upper == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            resp = requests.request(method_upper, url, headers=headers, data=body_str, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "0":
            raise RuntimeError(data.get("msg", "OKX返回错误"))
        return data
    except requests.RequestException as exc:
        raise RuntimeError(f"HTTP请求异常: {exc}") from exc



def place_limit_order(
    symbol: str,
    side: str,
    amount: float,
    price: float
) -> Dict:
    """
    发送限价单
    """
    payload = {
        "instId": symbol,
        "tdMode": _TD_MODE,
        "side": side.lower(),
        "ordType": "limit",
        "sz": _format_decimal(amount),
        "px": _format_decimal(price),
    }
    try:
        data = _request("POST", "/api/v5/trade/order", body=payload)
        order_info = data.get("data", [{}])[0]
        return {
            "success": True,
            "order_id": order_info.get("ordId", ""),
            "symbol": symbol,
            "side": side.lower(),
            "amount": amount,
            "price": price,
            "message": order_info.get("sCode", "ok"),
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol,
            "side": side.lower(),
            "amount": amount,
            "price": price,
            "message": str(exc),
        }


def place_market_order(
    symbol: str,
    side: str,
    amount: float
) -> Dict:
    """
    发送市价单
    """
    payload = {
        "instId": symbol,
        "tdMode": _TD_MODE,
        "side": side.lower(),
        "ordType": "market",
        "sz": _format_decimal(amount),
    }
    try:
        data = _request("POST", "/api/v5/trade/order", body=payload)
        order_info = data.get("data", [{}])[0]
        return {
            "success": True,
            "order_id": order_info.get("ordId", ""),
            "symbol": symbol,
            "side": side.lower(),
            "amount": amount,
            "message": order_info.get("sCode", "ok"),
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol,
            "side": side.lower(),
            "amount": amount,
            "message": str(exc),
        }


def cancel_order(
    symbol: str,
    order_id: str
) -> Dict:
    """
    撤销单个订单
    """
    payload = {"instId": symbol, "ordId": order_id}
    try:
        data = _request("POST", "/api/v5/trade/cancel-order", body=payload)
        info = data.get("data", [{}])[0]
        return {
            "success": info.get("sCode") == "0",
            "order_id": order_id,
            "message": info.get("sMsg", "cancel success"),
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "order_id": order_id,
            "message": str(exc),
        }


def cancel_all_orders(
    symbol: Optional[str] = None
) -> Dict:
    """
    撤销所有订单（或指定交易对的所有订单）
    """
    open_orders = get_open_orders(symbol)
    cancelled = 0
    errors: List[str] = []
    for order in open_orders:
        result = cancel_order(order["symbol"], order["order_id"])
        if result["success"]:
            cancelled += 1
        else:
            errors.append(result["message"])
    return {
        "success": cancelled == len(open_orders),
        "cancelled_count": cancelled,
        "message": "; ".join(errors) if errors else "ok",
    }


def get_order_status(
    symbol: str,
    order_id: str
) -> Dict:
    """
    查询订单状态
    """
    params = {"instId": symbol, "ordId": order_id}
    try:
        data = _request("GET", "/api/v5/trade/order", params=params)
        info = data.get("data", [{}])[0]
        return {
            "success": True,
            "order_id": order_id,
            "symbol": symbol,
            "side": info.get("side", ""),
            "type": info.get("ordType", ""),
            "amount": _safe_float(info.get("sz"), 0.0),
            "filled": _safe_float(info.get("accFillSz"), 0.0),
            "price": _safe_float(info.get("px")),
            "status": info.get("state", ""),
            "message": info.get("state", "ok"),
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "order_id": order_id,
            "symbol": symbol,
            "side": "",
            "type": "",
            "amount": 0.0,
            "filled": 0.0,
            "price": 0.0,
            "status": "",
            "message": str(exc),
        }


def get_open_orders(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取未成交订单列表
    """
    params = {"instId": symbol} if symbol else {}
    try:
        data = _request("GET", "/api/v5/trade/orders-pending", params=params)
        results = []
        for item in data.get("data", []):
            results.append({
                "order_id": item.get("ordId", ""),
                "symbol": item.get("instId", ""),
                "side": item.get("side", ""),
                "type": item.get("ordType", ""),
                "amount": _safe_float(item.get("sz"), 0.0),
                "filled": _safe_float(item.get("accFillSz"), 0.0),
                "price": _safe_float(item.get("px"), 0.0),
                "status": item.get("state", ""),
            })
        return results
    except RuntimeError:
        return []


def get_account_info() -> Dict:
    """
    获取账户信息
    """
    try:
        data = _request("GET", "/api/v5/account/balance")
        acct = data.get("data", [{}])[0]
        total_eq = _safe_float(acct.get("totalEq"), 0.0)
        avail_bal = _safe_float(acct.get("details", [{}])[0].get("availBal"), 0.0) if acct.get("details") else 0.0
        used_margin = _safe_float(acct.get("details", [{}])[0].get("ordFrozen"), 0.0) if acct.get("details") else 0.0
        unreal = _safe_float(acct.get("details", [{}])[0].get("upl"), 0.0) if acct.get("details") else 0.0
        return {
            "success": True,
            "total_equity": total_eq,
            "available_balance": avail_bal,
            "used_margin": used_margin,
            "unrealized_pnl": unreal,
            "message": "ok",
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "total_equity": 0.0,
            "available_balance": 0.0,
            "used_margin": 0.0,
            "unrealized_pnl": 0.0,
            "message": str(exc),
        }


def get_positions(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取持仓信息
    """
    params = {"instId": symbol} if symbol else {}
    try:
        data = _request("GET", "/api/v5/account/positions", params=params)
        positions = []
        for item in data.get("data", []):
            positions.append({
                "symbol": item.get("instId", ""),
                "side": "long" if item.get("posSide") == "long" else "short" if item.get("posSide") == "short" else "none",
                "size": _safe_float(item.get("pos"), 0.0),
                "entry_price": _safe_float(item.get("avgPx"), 0.0),
                "mark_price": _safe_float(item.get("markPx"), 0.0),
                "unrealized_pnl": _safe_float(item.get("upl"), 0.0),
                "leverage": _safe_float(item.get("lever"), 0.0),
            })
        return positions
    except RuntimeError:
        return []


def adjust_position(
    symbol: str,
    side: str,
    amount: float,
    price: Optional[float] = None
) -> Dict:
    """
    调整仓位
    """
    order_side = "buy" if side.lower() == "long" else "sell"
    if price is None:
        return place_market_order(symbol, order_side, amount)
    return place_limit_order(symbol, order_side, amount, price)

