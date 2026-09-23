#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Karaoke-style terminal lyrics player (Banglish + English translation).

Features:
- Precise absolute timestamps per line (from the real song).
- Word-by-word reveal: each word turns solid-colored the moment its
  time slot arrives (no pulsing/jumping); not-yet-reached words are
  shown as dim dash placeholders.
- English translation stays a plain/neutral color under the Banglish line.
- Continuously running header clock (updates every tick).
- During silence between lines: the last finished line lingers on
  screen (dimmed) instead of going blank, with a small animated
  audio-equalizer underneath for a lively feel.

Usage:
    python3 lyrics_player.py

Requirements:
    pip install pygame rich
"""

import math
import time
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        os.system("chcp 65001 > nul")
    except Exception:
        pass

import pygame
from rich.console import Console, Group
from rich.text import Text
from rich.align import Align
from rich.panel import Panel

# ---------- CONFIG ----------

AUDIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "song.mp3")
START_OFFSET = 180.0            # গান এখান থেকে শুরু হবে (সেকেন্ড) -> 3:00 (একটু লিড-ইন সহ)
SONG_TOTAL_DURATION = 241.97    # পুরো গানের দৈর্ঘ্য (সেকেন্ড) -> 4:01

# প্রতিটা এন্ট্রি: (start_sec, end_sec, Banglish line, English translation)
LYRICS = [
    (190, 193, "Alo Jole Alo Jole", "Lights shine, lights shine,"),
    (194, 197, "Amar Mone Amar Mone", "deep inside my heart, deep inside my heart,"),
    (198, 203, "Tomar Chobi Chokher Samne Ese Bhase", "your vision comes floating before my eyes."),
    (206, 209, "Brishti Pore Brishti Pore", "The rain falls, the rain falls,"),
    (210, 213, "Thoter Majhe Golpo Jome", "as untold stories gather on my lips."),
    (214, 217, "Tomay Ami Khunji Sarakhon", "I'm searching for you all the time,"),
    (219, 222, "Ei Amar Mon", "in this restless heart of mine."),
    (224, 226, "Ei Amar Mon", "in this restless heart of mine."),
    (227, 230, "Ei Amar Mon", "in this restless heart of mine."),
    (236, 240, "Tumi Samne Nei......", "You aren't standing before me......"),
]

WORD_COLORS = [
    "bright_magenta",
    "bright_cyan",
    "bright_yellow",
    "bright_green",
    "bright_red",
    "bright_blue",
    "orange3",
    "spring_green2",
]

ENGLISH_COLOR = "white"
DIM_COLOR = "grey50"
HIDDEN_COLOR = "grey27"

EQ_CHARS = "▁▂▃▄▅▆▇█"
EQ_BARS = 9

console = Console(force_terminal=True, legacy_windows=False)


def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")


def format_time(seconds):
    seconds = max(0, seconds)
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def word_reveal_line(start, end, banglish, song_time):
    """প্রতিটা শব্দ তার নিজের টাইম-স্লট আসার সাথে সাথে সরাসরি সলিড রঙে
    দেখা যায় (কোনো পালস/জাম্প নেই); এখনো না-আসা শব্দ হালকা প্লেসহোল্ডার।"""
    words = banglish.split(" ")
    n = len(words)
    slot = (end - start) / n if n else 0

    text = Text()
    for i, word in enumerate(words):
        w_start = start + i * slot
        color = WORD_COLORS[i % len(WORD_COLORS)]

        if song_time >= w_start:
            # সময় হয়ে গেছে -> সরাসরি সলিড রঙে দেখা যাবে
            text.append(word, style=f"bold {color}")
        else:
            # এখনো আসেনি -> প্লেসহোল্ডার (একই দৈর্ঘ্যের ড্যাশ), হালকা
            placeholder = "-" * len(word)
            text.append(placeholder, style=f"dim {HIDDEN_COLOR}")

        if i != n - 1:
            text.append(" ")
    return text


def render_active_line(idx, song_time):
    start, end, banglish, english = LYRICS[idx]
    blocks = []

    if idx > 0:
        _, _, prev_b, _ = LYRICS[idx - 1]
        blocks.append(Align.center(Text(prev_b, style=f"dim {DIM_COLOR}")))
        blocks.append(Text(""))

    blocks.append(Align.center(word_reveal_line(start, end, banglish, song_time)))
    blocks.append(Align.center(Text(english, style=f"italic {ENGLISH_COLOR}")))
    blocks.append(Text(""))

    if idx < len(LYRICS) - 1:
        _, _, next_b, _ = LYRICS[idx + 1]
        blocks.append(Align.center(Text(next_b, style=f"dim {DIM_COLOR}")))

    return Group(*blocks)


def get_prev_line(song_time):
    """gap-এর ঠিক আগে যে লাইনটা শেষ হয়েছে সেটা খুঁজে বের করে।"""
    prev = None
    for s, e, b, en in LYRICS:
        if e <= song_time:
            prev = (b, en)
        else:
            break
    return prev


def get_next_line(song_time):
    """এখনো শুরু হয়নি এমন সবচেয়ে কাছের পরের লাইনটা খুঁজে বের করে।"""
    for s, e, b, en in LYRICS:
        if s > song_time:
            return (b, en)
    return None


def equalizer_bars(song_time):
    """কয়েকটা সাইন-ওয়েভ মিলিয়ে একটা জীবন্ত, নাচতে থাকা mini equalizer বানায়।"""
    text = Text()
    for i in range(EQ_BARS):
        phase = i * 0.7
        val = (math.sin(song_time * 3 + phase) + math.sin(song_time * 5.3 + phase * 1.3)) / 2
        idx = int((val + 1) / 2 * (len(EQ_CHARS) - 1))
        idx = max(0, min(len(EQ_CHARS) - 1, idx))
        color = WORD_COLORS[i % len(WORD_COLORS)]
        text.append(EQ_CHARS[idx], style=f"bold {color}")
        if i != EQ_BARS - 1:
            text.append(" ")
    return text


def render_waiting(song_time):
    """লাইনগুলোর মাঝের নীরবতায় (gap) সদ্য-শেষ হওয়া লাইনটা হালকা ধূসরে
    ধরে রাখা হয় (ফাঁকা না রেখে); একদম শুরুতে (কোনো লাইন এখনো শেষ হয়নি)
    তার বদলে যে লাইনটা এখনই শুরু হবে সেটা ধূসরে দেখানো হয়। সাথে একটা
    নাচতে থাকা mini equalizer।"""
    blocks = [Text("")]

    line = get_prev_line(song_time) or get_next_line(song_time)
    if line:
        line_b, line_en = line
        blocks.append(Align.center(Text(line_b, style=f"dim {DIM_COLOR}")))
        blocks.append(Align.center(Text(line_en, style=f"dim italic {DIM_COLOR}")))
        blocks.append(Text(""))

    blocks.append(Align.center(equalizer_bars(song_time)))
    blocks.append(Text(""))

    return Group(*blocks)


def render_frame(song_time):
    current_idx = None
    for i, (s, e, b, en) in enumerate(LYRICS):
        if s <= song_time < e:
            current_idx = i
            break

    body = render_active_line(current_idx, song_time) if current_idx is not None else render_waiting(song_time)

    header_time = f"[{format_time(song_time)} / {format_time(SONG_TOTAL_DURATION)}]"
    title = f"🎵  Tumi - Level Five (Cover)  🎵   {header_time}"

    return Panel(body, title=title, border_style="bright_magenta", padding=(2, 4))


def main():
    if not os.path.exists(AUDIO_FILE):
        console.print(f"[bold red]Audio file not found:[/bold red] {AUDIO_FILE}")
        sys.exit(1)

    clear_screen()
    console.print(Align.center(Text("🎧 Loading song... 🎧", style="bold cyan")))

    pygame.mixer.init()
    pygame.mixer.music.load(AUDIO_FILE)
    pygame.mixer.music.play(start=START_OFFSET)

    start_time = time.time()

    try:
        while pygame.mixer.music.get_busy():
            song_time = START_OFFSET + (time.time() - start_time)
            clear_screen()
            console.print(render_frame(song_time))
            time.sleep(0.12)
    except KeyboardInterrupt:
        pygame.mixer.music.stop()
        console.print("\n[bold yellow]Stopped.[/bold yellow]")
        sys.exit(0)

    clear_screen()
    console.print(Align.center(Text("\n✨ Song ended ✨", style="bold green")))


if __name__ == "__main__":
    main()
