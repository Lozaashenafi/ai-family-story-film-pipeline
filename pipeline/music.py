"""Stage 5 - music: four cues, one continuous score bed.

Each cue is generated from its caption in the contract, with `candidates`
variations. Nothing here picks the winner by ear, so the stage writes every
candidate and reads the choice from outputs/audio/music/choices.json; the first
candidate is the default, and a human can change the chooser's mind by editing
that file and re-running `make assemble`.

Without a music endpoint the stage writes a deterministic synthesised bed from
the cue's key and tempo. It is a placeholder with the right shape and the right
lengths - not a score.

Run:  python -m pipeline.music [--force]
Writes: outputs/audio/music/<cue>_candidate_<n>.wav, outputs/audio/score.wav
"""

from __future__ import annotations

import json
import re
import wave

from . import common, providers
from .common import out_path, rel, stage_cli

SAMPLE_RATE = 24000
FADE_OUT = 1.2  # seconds of fade at each cue boundary
FADE_IN = 0.15  # the film opens on sound, not on silence: see normalise_bed()
BED_LUFS = -27.0  # score level before it is ducked under the voice

ROOT_NOTE = {
    "c": 130.81, "c#": 138.59, "db": 138.59, "d": 146.83, "d#": 155.56, "eb": 155.56,
    "e": 164.81, "f": 174.61, "f#": 185.00, "gb": 185.00, "g": 196.00,
    "g#": 207.65, "ab": 207.65, "a": 220.00, "a#": 233.08, "bb": 233.08, "b": 246.94,
}


def cue_windows(storyboard: dict, timing: dict) -> list[dict]:
    """A cue spans from the start of its first shot to the end of its last."""
    spans = {entry["id"]: (entry["start_s"], entry["start_s"] + entry["duration_s"]) for entry in timing["shots"]}
    order = [shot["id"] for shot in storyboard["shots"]]
    windows = []
    for cue in storyboard["music"]["cues"]:
        if cue["from_shot"] not in spans or cue["to_shot"] not in spans:
            continue
        start = spans[cue["from_shot"]][0]
        end = spans[cue["to_shot"]][1]
        if order.index(cue["to_shot"]) < order.index(cue["from_shot"]):
            common.die(f"cue {cue['id']} runs backwards in the shot order")
        windows.append({"cue": cue, "start": start, "end": end, "duration": round(end - start, 2)})
    return windows


def synth_cue(target, *, duration: float, bpm: int, key: str, gain_db: float,
              fade_in: float = FADE_IN) -> None:
    """A slow pentatonic drone with a pulse, shaped to the cue's tempo.

    Deliberately plain: it exists so the film has something under the voice in
    a keyless build, and so the ducking can be tested for real.
    """
    root_name = key.split()[0].lower() if key else "c"
    root = ROOT_NOTE.get(root_name, 130.81)
    beat = 60.0 / max(40, bpm)
    common.ff(
        "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono:d={duration}",
        "-t", duration,
        "-f", "lavfi", "-i", f"sine=frequency={root}:sample_rate={SAMPLE_RATE}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={root * 1.5:.2f}:sample_rate={SAMPLE_RATE}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={root * 2:.2f}:sample_rate={SAMPLE_RATE}:duration={duration}",
        "-filter_complex",
        "[1][2][3]amix=inputs=3:normalize=1,"
        f"tremolo=f={1 / beat:.3f}:d=0.35,"
        "lowpass=f=1600,aecho=0.7:0.5:180|360:0.35|0.18,"
        f"volume={gain_db}dB,"
        f"afade=t=in:d={fade_in},afade=t=out:st={max(0.0, duration - FADE_OUT):.3f}:d={FADE_OUT}[bed]",
        "-map", "[bed]", "-ac", "1", "-ar", SAMPLE_RATE, "-c:a", "pcm_s16le", target,
    )


def normalise_bed(path) -> None:
    """Raise the assembled bed to a level that survives a phone speaker.

    The first cut measured -47 dB in its opening second, because the bed was
    synthesised quietly and then faded in over 1.2 s. One tester thought his
    device audio was broken. Normalising the finished bed - rather than each
    cue - keeps the cue-to-cue arc (cold, urgent, warm, thinning) intact, and
    the assembly stage still ducks it under every line.
    """
    result = common.run([
        common.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"loudnorm=I={BED_LUFS}:TP=-6:LRA=9:print_format=json", "-f", "null", "-",
    ])
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr, re.S)
    if not match:
        return
    try:
        stats = json.loads(match.group(0))
    except json.JSONDecodeError:
        return
    normalised = path.with_name(path.stem + ".norm.wav")
    common.ff(
        "-i", path, "-af",
        f"loudnorm=I={BED_LUFS}:TP=-6:LRA=9:measured_I={stats['input_i']}"
        f":measured_TP={stats['input_tp']}:measured_LRA={stats['input_lra']}"
        f":measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}"
        f":linear=true,aresample={SAMPLE_RATE}",
        "-ac", "1", "-c:a", "pcm_s16le", normalised,
    )
    normalised.replace(path)
    print(f"  score: normalised to {BED_LUFS:.0f} LUFS for the mix")


def run(storyboard: dict, args, only) -> None:
    timing_path = out_path("audio", "timing.json")
    if not timing_path.exists():
        common.die("outputs/audio/timing.json is missing. Run `make narration` first.")
    timing = json.loads(timing_path.read_text())
    windows = cue_windows(storyboard, timing)
    mode = common.provider_mode()
    music_dir = out_path("audio", "music", ".keep").parent
    choices_path = music_dir / "choices.json"

    chosen: dict[str, str] = {}
    if choices_path.exists():
        chosen = json.loads(choices_path.read_text())
    if args.dry_run:
        for window in windows:
            print(f"  {window['cue']['id']}: {window['duration']:.1f}s from "
                  f"{window['cue']['from_shot']} to {window['cue']['to_shot']}")
        return

    for window in windows:
        cue = window["cue"]
        if only and cue["id"] not in only:
            continue
        candidates = cue.get("candidates", 3)
        for index in range(1, candidates + 1):
            target = music_dir / f"{cue['id']}_candidate_{index}.wav"
            key = common.artifact_key("music", cue["id"], cue["caption"], window["duration"],
                                      cue.get("bpm"), cue.get("key"), index, mode)
            if common.is_fresh(target, key) and not args.force:
                print(f"  {cue['id']} #{index}: cached")
                continue
            print(f"  {cue['id']} #{index}: {window['duration']:.1f}s, {cue.get('key')} at {cue.get('bpm')} bpm")
            if mode == "real":
                try:
                    raw, cost = providers.ace_step(
                        caption=cue["caption"], seconds=window["duration"],
                        bpm=cue.get("bpm", 80), key=cue.get("key", "C minor"), seed=1000 + index,
                    )
                    staged = music_dir / f"{cue['id']}_candidate_{index}.raw"
                    staged.write_bytes(raw)
                    common.ff("-i", staged, "-af", f"afade=t=in:d={FADE_IN},"
                                                   f"afade=t=out:st={max(0.0, window['duration'] - FADE_OUT):.3f}:d={FADE_OUT}",
                              "-t", window["duration"], "-ac", "1", "-ar", SAMPLE_RATE,
                              "-c:a", "pcm_s16le", target)
                    staged.unlink(missing_ok=True)
                    common.log_run(stage="music", operation="music", provider="ace-step", model="ace-step",
                                   status="ok", cue_id=cue["id"], candidate=index,
                                   cost_usd_estimate=round(cost, 4))
                except providers.ProviderError as exc:
                    print(f"    ! {exc}; writing the synthesised fallback instead")
                    common.log_run(stage="music", operation="music", provider="none", model="none",
                                   status="fallback", cue_id=cue["id"], candidate=index, note=str(exc))
                    synth_cue(target, duration=window["duration"], bpm=cue.get("bpm", 80),
                              key=cue.get("key", "C minor"), gain_db=cue.get("gain_db", -6))
            else:
                synth_cue(target, duration=window["duration"], bpm=cue.get("bpm", 80),
                          key=cue.get("key", "C minor"), gain_db=cue.get("gain_db", -6))
                common.log_run(stage="music", operation="music", provider="mock", model="synth",
                               status="ok", cue_id=cue["id"], candidate=index)
            common.mark_fresh(target, key)

    # Assemble the bed: cues placed on the timeline, faded at both ends, so the
    # scene changes are felt as a breath rather than heard as a splice.
    total = timing["total_s"]
    buffer = bytearray(int(round(total * SAMPLE_RATE)) * 2)
    for window in windows:
        cue = window["cue"]
        pick = chosen.get(cue["id"], f"{cue['id']}_candidate_1.wav")
        path = music_dir / pick
        if not path.exists():
            print(f"  ! {cue['id']}: {pick} does not exist, skipping the cue")
            continue
        with wave.open(str(path), "rb") as handle:
            pcm = handle.readframes(handle.getnframes())
        offset = int(round(window["start"] * SAMPLE_RATE)) * 2
        end = min(len(buffer), offset + len(pcm))
        buffer[offset:end] = pcm[: end - offset]

    score = out_path("audio", "score.wav")
    with wave.open(str(score), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(bytes(buffer))

    normalise_bed(score)

    if not choices_path.exists():
        choices_path.write_text(json.dumps(
            {c["id"]: f"{c['id']}_candidate_1.wav" for c in storyboard["music"]["cues"]}, indent=2) + "\n")
    print(f"  wrote {rel(score)} ({total:.1f}s) and {rel(choices_path)}")


if __name__ == "__main__":
    stage_cli("music", run, description="Generate and place the four music cues")
