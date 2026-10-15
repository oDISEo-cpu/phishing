import re
import httpx

PREVIEW_RE = re.compile(
    r"tiktok|bytedance|musical_ly|bytespider|facebookexternalhit|whatsapp|"
    r"telegrambot|twitterbot|slackbot|discordbot|googlebot|bingbot|applebot|"
    r"linkedinbot|embedly|bot|crawler|spider|preview",
    re.I,
)

_cache: dict[str, dict] = {}


def is_preview(ua: str) -> tuple[bool, str]:
    m = PREVIEW_RE.search(ua or "")
    return (bool(m), m.group(0).lower() if m else "")


def parse_ua(ua: str) -> dict:
    ua = ua or ""
    browser = "desconocido"
    for token, name in (
        ("Edg/", "Edge"), ("OPR/", "Opera"), ("CriOS", "Chrome iOS"),
        ("FxiOS", "Firefox iOS"), ("Chrome/", "Chrome"), ("Safari/", "Safari"),
        ("Firefox/", "Firefox"),
    ):
        if token in ua:
            browser = name
            break
    os_ = "desconocido"
    for token, name in (
        ("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"),
        ("Windows", "Windows"), ("Mac OS X", "macOS"), ("Linux", "Linux"),
    ):
        if token in ua:
            os_ = name
            break
    device = "escritorio" if os_ in ("Windows", "macOS", "Linux") else "movil"
    return {"browser": browser, "os": os_, "device": device}


def geo_lookup(ip: str) -> dict:
    if not ip:
        return {}
    if ip in _cache:
        return _cache[ip]
    data = {}
    if not ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "::1")):
        try:
            r = httpx.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,countryCode,regionName,city,lat,lon,isp,org,as"},
                timeout=2.0,
            )
            j = r.json()
            if j.get("status") == "success":
                data = {
                    "country": j.get("country", ""),
                    "region": j.get("regionName", ""),
                    "city": j.get("city", ""),
                    "lat": j.get("lat") or 0.0,
                    "lon": j.get("lon") or 0.0,
                    "org": j.get("isp", "") or j.get("org", ""),
                    "asn": (j.get("as", "") or "").split(" ")[0],
                }
        except Exception:
            data = {}
    _cache[ip] = data
    return data


TZ_COUNTRY = {
    "America/Caracas": "VE", "America/Bogota": "CO", "America/Lima": "PE",
    "America/Santiago": "CL", "America/Argentina": "AR", "America/Mexico_City": "MX",
    "America/New_York": "US", "America/Panama": "PA", "America/Santo_Domingo": "DO",
    "Europe/Madrid": "ES", "Europe/London": "GB", "Europe/Lisbon": "PT",
    "Europe/Rome": "IT", "Europe/Berlin": "DE", "Europe/Paris": "FR",
}


def tz_country(tz: str) -> str:
    if not tz:
        return ""
    if tz in TZ_COUNTRY:
        return TZ_COUNTRY[tz]
    return TZ_COUNTRY.get(tz.rsplit("/", 1)[0], "")