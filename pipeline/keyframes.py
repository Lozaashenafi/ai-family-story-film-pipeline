"""Stage 3 - keyframes: one still per shot, painted from the contract.

This is the stage where a real person enters the film, so it is the stage that
enforces the consent gate from ETHICS.md. If `meta.consent.status` is `pending`
nothing is generated at all.

Likeness rules:
  - a character's `source_photo` is sent as an image-to-image *reference*, never
    composited, never copied into outputs/
  - a missing photo is a warning, not a failure: the shot falls back to the
    written description and the fallback is recorded in runs.jsonl
  - the style block always applies, so the result is a painting, not a
    photograph of her

Run:  python -m pipeline.keyframes [--only A1,B1 | refsheet:girl] [--force]
Writes: outputs/keyframes/<shot>.png, outputs/refs/<character>_sheet.png

`--only` with shot ids paints only those shots. Reference sheets are then left
alone, because they are the most expensive thing to get wrong and the most
expensive to redo: ask for one by name with `--only refsheet:girl`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import common, providers
from .common import ROOT, out_path, rel, stage_cli
from .script import build_prompt

# The vertical frame is generated directly; horizontal is derived at assembly
# time from the same master. See DESIGN.md, "One master, two exports".
FRAME = (1080, 1920)


def reference_for(storyboard: dict, character_id: str, *, shot_id: str,
                  for_sheet: bool = False) -> Path | None:
    """The image a shot inherits its face from.

    Priority is the approved character sheet and only then the source photo.
    The order is the point: the sheet is already painted in the film's style, so
    an edit of it comes back painted. Editing the photograph instead produces a
    semi-realistic frame beside watercolour ones, which is exactly the drift
    User test 2 reported. The photograph is therefore consulted once, when the
    sheet is made, and never again per shot.

    `for_sheet` stops the sheet being handed to itself.
    """
    character = next(c for c in storyboard["characters"] if c["id"] == character_id)
    sheet = character.get("reference_sheet")
    if not for_sheet and sheet and (ROOT / sheet).exists():
        return ROOT / sheet
    declared = character.get("source_photo")
    if not declared:
        if sheet and not for_sheet:
            print(f"    ! {character_id}: no {sheet} yet, generating from text only")
        return None
    path = ROOT / declared
    if not path.exists():
        common.log_run(stage="keyframes", operation="reference", provider="local",
                       model="none", status="missing", shot_id=shot_id, character=character_id,
                       note=f"{declared} not found; generated from text only")
        print(f"    ! {character_id}: {declared} is missing, generating from text only")
        print(f"      (see {declared.rsplit('/', 1)[0]}/README.md for how to add it)")
        return None
    return path


def mock_frame(storyboard: dict, shot: dict, target: Path) -> None:
    common.mock_image(
        target, shot_id=shot["id"], scene=shot["scene"],
        label=shot["keyframe"]["prompt"].split(",")[0],
        width=FRAME[0], height=FRAME[1], seed=shot["keyframe"].get("seed", 1),
    )


def run(storyboard: dict, args, only) -> None:
    mode = common.provider_mode()
    sheets_wanted = {item.split(":", 1)[1] for item in (only or ()) if item.startswith("refsheet:")}
    # None means "every shot"; an empty set means "no shots", which is what
    # `--only refsheet:girl` has to mean. Keeping those two apart is why this is
    # not `or None`.
    shots_requested = {item for item in (only or ()) if not item.startswith("refsheet:")}
    shot_only = shots_requested if only is not None else None
    palette_ok = bool(storyboard["style"].get("palette"))
    if not palette_ok:
        print("  ! no palette in the storyboard; keyframes will be less consistent")

    # Reference sheets: the golden look, generated once, then reused by shots.py
    # when it needs to animate a character. They are also the artifact a human
    # reviewer checks before spending money on video.
    for character in storyboard["characters"]:
        if only is not None and character["id"] not in sheets_wanted:
            continue
        sheet = ROOT / (character.get("reference_sheet") or f"outputs/refs/{character['id']}_sheet.png")
        if not character.get("reference_sheet"):
            continue
        key = common.artifact_key("refsheet", character["id"], character["description"],
                                  character.get("sheet_prompt"), character.get("sheet_crop"),
                                  storyboard["style"]["block"], character.get("source_photo"), mode)
        if common.is_fresh(sheet, key) and not args.force:
            print(f"  refsheet {character['id']}: cached")
            continue
        if args.dry_run:
            print(f"  refsheet {character['id']}: would generate")
            continue
        sheet.parent.mkdir(parents=True, exist_ok=True)
        # The sheet is the face every later shot inherits, so its pose is part of
        # the contract rather than hardcoded here. The style block is appended
        # for the same reason it is on a shot: the reference must already be a
        # painting, or the image-edit shots copy photographic detail from it.
        # No "character reference sheet" here on purpose. A sheet is conventionally
        # a full-length turnaround, and the edit model then reproduces that whole
        # standing figure inside every scene, overriding the framing the shot asks
        # for. A cropped face gives the later shots identity without dictating
        # composition.
        pose = character.get("sheet_prompt", "head and shoulders portrait, plain background")
        prompt = (f"{pose}, {character['description']}. {storyboard['style']['block']}")
        reference = reference_for(storyboard, character["id"], shot_id="refsheet", for_sheet=True)
        generate(storyboard, prompt=prompt, target=sheet, seed=(character.get("seed") or 7),
                 reference=reference, shot_id="refsheet", stage="keyframes", mode=mode)
        # A sheet is asked for as a face, and the model keeps painting a full
        # standing figure anyway (it reads "reference" as a turnaround). Cropping
        # here rather than fighting the prompt means every later shot inherits a
        # face-shaped reference, so it cannot reproduce the whole silhouette
        # inside a frame that wanted feet or a shadow.
        crop = character.get("sheet_crop")
        if crop:
            temp = sheet.with_name(sheet.name + ".crop.png")
            common.ff("-i", sheet, "-vf", f"crop={crop},scale=1080:-2", "-frames:v", "1", temp)
            temp.replace(sheet)
        common.mark_fresh(sheet, key)

    for shot in storyboard["shots"]:
        if shot_only is not None and shot["id"] not in shot_only:
            continue
        target = out_path("keyframes", f"{shot['id']}.png")
        prompt = build_prompt(storyboard, shot)
        reference = None
        if shot["keyframe"].get("use_reference", True):
            for character_id in shot["keyframe"].get("characters", []):
                reference = reference_for(storyboard, character_id, shot_id=shot["id"])
                if reference:
                    break
        # A shot may add its own negative for a defect that only appears in that
        # frame (a watch, six toes, a paper border). It is appended to the style
        # negative rather than replacing it, and it is in the cache key so fixing
        # one shot never invalidates the other eleven.
        negative = shot["keyframe"].get("negative")
        full_negative = storyboard["style"]["negative"] + (", " + negative if negative else "")
        key = common.artifact_key(
            "keyframe", shot["id"], prompt, full_negative, shot["keyframe"].get("seed"),
            str(reference) if reference else None,
            common.sha256_file(reference) if reference else None, mode,
        )
        if common.is_fresh(target, key) and not args.force:
            print(f"  {shot['id']}: cached")
            common.log_run(stage="keyframes", operation="image", provider=mode, model="cache",
                           status="ok", cached=True, shot_id=shot["id"])
            continue
        if args.dry_run:
            print(f"  {shot['id']}: would generate ({'with' if reference else 'without'} reference)")
            continue
        print(f"  {shot['id']}: painting{' from ' + rel(reference) if reference else ''} ...")
        generate(storyboard, prompt=prompt, target=target, seed=shot["keyframe"].get("seed", 1),
                 reference=reference, shot_id=shot["id"], stage="keyframes", mode=mode,
                 scene=shot["scene"], negative=negative)
        common.mark_fresh(target, key)


def generate(storyboard: dict, *, prompt: str, target: Path, seed: int, reference: Path | None,
             shot_id: str, stage: str, mode: str, scene: str = "A",
             negative: str | None = None) -> None:
    """Generate one image, choosing the provider by what the request needs.

    FLUX.2 on Cloudflare handles both cases and is the default: it accepts
    width, height, seed and up to four reference images, and it is the only one
    of the two available on a free tier. Gemini's image model is the fallback
    for a key that has no Cloudflare account, even though its free quota is 0.
    """
    negative = storyboard["style"]["negative"] + (", " + negative if negative else "")
    if mode == "mock":
        common.mock_image(target, shot_id=shot_id, scene=scene, label=prompt.split(",")[0],
                          width=FRAME[0], height=FRAME[1], seed=seed)
        common.log_run(stage=stage, operation="image", provider="mock", model="mock",
                       status="ok", shot_id=shot_id, bytes=target.stat().st_size)
        return

    # FLUX.2 on Cloudflare does both jobs: plain text-to-image, and an edit when
    # a reference photo is supplied. It is the default because Gemini's image
    # model is paid-only (free-tier quota is zero), so a key alone cannot paint
    # a frame. Gemini remains the fallback when there is no Cloudflare token.
    common.load_env()
    use_gemini = not common.secrets_present()["CLOUDFLARE_API_TOKEN"]
    if use_gemini:
        raw, cost = providers.gemini_image(
            prompt=prompt, negative=negative, aspect_ratio="9:16", reference=reference,
        )
        model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
        provider_name = "gemini"
    else:
        raw, cost = providers.cloudflare_image(
            prompt=prompt, negative=negative, width=FRAME[0], height=FRAME[1],
            seed=seed, reference=reference,
        )
        model = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
        provider_name = "cloudflare"

    suffix = ".jpg" if raw[:3] == b"\xff\xd8\xff" else ".png"
    staged = target.with_suffix(suffix)
    staged.write_bytes(raw)
    common.ff("-i", staged, "-vf", f"scale={FRAME[0]}:{FRAME[1]}:force_original_aspect_ratio=increase,"
                                   f"crop={FRAME[0]}:{FRAME[1]}", "-frames:v", "1", target)
    if staged != target:
        staged.unlink(missing_ok=True)
    common.log_run(stage=stage, operation="image", provider=provider_name,
                   model=model, status="ok", shot_id=shot_id, seed=seed,
                   reference=rel(reference) if reference else None,
                   cost_usd_estimate=round(cost, 4), bytes=target.stat().st_size)


if __name__ == "__main__":
    stage_cli("keyframes", run, description="Generate one painted keyframe per shot")
