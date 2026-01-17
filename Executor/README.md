# 🧠 Quant Executor模块 

## 模块分工

### 层林染：
- /exchanges/gate.py   /exchanges/hyperliquid.py
- /Executor/position_manager.py    /Executor/risk_manager.py
  
### NPCharacter：
- /exchanges/binance.py   /exchanges/dYdX.py
- /Executor/canceler.py    /Executor/executor.py
  
### 皑轩：
- /exchanges/okx.py   /exchanges/serum.py
- /Executor/order_manager.py    /Executor/order_sender.py

## 📋 模块概述

Execution模块负责量化交易策略的执行，包括订单管理、风险控制、仓位管理等核心功能。本模块采用**统一接口设计**，所有交易所相关操作都通过 `exchanges/` 目录下的封装函数实现。

**重要原则：** 所有模块只需要 `import` 交易所封装好的函数，不需要直接调用交易所API。

---

## 🏗️ 模块架构

```
Execution/
├── exchanges/              # 交易所封装层（每个成员负责一个交易所）
│   ├── okx.py             # OKX交易所封装
│   ├── binance.py         # Binance交易所封装
│   ├── gate.py            # Gate.io交易所封装
│   ├── dYdX.py            # dYdX交易所封装
│   ├── hyperliquid.py     # Hyperliquid交易所封装
│   └── serum.py           # Serum交易所封装
│
├── canceler.py            # 撤单模块
├── order_manager.py       # 本地订单管理模块
├── order_sender.py        # 挂单模块
├── risk_manager.py        # 风险管理模块
├── position_manager.py    # 仓位管理模块
└── executor.py            # 执行循环模块（主控制器）
```

---

## 📦 各模块功能说明

### 1. **canceler.py** - 撤单执行器

#### 功能职责
- 撤销指定订单（单个订单）
- 批量撤销订单（多个订单）
- 撤销某个交易对的所有订单
- 撤销所有订单（紧急清仓场景）

#### 需要从 exchanges 导入的函数
```python
from exchanges.okx import cancel_order, cancel_all_orders
from exchanges.binance import cancel_order, cancel_all_orders
# ... 其他交易所
```

#### 需要实现的函数接口

```python
def cancel_order(exchange_name: str, symbol: str, order_id: str) -> dict:
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
    pass

def cancel_all_orders(exchange_name: str, symbol: str = None) -> dict:
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
    pass
```

#### 实现示例
```python
# canceler.py
from exchanges.okx import cancel_order as okx_cancel_order
from exchanges.binance import cancel_order as binance_cancel_order
# ... 导入其他交易所

EXCHANGES = {
    "okx": okx_cancel_order,
    "binance": binance_cancel_order,
    # ... 其他交易所
}

def cancel_order(exchange_name: str, symbol: str, order_id: str) -> dict:
    cancel_func = EXCHANGES.get(exchange_name)
    if not cancel_func:
        return {"success": False, "message": f"不支持的交易所: {exchange_name}"}
    
    return cancel_func(symbol, order_id)
```

---

### 2. **order_sender.py** - 挂单执行器

#### 功能职责
- 发送限价单（Limit Order）
- 发送市价单（Market Order）
- 发送止损单（Stop Loss Order）
- 发送止盈单（Take Profit Order）

#### 需要从 exchanges 导入的函数
```python
from exchanges.okx import place_limit_order, place_market_order
from exchanges.binance import place_limit_order, place_market_order
# ... 其他交易所
```

#### 需要实现的函数接口

```python
def place_order(
    exchange_name: str,
    symbol: str,
    side: str,           # "buy" 或 "sell"
    order_type: str,     # "limit", "market", "stop", "take_profit"
    amount: float,       # 数量
    price: float = None, # 价格（限价单必需）
    stop_price: float = None  # 止损/止盈价格
) -> dict:
    """
    发送订单
    
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
    pass
```

---

### 3. **order_manager.py** - 本地订单管理

#### 功能职责
- 维护本地订单簿（内存或文件）
- 记录所有已发送的订单
- 查询订单状态
- 同步交易所订单状态
- 提供订单查询接口（按订单ID、交易对、状态等）

#### 需要从 exchanges 导入的函数
```python
from exchanges.okx import get_order_status, get_open_orders
from exchanges.binance import get_order_status, get_open_orders
# ... 其他交易所
```

#### 需要实现的函数接口

```python
class OrderManager:
    def __init__(self):
        """初始化订单管理器，可以维护内存中的订单字典或使用文件/数据库"""
        self.orders = {}  # {order_id: order_info}
    
    def add_order(self, order_info: dict):
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
        pass
    
    def update_order_status(self, exchange_name: str, order_id: str):
        """
        从交易所同步订单状态并更新本地记录
        """
        pass
    
    def get_order(self, order_id: str) -> dict:
        """根据订单ID查询订单"""
        pass
    
    def get_orders_by_symbol(self, exchange_name: str, symbol: str) -> list:
        """获取某个交易对的所有订单"""
        pass
    
    def get_open_orders(self, exchange_name: str = None) -> list:
        """获取所有未成交订单"""
        pass
```

---

### 4. **risk_manager.py** - 风险管理

#### 功能职责
- 监控账户风险指标（持仓、保证金、盈亏等）
- 检查单笔订单风险（仓位限制、资金限制）
- 发送清仓信号（当风险超过阈值时）
- 限制最大仓位
- 限制单笔订单大小

#### 需要从 exchanges 导入的函数
```python
from exchanges.okx import get_account_info, get_positions
from exchanges.binance import get_account_info, get_positions
# ... 其他交易所
```

#### 需要实现的函数接口

```python
class RiskManager:
    def __init__(self, max_position_size: float = 0.1, max_loss_ratio: float = 0.05):
        """
        初始化风险管理器
        
        参数:
            max_position_size: 最大仓位比例（相对于总资金）
            max_loss_ratio: 最大亏损比例（触发清仓）
        """
        pass
    
    def check_order_risk(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> dict:
        """
        检查订单风险
        
        返回:
            {
                "allowed": bool,      # 是否允许下单
                "reason": str,        # 拒绝原因（如果不允许）
                "risk_level": str     # "low", "medium", "high"
            }
        """
        pass
    
    def check_account_risk(self, exchange_name: str) -> dict:
        """
        检查账户整体风险
        
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
        pass
    
    def send_liquidation_signal(self, exchange_name: str, symbol: str = None) -> dict:
        """
        发送清仓信号
        
        返回:
            {
                "signal": "liquidate",
                "exchange": str,
                "symbol": str,  # None表示清仓所有
                "timestamp": float
            }
        """
        pass
```

---

### 5. **position_manager.py** - 仓位管理

#### 功能职责
- 查询当前仓位
- 增大仓位（加仓）
- 减小仓位（减仓）
- 平仓（完全平仓）
- 计算仓位大小和盈亏

#### 需要从 exchanges 导入的函数
```python
from exchanges.okx import get_positions, adjust_position
from exchanges.binance import get_positions, adjust_position
# ... 其他交易所
```

#### 需要实现的函数接口

```python
class PositionManager:
    def get_position(self, exchange_name: str, symbol: str) -> dict:
        """
        获取当前仓位
        
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
        pass
    
    def increase_position(
        self,
        exchange_name: str,
        symbol: str,
        side: str,      # "long" 或 "short"
        amount: float,
        price: float = None  # None表示市价
    ) -> dict:
        """
        增大仓位（加仓）
        """
        pass
    
    def decrease_position(
        self,
        exchange_name: str,
        symbol: str,
        amount: float,
        price: float = None
    ) -> dict:
        """
        减小仓位（减仓）
        """
        pass
    
    def close_position(
        self,
        exchange_name: str,
        symbol: str,
        price: float = None
    ) -> dict:
        """
        平仓（完全平仓）
        """
        pass
```

---

### 6. **executor.py** - 执行循环（主控制器）

#### 功能职责
- 整合所有模块，实现策略执行的主循环
- 接收策略信号（买入/卖出/平仓）
- 协调各个模块执行交易
- 处理风险信号和清仓指令
- 日志记录和错误处理

#### 需要导入的模块
```python
from canceler import cancel_order, cancel_all_orders
from order_sender import place_order
from order_manager import OrderManager
from risk_manager import RiskManager
from position_manager import PositionManager
```

#### 需要实现的函数接口

```python
class Executor:
    def __init__(self):
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.position_manager = PositionManager()
    
    def execute_signal(
        self,
        exchange_name: str,
        symbol: str,
        signal: dict  # {"action": "buy/sell/close", "amount": float, "price": float}
    ) -> dict:
        """
        执行策略信号
        
        流程:
        1. 风险检查
        2. 发送订单
        3. 记录到订单管理器
        4. 返回执行结果
        """
        pass
    
    def handle_risk_signal(self, risk_signal: dict):
        """
        处理风险信号（如清仓指令）
        """
        pass
    
    def run(self):
        """
        主循环（可选，如果需要持续运行）
        """
        pass
```

---

## 🔌 exchanges/ 目录开发规范

### 每个交易所文件需要实现的函数

每个成员在 `exchanges/` 目录下负责一个交易所，需要实现以下**统一接口**：

#### 1. 订单相关
```python
# 下单
def place_limit_order(symbol: str, side: str, amount: float, price: float) -> dict
def place_market_order(symbol: str, side: str, amount: float) -> dict

# 撤单
def cancel_order(symbol: str, order_id: str) -> dict
def cancel_all_orders(symbol: str = None) -> dict

# 查询订单
def get_order_status(symbol: str, order_id: str) -> dict
def get_open_orders(symbol: str = None) -> list
```

#### 2. 账户相关
```python
def get_account_info() -> dict  # 账户余额、保证金等
def get_positions(symbol: str = None) -> list  # 持仓信息
```

#### 3. 仓位相关
```python
def adjust_position(symbol: str, side: str, amount: float, price: float = None) -> dict
```

### 返回数据格式规范

所有函数返回的 `dict` 应该包含：
- `success`: bool - 操作是否成功
- `data`: dict/list - 实际数据
- `message`: str - 错误信息（失败时）

---

## 📝 开发流程

1. **第一步：完善 exchanges 封装**
   - 每个成员先完成自己负责的交易所封装
   - 确保所有函数接口统一

2. **第二步：实现功能模块**
   - 各模块开发者从 `exchanges/` 导入函数
   - 实现模块功能，不直接调用交易所API

3. **第三步：集成测试**
   - 在 `executor.py` 中整合所有模块
   - 进行端到端测试

---

## ⚠️ 注意事项

1. **统一接口**：所有交易所函数必须遵循相同的接口规范
2. **错误处理**：所有函数都要有完善的异常处理
3. **日志记录**：重要操作都要记录日志
4. **数据格式**：返回数据格式要统一，便于其他模块使用
5. **测试**：每个模块都要有单元测试

---

