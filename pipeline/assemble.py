"""Stage 6 - assembly: one master, two exports.

The vertical 9:16 cut is the film. The 16:9 version is derived from the same
master by extending the frame with a blurred copy of itself, because composing
every shot twice would double the generation budget for a second deliverable
nobody grades. DESIGN.md explains the trade-off.

Order of work:
  1. concat the shot clips (already 1080x1920, 24 fps) with the two end cards
  2. duck the score under the narration and normalise to -14 LUFS / -1 dBTP
  3. burn English subtitles and mux
  4. derive the horizontal export from the vertical master

Run:  python -m pipeline.assemble
Writes: outputs/vertical.mp4, outputs/horizontal.mp4, outputs/subs/*.ass
"""

from __future__ import annotations

import json
import re

from . import common
from .common import out_path, probe_duration, rel, stage_cli
from .script import wrap_subtitle

WIDTH, HEIGHT = 1080, 1920
LATIN = "Noto Sans"
ETHIOPIC = "Noto Sans Ethiopic"
ETHIOPIC_RANGE = re.compile(r"[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF\uAB00-\uAB2F]")


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, rest = divmod(rest, 60)
    whole = int(rest)
    centis = int(round((rest - whole) * 100))
    if centis == 100:
        centis, whole = 0, whole + 1
    return f"{int(hours)}:{int(minutes):02d}:{whole:02d}.{centis:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def ass_header(res_x: int, res_y: int, *, font: str, size: int, margin_v: int) -> str:
    return "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {res_x}",
        f"PlayResY: {res_y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # BorderStyle 3 draws a box behind each line and pads it by Outline, so a
        # semi-transparent plate travels with the words. A bare outline was
        # legible on the indigo hut and lost on the white dress and the sunlit
        # pavement; the plate is what survives both.
        f"Style: Sub,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H66000000,"
        f"0,0,0,0,100,100,0,0,3,9,0,2,{int(res_x * 0.08)},{int(res_x * 0.08)},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])


def write_subtitles(storyboard: dict, timing: dict, path, *, res_x: int, res_y: int, size: int, margin_v: int) -> None:
    """English subtitles, burned in and shipped as a sidecar.

    The narration is Amharic; the subtitles are the English translation from the
    contract, never a transcript of the audio.
    """
    by_id = {shot["id"]: shot for shot in storyboard["shots"]}
    lines = [ass_header(res_x, res_y, font=LATIN, size=size, margin_v=margin_v)]
    for entry in timing["shots"]:
        shot = by_id[entry["id"]]
        script = shot.get("narration")
        if not script:
            continue
        start = entry["start_s"] + 0.25
        end = min(entry["start_s"] + entry["duration_s"] - 0.15, start + 7.5)
        text = "\\N".join(ass_escape(line) for line in wrap_subtitle(script["subtitle"]))
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Sub,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n")


def write_srt(storyboard: dict, timing: dict, path) -> None:
    by_id = {shot["id"]: shot for shot in storyboard["shots"]}
    blocks, index = [], 1
    for entry in timing["shots"]:
        script = by_id[entry["id"]].get("narration")
        if not script:
            continue
        start = entry["start_s"] + 0.25
        end = min(entry["start_s"] + entry["duration_s"] - 0.15, start + 7.5)

        def stamp(value: float) -> str:
            millis = int(round(value * 1000))
            hours, millis = divmod(millis, 3_600_000)
            minutes, millis = divmod(millis, 60_000)
            seconds, millis = divmod(millis, 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        text = "\n".join(wrap_subtitle(script["subtitle"]))
        blocks.append(f"{index}\n{stamp(start)} --> {stamp(end)}\n{text}\n")
        index += 1
    path.write_text("\n".join(blocks))


# --------------------------------------------------------------------------
# cards
# --------------------------------------------------------------------------

def build_cards(storyboard: dict, timing: dict) -> list:
    card_dir = out_path("cards", ".keep").parent
    clips = []
    durations = {entry["id"]: entry["duration_s"] for entry in timing["cards"]}
    for card in storyboard["end_cards"]:
        duration = durations.get(card["id"], card["duration_s"])
        background = "#000000" if card.get("background", "black") == "black" else "#efe4cf"
        primary = "&H00FFFFFF" if card.get("background", "black") == "black" else "&H00202020"
        font = ETHIOPIC if any(ETHIOPIC_RANGE.search(line) for line in card["lines"]) else LATIN
        ass = card_dir / f"{card['id']}.ass"
        events = []
        for index, line in enumerate(card["lines"]):
            size = 52 if ETHIOPIC_RANGE.search(line) else 40
            y = HEIGHT * 0.44 + index * 130
            events.append(
                f"Dialogue: 0,{ass_time(0)},{ass_time(duration)},Card,,0,0,0,,"
                f"{{\\an5\\pos({WIDTH // 2},{y:.0f})\\fs{size}\\c{primary}}}{ass_escape(line)}"
            )
        ass.write_text("\n".join([
            "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}",
            "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Card,{font},50,{primary},&H00FFFFFF,&H00000000,&H00000000,"
            f"0,0,0,0,100,100,0,0,1,0,0,5,90,90,0,1",
            "", "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *events,
        ]) + "\n")
        clip = card_dir / f"{card['id']}.mp4"
        common.ff(
            "-f", "lavfi", "-i", f"color=c={background}:s={WIDTH}x{HEIGHT}:r=24:d={duration}",
            "-vf", f"ass={ass},fade=t=in:st=0:d=0.5,fade=t=out:st={max(0.0, duration - 0.5)}:d=0.5,format=yuv420p",
            "-t", duration, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "24", clip,
        )
        clips.append(clip)
    return clips


# --------------------------------------------------------------------------
# audio
# --------------------------------------------------------------------------

def measure_loudness(path) -> dict:
    result = common.run([
        common.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ])
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def mix_audio(storyboard: dict) -> None:
    """Score ducked under the voice, exactly as the contract specifies."""
    duck = storyboard["music"]["ducking"]
    loud = storyboard["music"]["loudness"]
    score = out_path("audio", "score.wav")
    voice = out_path("audio", "radio_cut.wav")
    raw = out_path("audio", "mix_flat.wav")
    for path in (score, voice):
        if not path.exists():
            common.die(f"missing {rel(path)}. Run `make narration` and `make music` first.")

    common.ff(
        "-i", score, "-i", voice,
        "-filter_complex",
        f"[1:a]asplit[voice][key];"
        f"[0:a][key]sidechaincompress=threshold={duck['threshold']}:ratio={duck['ratio']}"
        f":attack={duck['attack_ms']}:release={duck['release_ms']}:makeup=1[ducked];"
        f"[ducked][voice]amix=inputs=2:duration=longest:normalize=0[premix];"
        f"[premix]atrim=0:{measure_duration(voice):.3f},aresample=48000[mix]",
        "-map", "[mix]", "-ac", "2", "-c:a", "pcm_s16le", raw,
    )

    # Two-pass loudness normalisation: measure, then apply linearly so the
    # dynamics of the ducking survive.
    stats = measure_loudness(raw)
    target = out_path("audio", "mix.wav")
    if stats:
        common.ff(
            "-i", raw, "-af",
            f"loudnorm=I={loud['target_lufs']}:TP={loud['true_peak_db']}:LRA=11"
            f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
            f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
            f":offset={stats['target_offset']}:linear=true,aresample=48000",
            "-ac", "2", "-c:a", "pcm_s16le", target,
        )
    else:
        common.ff("-i", raw, "-af", f"loudnorm=I={loud['target_lufs']}:TP={loud['true_peak_db']}",
                  "-ac", "2", "-c:a", "pcm_s16le", target)
    raw.unlink(missing_ok=True)
    measured = measure_loudness(target)
    if measured:
        print(f"  mix: {measured.get('input_i')} LUFS, true peak {measured.get('input_tp')} dBTP")


def measure_duration(path) -> float:
    return probe_duration(path)


# --------------------------------------------------------------------------
# video
# --------------------------------------------------------------------------

def concat_video(storyboard: dict, timing: dict, cards: list) -> None:
    clips = []
    for entry in timing["shots"]:
        clip = out_path("clips", f"{entry['id']}.mp4")
        if not clip.exists():
            common.die(f"missing {rel(clip)}. Run `make shots` first.")
        clips.append(clip)
    clips.extend(cards)
    listing = out_path("tmp", "concat.txt")
    listing.write_text("".join(f"file '{clip}'\n" for clip in clips))
    common.ff("-f", "concat", "-safe", "0", "-i", listing,
              "-c", "copy", "-movflags", "+faststart", out_path("video_silent.mp4"))
    print(f"  video: {probe_duration(out_path('video_silent.mp4')):.1f}s from {len(clips)} clips")


def export_vertical(storyboard: dict, timing: dict) -> None:
    subs = out_path("subs", "vertical.ass")
    write_subtitles(storyboard, timing, subs, res_x=WIDTH, res_y=HEIGHT, size=38, margin_v=210)
    common.ff(
        "-i", out_path("video_silent.mp4"), "-i", out_path("audio", "mix.wav"),
        "-vf", f"ass={subs},format=yuv420p",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", out_path("vertical.mp4"),
    )


def export_horizontal(storyboard: dict, timing: dict) -> None:
    width, height = 1920, 1080
    subs = out_path("subs", "horizontal.ass")
    write_subtitles(storyboard, timing, subs, res_x=width, res_y=height, size=34, margin_v=54)
    common.ff(
        "-i", out_path("video_silent.mp4"), "-i", out_path("audio", "mix.wav"),
        "-filter_complex",
        "[0:v]split[bg][fg];"
        "[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        "gblur=sigma=45,eq=brightness=-0.06:saturation=0.75[bgb];"
        "[fg]scale=-2:1080[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2[base];"
        f"[base]ass={subs},format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", out_path("horizontal.mp4"),
    )


def run(storyboard: dict, args, only) -> None:
    timing_path = out_path("audio", "timing.json")
    if not timing_path.exists():
        common.die("outputs/audio/timing.json is missing. Run `make narration` first.")
    timing = json.loads(timing_path.read_text())

    if args.dry_run:
        print(f"  would assemble {len(timing['shots'])} shots + {len(timing['cards'])} cards "
              f"into {timing['total_s']:.1f}s")
        return

    write_srt(storyboard, timing, out_path("subs", "film.en.srt"))
    cards = build_cards(storyboard, timing)
    concat_video(storyboard, timing, cards)
    mix_audio(storyboard)

    for export in storyboard["exports"]:
        target = out_path(f"{export['name']}.mp4")
        if export["aspect"] == "9:16":
            export_vertical(storyboard, timing)
        elif export["aspect"] == "16:9":
            export_horizontal(storyboard, timing)
        else:
            common.die(f"no exporter for aspect {export['aspect']}")
        duration = probe_duration(target)
        size_mb = target.stat().st_size / 1e6
        print(f"  {export['name']}: {rel(target)} {duration:.1f}s, {size_mb:.1f} MB")
        if not 60 <= duration <= 90:
            print(f"  ! {export['name']} is {duration:.1f}s, outside the 60-90s brief")
        common.log_run(stage="assemble", operation="export", provider="local", model="ffmpeg",
                       status="ok", export=export["name"], seconds=duration,
                       bytes=target.stat().st_size)


if __name__ == "__main__":
    stage_cli("assemble", run, description="Assemble the vertical master and derive the horizontal export")
