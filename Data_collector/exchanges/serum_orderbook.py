import requests

BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders"  # 根据 Lighter 文档调整为正确 base URL

def orderbook(symbol: str, depth: int = 10) -> dict:
    """
    从 Lighter REST API 获取 orderbook 快照
    输入:
      symbol: 标准交易对名称，例如 "BTC-PERP" / "ETH-PERP" / 根据 Lighter 支持的 symbol
      depth: 想获取档数（这里尽量 >= 10）
    返回：
      {
        "bids": [ [price: float, size: float], ... ],
        "asks": [ [price: float, size: float], ... ]
      }
      如果失败，返回 {"bids": [], "asks": []}
    """
    try:
        # 假设 Lighter 的 REST orderbook endpoint 是 /api/v1/orderbook?market=symbol&limit=depth
        url = f"{BASE_URL}/api/v1/orderbook"
        params = {"market": symbol, "limit": depth}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        # 假设返回结构：
        # {
        #   "asks": [ {"price": "x", "size": "y"}, ... ],
        #   "bids": [ {"price": "x", "size": "y"}, ... ]
        # }
        asks = data.get("asks", [])
        bids = data.get("bids", [])

        # 解析前 depth 档
        asks_list = [[float(a["price"]), float(a["size"])] for a in asks[:depth]]
        bids_list = [[float(b["price"]), float(b["size"])] for b in bids[:depth]]

        return {"bids": bids_list, "asks": asks_list}
    except Exception as e:
        print("⚠️ 获取 Lighter orderbook 失败:", e)
        return {"bids": [], "asks": []}


if __name__ == "__main__":
    sym = "BTC-PERP"  # 注意 symbol 要符合 Lighter 的命名规则
    ob = orderbook(sym, depth=10)
    import json
    print(json.dumps(ob, indent=2))
