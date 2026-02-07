from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class OpenHoliday:
    date: str                 # YYYY-MM-DD
    name: str                 # nombre en ES si existe
    country_code: str         # 'ES'
    subdivision_code: Optional[str]  # 'ES-AN' o None


def fetch_public_holidays(
    *,
    country_code: str,
    subdivision_code: Optional[str],
    valid_from: str,
    valid_to: str,
    language_iso_code: str = "ES",
) -> List[OpenHoliday]:
    """
    Llama a:
      https://openholidaysapi.org/PublicHolidays?countryIsoCode=ES&subdivisionCode=ES-AN&languageIsoCode=ES&validFrom=YYYY-MM-DD&validTo=YYYY-MM-DD
    """
    base = "https://openholidaysapi.org/PublicHolidays"
    params = {
        "countryIsoCode": country_code,
        "languageIsoCode": language_iso_code,
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    if subdivision_code:
        params["subdivisionCode"] = subdivision_code

    url = base + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"accept": "text/json", "User-Agent": "calendarioFarmacia/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    out: List[OpenHoliday] = []
    for item in data:
        # Estructura típica: date + name[] (multidioma) + subdivisions opcional
        date = item.get("date") or item.get("startDate")  # por si cambia el campo
        if not date:
            continue

        name = _pick_name(item.get("name"), language_iso_code) or _pick_name(item.get("name"), "EN") or "Festivo"
        subs = item.get("subdivisions") or []
        subs_codes = [s.get("code") for s in subs if isinstance(s, dict) and s.get("code")]

        # Si pedimos con subdivision_code, normalmente vendrá incluido.
        # Si no viene, lo dejamos None => se tratará como nacional.
        out.append(
            OpenHoliday(
                date=date,
                name=name,
                country_code=country_code,
                subdivision_code=subdivision_code if subdivision_code in subs_codes else (subdivision_code if subdivision_code else None),
            )
        )

    return out


def _pick_name(name_field, lang: str) -> Optional[str]:
    """
    OpenHolidays suele devolver name como lista de {language, text}.
    """
    if not name_field:
        return None
    if isinstance(name_field, str):
        return name_field
    if isinstance(name_field, list):
        for n in name_field:
            if isinstance(n, dict) and (n.get("language") == lang or n.get("languageIsoCode") == lang):
                return n.get("text") or n.get("name")
        # fallback al primero
        for n in name_field:
            if isinstance(n, dict):
                return n.get("text") or n.get("name")
    return None
