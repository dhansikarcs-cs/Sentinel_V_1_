import re
from dataclasses import dataclass


@dataclass
class DeviceInfo:
    device: str
    browser: str
    os: str
    is_mobile: bool
    raw_ua: str


MOBILE_PATTERNS = re.compile(
    r"android|iphone|ipad|ipod|mobile|blackberry|opera mini|iemobile|wpdesktop",
    re.IGNORECASE,
)


def parse_user_agent(ua: str) -> DeviceInfo:
    if not ua:
        return DeviceInfo("unknown", "unknown", "unknown", False, "")

    is_mobile = bool(MOBILE_PATTERNS.search(ua))

    if "Firefox" in ua:
        browser = "Firefox"
    elif "Edg/" in ua:
        browser = "Edge"
    elif "Chrome" in ua and "Safari" in ua:
        browser = "Chrome"
    elif "Safari" in ua:
        browser = "Safari"
    elif "Opera" in ua or "OPR" in ua:
        browser = "Opera"
    elif "MSIE" in ua or "Trident" in ua:
        browser = "IE"
    else:
        browser = "Unknown"

    if "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    else:
        os_name = "Unknown"

    if "Mobile" in ua and "Android" in ua:
        device = "Android Phone"
    elif "Android" in ua:
        device = "Android Tablet"
    elif "iPhone" in ua:
        device = "iPhone"
    elif "iPad" in ua:
        device = "iPad"
    elif is_mobile:
        device = "Mobile Device"
    else:
        device = "Desktop"

    return DeviceInfo(device=device, browser=browser, os=os_name, is_mobile=is_mobile, raw_ua=ua)
