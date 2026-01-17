"""
执行循环
策略发信号后执行挂单/撤单，整合所有模块的主控制器
"""
from typing import Dict, Optional
from canceler import cancel_order, cancel_all_orders
from order_sender import place_order
from order_manager import OrderManager
from risk_manager import RiskManager
from position_manager import PositionManager


class Executor:
    """
    执行器
    整合所有模块，实现策略执行的主循环
    """
    
    def __init__(self):
        """初始化执行器"""
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.position_manager = PositionManager()
    
    def execute_signal(
        self,
        exchange_name: str,
        symbol: str,
        signal: Dict  # {"action": "buy/sell/close", "amount": float, "price": float, "order_type": str}
    ) -> Dict:
        """
        执行策略信号
        
        流程:
        1. 风险检查
        2. 发送订单
        3. 记录到订单管理器
        4. 返回执行结果
        
        参数:
            exchange_name: 交易所名称
            symbol: 交易对
            signal: 策略信号
                {
                    "action": str,      # "buy", "sell", "close"
                    "amount": float,    # 数量
                    "price": float,     # 价格（可选，限价单需要）
                    "order_type": str   # "limit", "market"（可选，默认"limit"）
                }
        
        返回:
            {
                "success": bool,
                "order_id": str,
                "message": str
            }
        """
        action = signal.get("action")
        amount = signal.get("amount", 0)
        price = signal.get("price")
        order_type = signal.get("order_type", "limit")
        
        if action not in ["buy", "sell", "close"]:
            return {
                "success": False,
                "order_id": None,
                "message": f"不支持的操作: {action}"
            }
        
        # 1. 风险检查（如果是下单操作）
        if action in ["buy", "sell"] and price:
            risk_check = self.risk_manager.check_order_risk(
                exchange_name, symbol, action, amount, price
            )
            if not risk_check.get("allowed"):
                return {
                    "success": False,
                    "order_id": None,
                    "message": f"风险检查未通过: {risk_check.get('reason')}"
                }
        
        # 2. 执行操作
        if action == "close":
            # 平仓操作
            result = self.position_manager.close_position(exchange_name, symbol, price)
            return {
                "success": result.get("success", False),
                "order_id": None,
                "message": result.get("message", "")
            }
        else:
            # 下单操作
            result = place_order(
                exchange_name,
                symbol,
                action,
                order_type,
                amount,
                price
            )
            
            # 3. 记录到订单管理器
            if result.get("success") and result.get("order_id"):
                order_info = {
                    "order_id": result.get("order_id"),
                    "exchange": exchange_name,
                    "symbol": symbol,
                    "side": action,
                    "type": order_type,
                    "amount": amount,
                    "price": price,
                    "status": "pending",
                    "timestamp": None
                }
                self.order_manager.add_order(order_info)
            
            return {
                "success": result.get("success", False),
                "order_id": result.get("order_id"),
                "message": result.get("message", "")
            }
    
    def handle_risk_signal(self, risk_signal: Dict) -> Dict:
        """
        处理风险信号（如清仓指令）
        
        参数:
            risk_signal: {
                "signal": "liquidate",
                "exchange": str,
                "symbol": str  # None表示清仓所有
            }
        
        返回:
            {
                "success": bool,
                "message": str
            }
        """
        if risk_signal.get("signal") != "liquidate":
            return {
                "success": False,
                "message": f"不支持的风险信号: {risk_signal.get('signal')}"
            }
        
        exchange_name = risk_signal.get("exchange")
        symbol = risk_signal.get("symbol")
        
        if symbol:
            # 清仓指定交易对
            result = self.position_manager.close_position(exchange_name, symbol)
            return {
                "success": result.get("success", False),
                "message": result.get("message", "")
            }
        else:
            # 清仓所有交易对
            # 先撤销所有未成交订单
            cancel_result = cancel_all_orders(exchange_name)
            
            # 获取所有持仓并平仓
            # TODO: 实现获取所有持仓并逐一平仓的逻辑
            return {
                "success": cancel_result.get("success", False),
                "message": "清仓所有交易对（部分功能待实现）"
            }
    
    def run(self):
        """
        主循环（可选，如果需要持续运行）
        可以在这里实现持续监控策略信号、风险检查等
        """
        # TODO: 实现主循环逻辑
        # 例如：
        # while True:
        #     # 1. 检查风险
        #     # 2. 接收策略信号
        #     # 3. 执行信号
        #     # 4. 更新订单状态
        #     pass
        while True:
            self.handle_risk_signal({})  # 占位符
