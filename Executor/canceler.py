"""
撤单执行器
负责撤销订单的功能
"""
from typing import Dict, Optional
from exchanges.okx import cancel_order as okx_cancel_order, cancel_all_orders as okx_cancel_all_orders
from exchanges.binance import cancel_order as binance_cancel_order, cancel_all_orders as binance_cancel_all_orders
from exchanges.gate import cancel_order as gate_cancel_order, cancel_all_orders as gate_cancel_all_orders
from exchanges.dYdX import cancel_order as dYdX_cancel_order, cancel_all_orders as dYdX_cancel_all_orders
from exchanges.hyperliquid import cancel_order as hyperliquid_cancel_order, cancel_all_orders as hyperliquid_cancel_all_orders
from exchanges.serum import cancel_order as serum_cancel_order, cancel_all_orders as serum_cancel_all_orders


# 交易所撤单函数映射
CANCEL_ORDER_FUNCS = {
    "okx": okx_cancel_order,
    "binance": binance_cancel_order,
    "gate": gate_cancel_order,
    "dYdX": dYdX_cancel_order,
    "hyperliquid": hyperliquid_cancel_order,
    "serum": serum_cancel_order
}

CANCEL_ALL_ORDERS_FUNCS = {
    "okx": okx_cancel_all_orders,
    "binance": binance_cancel_all_orders,
    "gate": gate_cancel_all_orders,
    "dYdX": dYdX_cancel_all_orders,
    "hyperliquid": hyperliquid_cancel_all_orders,
    "serum": serum_cancel_all_orders
}


def cancel_order(exchange_name: str, symbol: str, order_id: str) -> Dict:
    """
    撤销单个订单
    
    参数:
        exchange_name: 交易所名称 (如 "okx", "binance", "gate")
        symbol: 交易对 (如 "BTC-USDT")
        order_id: 订单ID
    
    返回:
        {
            "success": bool,      # 是否成功
            "order_id": str,      # 订单ID
            "message": str        # 错误信息（如果失败）
        }
    """
    cancel_func = CANCEL_ORDER_FUNCS.get(exchange_name)
    if cancel_func is None:
        return {
            "success": False,
            "order_id": order_id,
            "message": f"不支持的交易所: {exchange_name}"
        }
    
    try:
        result = cancel_func(symbol, order_id)
        return result
    except Exception as e:
        return {
            "success": False,
            "order_id": order_id,
            "message": f"撤单失败: {str(e)}"
        }


def cancel_all_orders(exchange_name: str, symbol: Optional[str] = None) -> Dict:
    """
    撤销订单（支持撤销某个交易对或所有交易对）
    
    参数:
        exchange_name: 交易所名称
        symbol: 交易对，如果为None则撤销所有交易对的订单
    
    返回:
        {
            "success": bool,
            "cancelled_count": int,  # 撤销的订单数量
            "message": str
        }
    """
    cancel_all_func = CANCEL_ALL_ORDERS_FUNCS.get(exchange_name)
    if cancel_all_func is None:
        return {
            "success": False,
            "cancelled_count": 0,
            "message": f"不支持的交易所: {exchange_name}"
        }
    
    try:
        result = cancel_all_func(symbol)
        return result
    except Exception as e:
        return {
            "success": False,
            "cancelled_count": 0,
            "message": f"批量撤单失败: {str(e)}"
        }
