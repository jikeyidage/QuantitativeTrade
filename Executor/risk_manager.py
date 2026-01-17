"""
风险管理
监控账户风险指标，发送清仓信号
"""
from typing import Dict, Optional
import time
from exchanges.okx import get_account_info as okx_get_account_info, get_positions as okx_get_positions
from exchanges.binance import get_account_info as binance_get_account_info, get_positions as binance_get_positions
from exchanges.gate import get_account_info as gate_get_account_info, get_positions as gate_get_positions
from exchanges.dYdX import get_account_info as dYdX_get_account_info, get_positions as dYdX_get_positions
from exchanges.hyperliquid import get_account_info as hyperliquid_get_account_info, get_positions as hyperliquid_get_positions
from exchanges.serum import get_account_info as serum_get_account_info, get_positions as serum_get_positions


# 交易所查询函数映射
GET_ACCOUNT_INFO_FUNCS = {
    "okx": okx_get_account_info,
    "binance": binance_get_account_info,
    "gate": gate_get_account_info,
    "dYdX": dYdX_get_account_info,
    "hyperliquid": hyperliquid_get_account_info,
    "serum": serum_get_account_info
}

GET_POSITIONS_FUNCS = {
    "okx": okx_get_positions,
    "binance": binance_get_positions,
    "gate": gate_get_positions,
    "dYdX": dYdX_get_positions,
    "hyperliquid": hyperliquid_get_positions,
    "serum": serum_get_positions
}


class RiskManager:
    """
    风险管理器
    监控账户风险指标，检查订单风险，发送清仓信号
    """
    
    def __init__(self, max_position_size: float = 0.1, max_loss_ratio: float = 0.05):
        """
        初始化风险管理器
        
        参数:
            max_position_size: 最大仓位比例（相对于总资金），默认10%
            max_loss_ratio: 最大亏损比例（触发清仓），默认5%
        """
        self.max_position_size = max_position_size
        self.max_loss_ratio = max_loss_ratio
    
    def check_order_risk(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> Dict:
        """
        检查订单风险
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
            side: 方向 ("buy" 或 "sell")
            amount: 数量
            price: 价格
        
        返回:
            {
                "allowed": bool,      # 是否允许下单
                "reason": str,        # 拒绝原因（如果不允许）
                "risk_level": str     # "low", "medium", "high"
            }
        """
        try:
            # 获取账户信息
            get_account_func = GET_ACCOUNT_INFO_FUNCS.get(exchange_name)
            if get_account_func is None:
                return {
                    "allowed": False,
                    "reason": f"不支持的交易所: {exchange_name}",
                    "risk_level": "high"
                }
            
            account_info = get_account_func()
            if not account_info.get("success"):
                return {
                    "allowed": False,
                    "reason": "无法获取账户信息",
                    "risk_level": "high"
                }
            
            total_equity = account_info.get("total_equity", 0)
            available_balance = account_info.get("available_balance", 0)
            
            # 计算订单价值
            order_value = amount * price
            
            # 检查1: 订单价值是否超过最大仓位比例
            if order_value > total_equity * self.max_position_size:
                return {
                    "allowed": False,
                    "reason": f"订单价值 {order_value} 超过最大仓位限制 {total_equity * self.max_position_size}",
                    "risk_level": "high"
                }
            
            # 检查2: 可用余额是否足够
            if order_value > available_balance:
                return {
                    "allowed": False,
                    "reason": f"可用余额不足，需要 {order_value}，可用 {available_balance}",
                    "risk_level": "high"
                }
            
            # 检查3: 风险等级评估
            position_ratio = order_value / total_equity if total_equity > 0 else 0
            if position_ratio > 0.08:
                risk_level = "high"
            elif position_ratio > 0.05:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "allowed": True,
                "reason": "",
                "risk_level": risk_level
            }
        
        except Exception as e:
            return {
                "allowed": False,
                "reason": f"风险检查失败: {str(e)}",
                "risk_level": "high"
            }
    
    def check_account_risk(self, exchange_name: str) -> Dict:
        """
        检查账户整体风险
        
        参数:
            exchange_name: 交易所名称
        
        返回:
            {
                "risk_level": str,    # "safe", "warning", "danger"
                "should_liquidate": bool,  # 是否需要清仓
                "message": str,
                "metrics": {
                    "total_equity": float,
                    "used_margin": float,
                    "unrealized_pnl": float,
                    "margin_ratio": float
                }
            }
        """
        try:
            get_account_func = GET_ACCOUNT_INFO_FUNCS.get(exchange_name)
            get_positions_func = GET_POSITIONS_FUNCS.get(exchange_name)
            
            if get_account_func is None or get_positions_func is None:
                return {
                    "risk_level": "danger",
                    "should_liquidate": False,
                    "message": f"不支持的交易所: {exchange_name}",
                    "metrics": {}
                }
            
            account_info = get_account_func()
            if not account_info.get("success"):
                return {
                    "risk_level": "danger",
                    "should_liquidate": False,
                    "message": "无法获取账户信息",
                    "metrics": {}
                }
            
            total_equity = account_info.get("total_equity", 0)
            used_margin = account_info.get("used_margin", 0)
            unrealized_pnl = account_info.get("unrealized_pnl", 0)
            
            # 计算保证金率
            margin_ratio = used_margin / total_equity if total_equity > 0 else 0
            
            # 计算亏损比例
            loss_ratio = abs(unrealized_pnl) / total_equity if total_equity > 0 and unrealized_pnl < 0 else 0
            
            # 判断风险等级
            should_liquidate = False
            if loss_ratio >= self.max_loss_ratio or margin_ratio > 0.9:
                risk_level = "danger"
                should_liquidate = True
                message = f"风险过高：亏损比例 {loss_ratio:.2%}，保证金率 {margin_ratio:.2%}"
            elif loss_ratio >= self.max_loss_ratio * 0.7 or margin_ratio > 0.7:
                risk_level = "warning"
                message = f"风险警告：亏损比例 {loss_ratio:.2%}，保证金率 {margin_ratio:.2%}"
            else:
                risk_level = "safe"
                message = "账户风险正常"
            
            return {
                "risk_level": risk_level,
                "should_liquidate": should_liquidate,
                "message": message,
                "metrics": {
                    "total_equity": total_equity,
                    "used_margin": used_margin,
                    "unrealized_pnl": unrealized_pnl,
                    "margin_ratio": margin_ratio
                }
            }
        
        except Exception as e:
            return {
                "risk_level": "danger",
                "should_liquidate": False,
                "message": f"风险检查失败: {str(e)}",
                "metrics": {}
            }
    
    def send_liquidation_signal(self, exchange_name: str, symbol: Optional[str] = None) -> Dict:
        """
        发送清仓信号
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对，如果为None表示清仓所有
        
        返回:
            {
                "signal": "liquidate",
                "exchange": str,
                "symbol": str,  # None表示清仓所有
                "timestamp": float
            }
        """
        return {
            "signal": "liquidate",
            "exchange": exchange_name,
            "symbol": symbol,
            "timestamp": time.time()
        }
