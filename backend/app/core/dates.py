from datetime import UTC, date, datetime, timedelta


def parse_dob(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def compute_age(dob: str | None, on: date | None = None) -> int:
    d = parse_dob(dob)
    if not d:
        return 0
    ref = on or datetime.now(UTC).date()
    age = ref.year - d.year
    if (ref.month, ref.day) < (d.month, d.day):
        age -= 1
    return max(0, age)


def dob_matches_today(dob: str | None, on: date | None = None) -> bool:
    d = parse_dob(dob)
    if not d:
        return False
    ref = on or datetime.now(UTC).date()
    return (d.month, d.day) == (ref.month, ref.day)


def user_local_date(tz_offset_minutes: int | None, now_utc: datetime | None = None) -> date:
    """User's calendar day, given their preferred country/region UTC offset."""
    ref = now_utc or datetime.now(UTC)
    offset = tz_offset_minutes if isinstance(tz_offset_minutes, int) else 0

    return (ref + timedelta(minutes=offset)).date()


def is_weekend(day: date | None = None) -> bool:
    return (day or datetime.now(UTC).date()).weekday() >= 5


def is_valid_dob(value: str) -> bool:
    d = parse_dob(value)
    if not d:
        return False
    today = date.today()
    if d > today:
        return False
    return d >= date(1900, 1, 1)
