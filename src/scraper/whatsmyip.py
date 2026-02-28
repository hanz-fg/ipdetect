import time

def check_whatsmyip(sb, ip):
    sb.uc_open_with_reconnect(f"https://whatismyipaddress.com/ip/{ip}", 4)

    try:
        sb.uc_gui_click_captcha()
        time.sleep(2)
    except:
        pass

    try:
        country_wimip = sb.get_text("//p[@class='information']/span[text()='Country:']/following-sibling::span", by="xpath")
    except:
        country_wimip = "N/A"

    return {
        "ip": ip,
        "country_wimip": country_wimip
    }