#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

URL = "https://www.czehockey.cz/souteze-muzi/tipsport-extraliga"
OUT = "extraliga.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VinnerDashboard/1.0; +https://github.com/Vinner99/vinner.github.io)"
}

def norm(text):
    return " ".join((text or "").split())

def find_standings_table(soup):
    candidates = []
    for table in soup.find_all("table"):
        headers = [norm(th.get_text(" ", strip=True)).upper() for th in table.find_all("th")]
        joined = " | ".join(headers)
        score = 0
        for needle in ("TÝM", "SKÓRE", "VP", "PP"):
            if needle in joined:
                score += 1
        if "Z" in headers:
            score += 1
        if "B" in headers:
            score += 1
        candidates.append((score, table))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates or candidates[0][0] < 4:
        return None
    return candidates[0][1]

def parse_table(table):
    teams = []

    for tr in table.find_all("tr"):
        cells = [norm(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(cells) < 9:
            continue

        # Standard czehockey layout:
        # # | TÝM | Z | V | VP | PP | P | SKÓRE | B
        raw_pos, team, games, wins, ot_wins, ot_losses, losses, score, points = cells[:9]

        try:
            position = int(raw_pos.rstrip("."))
            games = int(games)
            wins = int(wins)
            ot_wins = int(ot_wins)
            ot_losses = int(ot_losses)
            losses = int(losses)
            points = int(points)
        except ValueError:
            continue

        teams.append({
            "position": position,
            "team": team,
            "games": games,
            "wins": wins,
            "ot_wins": ot_wins,
            "ot_losses": ot_losses,
            "losses": losses,
            "score": score,
            "points": points,
        })

    return teams

def main():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = find_standings_table(soup)

    if table is None:
        raise RuntimeError("Na stránce Českého hokeje nebyla nalezena tabulka extraligy.")

    teams = parse_table(table)

    if len(teams) < 10:
        raise RuntimeError(f"Načetlo se jen {len(teams)} týmů; odmítám přepsat JSON neúplnými daty.")

    now_prague = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Prague"))

    payload = {
        "competition": "Tipsport extraliga",
        "source": URL,
        "updated_at": now_prague.isoformat(timespec="seconds"),
        "teams": teams,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Uloženo {len(teams)} týmů do {OUT}.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Chyba: {exc}", file=sys.stderr)
        sys.exit(1)
