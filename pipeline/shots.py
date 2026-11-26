"""Stage 4 - shots: turn each keyframe into a moving clip.

Two ways a shot moves, and the storyboard decides which:

  wan      image-to-video on a Wan-class model. Used on the four shots that
           carry the film's motion (the smoke, the walk, the valley, the
           coffee steam). Hands are never animated: that is the failure mode
           that ruins generated video, so hand shots are Ken Burns.
  kenburns slow push or pan over the still, rendered in FFmpeg. Deterministic,
           free, and it cannot invent a sixth finger.

If no video endpoint is configured the stage falls back to Ken Burns for every
shot and logs each fallback to runs.jsonl. A clone with no keys still finishes.

Run:  python -m pipeline.shots [--only A1] [--force]
Writes: outputs/clips/<shot>.mp4
"""

from __future__ import annotations

import json
import os

from . import common, providers
from .common import out_path, rel, stage_cli

WIDTH, HEIGHT = 1080, 1920
FPS = 24


def load_timing() -> dict:
    path = out_path("audio", "timing.json")
    if not path.exists():
        common.die("outputs/audio/timing.json is missing. Run `make narration` first: "
                   "the narration is what decides how long each shot lasts.")
    return json.loads(path.read_text())


# Bump when the moving-still treatment changes, so cached clips re-render.
RENDERER = "living-still-v3"


def render_kenburns(source, target, *, duration: float, zoom_from: float, zoom_to: float,
                    pan: str, seed: int = 1, grade: str | None = None,
                    finish: str | None = None, haze: float = 0.0) -> None:
    """Animate a still so it reads as filmed rather than as a photo on a slider.

    Four treatments, all deterministic and all rendered locally:

      eased move   smoothstep instead of a linear ramp, so the camera eases out of
                   the first frame and settles on the last instead of sliding at
                   constant speed on rails.
      handheld     two slow sine drifts on x and y, sampled from the source and
                   therefore sub-pixel after the 2x supersample, which is what
                   stops the frame feeling locked to a tripod.
      flicker      a very small per-frame brightness wobble, the way a kerosene
                   lamp or a practical light actually behaves.
      finish       style.finish: the film-wide painterly pass (median, gentle
                   desaturation, a touch of edge return). It runs on every shot,
                   which is what makes twelve generated frames read as one film
                   even when the generator drew them in slightly different
                   hands. It is applied last so it also hides the softness of
                   frames recovered from an earlier render.
      haze         optional, per shot: a heavily blurred copy of the frame drifts
                   slowly over the sharp one at low opacity, so fog, smoke and
                   dust move inside a still that is otherwise only being pushed.
                   Ken Burns can move the camera but it cannot move the weather,
                   which is what the second test round asked for.
      grain        temporal luma noise with a fixed seed: adds texture and, because
                   the seed is fixed, keeps the stage reproducible.

    The input is scaled up before the move and the crop is taken from that, which
    is what stops zoompan from stepping by whole pixels and juddering.
    """
    frames = max(2, int(round(duration * FPS)))
    last = frames - 1
    z0, z1 = zoom_from, zoom_to
    if pan in {"left", "right", "up", "down"}:
        z0, z1 = max(1.02, z0), max(1.02, z1)
    progress = f"(on/{last})"
    ease = f"({progress}*{progress}*(3-2*{progress}))"
    zoom = f"{z0}+({z1}-{z0})*{ease}"
    centre_x = "(iw/2-(iw/zoom/2))"
    centre_y = "(ih/2-(ih/zoom/2))"
    drift_x = f"+7*sin(2*PI*(on/{FPS})/6.3)+2.5*sin(2*PI*(on/{FPS})/2.9)"
    drift_y = f"+5*sin(2*PI*(on/{FPS})/8.1)+2*sin(2*PI*(on/{FPS})/3.3)"
    offsets = {
        "none": (centre_x, centre_y),
        "in": (centre_x, centre_y),
        "out": (centre_x, centre_y),
        "left": (f"{centre_x}-{ease}*iw*0.04", centre_y),
        "right": (f"{centre_x}+{ease}*iw*0.04", centre_y),
        "up": (centre_x, f"{centre_y}-{ease}*ih*0.04"),
        "down": (centre_x, f"{centre_y}+{ease}*ih*0.04"),
    }
    x_expr, y_expr = offsets.get(pan, offsets["none"])
    flicker = "0.004*sin(2*PI*t/1.9)+0.002*sin(2*PI*t/0.83)"
    # Built as one string: -vf takes exactly one argument, so the chain may not be
    # split across positional arguments.
    chain = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zoom}':x='{x_expr}{drift_x}':y='{y_expr}{drift_y}'"
        f":d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"eq=brightness='{flicker}':eval=frame"
    )
    if grade:
        chain += f",{grade}"
    if finish:
        chain += f",{finish}"
    chain += f",noise=c0s=3:c0f=t+u:c0_seed={seed}"
    if haze > 0:
        # One input, two layers: the sharp frame, and a blurred copy cropped
        # through a slowly orbiting window and scaled back to frame size. Because
        # the window moves, the blur moves with it, and a still starts breathing.
        # The seeded grain goes on the sharp layer so the veil stays smooth.
        chain += (
            f",split[sharp][veil];"
            f"[veil]gblur=sigma=22,"
            f"crop=w=iw*0.80:h=ih*0.80"
            f":x='(iw-ow)/2+sin(t*0.17)*iw*0.07'"
            f":y='(ih-oh)/2+sin(t*0.11)*ih*0.04',"
            f"scale={WIDTH}:{HEIGHT},format=yuva420p,"
            f"colorchannelmixer=aa={haze:.2f}[veil2];"
            f"[sharp][veil2]overlay=shortest=1"
        )
    chain += ",format=yuv420p"
    common.ff(
        "-loop", "1", "-framerate", FPS, "-i", source, "-t", round(duration, 3),
        "-filter_complex", chain,
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", FPS, target,
    )


def conform(source, target, *, duration: float, loop: bool, grade: str | None = None,
            finish: str | None = None) -> None:
    """Force a generated clip onto the film's grid: 1080x1920, 24 fps, exact length.

    A real image-to-video clip goes through the same finish pass as a moving
    still, or the four animated shots would be the only ones not painted.
    """
    args = ["-i", source]
    if loop:
        args = ["-stream_loop", "-1", "-i", source]
    tail = (f"{grade}," if grade else "") + (f"{finish}," if finish else "")
    common.ff(
        *args, "-t", round(duration, 3),
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
               f"crop={WIDTH}:{HEIGHT},fps={FPS}," + tail + "format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", target,
    )


def try_video(storyboard: dict, shot: dict, keyframe, duration: float, seed: int):
    """One attempt at real image-to-video; returns a temp path or None."""
    common.load_env()
    image = keyframe.read_bytes()
    motion = shot.get("motion") or shot["keyframe"]["prompt"]
    temp = out_path("clips", f"{shot['id']}.raw.mp4")
    used = None
    try:
        if common.secrets_present()["CLOUDFLARE_API_TOKEN"] and os.environ.get("CF_VIDEO_MODEL"):
            raw, cost = providers.cloudflare_video(image=image, motion=motion, seconds=duration, seed=seed)
            used = "cloudflare"
        elif os.environ.get("WAN_ENDPOINT"):
            raw, cost = providers.wan_endpoint_video(image=image, motion=motion, seconds=duration, seed=seed)
            used = "wan-endpoint"
        else:
            raise providers.ProviderError("no video endpoint configured")
    except providers.ProviderError as exc:
        print(f"    ! {exc}; using Ken Burns")
        common.log_run(stage="shots", operation="video", provider="none", model="none",
                       status="skipped", shot_id=shot["id"], note=str(exc))
        return None
    temp.write_bytes(raw)
    if temp.stat().st_size < 2048:
        temp.unlink(missing_ok=True)
        common.log_run(stage="shots", operation="video", provider=used, model="video",
                       status="empty-response", shot_id=shot["id"])
        return None
    common.log_run(stage="shots", operation="video", provider=used,
                   model="wan", status="ok", shot_id=shot["id"],
                   seed=seed, cost_usd_estimate=round(cost, 4), bytes=temp.stat().st_size)
    return temp


def run(storyboard: dict, args, only) -> None:
    timing = load_timing()
    durations = {entry["id"]: entry["duration_s"] for entry in timing["shots"]}
    mode = common.provider_mode()
    # Narration trims shots to fit the 90 s ceiling, so a shot shorter than its
    # storyboard intent is normal. Only warn when the cut leaves no room for the
    # line itself, which means the timing file is stale.
    lead = timing.get("narration_lead_in_s", 0.5)
    tail = timing.get("narration_tail_s", 0.6)
    for entry in timing["shots"]:
        if entry["id"] in durations and entry["narration_s"]:
            floor = entry["narration_s"] + lead + tail - 0.05
            if entry["duration_s"] < floor:
                print(f"  ! timing for {entry['id']} is shorter than its line; run `make narration`")

    for shot in storyboard["shots"]:
        if only and shot["id"] not in only:
            continue
        keyframe = out_path("keyframes", f"{shot['id']}.png")
        if not keyframe.exists():
            common.die(f"missing {rel(keyframe)}. Run `make keyframes` first.")
        target = out_path("clips", f"{shot['id']}.mp4")
        duration = durations.get(shot["id"], shot["duration_s"])
        kb = shot.get("kenburns") or {}
        grade = (storyboard.get("style", {}).get("grades") or {}).get(shot["scene"].lower())
        finish = storyboard.get("style", {}).get("finish")
        haze = float(shot.get("haze") or 0.0)
        key = common.artifact_key(
            "clip", shot["id"], common.sha256_file(keyframe), duration, shot["mode"], kb,
            shot.get("motion"), mode, RENDERER, grade, finish, haze,
        )
        if common.is_fresh(target, key) and not args.force:
            print(f"  {shot['id']}: cached")
            continue
        if args.dry_run:
            print(f"  {shot['id']}: would render {duration:.1f}s as {shot['mode']}")
            continue

        print(f"  {shot['id']}: {duration:.1f}s, {shot['mode']}")
        rendered = False
        if shot["mode"] == "wan" and mode == "real":
            temp = try_video(storyboard, shot, keyframe, duration, shot["keyframe"].get("seed", 1))
            if temp:
                conform(temp, target, duration=duration, loop=True, grade=grade, finish=finish)
                temp.unlink(missing_ok=True)
                rendered = True
                common.log_run(stage="shots", operation="render", provider="local", model="ffmpeg",
                               status="ok", shot_id=shot["id"], seconds=duration, mode="wan")
        if not rendered:
            if mode == "mock":
                common.log_run(stage="shots", operation="render", provider="mock", model="ffmpeg",
                               status="ok", shot_id=shot["id"], mode="kenburns-mock")
            render_kenburns(
                keyframe, target, duration=duration,
                zoom_from=kb.get("zoom_from", 1.0), zoom_to=kb.get("zoom_to", 1.08),
                pan=kb.get("pan", "in"), seed=shot["keyframe"].get("seed", 1),
                grade=grade, finish=finish, haze=haze,
            )
            if shot["mode"] == "wan" and mode == "real":
                common.log_run(stage="shots", operation="render", provider="local", model="ffmpeg",
                               status="fallback", shot_id=shot["id"], seconds=duration,
                               mode="kenburns", note="no video endpoint; keyframe animated in FFmpeg")
        common.mark_fresh(target, key)
        print(f"    wrote {rel(target)}")


if __name__ == "__main__":
    stage_cli("shots", run, description="Animate each keyframe into a shot clip")
