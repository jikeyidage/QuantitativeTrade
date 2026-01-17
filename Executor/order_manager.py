"""
本地订单管理
维护本地订单簿，记录所有已发送的订单
"""
from typing import Dict, List, Optional
import time
from exchanges.okx import get_order_status as okx_get_order_status, get_open_orders as okx_get_open_orders
from exchanges.binance import get_order_status as binance_get_order_status, get_open_orders as binance_get_open_orders
from exchanges.gate import get_order_status as gate_get_order_status, get_open_orders as gate_get_open_orders
from exchanges.dYdX import get_order_status as dYdX_get_order_status, get_open_orders as dYdX_get_open_orders
from exchanges.hyperliquid import get_order_status as hyperliquid_get_order_status, get_open_orders as hyperliquid_get_open_orders
from exchanges.serum import get_order_status as serum_get_order_status, get_open_orders as serum_get_open_orders


# 交易所查询函数映射
GET_ORDER_STATUS_FUNCS = {
    "okx": okx_get_order_status,
    "binance": binance_get_order_status,
    "gate": gate_get_order_status,
    "dYdX": dYdX_get_order_status,
    "hyperliquid": hyperliquid_get_order_status,
    "serum": serum_get_order_status
}

GET_OPEN_ORDERS_FUNCS = {
    "okx": okx_get_open_orders,
    "binance": binance_get_open_orders,
    "gate": gate_get_open_orders,
    "dYdX": dYdX_get_open_orders,
    "hyperliquid": hyperliquid_get_open_orders,
    "serum": serum_get_open_orders
}


class OrderManager:
    """
    订单管理器
    维护本地订单簿，记录所有已发送的订单
    """
    
    def __init__(self):
        """初始化订单管理器，维护内存中的订单字典"""
        self.orders = {}  # {order_id: order_info}
    
    def add_order(self, order_info: Dict):
        """
        添加订单到本地管理
        
        参数:
            order_info: {
                "order_id": str,
                "exchange": str,
                "symbol": str,
                "side": str,
                "type": str,
                "amount": float,
                "price": float,
                "status": str,  # "pending", "filled", "cancelled", "rejected"
                "timestamp": float
            }
        """
        if "order_id" not in order_info:
            raise ValueError("order_info 必须包含 order_id")
        
        if "timestamp" not in order_info:
            order_info["timestamp"] = time.time()
        
        self.orders[order_info["order_id"]] = order_info
    
    def update_order_status(self, exchange_name: str, order_id: str) -> Dict:
        """
        从交易所同步订单状态并更新本地记录
        
        参数:
            exchange_name: 交易所名称
            order_id: 订单ID
        
        返回:
            更新后的订单信息
        """
        if order_id not in self.orders:
            return {
                "success": False,
                "message": f"订单 {order_id} 不存在于本地记录中"
            }
        
        order_info = self.orders[order_id]
        symbol = order_info.get("symbol")
        
        get_status_func = GET_ORDER_STATUS_FUNCS.get(exchange_name)
        if get_status_func is None:
            return {
                "success": False,
                "message": f"不支持的交易所: {exchange_name}"
            }
        
        try:
            result = get_status_func(symbol, order_id)
            if result.get("success"):
                # 更新本地订单状态
                self.orders[order_id].update({
                    "status": result.get("status", order_info.get("status")),
                    "filled": result.get("filled", order_info.get("filled", 0))
                })
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"同步订单状态失败: {str(e)}"
            }
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        根据订单ID查询订单
        
        参数:
            order_id: 订单ID
        
        返回:
            订单信息，如果不存在则返回None
        """
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, exchange_name: str, symbol: str) -> List[Dict]:
        """
        获取某个交易对的所有订单
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
        
        返回:
            订单列表
        """
        return [
            order for order in self.orders.values()
            if order.get("exchange") == exchange_name and order.get("symbol") == symbol
        ]
    
    def get_open_orders(self, exchange_name: Optional[str] = None) -> List[Dict]:
        """
        获取所有未成交订单
        
        参数:
            exchange_name: 交易所名称，如果为None则返回所有交易所的未成交订单
        
        返回:
            未成交订单列表
        """
        open_orders = [
            order for order in self.orders.values()
            if order.get("status") in ["pending", "partially_filled"]
        ]
        
        if exchange_name:
            open_orders = [
                order for order in open_orders
                if order.get("exchange") == exchange_name
            ]
        
        return open_orders
    
    def sync_open_orders(self, exchange_name: str, symbol: Optional[str] = None):
        """
        从交易所同步未成交订单到本地
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对，如果为None则同步所有交易对的未成交订单
        """
        get_open_func = GET_OPEN_ORDERS_FUNCS.get(exchange_name)
        if get_open_func is None:
            return
        
        try:
            open_orders = get_open_func(symbol)
            for order in open_orders:
                order_info = {
                    "order_id": order.get("order_id"),
                    "exchange": exchange_name,
                    "symbol": order.get("symbol"),
                    "side": order.get("side"),
                    "type": order.get("type"),
                    "amount": order.get("amount"),
                    "filled": order.get("filled", 0),
                    "price": order.get("price"),
                    "status": order.get("status", "pending"),
                    "timestamp": time.time()
                }
                self.add_order(order_info)
        except Exception as e:
            print(f"同步未成交订单失败: {str(e)}")
