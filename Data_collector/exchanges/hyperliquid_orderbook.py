import requests

def contract_information(symbol: str, client=None) -> dict:
    """
    获取 Hyperliquid 永续合约的详细信息
    参数:
        symbol: 交易对名称，格式为 "BTC-USDT"
        client: 未使用，保持接口一致性
    返回:
        合约信息的字典，包含合约的所有详细信息
        如果获取失败，返回空字典 {}
    """
    return {}


def orderbook(symbol: str) -> dict:
    """
    使用 Hyperliquid 的 L2 Snapshot 接口，返回格式化后的订单簿：
    {
        "bids": [[price, size], ... 10 个],
        "asks": [[price, size], ... 10 个]
    }
    """
    url = "https://api.hyperliquid.xyz/info"
    coin = symbol.split("-")[0]  # BTC-USDT -> BTC

    payload = {
        "type": "l2Book",
        "coin": coin,
        "nSigFigs": None,   # 不聚合，使用 full precision
        "mantissa": None
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"Hyperliquid API Error: Status Code {resp.status_code}, Response: {resp.text}")
            return {"bids": [], "asks": []}
        data = resp.json()
    except Exception as e:
        print(f"An exception occurred during Hyperliquid API call: {e}")
        return {"bids": [], "asks": []}

    # data["levels"] = [bids, asks]
    levels = data.get("levels", [])
    if len(levels) != 2:
        return {"bids": [], "asks": []}

    bids_raw = levels[0]   # list of dict {px, sz, n}
    asks_raw = levels[1]

    # --- convert format ---
    # 只取前 10 个
    bids = [[float(entry["px"]), float(entry["sz"])] for entry in bids_raw[:10]]
    asks = [[float(entry["px"]), float(entry["sz"])] for entry in asks_raw[:10]]

    # --- Hyperliquid 已经按 px 排序，但保险起见我们再排序 ---
    bids.sort(key=lambda x: x[0], reverse=True)  # 价格从高到低
    asks.sort(key=lambda x: x[0])                # 价格从低到高

    return {
        "bids": bids,
        "asks": asks
    }


# ----------------------
# ✨ 测试
# ----------------------
if __name__ == "__main__":
    ob = orderbook("ETH-USDT")
    print(ob)
