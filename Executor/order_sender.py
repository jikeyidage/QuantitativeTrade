"""
挂单执行器
负责发送订单的功能
"""
from typing import Dict, Optional
from exchanges.okx import place_limit_order as okx_place_limit_order, place_market_order as okx_place_market_order
from exchanges.binance import place_limit_order as binance_place_limit_order, place_market_order as binance_place_market_order
from exchanges.gate import place_limit_order as gate_place_limit_order, place_market_order as gate_place_market_order
from exchanges.dYdX import place_limit_order as dYdX_place_limit_order, place_market_order as dYdX_place_market_order
from exchanges.hyperliquid import place_limit_order as hyperliquid_place_limit_order, place_market_order as hyperliquid_place_market_order
from exchanges.serum import place_limit_order as serum_place_limit_order, place_market_order as serum_place_market_order


# 交易所下单函数映射
PLACE_LIMIT_ORDER_FUNCS = {
    "okx": okx_place_limit_order,
    "binance": binance_place_limit_order,
    "gate": gate_place_limit_order,
    "dYdX": dYdX_place_limit_order,
    "hyperliquid": hyperliquid_place_limit_order,
    "serum": serum_place_limit_order
}

PLACE_MARKET_ORDER_FUNCS = {
    "okx": okx_place_market_order,
    "binance": binance_place_market_order,
    "gate": gate_place_market_order,
    "dYdX": dYdX_place_market_order,
    "hyperliquid": hyperliquid_place_market_order,
    "serum": serum_place_market_order
}


def place_order(
    exchange_name: str,
    symbol: str,
    side: str,           # "buy" 或 "sell"
    order_type: str,     # "limit", "market", "stop", "take_profit"
    amount: float,       # 数量
    price: Optional[float] = None, # 价格（限价单必需）
    stop_price: Optional[float] = None  # 止损/止盈价格
) -> Dict:
    """
    发送订单
    
    参数:
        exchange_name: 交易所名称
        symbol: 交易对
        side: 方向 ("buy" 或 "sell")
        order_type: 订单类型 ("limit", "market", "stop", "take_profit")
        amount: 数量
        price: 价格（限价单必需）
        stop_price: 止损/止盈价格（止损/止盈单必需）
    
    返回:
        {
            "success": bool,
            "order_id": str,      # 订单ID（成功时）
            "symbol": str,
            "side": str,
            "amount": float,
            "price": float,
            "message": str        # 错误信息（如果失败）
        }
    """
    if order_type == "limit":
        if price is None:
            return {
                "success": False,
                "order_id": None,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": None,
                "message": "限价单必须指定价格"
            }
        
        place_func = PLACE_LIMIT_ORDER_FUNCS.get(exchange_name)
        if place_func is None:
            return {
                "success": False,
                "order_id": None,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "message": f"不支持的交易所: {exchange_name}"
            }
        
        try:
            result = place_func(symbol, side, amount, price)
            return result
        except Exception as e:
            return {
                "success": False,
                "order_id": None,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "message": f"下单失败: {str(e)}"
            }
    
    elif order_type == "market":
        place_func = PLACE_MARKET_ORDER_FUNCS.get(exchange_name)
        if place_func is None:
            return {
                "success": False,
                "order_id": None,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": None,
                "message": f"不支持的交易所: {exchange_name}"
            }
        
        try:
            result = place_func(symbol, side, amount)
            return result
        except Exception as e:
            return {
                "success": False,
                "order_id": None,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": None,
                "message": f"下单失败: {str(e)}"
            }
    
    elif order_type in ["stop", "take_profit"]:
        # TODO: 实现止损/止盈单（需要根据各交易所API实现）
        return {
            "success": False,
            "order_id": None,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": stop_price,
            "message": f"暂不支持 {order_type} 订单类型"
        }
    
    else:
        return {
            "success": False,
            "order_id": None,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "message": f"不支持的订单类型: {order_type}"
        }
