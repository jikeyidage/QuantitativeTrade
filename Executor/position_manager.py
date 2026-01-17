"""
仓位管理
负责查询、增大、减小、平仓等仓位操作
"""
from typing import Dict, List, Optional
from exchanges.okx import get_positions as okx_get_positions, adjust_position as okx_adjust_position
from exchanges.binance import get_positions as binance_get_positions, adjust_position as binance_adjust_position
from exchanges.gate import get_positions as gate_get_positions, adjust_position as gate_adjust_position
from exchanges.dYdX import get_positions as dYdX_get_positions, adjust_position as dYdX_adjust_position
from exchanges.hyperliquid import get_positions as hyperliquid_get_positions, adjust_position as hyperliquid_adjust_position
from exchanges.serum import get_positions as serum_get_positions, adjust_position as serum_adjust_position
from order_sender import place_order


# 交易所查询和调整仓位函数映射
GET_POSITIONS_FUNCS = {
    "okx": okx_get_positions,
    "binance": binance_get_positions,
    "gate": gate_get_positions,
    "dYdX": dYdX_get_positions,
    "hyperliquid": hyperliquid_get_positions,
    "serum": serum_get_positions
}

ADJUST_POSITION_FUNCS = {
    "okx": okx_adjust_position,
    "binance": binance_adjust_position,
    "gate": gate_adjust_position,
    "dYdX": dYdX_adjust_position,
    "hyperliquid": hyperliquid_adjust_position,
    "serum": serum_adjust_position
}


class PositionManager:
    """
    仓位管理器
    负责查询、增大、减小、平仓等仓位操作
    """
    
    def get_position(self, exchange_name: str, symbol: str) -> Dict:
        """
        获取当前仓位
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
        
        返回:
            {
                "symbol": str,
                "side": str,          # "long", "short", "none"
                "size": float,        # 仓位大小
                "entry_price": float, # 开仓均价
                "mark_price": float,  # 标记价格
                "unrealized_pnl": float,  # 未实现盈亏
                "leverage": float     # 杠杆倍数
            }
        """
        get_positions_func = GET_POSITIONS_FUNCS.get(exchange_name)
        if get_positions_func is None:
            return {
                "symbol": symbol,
                "side": "none",
                "size": 0.0,
                "entry_price": 0.0,
                "mark_price": 0.0,
                "unrealized_pnl": 0.0,
                "leverage": 1.0
            }
        
        try:
            positions = get_positions_func(symbol)
            # 查找对应交易对的仓位
            for pos in positions:
                if pos.get("symbol") == symbol:
                    return pos
            
            # 如果没有找到，返回空仓位
            return {
                "symbol": symbol,
                "side": "none",
                "size": 0.0,
                "entry_price": 0.0,
                "mark_price": 0.0,
                "unrealized_pnl": 0.0,
                "leverage": 1.0
            }
        except Exception as e:
            print(f"获取仓位失败: {str(e)}")
            return {
                "symbol": symbol,
                "side": "none",
                "size": 0.0,
                "entry_price": 0.0,
                "mark_price": 0.0,
                "unrealized_pnl": 0.0,
                "leverage": 1.0
            }
    
    def increase_position(
        self,
        exchange_name: str,
        symbol: str,
        side: str,      # "long" 或 "short"
        amount: float,
        price: Optional[float] = None  # None表示市价
    ) -> Dict:
        """
        增大仓位（加仓）
        
        参数:
            exchange_name: 交易所名称
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
        if price is None:
            # 使用市价单加仓
            order_side = "buy" if side == "long" else "sell"
            result = place_order(exchange_name, symbol, order_side, "market", amount)
        else:
            # 使用限价单加仓
            order_side = "buy" if side == "long" else "sell"
            result = place_order(exchange_name, symbol, order_side, "limit", amount, price)
        
        return {
            "success": result.get("success", False),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "message": result.get("message", "")
        }
    
    def decrease_position(
        self,
        exchange_name: str,
        symbol: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        减小仓位（减仓）
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
            amount: 数量
            price: 价格，如果为None则使用市价
        
        返回:
            {
                "success": bool,
                "symbol": str,
                "amount": float,
                "message": str
            }
        """
        # 先获取当前仓位，确定是long还是short
        position = self.get_position(exchange_name, symbol)
        current_side = position.get("side", "none")
        
        if current_side == "none":
            return {
                "success": False,
                "symbol": symbol,
                "amount": amount,
                "message": "当前没有持仓，无法减仓"
            }
        
        # 减仓方向与当前持仓相反
        order_side = "sell" if current_side == "long" else "buy"
        
        if price is None:
            result = place_order(exchange_name, symbol, order_side, "market", amount)
        else:
            result = place_order(exchange_name, symbol, order_side, "limit", amount, price)
        
        return {
            "success": result.get("success", False),
            "symbol": symbol,
            "amount": amount,
            "message": result.get("message", "")
        }
    
    def close_position(
        self,
        exchange_name: str,
        symbol: str,
        price: Optional[float] = None
    ) -> Dict:
        """
        平仓（完全平仓）
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
            price: 价格，如果为None则使用市价
        
        返回:
            {
                "success": bool,
                "symbol": str,
                "message": str
            }
        """
        # 获取当前仓位
        position = self.get_position(exchange_name, symbol)
        current_size = position.get("size", 0.0)
        current_side = position.get("side", "none")
        
        if current_side == "none" or current_size == 0.0:
            return {
                "success": False,
                "symbol": symbol,
                "message": "当前没有持仓，无需平仓"
            }
        
        # 平仓方向与当前持仓相反
        order_side = "sell" if current_side == "long" else "buy"
        
        if price is None:
            result = place_order(exchange_name, symbol, order_side, "market", current_size)
        else:
            result = place_order(exchange_name, symbol, order_side, "limit", current_size, price)
        
        return {
            "success": result.get("success", False),
            "symbol": symbol,
            "message": result.get("message", "")
        }

