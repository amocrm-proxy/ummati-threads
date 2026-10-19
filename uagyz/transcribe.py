"""Уағыз: расшифровка длинного видео (казахский) с привязкой ко времени — для выбора законченных по смыслу отрывков.
python uagyz/transcribe.py <видео> <папка_вывода>
Пишет transcript.json (сегменты и слова со временем) и transcript.txt (читаемый текст с таймкодами)."""
import json, os, subprocess, sys, time

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
import numpy as np                              # звук декодируем сами (ffmpeg), без PyAV — у него ломается совместимость
audio = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout, np.float32)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                           capture_output=True, text=True).stdout.strip())
info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                       "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip()
print("Видео:", round(dur), "сек,", info)

from faster_whisper import WhisperModel
model = WhisperModel(os.environ.get("WHISPER_MODEL", "medium"), device="cpu", compute_type="int8")
t0 = time.time()
segs, meta = model.transcribe(audio, language="kk", word_timestamps=True, vad_filter=True,
                              vad_parameters={"min_silence_duration_ms": 400}, beam_size=5)
res = []
for s in segs:
    res.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                "words": [[round(w.start, 2), round(w.end, 2), w.word] for w in (s.words or [])]})
    if len(res) % 50 == 0:
        print(f"{s.end / 60:.1f} мин из {dur / 60:.1f} ({time.time() - t0:.0f} с)")
json.dump({"source": os.path.basename(src), "duration": dur, "size": info, "segments": res},
          open(os.path.join(out, "transcript.json"), "w", encoding="utf-8"), ensure_ascii=False)
with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
    for s in res:
        f.write(f"[{int(s['start'] // 60):02d}:{s['start'] % 60:05.2f} – {int(s['end'] // 60):02d}:{s['end'] % 60:05.2f}] {s['text']}\n")
print("Готово:", len(res), "сегментов за", round(time.time() - t0), "с")
