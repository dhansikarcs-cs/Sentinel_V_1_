from zoneinfo import ZoneInfo

# Country -> sensible default IANA timezone. Users can refine it later in Edit Profile.
COUNTRY_TZ: dict[str, str] = {
    "India": "Asia/Kolkata",
    "United States": "America/New_York",
    "United Kingdom": "Europe/London",
    "Canada": "America/Toronto",
    "Australia": "Australia/Sydney",
    "Singapore": "Asia/Singapore",
    "United Arab Emirates": "Asia/Dubai",
    "Saudi Arabia": "Asia/Riyadh",
    "Germany": "Europe/Berlin",
    "France": "Europe/Paris",
    "Netherlands": "Europe/Amsterdam",
    "Japan": "Asia/Tokyo",
    "China": "Asia/Shanghai",
    "South Korea": "Asia/Seoul",
    "Indonesia": "Asia/Jakarta",
    "Malaysia": "Asia/Kuala_Lumpur",
    "Philippines": "Asia/Manila",
    "Thailand": "Asia/Bangkok",
    "Brazil": "America/Sao_Paulo",
    "South Africa": "Africa/Johannesburg",
    "Nigeria": "Africa/Lagos",
    "Kenya": "Africa/Nairobi",
    "New Zealand": "Pacific/Auckland",
}

DEFAULT_TZ = "UTC"

# Curated friendly list for the Edit Profile timezone picker.
COMMON_TIMEZONES: list[tuple[str, str]] = [
    ("Asia/Kolkata", "India (GMT+5:30)"),
    ("Asia/Tokyo", "Japan / Korea (GMT+9)"),
    ("Asia/Shanghai", "China (GMT+8)"),
    ("Asia/Singapore", "Singapore / Malaysia (GMT+8)"),
    ("Asia/Dubai", "Dubai / UAE (GMT+4)"),
    ("Asia/Riyadh", "Saudi Arabia (GMT+3)"),
    ("Europe/London", "UK / Ireland (GMT+0)"),
    ("Europe/Paris", "France / Central Europe (GMT+1)"),
    ("Europe/Berlin", "Germany / Central Europe (GMT+1)"),
    ("America/New_York", "US East (GMT-5)"),
    ("America/Chicago", "US Central (GMT-6)"),
    ("America/Denver", "US Mountain (GMT-7)"),
    ("America/Los_Angeles", "US West (GMT-8)"),
    ("America/Toronto", "Canada East (GMT-5)"),
    ("America/Sao_Paulo", "Brazil (GMT-3)"),
    ("Australia/Sydney", "Australia East (GMT+10)"),
    ("Pacific/Auckland", "New Zealand (GMT+12)"),
    ("Africa/Johannesburg", "South Africa (GMT+2)"),
    ("Africa/Lagos", "West Africa (GMT+1)"),
    ("UTC", "UTC (GMT+0)"),
]


def default_tz_for_country(country: str) -> str:
    return COUNTRY_TZ.get(country or "", DEFAULT_TZ)


def is_valid_tz(tz: str) -> bool:
    if not tz:
        return False
    try:
        ZoneInfo(tz)
        return True
    except Exception:
        return False


def user_timezone(country: str, timezone: str) -> str:
    chosen = (timezone or "").strip()
    if chosen and is_valid_tz(chosen):
        return chosen
    return default_tz_for_country(country)
