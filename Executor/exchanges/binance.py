"""
Binance交易所封装
实现统一的交易接口函数
"""
from typing import Dict, List, Optional
import hashlib
import hmac
import os
import time
from urllib.parse import urlencode
import json
import requests
import importlib


# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")

# 如果在当前脚本同级目录下找不到，尝试使用相对路径（兼容从项目根目录运行的情况）
if not os.path.exists(config_path):
    config_path = "Executor/exchanges/config.json"

try:
    with open(config_path, "r", encoding="utf-8") as f:
        api_config = json.load(f)
except FileNotFoundError:
    print(f"严重错误: 找不到配置文件。请在 {current_dir} 下创建 config.json")
    # 提供默认空值防止立即报错，但在实际调用时会失败
    api_config = {"binance": {"api_key": "", "api_secret": ""}}

# 使用测试网配置
binance_api_key = api_config["binance_testnet"]["api_key"]
binance_api_secret = api_config["binance_testnet"]["api_secret"]

# API 基础 URL (默认为测试网，如需主网请修改)
BASE_URL = 'https://testnet.binance.vision/api/v3'
# BASE_URL = 'https://api.binance.com/api/v3'  # 主网 URL


def _format_decimal(value: float) -> str:
    """格式化浮点数为字符串，去除末尾的0"""
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted or "0"


def _to_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _send_request(method: str, endpoint: str, params: Dict = None) -> Dict:
    """发送带签名的请求"""
    if params is None:
        params = {}
    api_key = binance_api_key
    api_secret = binance_api_secret
    if not api_key or not api_secret:
        raise RuntimeError("BINANCE_API_KEY / BINANCE_API_SECRET not configured")

    params["timestamp"] = int(time.time() * 1000)

    # 按排序生成待签名字符串
    query_string = urlencode(sorted(params.items()))
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # 拼接最终发送的参数字符串，确保顺序一致
    final_params_str = f"{query_string}&signature={signature}"

    headers = {"X-MBX-APIKEY": api_key}
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() in ["GET", "DELETE"]:
            full_url = f"{url}?{final_params_str}"
            if method.upper() == "GET":
                resp = requests.get(full_url, headers=headers, timeout=10)
            else:
                resp = requests.delete(full_url, headers=headers, timeout=10)
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            resp = requests.post(url, headers=headers, data=final_params_str, timeout=10)

        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        error_msg = str(exc)
        if exc.response is not None:
            try:
                error_json = exc.response.json()
                error_msg = error_json.get("msg", exc.response.text)
                raise RuntimeError(f"Binance API Error: {error_msg}") from exc
            except ValueError:
                error_msg = exc.response.text
        raise RuntimeError(f"Request Error: {error_msg}") from exc


def _get_symbol_price(symbol: str) -> Optional[float]:
    """获取现货最新价格（公共接口，无需签名）"""
    try:
        resp = requests.get(
            f"https://testnet.binance.vision/api/v3/ticker/price",
            params={"symbol": symbol.upper()},
            timeout=5
        )
        resp.raise_for_status()
        return float(resp.json().get("price", 0.0))
    except Exception:
        return None


_order_manager = None
def _get_order_manager():
    """延迟加载订单管理器，避免循环引用"""
    global _order_manager
    if _order_manager is None:
        try:
            _order_manager = importlib.import_module("Executor.order_manager").OrderManager()
        except Exception:
            _order_manager = None
    return _order_manager


def place_limit_order(
    symbol: str,
    side: str,
    amount: float,
    price: float,
    time_in_force: str = "GTC",
    **kwargs
) -> Dict:
    """
    发送限价单
    
    支持额外参数 (kwargs):
        newClientOrderId (str): 用户自定义订单ID
        icebergQty (float): 冰山订单数量
        newOrderRespType (str): 响应类型 ACK, RESULT, FULL
        selfTradePreventionMode (str): STP 模式
        recvWindow (int): 请求接收窗口
    """
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    if amount <= 0 or price <= 0:
        raise ValueError("amount and price must be positive")

    params = {
        "symbol": symbol.upper(),
        "side": side,
        "type": "LIMIT",
        "timeInForce": time_in_force.upper(),
        "quantity": _format_decimal(amount),
        "price": _format_decimal(price),
    }
    
    # 处理需要特殊格式化的参数
    if "icebergQty" in kwargs:
        params["icebergQty"] = _format_decimal(float(kwargs.pop("icebergQty")))

    # 合并额外参数
    params.update(kwargs)

    try:
        data = _send_request("POST", "/order", params)
        order_id = str(data.get("orderId", ""))
        mgr = _get_order_manager()
        if mgr and order_id:
            mgr.add_order({
                "order_id": order_id,
                "exchange": "binance",
                "symbol": data.get("symbol", symbol.upper()),
                "side": data.get("side", side),
                "type": "LIMIT",
                "amount": _to_float(data.get("origQty"), amount),
                "price": _to_float(data.get("price"), price),
                "status": data.get("status", "NEW"),
                "timestamp": time.time()
            })
        return {
            "success": True,
            "order_id": order_id,
            "client_order_id": data.get("clientOrderId", ""),
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "amount": _to_float(data.get("origQty"), amount),
            "price": _to_float(data.get("price"), price),
            "time_in_force": data.get("timeInForce"),
            "message": data.get("status", "NEW"),
            "fills": data.get("fills", [])
        }
    except Exception as e:
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol.upper(),
            "side": side,
            "amount": amount,
            "price": price,
            "time_in_force": time_in_force,
            "message": str(e),
        }


def place_market_order(
    symbol: str,
    side: str,
    amount: float
) -> Dict:
    """
    发送市价单
    """
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
        
    if amount <= 0:
        raise ValueError("amount must be positive")

    params = {
        "symbol": symbol.upper(),
        "side": side,
        "type": "MARKET",
        "quantity": _format_decimal(amount),
    }

    try:
        data = _send_request("POST", "/order", params)
        order_id = str(data.get("orderId", ""))
        mgr = _get_order_manager()
        if mgr and order_id:
            mgr.add_order({
                "order_id": order_id,
                "exchange": "binance",
                "symbol": data.get("symbol", symbol.upper()),
                "side": data.get("side", side),
                "type": "MARKET",
                "amount": _to_float(data.get("origQty"), amount),
                "price": 0.0,
                "status": data.get("status", "NEW"),
                "timestamp": time.time()
            })
        return {
            "success": True,
            "order_id": order_id,
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "amount": _to_float(data.get("origQty"), amount),
            "message": data.get("status", "NEW"),
        }
    except Exception as e:
        return {
            "success": False,
            "order_id": "",
            "symbol": symbol.upper(),
            "side": side,
            "amount": amount,
            "message": str(e),
        }


def cancel_order(
    symbol: str,
    order_id: str
) -> Dict:
    """
    撤销单个订单
    """
    params = {
        "symbol": symbol.upper(),
        "orderId": order_id
    }
    
    try:
        data = _send_request("DELETE", "/order", params)
        mgr = _get_order_manager()
        if mgr:
            mgr.add_order({
                "order_id": str(data.get("orderId", order_id)),
                "exchange": "binance",
                "symbol": symbol.upper(),
                "side": "",
                "type": "",
                "amount": 0.0,
                "price": 0.0,
                "status": data.get("status", "CANCELED"),
                "timestamp": time.time()
            })
        return {
            "success": True,
            "order_id": str(data.get("orderId", order_id)),
            "message": data.get("status", "CANCELED")
        }
    except Exception as e:
        return {
            "success": False,
            "order_id": order_id,
            "message": str(e)
        }


def cancel_all_orders(
    symbol: Optional[str] = None
) -> Dict:
    """
    撤销所有订单（或指定交易对的所有订单）
    注意：Binance Spot API 要求必须指定 symbol 才能撤销所有订单
    """
    if not symbol:
        return {
            "success": False,
            "cancelled_count": 0,
            "message": "Binance Spot API requires a symbol to cancel all orders."
        }

    params = {
        "symbol": symbol.upper()
    }
    
    try:
        data = _send_request("DELETE", "/openOrders", params)
        mgr = _get_order_manager()
        if mgr and isinstance(data, list):
            now = time.time()
            for o in data:
                mgr.add_order({
                    "order_id": str(o.get("orderId", "")),
                    "exchange": "binance",
                    "symbol": o.get("symbol", symbol.upper()),
                    "side": o.get("side", ""),
                    "type": o.get("type", ""),
                    "amount": _to_float(o.get("origQty"), 0),
                    "price": _to_float(o.get("price"), 0),
                    "status": o.get("status", "CANCELED"),
                    "timestamp": now
                })
        return {
            "success": True,
            "cancelled_count": len(data) if isinstance(data, list) else 0,
            "message": "Success"
        }
    except Exception as e:
        return {
            "success": False,
            "cancelled_count": 0,
            "message": str(e)
        }


def get_order_status(
    symbol: str,
    order_id: str
) -> Dict:
    """
    查询订单状态
    """
    params = {
        "symbol": symbol.upper(),
        "orderId": order_id
    }
    
    try:
        data = _send_request("GET", "/order", params)
        status = data.get("status", "UNKNOWN")
        mgr = _get_order_manager()
        if mgr:
            mgr.add_order({
                "order_id": str(data.get("orderId", order_id)),
                "exchange": "binance",
                "symbol": data.get("symbol", symbol.upper()),
                "side": data.get("side", ""),
                "type": data.get("type", ""),
                "amount": _to_float(data.get("origQty"), 0.0),
                "price": _to_float(data.get("price"), 0.0),
                "status": status,
                "filled": _to_float(data.get("executedQty"), 0.0),
                "timestamp": time.time()
            })
        return {
            "success": True,
            "order_id": str(data.get("orderId")),
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "type": data.get("type"),
            "amount": _to_float(data.get("origQty")),
            "filled": _to_float(data.get("executedQty")),
            "price": _to_float(data.get("price")),
            "status": data.get("status"),
            "message": "Success"
        }
    except Exception as e:
        return {
            "success": False,
            "order_id": order_id,
            "symbol": symbol,
            "side": "",
            "type": "",
            "amount": 0.0,
            "filled": 0.0,
            "price": 0.0,
            "status": "ERROR",
            "message": str(e)
        }


def get_open_orders(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取未成交订单列表
    """
    params = {}
    if symbol:
        params["symbol"] = symbol.upper()
        
    try:
        data = _send_request("GET", "/openOrders", params)
        result = []
        for order in data:
            result.append({
                "order_id": str(order.get("orderId")),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "type": order.get("type"),
                "amount": _to_float(order.get("origQty")),
                "filled": _to_float(order.get("executedQty")),
                "price": _to_float(order.get("price")),
                "status": order.get("status")
            })
        return result
    except Exception as e:
        print(f"Error getting open orders: {e}")
        return []


def get_account_info() -> Dict:
    """
    获取账户信息
    注意：Spot 账户没有权益(Equity)和未实现盈亏(Unrealized PnL)的概念，
    这里主要返回 USDT 的可用余额。
    """
    try:
        data = _send_request("GET", "/account", {})
        balances = data.get("balances", [])
        
        usdt_balance = 0.0
        total_balance_approx = 0.0
        
        for b in balances:
            asset = b.get("asset")
            free = _to_float(b.get("free"))
            locked = _to_float(b.get("locked"))
            total = free + locked
            
            if asset == "USDT":
                usdt_balance = free
                total_balance_approx += total # 简化处理，假设USDT价值为1
            # 注意：要计算准确的总权益(Total Equity)，需要获取所有资产的当前价格并折算为USDT
            # 这里为了性能和简化，仅返回 USDT 余额作为可用余额
            
        return {
            "success": True,
            "total_equity": total_balance_approx, # 仅供参考，不准确
            "available_balance": usdt_balance,
            "used_margin": 0.0,
            "unrealized_pnl": 0.0,
            "message": "Success"
        }
    except Exception as e:
        return {
            "success": False,
            "total_equity": 0.0,
            "available_balance": 0.0,
            "used_margin": 0.0,
            "unrealized_pnl": 0.0,
            "message": str(e)
        }


def get_positions(
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    获取持仓信息
    注意：Spot 接口返回的是非零余额的资产列表，模拟为持仓格式。
    """
    try:
        data = _send_request("GET", "/account", {})
        balances = data.get("balances", [])
        positions = []
        
        target_asset = None
        if symbol:
            # 简单的假设：symbol "BTCUSDT" -> asset "BTC"
            target_asset = symbol.replace("USDT", "").replace("BUSD", "")
            
        for b in balances:
            asset = b.get("asset")
            free = _to_float(b.get("free"))
            locked = _to_float(b.get("locked"))
            total = free + locked
            
            if total > 0:
                # 如果指定了 symbol，只返回对应的资产
                if target_asset and asset != target_asset:
                    continue
                    
                # 忽略 USDT/BUSD 等计价货币作为"持仓"
                if asset in ["USDT", "BUSD", "USDC"]:
                    continue

                positions.append({
                    "symbol": f"{asset}USDT", # 假设对 USDT
                    "side": "long",           # 现货只能做多
                    "size": total,
                    "entry_price": 0.0,       # 现货API不提供均价
                    "mark_price": 0.0,        # 需额外查询
                    "unrealized_pnl": 0.0,
                    "leverage": 1.0
                })
        return positions
    except Exception as e:
        print(f"Error getting positions: {e}")
        return []


def adjust_position(
    symbol: str,
    side: str,
    amount: float,
    price: Optional[float] = None
) -> Dict:
    """
    调整仓位
    对于现货：
    side="long" -> 买入 (BUY)
    side="short" -> 卖出 (SELL)
    """
    side = side.lower()
    binance_side = "BUY" if side == "long" else "SELL"
    
    if side == "short":
        binance_side = "SELL"
    elif side == "long":
        binance_side = "BUY"
    else:
        # 尝试直接使用传入的 side (如 "BUY", "SELL")
        binance_side = side.upper()

    if price:
        return place_limit_order(symbol, binance_side, amount, price)
    else:
        return place_market_order(symbol, binance_side, amount)


if __name__ == "__main__":
    def run_full_test():
        print("=" * 60)
        print("开始币安 REST API 全功能测试")
        print("=" * 60)

        symbol = "BTCUSDT"

        # 1. 账户信息
        print("\n[1] 测试 get_account_info()...")
        account = get_account_info()
        print(f"可用余额 (USDT): {account.get('available_balance')}")
        # print(json.dumps(account, indent=2))

        # 2. 下限价单（使用接近市价的价格，避免触发过滤器）
        last_price = _get_symbol_price(symbol)
        if last_price:
            price = round(last_price * 0.98, 2)  # 略低于市价，确保不过滤
        else:
            price = 15000.0  # 回退值
        amount = 0.001
        print(f"\n[2] 测试 place_limit_order({symbol}, \"BUY\", {amount}, {price})...")
        limit_order = place_limit_order(symbol, "BUY", amount, price)
        print(json.dumps(limit_order, indent=2))

        order_id = limit_order.get("order_id")
        if not order_id:
            print("下单失败，停止后续依赖订单ID的测试")
        else:
            # 3. 获取未成交订单
            print(f"\n[3] 测试 get_open_orders({symbol})...")
            open_orders = get_open_orders(symbol)
            print(f"当前挂单数量: {len(open_orders)}")
            for o in open_orders:
                print(f"  - ID: {o['order_id']}, 价格: {o['price']}, 数量: {o['amount']}")

            # 4. 查询订单状态
            print(f"\n[4] 测试 get_order_status({symbol}, {order_id})...")
            status = get_order_status(symbol, order_id)
            print(f"订单状态: {status.get('status')}")

            # 5. 撤销单个订单
            print(f"\n[5] 测试 cancel_order({symbol}, {order_id})...")
            cancel_res = cancel_order(symbol, order_id)
            print(f"撤单结果: {cancel_res.get('message')}")

    
        # 6. 下市价单 (买入) - 真实成交
        print(f"\n[6] 测试 place_market_order({symbol}, 'BUY', 0.001)...")
        market_order = place_market_order(symbol, "BUY", 0.001)
        print(f"市价单结果: {market_order.get('message')}, ID: {market_order.get('order_id')}")

        # 等待一下成交数据更新
        time.sleep(1)

        # 7. 获取持仓 (现货余额)
        print(f"\n[7] 测试 get_positions({symbol})...")
        positions = get_positions(symbol)
        print("当前持仓:")
        print(json.dumps(positions, indent=2))

        # 8. 调整仓位 (卖出刚才买入的)
        # adjust_position 在现货中: long -> buy, short -> sell
        print(f"\n[8] 测试 adjust_position({symbol}, 'short', 0.001) [即市价卖出]...")
        adjust_res = adjust_position(symbol, "short", 0.001) 
        print(f"调仓结果: {adjust_res.get('message')}")

        # 9. 撤销所有订单：先挂两个有效价位的限价单
        print(f"\n[9] 准备测试 cancel_all_orders: 先挂两个限价单...")
        orders_to_cancel = []
        if last_price:
            prices = [round(last_price * 0.9, 2), round(last_price * 0.88, 2)]
        else:
            prices = [12000.0, 11000.0]

        for p in prices:
            o = place_limit_order(symbol, "BUY", 0.001, p)
            if o.get("order_id"):
                orders_to_cancel.append(o.get("order_id"))
                print(f"挂单成功: {o.get('order_id')} @ {p}")
            else:
                print(f"挂单失败 @ {p}: {o.get('message')}")

        print(f"测试 cancel_all_orders({symbol})...")
        cancel_all = cancel_all_orders(symbol)
        print(f"撤销订单数量: {cancel_all.get('cancelled_count')}")
        print(f"结果信息: {cancel_all.get('message')}")

        # 订单管理器验证
        mgr = _get_order_manager()
        if mgr:
            all_orders = mgr.get_open_orders("binance")
            print(f"\n[10] 订单管理器校验: 当前本地未完成订单数(币安): {len(all_orders)}")
            if all_orders:
                print("示例订单:", all_orders[0])

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    run_full_test()
