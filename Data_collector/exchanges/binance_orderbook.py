import json
import asyncio
import requests
import websockets

BASE_URL = "https://fapi.binance.com"
WS_URL = "wss://fstream.binance.com/ws"

# REST 快照部分
def get_symbols(inst_type: str = "SWAP",
                base_currencies: list[str] | None = None,
                quote_currency: str | None = "USDT") -> list[str]:
    """
    获取 Binance 的交易对 symbol 列表
    """
    url = f"{BASE_URL}/fapi/v1/exchangeInfo"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

    symbols = []
    for item in data.get("symbols", []):
        # 筛选合约类型: SWAP 对应 Binance 的 PERPETUAL
        if inst_type == "SWAP" and item.get("contractType") != "PERPETUAL":
            continue
        if item.get("status") != "TRADING":
            continue
        
        # 筛选 Quote Currency
        if quote_currency and item.get("quoteAsset") != quote_currency:
            continue
        
        # 筛选 Base Currency
        if base_currencies and item.get("baseAsset") not in base_currencies:
            continue
        
        symbols.append(item["symbol"])
    
    return symbols


# WebSocket 实时部分
async def subscribe_tickers(symbols: list[str]):
    """
    订阅指定交易对的实时ticker（行情）数据
    """
    async with websockets.connect(WS_URL) as ws:
        # 构造订阅请求
        # Binance stream name format: <symbol>@ticker (lowercase)
        params = [f"{s.lower()}@ticker" for s in symbols]
        sub_msg = {
            "method": "SUBSCRIBE",
            "params": params,
            "id": 1
        }
        await ws.send(json.dumps(sub_msg))
        print(f"已订阅: {symbols}")

        # 持续接收推送数据
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                
                # Binance ticker event
                # {"e":"24hrTicker", "s":"BTCUSDT", "c":"last", "v":"vol", ...}
                if data.get("e") == "24hrTicker":
                    inst = data["s"]
                    last = data["c"]
                    vol = data["v"] # base asset volume
                    print(f"{inst} 最新价: {last}  24h成交量: {vol}")
                elif "result" in data and data["result"] is None:
                    # Subscription confirmation
                    pass
            except Exception as e:
                print(f"WebSocket 错误: {e}")
                break

def contract_information(symbol: str, client=None) -> dict:
    """
    获取 Binance 永续合约的详细信息
    参数:
        symbol: 交易对名称，格式为 "BTC-USDT"
        client: 未使用，保持接口一致性
    返回:
        合约信息的字典，包含合约的所有详细信息
        如果获取失败，返回空字典 {}
    """
    return {}


def orderbook(symbol: str) -> dict:
    '''
    获取 Binance 订单簿快照
    输入：symbol 交易对名称，比如 "BTCUSDT" 或 "BTC-USDT"
    输出：标准字典结构 {"bids": [], "asks": []}
    '''
    # Binance API requires symbol without hyphens, e.g. BTCUSDT
    clean_symbol = symbol.replace("-", "").upper()
    url = f"{BASE_URL}/fapi/v1/depth"
    params = {"symbol": clean_symbol, "limit": 10}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # 格式化为统一结构
        bids = [[float(p), float(q)] for p, q in data.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in data.get("asks", [])]
        
        return {
            "bids": bids,
            "asks": asks
        }
    except Exception as e:
        print(f"获取订单簿失败 {symbol}: {e}")
        return {"bids": [], "asks": []}


if __name__ == "__main__":
    base_coins = ["BTC", "ETH"]
    # 获取符合条件的交易对
    symbols = get_symbols(inst_type="SWAP", base_currencies=base_coins)
    print("获取到的交易对:", symbols)

    if symbols:
        # 测试 REST 订单簿
        print(f"\nTesting orderbook for {symbols[0]}...")
        ob = orderbook(symbols[0])
        print(f"Bids: {ob['bids'][:2]}")
        print(f"Asks: {ob['asks'][:2]}")

        # 测试 WebSocket
        print("\nStarting WebSocket...")
        try:
            asyncio.run(subscribe_tickers(symbols))
        except KeyboardInterrupt:
            print("Stopped.")
