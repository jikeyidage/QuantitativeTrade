import json
import asyncio
import requests
import websockets

BASE_URL = "https://www.okx.com"
WS_URL = "wss://ws.okx.com:8443/ws/v5/public"


# === 获取交易对 ===
def get_symbols(inst_type: str = "SWAP",
                base_currencies: list[str] | None = None,
                quote_currency: str | None = "USDT") -> dict:
    """
    获取 OKX 的交易对 symbol 映射
    返回格式：
        {
            "BTC-USDT": "BTC-USDT-SWAP",
            "ETH-USDT": "ETH-USDT-SWAP"
        }
    """
    url = f"{BASE_URL}/api/v5/public/instruments?instType={inst_type}"
    resp = requests.get(url)
    data = resp.json()

    if data.get("code") != "0":
        raise Exception(f"Error fetching symbols: {data}")

    instruments = data["data"]

    if base_currencies:
        instruments = [
            i for i in instruments
            if i["instId"].split("-")[0] in base_currencies
            and i["instId"].split("-")[1] == quote_currency
        ]

    mapping = {}
    for i in instruments:
        okx_symbol = i["instId"]
        base, quote = okx_symbol.split("-")[0], okx_symbol.split("-")[1]
        std_symbol = f"{base}-{quote}"
        mapping[std_symbol] = okx_symbol

    return mapping


# === 获取合约信息 ===
def contract_information(symbol: str, client=None) -> dict:
    """
    获取 OKX 永续合约的详细信息
    参数:
        symbol: 交易对名称，格式为 "BTC-USDT"
        client: 未使用，保持接口一致性
    返回:
        合约信息的字典，包含合约的所有详细信息
        如果获取失败，返回空字典 {}
    """
    return {}


# === 获取订单簿 ===
def orderbook(symbol: str) -> dict:
    """
    返回一个静态订单簿（自动完成 symbol 映射）
    输入: "BTC-USDT"
    输出: {
        "bids": [[price, size], ...],
        "asks": [[price, size], ...]
    }
    """
    # Step 1: 建立映射（缓存静态变量以避免多次请求）
    if not hasattr(orderbook, "_symbol_map"):
        try:
            print("🔄 初始化交易对映射中...")
            orderbook._symbol_map = get_symbols(inst_type="SWAP")
            print("✅ 交易对映射完成")
        except Exception as e:
            print(f"❌ 获取 symbol 映射失败: {e}")
            return {"bids": [], "asks": []}

    symbol_map = orderbook._symbol_map
    okx_symbol = symbol_map.get(symbol, symbol)

    # Step 2: 获取订单簿快照
    url = f"{BASE_URL}/api/v5/market/books?instId={okx_symbol}&sz=10"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("code") != "0":
            print(f"❌ 获取订单簿失败: {data}")
            return {"bids": [], "asks": []}

        book = data["data"][0]
        bids = [[float(p), float(s)] for p, s, *_ in book["bids"][:10]]
        asks = [[float(p), float(s)] for p, s, *_ in book["asks"][:10]]

        return {"bids": bids, "asks": asks}

    except Exception as e:
        print(f"⚠️ 请求订单簿时发生错误: {e}")
        return {"bids": [], "asks": []}


# === WebSocket 实时行情 ===
async def subscribe_tickers(symbol_map: dict):
    async with websockets.connect(WS_URL) as ws:
        params = [{"channel": "tickers", "instId": v} for v in symbol_map.values()]
        sub_msg = {"op": "subscribe", "args": params}
        await ws.send(json.dumps(sub_msg))
        print(f"✅ 已订阅: {list(symbol_map.keys())}")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if "data" in data:
                for item in data["data"]:
                    inst = item["instId"]
                    std_symbol = next((k for k, v in symbol_map.items() if v == inst), inst)
                    last = item["last"]
                    vol = item["vol24h"]
                    print(f"{std_symbol} 最新价: {last}  24h成交量: {vol}")


# === 测试 ===
if __name__ == "__main__":
    base_coins = ["BTC", "ETH"]
    symbol_map = get_symbols(inst_type="SWAP", base_currencies=base_coins)
    print("当前 symbol 映射:", symbol_map)

    # ✅ 调用 orderbook() 时只需传入标准名称
    snapshot = orderbook("BTC-USDT")
    print("📘 订单簿快照示例：")
    print(json.dumps(snapshot, indent=2))
