import requests
import time
import json
from websocket import create_connection

# API 配置
HOST = "https://api.gateio.ws"
PREFIX = "/api/v4"


def init_client(api_key=None, api_secret=None, passphrase=None):
    """
    初始化 Gate.io REST 客户端，返回 requests.Session 对象
    """
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    # 如果需要认证，可在这里添加 api_key / api_secret
    return session


def get_symbols(client=None) -> list:
    """
    从公共API获取该交易所支持的全部交易对（合约），只包括永续合约（SWAP）
    返回统一格式：json
    [
        {"symbol": "BTC-USDT-SWAP", "type": "swap"},
        {"symbol": "ETH-USDT-SWAP", "type": "swap"},
        ...
    ]
    """
    if client is None:
        client = init_client()

    url = f"{HOST}{PREFIX}/futures/usdt/contracts"
    resp = client.get(url)
    data = resp.json()

    symbols = []
    for contract in data:
        # 仅保留正在交易的USDT永续合约
        if contract.get("type") == "direct" and contract.get("status") == "trading":
            base, quote = contract["name"].split("_")
            symbols.append(
                f"{base}_{quote}"
            )

    return symbols


def fetch_snapshot(symbol: str, depth: int = 100, client=None) -> dict:
    """
    获取 Gate.io 合约市场订单簿快照（REST）
    symbol 格式: BTC_USDT, ETH_USDT 等
    depth: 返回买卖盘数量
    client: requests.Session 对象
    """
    if client is None:
        client = init_client()

    url = f"{HOST}{PREFIX}/futures/usdt/order_book"
    params = {
        "contract": symbol,
        "limit": depth  # Gate.io 支持的 depth 参数
    }

    resp = client.get(url, params=params)
    data = resp.json()


    # 返回原始格式，方便统一处理
    snapshot = {
        "timestamp": int(time.time() * 1000),
        "bids": sorted(
            [[float(bid["p"]), float(bid["s"])] for bid in data.get("bids", [])],
            key=lambda x: -x[0]
        ),
        "asks": sorted(
            [[float(ask["p"]), float(ask["s"])] for ask in data.get("asks", [])],
            key=lambda x: x[0]
        )
    }
    return snapshot


def run_ws(symbols: list, depth: int = 50, callback=None):
    """
    订阅多个交易对的订单簿实时增量（diff）。
    每当收到新数据时，调用 callback(data)
    data 格式与 fetch_snapshot 一致。
    """
    ws_url = "wss://fx-ws.gateio.ws/v4/ws/usdt"
    
    # 创建 WebSocket 客户端连接
    ws = create_connection(ws_url)

    # 订阅多个交易对的订单簿更新
    for symbol in symbols:
        subscribe_msg = json.dumps({
            "time": int(time.time() * 1000),
            "channel": "futures.order_book_update",
            "event": "subscribe",
            "payload": [symbol, "100ms", "100"]  # 订阅100ms频率，100层深度
        })
        ws.send(subscribe_msg)
        print(f"Subscribed to {symbol} with 100ms frequency and 100 levels.")

    try:
        while True:
            message = ws.recv()  # 阻塞直到接收到消息
            data = json.loads(message)
            if data.get('channel') == 'futures.order_book_update' and data.get('event') == 'update':
                result = data.get('result', {})
                timestamp = result.get('t')
                symbol = result.get('s')
                bids = result.get('b')
                asks = result.get('a')
                print(f"Symbol:{symbol}")
                print(f"Timestamp: {timestamp}")
                print(f"Updated Bids: {bids}")
                print(f"Updated Asks: {asks}")
                # 如果有回调函数，将数据传递给回调
                if callback:
                    callback({"bids": bids, "asks": asks, "timestamp": timestamp})

    except KeyboardInterrupt:
        print("WebSocket closed manually.")
        ws.close()  # 手动关闭连接


def close_ws(ws):
    """
    手动关闭 WebSocket 连接
    """
    print("Closing WebSocket connection...")
    ws.close()

def contract_information(symbol: str, client=None) -> dict:
    """
    获取 Gate.io 永续合约的详细信息
    参数:
        symbol: 交易对名称，格式为 "BTC_USDT"
        client: requests.Session 对象，如果为 None 则自动创建
    返回:
        合约信息的字典，包含合约的所有详细信息
        如果获取失败，返回空字典 {}
    """
    if client is None:
        client = init_client()
    formatted_symbol = symbol.replace("-", "_")
    url = f"{HOST}{PREFIX}/futures/usdt/contracts/{formatted_symbol}"
    
    try:
        resp = client.get(url)
        resp.raise_for_status()  # 如果状态码不是 200，会抛出异常
        data = resp.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"获取合约信息失败 {symbol}: {e}")
        return {}
    except Exception as e:
        print(f"处理合约信息时出错 {symbol}: {e}")
        return {}


def orderbook(symbol: str) -> dict:
    '''
    返回一个静态的订单簿
    格式要求：
    输入：symbol 交易对名称，比如"BTC-USDT" "ETH-USDT" "OKB-USDT"
    输出：一个字典（dictionary）
    {
        "bids":[                  # 10个买单列表（按价格从高到低排序）
            [price:(float), size:(float)],
            [price:(float), size:(float)],
            ...
        ],
        "asks":[                  # 10个卖单列表（按价格从低到高排序）
            [price:(float), size:(float)],
            [price:(float), size:(float)],
            ...
        ]
    }
    注意：
    -------
    - 若无法获取订单簿（比如请求失败），请返回空结构：
        {"bids": [], "asks": []}
    - 此函数应返回 Python 字典对象（dict），不要返回 JSON 字符串。
    '''
    # ✅ Gate.io 使用下划线分隔交易对
    formatted_symbol = symbol.replace("-", "_")
    snapshot = fetch_snapshot(formatted_symbol, depth=10)

    if not snapshot or not snapshot.get("bids") or not snapshot.get("asks"):
        return {"bids": [], "asks": []}

    return {
        "bids": snapshot["bids"][:10],
        "asks": snapshot["asks"][:10]
    }





# 测试
if __name__ == "__main__":
    client = init_client()

    # 获取所有交易对（合约）
    symbols = get_symbols(client)
    print(f"共获取到 {len(symbols)} 个合约：")
    for s in symbols[:10]:  # 只显示前10个
        print(s)

    # 获取某个合约的订单簿快照
    snap = fetch_snapshot("BTC_USDT", depth=10, client=client)
    print(snap)

    # 获取某个合约的详细信息
    contract_info = contract_information("BTC_USDT", client=client)
    print("\n合约信息:")
    print(json.dumps(contract_info, indent=2, ensure_ascii=False))

    # 运行 WebSocket 监听
    # run_ws(symbols)  # 订阅并监听多个合约订单簿更新

