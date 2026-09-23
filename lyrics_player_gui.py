#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Karaoke-style GUI lyrics player (Banglish + English translation).

Features:
- Precise absolute timestamps per line (matches the real song).
- Word-by-word color reveal inside a tkinter Text widget: each word
  turns solid-colored the moment its time slot arrives (no
  pulsing/jumping); not-yet-reached words show as dim dash
  placeholders.
- English translation stays a plain/neutral color under the Banglish line.
- During silence between lines, the last finished (or next upcoming)
  line lingers on screen dimmed, with a small animated equalizer.

Usage:
    python3 lyrics_player_gui.py

Requirements:
    pip install pygame
    (tkinter সাধারণত Python-এর সাথেই বিল্ট-ইন থাকে)
"""

import math
import time
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import tkinter as tk
import pygame

# ---------- CONFIG ----------

AUDIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "song.mp3")
START_OFFSET = 180.0            # গান এখান থেকে শুরু হবে (সেকেন্ড) -> 3:00
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
    "#FF6EC7",  # pink
    "#5ED3F3",  # cyan
    "#FFE066",  # yellow
    "#6BFF95",  # green
    "#FF7676",  # red
    "#8C9EFF",  # blue
    "#FFB454",  # orange
    "#7CFFCB",  # spring green
]

FONT_FAMILY = "Segoe UI"
BG_COLOR = "#0e0e14"
DIM_COLOR = "#666677"
HIDDEN_COLOR = "#3a3a44"
ENGLISH_COLOR = "#e8e8ee"


def format_time(seconds):
    seconds = max(0, seconds)
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def get_prev_line(song_time):
    prev = None
    for s, e, b, en in LYRICS:
        if e <= song_time:
            prev = (b, en)
        else:
            break
    return prev


def get_next_line(song_time):
    for s, e, b, en in LYRICS:
        if s > song_time:
            return (b, en)
    return None


class KaraokeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tumi - Level Five (Cover)")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("1000x520")

        self.title_label = tk.Label(
            root, text="🎵 Tumi - Level Five (Cover) 🎵",
            font=(FONT_FAMILY, 16, "bold"),
            fg="#c084fc", bg=BG_COLOR,
        )
        self.title_label.pack(pady=(25, 5))

        self.time_label = tk.Label(
            root, text="", font=(FONT_FAMILY, 12),
            fg=DIM_COLOR, bg=BG_COLOR,
        )
        self.time_label.pack(pady=(0, 25))

        self.prev_label = tk.Label(
            root, text="", font=(FONT_FAMILY, 18),
            fg=DIM_COLOR, bg=BG_COLOR,
        )
        self.prev_label.pack(pady=5)

        # বর্তমান লাইন দেখানোর জন্য Text widget — কারণ একই লাইনে একাধিক
        # শব্দকে আলাদা আলাদা রঙ দিতে হলে Label যথেষ্ট না, Text-এর tag লাগবে
        self.current_text = tk.Text(
            root, height=1, font=(FONT_FAMILY, 30, "bold"),
            fg="white", bg=BG_COLOR, bd=0, highlightthickness=0,
            wrap="none", cursor="arrow",
        )
        self.current_text.tag_configure("center", justify="center")
        self.current_text.pack(pady=15, fill="x", padx=20)
        self.current_text.config(state="disabled")

        # প্রতিটা রঙের জন্য একটা করে ট্যাগ আগে থেকেই বানানো
        for i, color in enumerate(WORD_COLORS):
            self.current_text.tag_configure(f"word{i}", foreground=color, justify="center")
        self.current_text.tag_configure("hidden", foreground=HIDDEN_COLOR, justify="center")
        self.current_text.tag_configure("dim_line", foreground=DIM_COLOR, justify="center")

        self.english_label = tk.Label(
            root, text="", font=(FONT_FAMILY, 16, "italic"),
            fg=ENGLISH_COLOR, bg=BG_COLOR,
        )
        self.english_label.pack(pady=5)

        self.next_label = tk.Label(
            root, text="", font=(FONT_FAMILY, 18),
            fg=DIM_COLOR, bg=BG_COLOR,
        )
        self.next_label.pack(pady=(20, 5))

        # ছোট্ট একটা অ্যানিমেটেড ইকুয়ালাইজার (গ্যাপের সময়ে জীবন্ত রাখার জন্য)
        self.eq_canvas = tk.Canvas(
            root, width=260, height=50, bg=BG_COLOR, highlightthickness=0,
        )
        self.eq_canvas.pack(pady=10)

        self.start_time = None

    def set_current_line_text(self, words, revealed_upto):
        """words: list[str]; revealed_upto: কয়টা শব্দ পর্যন্ত রঙিন দেখাবে।"""
        self.current_text.config(state="normal")
        self.current_text.delete("1.0", "end")
        for i, word in enumerate(words):
            if i < revealed_upto:
                tag = f"word{i % len(WORD_COLORS)}"
                display = word
            else:
                tag = "hidden"
                display = "-" * len(word)
            self.current_text.insert("end", display, (tag, "center"))
            if i != len(words) - 1:
                self.current_text.insert("end", " ", ("center",))
        self.current_text.config(state="disabled")

    def draw_equalizer(self, song_time):
        self.eq_canvas.delete("all")
        num_bars = 9
        bar_w = 18
        gap = 8
        total_w = num_bars * bar_w + (num_bars - 1) * gap
        x0 = (260 - total_w) / 2
        for i in range(num_bars):
            phase = i * 0.7
            val = (math.sin(song_time * 3 + phase) + math.sin(song_time * 5.3 + phase * 1.3)) / 2
            height = max(4, (val + 1) / 2 * 44)
            x = x0 + i * (bar_w + gap)
            y0 = 48 - height
            color = WORD_COLORS[i % len(WORD_COLORS)]
            self.eq_canvas.create_rectangle(x, y0, x + bar_w, 48, fill=color, outline="")

    def show_active_line(self, idx, song_time):
        start, end, banglish, english = LYRICS[idx]
        words = banglish.split(" ")
        n = len(words)
        slot = (end - start) / n if n else 0

        revealed_upto = 0
        for i in range(n):
            w_start = start + i * slot
            if song_time >= w_start:
                revealed_upto = i + 1

        self.set_current_line_text(words, revealed_upto)
        self.english_label.config(text=english)

        self.prev_label.config(text=LYRICS[idx - 1][2] if idx > 0 else "")
        self.next_label.config(text=LYRICS[idx + 1][2] if idx < len(LYRICS) - 1 else "")

        self.eq_canvas.delete("all")

    def show_waiting(self, song_time):
        line = get_prev_line(song_time) or get_next_line(song_time)
        if line:
            line_b, line_en = line
            self.set_current_line_text([line_b], 0)  # পুরোটাই dim/hidden স্টাইলে
            self.current_text.config(state="normal")
            self.current_text.tag_add("dim_line", "1.0", "end")
            self.current_text.config(state="disabled")
            self.english_label.config(text=line_en, fg=DIM_COLOR)
        else:
            self.set_current_line_text([""], 0)
            self.english_label.config(text="")

        self.prev_label.config(text="")
        self.next_label.config(text="")
        self.draw_equalizer(song_time)
        self.english_label.config(fg=DIM_COLOR)

    def start_playback(self):
        pygame.mixer.init()
        pygame.mixer.music.load(AUDIO_FILE)
        pygame.mixer.music.play(start=START_OFFSET)
        self.start_time = time.time()
        self.update_loop()

    def update_loop(self):
        if not pygame.mixer.music.get_busy():
            self.set_current_line_text(["✨", "Song", "ended", "✨"], 4)
            self.english_label.config(text="")
            self.prev_label.config(text="")
            self.next_label.config(text="")
            self.eq_canvas.delete("all")
            return

        song_time = START_OFFSET + (time.time() - self.start_time)

        current_idx = None
        for i, (s, e, b, en) in enumerate(LYRICS):
            if s <= song_time < e:
                current_idx = i
                break

        self.english_label.config(fg=ENGLISH_COLOR)
        if current_idx is not None:
            self.show_active_line(current_idx, song_time)
        else:
            self.show_waiting(song_time)

        self.time_label.config(
            text=f"{format_time(song_time)} / {format_time(SONG_TOTAL_DURATION)}"
        )

        self.root.after(100, self.update_loop)

    def on_close(self):
        pygame.mixer.music.stop()
        self.root.destroy()


def main():
    if not os.path.exists(AUDIO_FILE):
        print(f"Audio file not found: {AUDIO_FILE}")
        sys.exit(1)

    root = tk.Tk()
    app = KaraokeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.after(200, app.start_playback)
    root.mainloop()


if __name__ == "__main__":
    main()
