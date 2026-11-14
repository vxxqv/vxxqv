"""Render an animated GitHub contribution graph from GitHub's own calendar."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "contributions.gif"
USERNAME = os.environ.get("GITHUB_USERNAME", "vxxqv")
TOKEN = os.environ.get("GITHUB_TOKEN")

WIDTH, HEIGHT = 1000, 326
LEFT, TOP, PITCH, CELL = 42, 115, 17, 12
BACKGROUND = "#0C1520"
PANEL = "#142330"
MUTED = "#91A8B5"
PALETTE = {
    "NONE": "#1D303A",
    "FIRST_QUARTILE": "#1D5D59",
    "SECOND_QUARTILE": "#237F73",
    "THIRD_QUARTILE": "#2BAB90",
    "FOURTH_QUARTILE": "#69E0B8",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold
        else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def get_calendar() -> dict:
    if not TOKEN:
        raise SystemExit("Set GITHUB_TOKEN to read the contribution calendar.")
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount contributionLevel }
            }
          }
        }
      }
    }"""
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "vxxqv-profile-contribution-graph",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(calendar: dict, reveal: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((9, 9, WIDTH - 10, HEIGHT - 10), radius=18, outline="#2D4750", width=2)
    draw.text((42, 30), "GITHUB CONTRIBUTIONS", fill="#E9F6F2", font=font(25, bold=True))
    draw.text((43, 65), "The past year, week by week", fill=MUTED, font=font(17))
    draw.text((772, 30), f"{calendar['totalContributions']:,}", fill="#69E0B8", font=font(36, bold=True))
    draw.text((774, 74), "contributions", fill=MUTED, font=font(16))

    weeks = calendar["weeks"][-53:]
    draw.text((42, 96), "SUN", fill=MUTED, font=font(11))
    draw.text((42, 130), "TUE", fill=MUTED, font=font(11))
    draw.text((42, 164), "THU", fill=MUTED, font=font(11))
    x0 = 78
    totals = []
    for wi, week in enumerate(weeks):
        totals.append(sum(day["contributionCount"] for day in week["contributionDays"]))
        for di, day in enumerate(week["contributionDays"]):
            x, y = x0 + wi * PITCH, TOP + di * PITCH
            level = day["contributionLevel"]
            color = PALETTE[level] if wi < reveal else PANEL
            draw.rounded_rectangle((x, y, x + CELL, y + CELL), radius=3, fill=color)
        if wi == reveal - 1 and reveal < len(weeks):
            x = x0 + wi * PITCH
            draw.rounded_rectangle((x - 3, TOP - 4, x + CELL + 3, TOP + 6 * PITCH + CELL + 4), radius=5, outline="#9DF6D4", width=2)

    # A true weekly-total trace beneath the calendar, revealed with the grid.
    draw.text((42, 249), "WEEKLY ACTIVITY", fill=MUTED, font=font(12, bold=True))
    max_total = max(totals, default=1) or 1
    points = []
    for wi, total in enumerate(totals):
        x = x0 + wi * PITCH + CELL // 2
        y = 303 - round((total / max_total) * 45)
        points.append((x, y))
    draw.line((x0, 304, x0 + (len(weeks) - 1) * PITCH + CELL, 304), fill="#29424A", width=1)
    if reveal > 1:
        draw.line(points[:reveal], fill="#42CDA7", width=3, joint="curve")
    if reveal:
        x, y = points[min(reveal, len(points)) - 1]
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#A5F9D9")
    return image


def main() -> None:
    calendar = get_calendar()
    weeks = calendar["weeks"][-53:]
    if not weeks or not all("contributionDays" in week for week in weeks):
        raise RuntimeError("GitHub returned an incomplete contribution calendar")
    steps = list(range(0, len(weeks) + 1, 2))
    if steps[-1] != len(weeks):
        steps.append(len(weeks))
    frames = [render(calendar, count).quantize(colors=32) for count in steps]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=[95] * (len(frames) - 1) + [1500],
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Wrote {OUT} ({len(frames)} frames, {calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
