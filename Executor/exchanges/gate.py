"""
Gate.io交易所封装
实现统一的交易接口函数
"""
from typing import Dict, List, Optional
import time
import hashlib
import hmac
import json
import requests
import os

quanto_multiplier_BTC_USDT = 0.0001
quanto_multiplier_ETH_USDT = 0.01

with open("Executor/exchanges/config.json", "r") as f:
    api_config = json.load(f)

gate_api_key = api_config["gate"]["api_key"]
gate_api_secret = api_config["gate"]["api_secret"]

def gen_sign(method, url, query_string=None, payload_string=None):
    key = gate_api_key        # api_key
    secret = gate_api_secret     # api_secret

    t = time.time()
    m = hashlib.sha512()
    m.update((payload_string or "").encode('utf-8'))
    hashed_payload = m.hexdigest()
    s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
    sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
    return {'KEY': key, 'Timestamp': str(t), 'SIGN': sign}


def _get_quanto_multiplier(symbol: str) -> float:
    """
    获取合约的 quanto_multiplier
    优先从合约信息文件读取，如果没有则使用硬编码值
    """
    # 尝试从合约信息文件读取
    symbol_formatted = symbol.replace("_", "-")
    contract_info_path = f"Data_collector/contract_information/gate/{symbol_formatted}.json"
    
    if os.path.exists(contract_info_path):
        try:
            with open(contract_info_path, "r") as f:
                contract_info = json.load(f)
                quanto = contract_info.get("quanto_multiplier")
                if quanto:
                    return float(quanto)
        except Exception:
            pass
    
    # 使用硬编码值作为后备
    if symbol == "BTC_USDT":
        return quanto_multiplier_BTC_USDT
    elif symbol == "ETH_USDT":
        return quanto_multiplier_ETH_USDT
    else:
        # 默认值，建议从合约信息文件获取
        return 0.0001


def place_limit_order(
    symbol: str,
    side: str,
    amount: float,
    price: float
) -> Dict:
    """
    发送限价单
    
    参数:
        symbol: 交易对 (如 "BTC_USDT")
        side: 方向 ("buy" 或 "sell")
        amount: 数量
        price: 价格
    
    返回:
        {
            "success": bool,
            "order_id": str,
            "symbol": str,
            "side": str,
            "amount": float,
            "price": float,
            "message": str
        }
    """
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url_path = f"{prefix}/futures/usdt/orders"
    
    # 获取 quanto_multiplier 并计算合约张数
    quanto_multiplier = _get_quanto_multiplier(symbol)
    size = amount / quanto_multiplier
    
    # 根据 side 确定 size 的正负：buy 为正数，sell 为负数
    if side.lower() == "sell":
        size = -abs(size)
    else:
        size = abs(size)
    
    # 构建请求体
    body = {
        "contract": symbol,
        "size": str(int(size)),  # Gate.io 要求 size 为字符串
        "price": str(price),
        "tif": "gtc"  # Good Till Cancelled
    }
    
    body_str = json.dumps(body)
    
    # 生成签名
    sign_headers = gen_sign('POST', url_path, '', body_str)
    
    # 构建请求头
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    headers.update(sign_headers)
    
    try:
        resp = requests.post(
            f"{host}{url_path}",
            headers=headers,
            data=body_str,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 返回统一格式
        return {
            "success": True,
            "order_id": str(data.get("id", "")),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "message": "订单提交成功"
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("label", error_data.get("message", str(e)))
            except:
                error_msg = e.response.text
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "message": f"下单失败: {error_msg}"
        }


def place_market_order(
    symbol: str,
    side: str,
    amount: float
) -> Dict:
    """
    发送市价单
    
    参数:
        symbol: 交易对
        side: 方向 ("buy" 或 "sell")
        amount: 数量
    
    返回:
        {
            "success": bool,
            "order_id": str,
            "symbol": str,
            "side": str,
            "amount": float,
            "message": str
        }
    """
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url_path = f"{prefix}/futures/usdt/orders"
    
    # 获取 quanto_multiplier 并计算合约张数
    quanto_multiplier = _get_quanto_multiplier(symbol)
    size = amount / quanto_multiplier
    
    # 根据 side 确定 size 的正负：buy 为正数，sell 为负数
    if side.lower() == "sell":
        size = -abs(size)
    else:
        size = abs(size)
    
    # 构建请求体（市价单：price 为 0，tif 为 ioc）
    body = {
        "contract": symbol,
        "size": str(int(size)),  # Gate.io 要求 size 为字符串
        "price": "0",  # 市价单价格为 0
        "tif": "ioc"  # Immediate Or Cancelled
    }
    
    body_str = json.dumps(body)
    
    # 生成签名
    sign_headers = gen_sign('POST', url_path, '', body_str)
    
    # 构建请求头
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    headers.update(sign_headers)
    
    try:
        resp = requests.post(
            f"{host}{url_path}",
            headers=headers,
            data=body_str,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 返回统一格式
        return {
            "success": True,
            "order_id": str(data.get("id", "")),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "message": "订单提交成功"
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("label", error_data.get("message", str(e)))
            except:
                error_msg = e.response.text
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "message": f"下单失败: {error_msg}"
        }


def cancel_order(
    symbol: str,
    order_id: str
) -> Dict:
    """
    撤销单个订单
    
    参数:
        symbol: 交易对
        order_id: 订单ID
    
    返回:
        {
            "success": bool,
            "order_id": str,
            "message": str
        }
    """
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url_path = f"{prefix}/futures/usdt/orders/{order_id}"
    
    # DELETE 请求没有请求体，query_param 为空
    query_param = ''
    
    # 生成签名
    sign_headers = gen_sign('DELETE', url_path, query_param, None)
    
    # 构建请求头
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    headers.update(sign_headers)
    
    try:
        resp = requests.delete(
            f"{host}{url_path}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 返回统一格式
        return {
            "success": True,
            "order_id": str(data.get("id", order_id)),
            "message": "订单撤销成功"
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("label", error_data.get("message", str(e)))
            except:
                error_msg = e.response.text
        return {
            "success": False,
            "order_id": order_id,
            "message": f"撤销订单失败: {error_msg}"
        }


def cancel_all_orders(
    symbol: Optional[str] = None
) -> Dict:
    """
    撤销所有订单（或指定交易对的所有订单）
    
    参数:
        symbol: 交易对，如果为None则撤销所有交易对的订单
    
    返回:
        {
            "success": bool,
            "cancelled_count": int,
            "message": str
        }
    """
    raise NotImplementedError("请在 exchanges/gate.py 中实现此函数")


def get_order_status(
    symbol: str,
    order_id: str
) -> Dict:
    """
    查询订单状态
    
    参数:
        symbol: 交易对
        order_id: 订单ID
    
    返回:
        {
            "success": bool,
            "order_id": str,
            "symbol": str,
            "side": str,
            "type": str,
            "amount": float,
            "filled": float,
            "price": float,
            "status": str,  # "pending", "filled", "cancelled", "rejected"
            "message": str
        }
    """
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url_path = f"{prefix}/futures/usdt/orders/{order_id}"
    
    # GET 请求没有请求体，query_param 为空
    query_param = ''
    
    # 生成签名
    sign_headers = gen_sign('GET', url_path, query_param, None)
    
    # 构建请求头
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    headers.update(sign_headers)
    
    try:
        resp = requests.get(
            f"{host}{url_path}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 获取 quanto_multiplier 用于计算数量
        contract_symbol = data.get("contract", symbol)
        quanto_multiplier = _get_quanto_multiplier(contract_symbol)
        
        # 解析订单信息
        order_id_str = str(data.get("id", order_id))
        contract = data.get("contract", symbol)
        size = float(data.get("size", "0"))
        left = float(data.get("left", "0"))
        price = float(data.get("price", "0"))
        tif = data.get("tif", "")
        status = data.get("status", "")
        finish_as = data.get("finish_as", "")
        
        # 根据 size 的正负判断 side
        if size > 0:
            side = "buy"
        elif size < 0:
            side = "sell"
        else:
            side = "unknown"
        
        # 根据 tif 判断订单类型
        if tif == "gtc":
            order_type = "limit"
        elif tif == "ioc":
            order_type = "market"
        else:
            order_type = tif
        
        # 计算原始数量（币的数量）
        amount = abs(size) * quanto_multiplier
        filled = (abs(size) - abs(left)) * quanto_multiplier
        
        # 映射状态
        if status == "open":
            mapped_status = "pending"
        elif status == "finished":
            if finish_as == "filled":
                mapped_status = "filled"
            elif finish_as == "cancelled":
                mapped_status = "cancelled"
            else:
                mapped_status = "finished"
        else:
            mapped_status = status.lower() if status else "unknown"
        
        # 返回统一格式
        return {
            "success": True,
            "order_id": order_id_str,
            "symbol": contract,
            "side": side,
            "type": order_type,
            "amount": amount,
            "filled": filled,
            "price": price,
            "status": mapped_status,
            "message": "查询成功"
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("label", error_data.get("message", str(e)))
            except:
                error_msg = e.response.text
        return {
            "success": False,
            "order_id": order_id,
            "symbol": symbol,
            "side": "",
            "type": "",
            "amount": 0.0,
            "filled": 0.0,
            "price": 0.0,
            "status": "error",
            "message": f"查询订单状态失败: {error_msg}"
        }


def get_open_orders(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取未成交订单列表
    
    参数:
        symbol: 交易对，如果为None则返回所有交易对的未成交订单
    
    返回:
        [
            {
                "order_id": str,
                "symbol": str,
                "side": str,
                "type": str,
                "amount": float,
                "filled": float,
                "price": float,
                "status": str
            },
            ...
        ]
    """
    raise NotImplementedError("请在 exchanges/gate.py 中实现此函数")


def get_account_info() -> Dict:
    """
    获取账户信息
    
    返回:
        {
            "success": bool,
            "total_equity": float,      # 总权益
            "available_balance": float,  # 可用余额
            "used_margin": float,        # 已用保证金
            "unrealized_pnl": float,     # 未实现盈亏
            "message": str
        }
    """
    raise NotImplementedError("请在 exchanges/gate.py 中实现此函数")

def get_positions(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取持仓信息
    
    参数:
        symbol: 交易对，如果为None则返回所有持仓
    
    返回:
        [
            {
                "symbol": str,
                "side": str,          # "long", "short", "none"
                "size": float,        # 仓位大小
                "entry_price": float, # 开仓均价
                "mark_price": float,  # 标记价格
                "unrealized_pnl": float,
                "leverage": float
            },
            ...
        ]
    """
    raise NotImplementedError("请在 exchanges/gate.py 中实现此函数")


def adjust_position(
    symbol: str,
    side: str,
    amount: float,
    price: Optional[float] = None
) -> Dict:
    """
    调整仓位
    
    参数:
        symbol: 交易对
        side: 方向 ("long" 或 "short")
        amount: 数量
        price: 价格，如果为None则使用市价
    
    返回:
        {
            "success": bool,
            "symbol": str,
            "side": str,
            "amount": float,
            "message": str
        }
    """
    raise NotImplementedError("请在 exchanges/gate.py 中实现此函数")

