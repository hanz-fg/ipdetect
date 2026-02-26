import json, os, time, random, sqlite3
from seleniumbase import SB
from base import load_proxies
from scraper.scamalytics import check_ip
from scraper.ipinfo import check_ipinfo


os.makedirs("../results", exist_ok=True)

conn = sqlite3.connect("../results/results.db", timeout=30)
cursor = conn.cursor()
cursor.execute("PRAGMA journal_mode=WAL")
conn.commit()

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
                                                      run_key TEXT,
                                                      ip TEXT,
                                                      third_octet INTEGER,
                                                      status TEXT DEFAULT 'pending',
                                                      PRIMARY KEY (run_key, ip)
                   )
               """)
conn.commit()


v = int(input("First Octet: "))
w = int(input("Second Octet: "))
z = int(input("Fourth Octet: "))

run_key = f"{v}.{w}.x.{z}"
print("Run:", run_key)
cursor.execute("SELECT COUNT(*) FROM ip_jobs WHERE run_key=?", (run_key,))

if cursor.fetchone()[0] == 0:
    print("Setting up job queue...")
    jobs = [(run_key, f"{v}.{w}.{x}.{z}", x) for x in range(256)]
    cursor.executemany(
        "INSERT OR IGNORE INTO ip_jobs (run_key, ip, third_octet) VALUES (?, ?, ?)",
        jobs
    )
    conn.commit()
    print(f"Added {len(jobs)} jobs")

def run_scraper():
    proxy = random.choice(load_proxies())
    proxy_str = f"{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"

    with SB(uc=True, test=True, proxy=proxy_str, headless=True, time_limit=300) as sb:
        sb.uc_open_with_reconnect("https://api.ipify.org", 4)
        print("Outgoing IP:", sb.get_text("body"))

        while True:
            cursor.execute("""
                           UPDATE ip_jobs
                           SET status='processing'
                           WHERE (run_key, ip) = (
                               SELECT run_key, ip
                               FROM ip_jobs
                               WHERE run_key=? AND status='pending'
                               ORDER BY third_octet
                               LIMIT 1
                               )
                               RETURNING ip
                           """, (run_key,))
            row = cursor.fetchone()
            conn.commit()

            if not row:
                print("All IPs done!")
                break

            ip = row[0]
            retries = 0
            max_retries = 3

            while retries < max_retries:
                try:
                    scam_data = check_ip(sb, ip)
                    ipinfo_data = check_ipinfo(sb, ip)
                    data = {**scam_data, **ipinfo_data}

                    print(f"{ip} -> {data['fraud_score']} | {data['asn_type']} | {data['proxy_type']} | {data['country']}")

                    if data.get("data_center", "").lower() == "unknown" and data.get("asn_type", "").lower() == "isp":
                        cursor.execute("""
                        INSERT INTO ip_results (ip, fraud_score, data_center, server, vpn, asn_type, proxy_type, country)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                           data["ip"], data["fraud_score"], data["data_center"],
                           data["server"], data["vpn"], data["asn_type"],
                           data["proxy_type"], data["country"]
                        ))

                    cursor.execute("""
                                   UPDATE ip_jobs SET status = 'done'
                                   WHERE run_key = ? AND ip = ?
                                   """, (run_key, ip))
                    conn.commit()
                    break
                    
                except Exception as e:
                    retries += 1
                    print(f"failed {ip} (attempt {retries}/{max_retries}): {e}")
                    if retries >= max_retries:
                        cursor.execute("UPDATE ip_jobs SET status = 'done' WHERE run_key = ? AND ip = ?", (run_key, ip))
                        conn.commit()
                        print(f"giving up {ip}")
                    else:
                        time.sleep(5)

            time.sleep(random.uniform(3, 7))

while True:
    try:
        run_scraper()
        break
    except Exception as e:
        print(f"Browser crashed: {e}, restarting in 10 seconds...")
        time.sleep(10)


conn.close()