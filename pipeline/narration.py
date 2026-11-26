"""Stage 2 - narration, and the timings the rest of the film hangs on.

Voice: one Amharic narrator (storyboard.voices.narrator). Subtitles: English,
from the contract.

The narration is generated first, before any image, because the measured speech
decides how long each shot has to be. A shot's final duration is the larger of
the storyboard's intent and what the line actually needs, plus breathing room.

Tempo is a separate, cached pass: the model's voice is kept in audio/tts/ and
`voices.<name>.speed` re-times it with atempo. Changing the pace therefore costs
no TTS calls and cannot change the performance, only how fast it plays.

Run:  python -m pipeline.narration
Writes: outputs/audio/tts/<shot>.wav (natural pace),
        outputs/audio/narration/<shot>.wav (after speed),
        outputs/audio/radio_cut.wav, outputs/audio/timing.json
"""

from __future__ import annotations

import json
import time
import wave

from . import common, providers
from .common import out_path, rel, stage_cli, wav_duration

SAMPLE_RATE = 24000
LEAD_IN = 0.5   # silence before the first word of a line
# Kore speaks Amharic at 1.23 words/s, not the 2.2 the storyboard was timed for,
# so 83 words needed 67 s of an 82 s picture budget. The first cut paid for that
# by trimming shots; testers heard the result as slow speech, so the voice is
# now re-timed by `speed` (1.10 in this cut) and the shots keep their lengths.
TAIL = 0.6
CEILING = 90.0  # seconds; the brief's hard limit
PACE_S = 6.0    # seconds between real TTS requests; the preview model throttles bursts


def post_process(src, dst, speed: float) -> None:
    """Set the film's pace without a second TTS call.

    Two changes, in this order, because testers described the first cut as slow
    and the measurement agrees: the model sometimes leaves 1-2 s of dead air
    inside a line and up to 5 s at the end. silenceremove cuts any pause longer
    than 0.55 s back to a 0.30 s beat, so the words keep their shape and the
    gaps stop dragging. atempo then trims the remaining 10%: duration changes,
    pitch and timbre do not, so it is still the same narrator.

    This is a post pass on purpose - the performance is paid for once, pace is a
    number in the contract, and re-timing costs one FFmpeg call.
    """
    common.ff(
        "-i", src,
        "-af", "silenceremove=stop_periods=-1:stop_duration=0.55:stop_threshold=-38dB:stop_silence=0.30,"
               f"atempo={speed:.3f}",
        "-ac", "1", "-ar", SAMPLE_RATE, "-c:a", "pcm_s16le", dst,
    )


def normalise(src, dst) -> None:
    """One canonical audio format for the whole film: 24 kHz mono PCM."""
    common.ff(
        "-i", src,
        "-af", "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,"
               "areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.12,areverse,"
               "loudnorm=I=-18:TP=-2:LRA=9",
        "-ac", "1", "-ar", SAMPLE_RATE, "-c:a", "pcm_s16le", dst,
    )


def mock_length(text: str) -> float:
    """Mock speech is paced like real speech so the timings stay honest."""
    return max(1.6, len(text.split()) / 2.2 + 0.4)


def run(storyboard: dict, args, only) -> None:
    voice_name = "narrator"
    voice = storyboard["voices"][voice_name]
    model = voice.get("model") or "gemini-2.5-flash-preview-tts"
    speed = float(voice.get("speed", 1.0))
    mode = common.provider_mode()

    tts_dir = out_path("audio", "tts", ".keep").parent
    narration_dir = out_path("audio", "narration", ".keep").parent
    # Measure the lines that already exist before speaking anything. `--only`
    # re-records one line, but the film's layout still has to account for the
    # other eight, or the timing file is rewritten as if they were silent and
    # every shot snaps back to its storyboard length.
    timings = {shot["id"]: wav_duration(narration_dir / f"{shot['id']}.wav")
               for shot in storyboard["shots"]
               if shot.get("narration") and (narration_dir / f"{shot['id']}.wav").exists()}
    pieces = []
    last_call = 0.0

    for shot in storyboard["shots"]:
        script = shot.get("narration")
        if not script:
            continue
        if only and shot["id"] not in only:
            continue
        tts_target = tts_dir / f"{shot['id']}.wav"
        target = narration_dir / f"{shot['id']}.wav"
        # `tts_text` is what the voice is asked to say; `text` is what the film
        # means, and `subtitle` is what the audience reads. They differ only when
        # a word needs help being pronounced: an extra comma buys a beat, and a
        # respelling can be tried without touching the subtitle or the meaning.
        spoken = script.get("tts_text") or script["text"]
        key = common.artifact_key("narration", shot["id"], spoken, voice["voice_id"],
                                  voice["instruction"], model, mode)

        if common.is_fresh(tts_target, key) and not args.force:
            cached = True
        elif args.dry_run:
            print(f"  {shot['id']}: would speak {len(spoken.split())} words as {voice['voice_id']}"
                  f", then play at {speed:g}x")
            continue
        else:
            cached = False
            print(f"  {shot['id']}: speaking as {voice['voice_id']} ...")
            if mode == "mock":
                seconds = mock_length(spoken)
                common.mock_tone(tts_target, seconds=seconds, freq=196.0, gain_db=-30)
                cost = 0.0
            else:
                # The free tier caps TTS at ten requests a day per model, and
                # overloads show up as finishReason OTHER. Pace the requests so a
                # partial build resumes where it stopped instead of burning quota.
                wait = PACE_S - (time.monotonic() - last_call)
                if wait > 0:
                    time.sleep(wait)
                last_call = time.monotonic()
                raw, cost = providers.gemini_speech(
                    text=spoken, voice_id=voice["voice_id"],
                    instruction=voice["instruction"], model=model,
                )
                raw_path = tts_dir / f"{shot['id']}.raw"
                raw_path.write_bytes(raw)
                try:
                    normalise(raw_path, tts_target)
                finally:
                    raw_path.unlink(missing_ok=True)
            common.mark_fresh(tts_target, key)

        if args.dry_run:
            print(f"  {shot['id']}: voice cached, would play at {speed:g}x")
            continue

        # Tempo is keyed on the voice file, not on the text: changing `speed`
        # re-times cached audio in a second and leaves the TTS cache untouched.
        post_key = common.artifact_key("narration-post", shot["id"],
                                       common.sha256_file(tts_target), speed, mode)
        if not (common.is_fresh(target, post_key) and not args.force):
            post_process(tts_target, target, speed)
            common.mark_fresh(target, post_key)

        duration = wav_duration(target)
        common.log_run(stage="narration", operation="tts", provider=mode, model=model,
                       status="ok", cached=cached, shot_id=shot["id"], seconds=duration,
                       voice=voice["voice_id"], speed=speed,
                       cost_usd_estimate=round(cost, 4) if not cached else None)
        print(f"  {shot['id']}: {'cached' if cached else 'new'}, {duration:.1f}s at {speed:g}x")

        if not args.dry_run:
            timings[shot["id"]] = duration

    if args.dry_run:
        return

    # Lay out the film: every shot keeps its storyboard length unless its line
    # needs more room. If that pushes the film past the brief, trim the shots
    # that have slack rather than the lines that carry the story.
    order, cursor = [], 0.0
    for shot in storyboard["shots"]:
        need = timings.get(shot["id"], 0.0)
        duration = shot["duration_s"]
        if need:
            duration = max(duration, round(need + LEAD_IN + TAIL, 2))
        order.append({"id": shot["id"], "start_s": 0.0, "duration_s": round(duration, 2),
                      "narration_s": round(need, 2) if need else 0.0, "narration_start_s": None})
        cursor += duration

    cards_duration = sum(card["duration_s"] for card in storyboard["end_cards"])
    trimmable = CEILING - cards_duration  # what the shots may occupy
    overflow = round(cursor - trimmable, 2)
    if overflow > 0:
        for entry in reversed(order):
            floor = max(entry["narration_s"] + LEAD_IN + TAIL, 2.0)
            slack = round(entry["duration_s"] - floor, 2)
            if slack <= 0 or overflow <= 0:
                continue
            cut = min(slack, overflow)
            entry["duration_s"] = round(entry["duration_s"] - cut, 2)
            entry["trimmed_s"] = round(cut, 2)
            overflow = round(overflow - cut, 2)
            print(f"  {entry['id']}: trimmed {cut:.1f}s of slack to stay under {CEILING:.0f}s")

    cursor = 0.0
    for entry in order:
        entry["start_s"] = round(cursor, 2)
        if entry["narration_s"]:
            entry["narration_start_s"] = round(cursor + LEAD_IN, 2)
        cursor += entry["duration_s"]

    cards = []
    for card in storyboard["end_cards"]:
        cards.append({"id": card["id"], "start_s": round(cursor, 2), "duration_s": card["duration_s"]})
        cursor += card["duration_s"]

    total = round(cursor, 2)
    if total > 90:
        print(f"  ! the film is {total:.1f}s, over the 90s ceiling. Shorten a line or a shot.")
    elif total < 60:
        print(f"  ! the film is {total:.1f}s, under the 60s floor.")

    timing = {"fps": storyboard["meta"]["fps"], "sample_rate": SAMPLE_RATE,
              "shots": order, "cards": cards, "total_s": total,
              "narration_lead_in_s": LEAD_IN, "narration_tail_s": TAIL}
    (out_path("audio", "timing.json")).write_text(json.dumps(timing, ensure_ascii=False, indent=2) + "\n")

    for entry in order:
        if entry["narration_s"]:
            pieces.append((entry["narration_start_s"], narration_dir / f"{entry['id']}.wav"))
    write_radio_cut(pieces, total)
    print(f"  timing: {total:.1f}s total, {sum(e['narration_s'] for e in order):.1f}s of speech")
    print(f"  wrote {rel(out_path('audio', 'timing.json'))} and outputs/audio/radio_cut.wav")


def write_radio_cut(pieces: list[tuple[float, object]], total: float) -> None:
    """Place each line on one continuous track with raw PCM, so the offsets are
    sample-exact and the assembly stage has nothing to line up."""
    frame = 2  # bytes per sample, mono 16-bit
    buffer = bytearray(int(round(total * SAMPLE_RATE)) * frame)
    for start, path in pieces:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
                raise common.ProviderError(f"{path} is not mono 16-bit PCM")
            if handle.getframerate() != SAMPLE_RATE:
                raise common.ProviderError(f"{path} is not {SAMPLE_RATE} Hz")
            pcm = handle.readframes(handle.getnframes())
        offset = int(round(start * SAMPLE_RATE)) * frame
        end = min(len(buffer), offset + len(pcm))
        buffer[offset:end] = pcm[: end - offset]
    target = out_path("audio", "radio_cut.wav")
    with wave.open(str(target), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(bytes(buffer))


if __name__ == "__main__":
    stage_cli("narration", run, description="Generate Amharic narration and measure the film's timing")
