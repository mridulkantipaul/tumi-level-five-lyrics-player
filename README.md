# Karaoke Lyrics Player 🎤

A terminal and GUI karaoke-style lyrics player that syncs Banglish (romanized
Bengali) lyrics with an audio track — word-by-word color reveal, English
translation underneath, and a small animated equalizer during silent gaps.

## Demo

- `lyrics_player.py` — runs in the terminal (uses [`rich`](https://github.com/Textualize/rich) for colored text)
- `lyrics_player_gui.py` — runs in a small desktop window (uses `tkinter`), useful if your terminal doesn't render complex scripts well

## Setup

```bash
pip install -r requirements.txt
```

> On Windows, if you have multiple Python versions installed, target the
> right one explicitly, e.g. `py -3.12 -m pip install -r requirements.txt`.

## Usage

1. Place your audio file in the project folder and name it `song.mp3`
   (or edit the `AUDIO_FILE` path at the top of the script).
2. Edit the `LYRICS` list in either script — each entry is
   `(start_second, end_second, "Banglish line", "English translation")`.
3. Run:

```bash
python3 lyrics_player.py
# or
python3 lyrics_player_gui.py
```

## ⚠️ About the audio file

This repo includes `song.mp3`. If it's a copyrighted song or cover, keep the
GitHub repository **private** — publicly distributing copyrighted audio can
lead to a DMCA takedown or account issues. Only make the repo public if you
own the rights to the audio or it's royalty-free.

## Customizing

- **Colors**: edit `WORD_COLORS` in either script.
- **Timing**: `LYRICS` timestamps are in seconds from the start of the audio
  file. `START_OFFSET` controls where playback begins.
- **Font (GUI version)**: change `FONT_FAMILY` — use a font that supports
  the script you're displaying if you switch back to native Bengali text.

## License

MIT — do whatever you like with the code. Just don't redistribute copyrighted
audio through it.
