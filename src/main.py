import json, os, time, random, sqlite3
from seleniumbase import SB
from base import load_proxies
from scraper.scamalytics import check_ip
from scraper.ipinfo import check_ipinfo

os.makedirs("../results", exist_ok=True)

conn = sqlite3.connect("../results/results.db", timeout=30)
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
                                                         country TEXT,
                                                         checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
               """)

cursor.execute("""
               CREATE TABLE IF NOT EXISTS ip_jobs (
                                                      ip TEXT PRIMARY KEY,
                                                      status TEXT DEFAULT 'pending'
               )
               """)
conn.commit()

v = int(input("First Octet: "))
w = int(input("Second Octet: "))
z = int(input("Fourth Octet: "))

cursor.execute("SELECT COUNT(*) FROM ip_jobs")
if cursor.fetchone()[0] == 0:
    print("Setting up job queue...")
    jobs = [(f"{v}.{w}.{x}.{z}",) for x in range(255)]
    cursor.executemany("INSERT OR IGNORE INTO ip_jobs (ip) VALUES (?)", jobs)
    conn.commit()
    print(f"Added {len(jobs)} jobs")

def run_scraper():
    proxy = random.choice(load_proxies())
    proxy_str = f"{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"

    with SB(uc=True, test=True, proxy=proxy_str) as sb:
        sb.uc_open_with_reconnect("https://api.ipify.org", 4)
        print("Outgoing IP:", sb.get_text("body"))

        while True:
            cursor.execute("""
                           UPDATE ip_jobs SET status = 'processing'
                           WHERE ip = (SELECT ip FROM ip_jobs WHERE status = 'pending' LIMIT 1)
                               RETURNING ip
                           """)
            row = cursor.fetchone()
            conn.commit()

            if not row:
                print("All IPs done!")
                break

            ip = row[0]

            try:
                scam_data = check_ip(sb, ip)
                ipinfo_data = check_ipinfo(sb, ip)
                data = {**scam_data, **ipinfo_data}

                print(f"{ip} -> {data['fraud_score']} | {data['asn_type']} | {data['proxy_type']} | {data['country']}")
                if data["data_center"].lower() == "unknown" and data["asn_type"].lower() == "isp":
                    cursor.execute("""
                                   INSERT INTO ip_results (ip, fraud_score, data_center, server, vpn, asn_type, proxy_type, country)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                   """, (
                                       data["ip"], data["fraud_score"], data["data_center"],
                                       data["server"], data["vpn"], data["asn_type"],
                                       data["proxy_type"], data["country"]
                                   )
                cursor.execute("UPDATE ip_jobs SET status = 'done' WHERE ip = ?", (ip,))
                conn.commit()

            except Exception as e:
                cursor.execute("UPDATE ip_jobs SET status = 'pending' WHERE ip = ?", (ip,))
                conn.commit()
                print(f"failed {ip}: {e}")

            time.sleep(random.uniform(3, 7))

while True:
    try:
        run_scraper()
        break
    except Exception as e:
        print(f"Browser crashed: {e}, restarting in 10 seconds...")
        time.sleep(10)

conn.close()