"""So'rov yuborgan mijoz haqida ma'lumot: IP, qurilma va geolokatsiya.

Geolokatsiyani Vercel har bir so'rovga sarlavha sifatida qo'shadi
(``x-vercel-ip-country``, ``-country-region``, ``-city``, ``-latitude``, ``-longitude``).
Proxy sarlavhalariga faqat ``trust_proxy`` yoqilganda ishoniladi — aks holda mijoz
o'zini istalgan IP/shahar qilib ko'rsatishi mumkin bo'lardi.
"""

import ipaddress
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import unquote


@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip: str | None
    user_agent: str | None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    request_id: str | None = None


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _text(value: str | None, limit: int = 100) -> str | None:
    return unquote(value)[:limit] if value else None


def extract_client_info(headers: Mapping[str, str], peer_ip: str | None, *, trust_proxy: bool) -> ClientInfo:
    """``headers`` — kichik harfli nomlar bilan."""
    user_agent = (headers.get("user-agent") or "")[:500] or None
    if not trust_proxy:
        return ClientInfo(ip=_valid_ip(peer_ip), user_agent=user_agent)

    forwarded = (headers.get("x-forwarded-for") or "").split(",")[0]
    ip = _valid_ip(headers.get("x-real-ip")) or _valid_ip(forwarded) or _valid_ip(peer_ip)
    return ClientInfo(
        ip=ip,
        user_agent=user_agent,
        country=_text(headers.get("x-vercel-ip-country"), 8),
        region=_text(headers.get("x-vercel-ip-country-region"), 16),
        city=_text(headers.get("x-vercel-ip-city")),
        latitude=_float(headers.get("x-vercel-ip-latitude")),
        longitude=_float(headers.get("x-vercel-ip-longitude")),
        request_id=_text(headers.get("x-vercel-id")),
    )
