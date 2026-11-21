"""Đọc content bằng OmniVoice (k2-fsa/OmniVoice).

3 chế độ:
  clone  – nhân bản giọng từ file giọng mẫu (3–10 giây) trong thư viện giọng
  design – mô tả giọng: giới tính, độ tuổi, cao độ...
  auto   – ủy quyền cho tool: Claude chọn kiểu giọng hợp với chủ đề
Với design/auto: đọc cảnh đầu bằng mô tả, rồi dùng chính giọng đó để nhân bản cho các
cảnh sau, để cả video chỉ có MỘT giọng thống nhất.
"""
import threading
from pathlib import Path

import numpy as np

from . import audio_check as AC
from . import languages as LG
from . import project as P
from .config import VOICES, load_settings

SR = 24000
PAUSE_SEC = 0.18  # nghỉ giữa các cảnh

VOICE_DESIGN_OPTIONS = {
    "gender": ["male", "female"],
    "age": ["child", "teenager", "young adult", "middle-aged", "elderly"],
    "pitch": ["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"],
    "style": ["", "whisper"],
}
_ALLOWED = {x for v in VOICE_DESIGN_OPTIONS.values() for x in v if x}

_model = None
_model_lock = threading.Lock()


def get_model(log=print):
    global _model
    with _model_lock:
        if _model is None:
            import torch
            from omnivoice import OmniVoice
            if torch.cuda.is_available():
                dev, dtype = "cuda:0", torch.float16
                log(f"Đang tải OmniVoice lên GPU {torch.cuda.get_device_name(0)} (lần đầu sẽ tải model ~vài GB)...")
            else:
                dev, dtype = "cpu", torch.float32
                log("⚠️ Không thấy GPU NVIDIA (CUDA) – chạy bằng CPU sẽ rất chậm. Kiểm tra lại bản torch cài đặt.")
            _model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev, dtype=dtype)
        return _model


def clean_instruct(instruct: str) -> str:
    parts = [x.strip().lower() for x in (instruct or "").split(",")]
    return ", ".join(x for x in parts if x in _ALLOWED)


def list_voices() -> list[dict]:
    out = []
    for f in sorted(VOICES.iterdir()):
        if f.suffix.lower() in (".wav", ".mp3", ".m4a", ".flac", ".ogg"):
            txt = f.with_suffix(".txt")
            out.append({"name": f.stem, "file": f.name,
                        "ref_text": txt.read_text(encoding="utf-8") if txt.exists() else ""})
    return out


def voice_file(name: str) -> Path | None:
    for v in list_voices():
        if v["name"] == name:
            return VOICES / v["file"]
    return None


def _trim(audio: np.ndarray, thr_db: float = -42) -> np.ndarray:
    """Cắt khoảng lặng đầu/cuối."""
    if audio.size == 0:
        return audio
    frame = int(SR * 0.02)
    n = len(audio) // frame
    if n == 0:
        return audio
    rms = np.sqrt(np.mean(audio[: n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-9) + 1e-12)
    idx = np.where(db > thr_db)[0]
    if idx.size == 0:
        return audio
    a = max(0, idx[0] - 2) * frame
    b = min(len(audio), (idx[-1] + 3) * frame)
    return audio[a:b]


def _prompt_for_clone(model, ref_audio: Path, ref_text: str, cache: Path):
    from omnivoice import VoiceClonePrompt
    if cache.exists() and cache.stat().st_mtime >= ref_audio.stat().st_mtime:
        try:
            return VoiceClonePrompt.load(str(cache))
        except Exception:
            pass
    if not ref_text and getattr(model, "_asr_pipe", None) is None:
        model.load_asr_model()  # Whisper tự chép lời giọng mẫu
    prompt = model.create_voice_clone_prompt(ref_audio=str(ref_audio), ref_text=ref_text or None)
    try:
        prompt.save(str(cache))
    except Exception:
        pass
    return prompt


def synth(pid: str, log, only: list[str] | None = None) -> None:
    import soundfile as sf

    p = P.load(pid)
    scenes = p["scenes"]
    if not scenes:
        raise RuntimeError("Chưa có content.")
    voice = p.get("voice", {})
    lang = LG.get(p.get("lang"))["tts"]
    mode = voice.get("mode", "clone")
    speed = float(voice.get("speed") or 1.0)
    num_step = int(load_settings().get("tts_num_step", 32))
    model = get_model(log)
    adir = P.pdir(pid) / "audio"
    adir.mkdir(exist_ok=True)

    kwargs: dict = {}
    if mode == "clone":
        vf = voice_file(voice.get("voice", ""))
        if not vf:
            raise RuntimeError("Chưa chọn giọng mẫu. Hãy upload giọng mẫu ở bước Giọng đọc.")
        ref_txt = vf.with_suffix(".txt")
        kwargs["voice_clone_prompt"] = _prompt_for_clone(
            model, vf, ref_txt.read_text(encoding="utf-8") if ref_txt.exists() else "",
            vf.with_suffix(".pt"))
        log(f"Nhân bản giọng từ: {vf.name}")
    else:
        instruct = clean_instruct(voice.get("instruct") if mode == "design" else voice.get("auto_instruct"))
        anchor = P.pdir(pid) / "audio" / "_voice_anchor.wav"
        anchor_txt = anchor.with_suffix(".txt")
        if anchor.exists() and voice.get("anchor_instruct") == instruct and only:
            kwargs["voice_clone_prompt"] = _prompt_for_clone(
                model, anchor, anchor_txt.read_text(encoding="utf-8"), anchor.with_suffix(".pt"))
        else:
            # Đọc cảnh đầu bằng mô tả giọng → dùng làm giọng mẫu cho cả video
            first = scenes[0]
            text = first.get("tts") or P.scene_plain_text(first)
            log(f"Tạo giọng theo mô tả: “{instruct or 'tự động'}”")
            gen = model.generate(text=text, language=lang, instruct=instruct or None,
                                 speed=speed, num_step=num_step)
            sf.write(anchor, _trim(np.asarray(gen[0], dtype=np.float32)), SR)
            anchor_txt.write_text(text, encoding="utf-8")
            anchor.with_suffix(".pt").unlink(missing_ok=True)
            kwargs["voice_clone_prompt"] = _prompt_for_clone(model, anchor, text, anchor.with_suffix(".pt"))
            P.update(pid, lambda pp: pp["voice"].__setitem__("anchor_instruct", instruct))

    todo = [s for s in scenes if not only or s["id"] in only]
    results = {}
    for i, s in enumerate(todo):
        text = s.get("tts") or P.scene_plain_text(s)
        log(f"Đọc cảnh {s['id']} ({i + 1}/{len(todo)}): {text[:30]}...", i / len(todo))
        expect = LG.est_seconds(P.scene_plain_text(s)) / max(speed, 0.3)
        best, best_bad = None, None
        for attempt in range(3):   # đọc lỗi (im lặng / thiếu / mẫu hỏng) → tự đọc lại tối đa 2 lần
            gen = model.generate(text=text, language=lang, speed=speed, num_step=num_step, **kwargs)
            raw = np.asarray(gen[0], dtype=np.float32)
            bad = AC.problem(raw, SR, expect)
            cand = _trim(AC.clean(raw))
            if best is None or (best_bad and not bad) or \
                    (bad and AC.stats(cand, SR)["voiced_sec"] > AC.stats(best, SR)["voiced_sec"]):
                best, best_bad = cand, bad
            if not bad:
                break
            log(f"  ⚠️ cảnh {s['id']}: {bad} → đọc lại (lần {attempt + 2})")
        if best_bad:
            log(f"  ⚠️ cảnh {s['id']} vẫn {best_bad} – hãy nghe lại cảnh này, nếu thiếu thì bấm đọc lại")
        audio = AC.level(best, SR)   # cân bằng âm lượng theo giọng nói, không theo tiếng lách tách
        audio = np.concatenate([audio, np.zeros(int(SR * PAUSE_SEC), dtype=np.float32)])
        f = adir / f"{s['id']}.wav"
        sf.write(f, audio, SR)
        results[s["id"]] = {"audio": f"audio/{f.name}", "duration": round(len(audio) / SR, 3),
                            "audio_text": text}

    def apply(pp):
        for sc in pp["scenes"]:
            if sc["id"] in results:
                sc.update(results[sc["id"]])
    P.update(pid, apply)
    total = sum(r["duration"] for r in results.values())
    log(f"Đã đọc {len(results)} cảnh, tổng {total:.1f}s.", 1.0)
