# coding: utf-8
import requests
import time
import hashlib
import hmac
import json

with open("config.json", "r") as f:
    api_config = json.load(f)

gate_api_key = api_config["gate"]["api_key"]
gate_api_secret = api_config["gate"]["api_secret"]

def gen_sign(method, url, query_string=None, payload_string=None):
    key = gate_api_key        # api_key
    secret = gate_api_secret     # api_secret

    t = time.time()
    m = hashlib.sha512()
    m.update((payload_string or "").encode('utf-8'))
    hashed_payload = m.hexdigest()
    s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
    sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
    return {'KEY': key, 'Timestamp': str(t), 'SIGN': sign}

if __name__ == "__main__":
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    common_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    url = '/futures/usdt/orders'
    query_param = ''
    body='{"contract":"BTC_USDT","size":"6024","iceberg":"0","price":"3765","tif":"gtc","text":"t-my-custom-id","stp_act":"-","order_value":"64112.2099000000005","trade_value":"64112.2099000000005"}'
    sign_headers = gen_sign('POST', prefix + url, query_param, body)
    common_headers.update(sign_headers)
    r = requests.request('POST', host + prefix + url, headers=common_headers, data=body)
    print(r.json())
