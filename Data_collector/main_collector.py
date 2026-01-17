"""
main_collector.py
=================
统一启动 OKX / Binance / Gate 三个交易所的订单簿采集任务。
每个交易所文件都实现一个 orderbook(symbol) 函数，
该函数返回最新订单簿dict。
"""
import time
import os
import json
from exchanges.okx_orderbook import orderbook as okx_orderbook, contract_information as okx_contract_information
from exchanges.binance_orderbook import orderbook as binance_orderbook, contract_information as binance_contract_information
from exchanges.gate_orderbook import orderbook as gate_orderbook, contract_information as gate_contract_information
from exchanges.dYdX_orderbook import orderbook as dYdX_orderbook, contract_information as dYdX_contract_information
from exchanges.hyperliquid_orderbook import orderbook as hyperliquid_orderbook, contract_information as hyperliquid_contract_information
from exchanges.serum_orderbook import orderbook as serum_orderbook, contract_information as serum_contract_information


EXCHANGES = {
    "okx": {
        "orderbook": okx_orderbook,
        "contract_information": okx_contract_information
    },
    "binance": {
        "orderbook": binance_orderbook,
        "contract_information": binance_contract_information
    },
    "gate": {
        "orderbook": gate_orderbook,
        "contract_information": gate_contract_information
    },
    "dYdX": {
        "orderbook": dYdX_orderbook,
        "contract_information": dYdX_contract_information
    },
    "serum": {
        "orderbook": serum_orderbook,
        "contract_information": serum_contract_information
    },
    "hyperliquid": {
        "orderbook": hyperliquid_orderbook,
        "contract_information": hyperliquid_contract_information
    }
}
def collector_worker(exchange_name: str, symbol: str) -> tuple[dict, dict]:
    """
    获取该交易所某个交易对的订单簿
    返回标准化后的dict结构
    """
    exchange_info = EXCHANGES.get(exchange_name)
    if exchange_info is None:
        raise ValueError(f"Unsupported exchange: {exchange_name}")

    orderbook_func = exchange_info.get("orderbook")
    if orderbook_func is None:
        raise ValueError(f"Unsupported exchange: {exchange_name}")

    contract_information_func = exchange_info.get("contract_information")
    if contract_information_func is None:
        raise ValueError(f"Unsupported exchange: {exchange_name}")

    data = orderbook_func(symbol)
    contract_information = contract_information_func(symbol)
    return data, contract_information

def local_orderbook(exchange_name: str, symbol: str, data: dict, contract_information: dict):
    """
    获取本地订单簿数据
    返回标准化后的dict结构
    """
    orderbook_path = f"./orderbook/{exchange_name}/{symbol}.json"
    os.makedirs(os.path.dirname(orderbook_path), exist_ok=True)
    with open(orderbook_path, "w") as f:
        json.dump(data, f)
    print(f"订单簿数据已保存到 {orderbook_path}")
    contract_information_path = f"./contract_information/{exchange_name}/{symbol}.json"
    os.makedirs(os.path.dirname(contract_information_path), exist_ok=True)
    with open(contract_information_path, "w") as f:
        json.dump(contract_information, f)
    print(f"合约信息数据已保存到 {contract_information_path}")


if __name__ == "__main__":
    exchange_name = input("请输入你的交易所名单（okx/binance/gate/dYdX/serum/hyperliquid）")
    symbol = input("请输入要查询的合约（例如 BTC-USDT ETH-USDT OKB-USDT）：")
    current_time = int(time.time())
    data, contract_information = collector_worker(exchange_name, symbol)
    final_time = int(time.time())
    print(f"数据获取时间：{final_time - current_time} 秒")
    local_orderbook(exchange_name, symbol, data, contract_information)

    


