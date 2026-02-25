import json, os, time, random, sqlite3
from seleniumbase import SB
from base import load_proxies
from scraper.scamalytics import check_ip
from scraper.ipinfo import check_ipinfo

os.makedirs("../results", exist_ok=True)

conn = sqlite3.connect("../results/results.db")
cursor = conn.cursor()
cursor.execute("""
               CREATE TABLE IF NOT EXISTS ip_results (
                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                         ip TEXT,
                                                         fraud_score TEXT,
                                                         data_center TEXT,
                                                         server TEXT,
                                                         vpn TEXT,
                                                         asn_type TEXT,
                                                         proxy_type TEXT,
                                                         checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
               """)
conn.commit()

proxy = random.choice(load_proxies())
proxy_str = f"{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"

with SB(uc=True, test=True, proxy=proxy_str) as sb:
    sb.uc_open_with_reconnect("https://api.ipify.org", 4)
    print("Outgoing IP:", sb.get_text("body"))

    for x in range(255):
        for y in range(255):
            ip = f"64.52.{x}.{y}"
            try:
                scam_data = check_ip(sb, ip)
                ipinfo_data = check_ipinfo(sb, ip)
                data = {**scam_data, **ipinfo_data}

                cursor.execute("""
                               INSERT INTO ip_results (ip, fraud_score, data_center, server, vpn, asn_type, proxy_type)
                               VALUES (?, ?, ?, ?, ?, ?, ?)
                               """, (
                                   data["ip"],
                                   data["fraud_score"],
                                   data["data_center"],
                                   data["server"],
                                   data["vpn"],
                                   data["asn_type"],
                                   data["proxy_type"]
                               ))
                conn.commit()

                print(f"{ip} -> {data['fraud_score']} | {data['asn_type']} | {data['proxy_type']}")
            except Exception as e:
                print(f"failed {ip}: {e}")
            time.sleep(random.uniform(3, 7))

conn.close()