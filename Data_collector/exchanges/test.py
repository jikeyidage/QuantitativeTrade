import requests

host = "https://api.gateio.ws"
prefix = "/api/v4"
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

url = '/futures/usdt/contracts/ETH_USDT'
query_param = ''
r = requests.request('GET', host + prefix + url, headers=headers)
print(r.json())