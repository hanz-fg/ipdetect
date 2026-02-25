from seleniumbase import SB
import json, random

def load_proxies(path="../proxies.json"):
    with open(path) as f:
        raw = json.load(f)
    return [dict(zip(["host","port","user","pass"], e.split(":"))) for e in raw]

def get_proxy():
    proxy = random.choice(load_proxies())
    proxy_str = f"{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"
    return proxy, proxy_str