const audioInput = document.getElementById("audio-file");
const lyricsInput = document.getElementById("lyrics-file");
const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

let audioUrl;
let lyrics = [];
let activeIndex = -1;

const createPlaceholder = (message) => {
  lyricsContainer.innerHTML = "";
  const line = document.createElement("p");
  line.className = "placeholder";
  line.textContent = message;
  lyricsContainer.appendChild(line);
};

const parseLyrics = (text) => {
  const parsed = [];

  for (const rawLine of text.split(/\r?\n/)) {
    const timestampPattern = /\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]/g;
    const lineText = rawLine.replace(timestampPattern, "").trim();
    let match = timestampPattern.exec(rawLine);

    while (match) {
      const minutes = Number(match[1]);
      const seconds = Number(match[2]);
      const fractionRaw = match[3] || "0";
      const fraction = Number(`0.${fractionRaw.padEnd(3, "0")}`);

      parsed.push({
        time: minutes * 60 + seconds + fraction,
        text: lineText || "…",
      });

      match = timestampPattern.exec(rawLine);
    }
  }

  return parsed.sort((a, b) => a.time - b.time);
};

const renderLyrics = () => {
  lyricsContainer.innerHTML = "";

  if (!lyrics.length) {
    createPlaceholder("No timestamped lyrics found in this file.");
    return;
  }

  const fragment = document.createDocumentFragment();

  lyrics.forEach((entry, index) => {
    const line = document.createElement("p");
    line.className = "lyric-line";
    line.dataset.index = String(index);
    line.textContent = entry.text;
    fragment.appendChild(line);
  });

  lyricsContainer.appendChild(fragment);
  activeIndex = -1;
};

const syncLyrics = () => {
  if (!lyrics.length) {
    return;
  }

  const currentTime = audio.currentTime;

  let index = -1;
  for (let i = 0; i < lyrics.length; i += 1) {
    if (lyrics[i].time <= currentTime) {
      index = i;
    } else {
      break;
    }
  }

  if (index === activeIndex) {
    return;
  }

  const previousLine = lyricsContainer.querySelector(".lyric-line.active");
  if (previousLine) {
    previousLine.classList.remove("active");
  }

  activeIndex = index;

  if (activeIndex < 0) {
    return;
  }

  const activeLine = lyricsContainer.querySelector(`.lyric-line[data-index=\"${activeIndex}\"]`);
  if (!activeLine) {
    return;
  }

  activeLine.classList.add("active");
  activeLine.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
};

audioInput.addEventListener("change", () => {
  const [file] = audioInput.files || [];

  if (!file) {
    return;
  }

  if (audioUrl) {
    URL.revokeObjectURL(audioUrl);
  }

  audioUrl = URL.createObjectURL(file);
  audio.src = audioUrl;
  audio.load();
});

lyricsInput.addEventListener("change", async () => {
  const [file] = lyricsInput.files || [];

  if (!file) {
    return;
  }

  const content = await file.text();
  lyrics = parseLyrics(content);
  renderLyrics();
  syncLyrics();
});

audio.addEventListener("timeupdate", syncLyrics);
audio.addEventListener("seeked", syncLyrics);
audio.addEventListener("ended", () => {
  activeIndex = -1;
  const previousLine = lyricsContainer.querySelector(".lyric-line.active");
  if (previousLine) {
    previousLine.classList.remove("active");
  }
});
