import time

def check_ip(sb, ip):
    sb.uc_open_with_reconnect(f"https://scamalytics.com/ip/{ip}", 4)

    try:
        sb.uc_gui_click_captcha()
        time.sleep(2)
    except:
        pass

    fraud_score = sb.get_text("//div[@class='score']", by="xpath")
    data_center = sb.get_text("//div[contains(@class,'risk') and contains(@class,'stretch')]", by="xpath")
    server = sb.get_text("//th[text()='Server']/following-sibling::td/div", by="xpath")
    vpn = sb.get_text("//th[text()='Anonymizing VPN']/following-sibling::td/div", by="xpath")
    country = sb.get_text("//th[text()='Country Name']/following-sibling::td/div", by="xpath")

    return {
        "ip": ip,
        "fraud_score": fraud_score,
        "data_center": data_center,
        "server": server,
        "vpn": vpn,
        "country": country
    }