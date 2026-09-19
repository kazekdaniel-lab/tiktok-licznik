"""Pobiera liczbę obserwujących z publicznych profili TikTok i zapisuje do data/.

latest.json  - ostatni odczyt (nadpisywany)
history.json - punkty historii, dopisywane gdy liczby się zmienią albo minęła godzina
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ACCOUNTS = ["pieseu.official", "psiapsi_pl"]
DATA = Path(__file__).resolve().parent.parent / "data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def fetch(user):
    req = urllib.request.Request(f"https://www.tiktok.com/@{user}",
                                 headers={"User-Agent": UA, "Accept-Language": "pl,en;q=0.8"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("brak danych w HTML")
    info = json.loads(m.group(1))["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
    stats = info.get("statsV2") or info["stats"]
    return {
        "nickname": info["user"].get("nickname", user),
        "followers": int(stats["followerCount"]),
        "likes": int(stats["heartCount"]),
        "videos": int(stats["videoCount"]),
    }


def main():
    now = int(time.time())
    latest_path, hist_path = DATA / "latest.json", DATA / "history.json"
    prev = json.loads(latest_path.read_text()) if latest_path.exists() else {"accounts": {}}
    history = json.loads(hist_path.read_text()) if hist_path.exists() else []

    accounts = {}
    for user in ACCOUNTS:
        for attempt in range(3):
            try:
                accounts[user] = fetch(user)
                break
            except Exception as e:
                print(f"{user}: próba {attempt + 1} nieudana: {e}", file=sys.stderr)
                time.sleep(5)
        else:
            # zostaw poprzedni odczyt, żeby strona nie pokazała pustki
            if user in prev["accounts"]:
                accounts[user] = prev["accounts"][user]

    if not accounts:
        sys.exit("Nie udało się pobrać żadnego konta")

    latest_path.write_text(json.dumps({"checked_at": now, "accounts": accounts},
                                      ensure_ascii=False, indent=2))

    point = {"t": now, **{u: a["followers"] for u, a in accounts.items()}}
    last = history[-1] if history else None
    changed = not last or any(last.get(u) != point.get(u) for u in ACCOUNTS)
    if changed or now - last["t"] >= 3600:
        history.append(point)
        hist_path.write_text(json.dumps(history, separators=(",", ":")))

    for u, a in accounts.items():
        print(f"{u}: {a['followers']} obserwujących")


if __name__ == "__main__":
    main()
