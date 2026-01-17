"""
Serum交易所封装
实现统一的交易接口函数
"""
from typing import Dict, List, Optional


def place_limit_order(
    symbol: str,
    side: str,
    amount: float,
    price: float
) -> Dict:
    """
    发送限价单
    
    参数:
        symbol: 交易对
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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")


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
    raise NotImplementedError("请在 exchanges/serum.py 中实现此函数")

