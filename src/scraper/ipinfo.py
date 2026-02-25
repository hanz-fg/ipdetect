import time

def check_ipinfo(sb, ip):
    sb.uc_open_with_reconnect(f"https://ipinfo.io/{ip}", 4)

    try:
        sb.uc_gui_click_captcha()
        time.sleep(2)
    except:
        pass

    try:
        asn_type = sb.get_text("//h6[text()='ASN type']/following-sibling::span", by="xpath")
    except:
        asn_type = "N/A"

    try:
        proxy_type = sb.get_text("//div[@class='privacy-card-title']/h3", by="xpath")
        badge = sb.get_text("//div[@class='privacy-card-badge']", by="xpath")
        proxy_type = f"{proxy_type} - {badge}"
    except:
        proxy_type = "N/A"

    return {
        "ip": ip,
        "asn_type": asn_type,
        "proxy_type": proxy_type
    }