# Her one step

A 90-second heritage short about my grandmother, and the pipeline that makes it
reproducible. Everything the film is - every duration, prompt, line and cue -
lives in one file, [`storyboard.json`](storyboard.json), which is validated
against [`schema/storyboard.schema.json`](schema/storyboard.schema.json) before
any stage runs.

Amharic narration. English subtitles. 9:16 master, 16:9 derivative. Painted
images, generated score, generated voice, and an end card that says so.

## The one command

```bash
make setup   # once: .venv with jsonschema, requests, imageio-ffmpeg
make film    # script -> narration -> keyframes -> shots -> music -> assemble
```

`make film` writes `outputs/vertical.mp4` (1080x1920) and
`outputs/horizontal.mp4` (1920x1080). It is resumable: every artifact is cached
against a hash of its inputs, so re-running only redoes what changed.

No keys? It still builds:

```bash
make mock    # PROVIDER_MODE=mock: no network, deterministic placeholders
```

## Toolchain

- Python 3.12
- FFmpeg, resolved in this order: `$FFMPEG`, the build shipped by
  `imageio-ffmpeg`, `.tools/ffmpeg-*/ffmpeg`, `PATH`. The build must have
  `freetype` (drawtext) and `libass` (burned subtitles) - the stage scripts
  check and use fallbacks rather than failing silently.
- Fonts: `Noto Sans` and `Noto Sans Ethiopic`. The Amharic end card is rendered
  through libass, which shapes Ge'ez correctly; a Latin-only font would turn it
  into boxes.

Tested with imageio-ffmpeg's 9.0.2 build on Ubuntu 24.04.

## Configuration

Copy `.env.example` to `.env` (git-ignored) and fill in what you have:

| variable | used by | needed for |
|---|---|---|
| `GEMINI_API_KEY` | narration, keyframes | real Amharic TTS; keyframes only if there is no Cloudflare token |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | keyframes | FLUX.2 keyframes, text-only or photo-referenced |
| `CF_IMAGE_MODEL` | keyframes | which FLUX.2 size to paint with (default `flux-2-klein-4b`) |
| `CF_VIDEO_MODEL` or `WAN_ENDPOINT` | shots | real image-to-video (optional) |
| `MUSIC_ENDPOINT` | music | real score generation (optional) |
| `PROVIDER_MODE` | all | `real` / `mock`; empty = real if a key is present |

Every optional capability degrades: no video endpoint means the local moving-still
treatment in `shots.py` (eased move, handheld drift, flicker, grain), no
music endpoint means a synthesised bed, no image reference means text-only
keyframes. Each fallback is one line in `runs.jsonl`.

Two free-tier facts shape the defaults, both measured on this build (see
[`EXPERIMENTS.md`](EXPERIMENTS.md)):

- Gemini's image model reports `limit: 0` on the free tier, so a Gemini key
alone cannot paint a frame; Cloudflare's FLUX.2 does both text and photo
references, so it is the default keyframe provider.
- Gemini's TTS allows ten requests per day per model, and the film needs eleven
lines. A build therefore resumes from cache across days instead of failing.

## What the stages do

| stage | reads | writes | can it call a model |
|---|---|---|---|
| `pipeline/script.py` | storyboard | `outputs/plan.json`, `outputs/script.md` | no |
| `pipeline/narration.py` | storyboard | voice WAVs, re-timed WAVs, `radio_cut.wav`, `timing.json` | Gemini TTS |
| `pipeline/keyframes.py` | storyboard, photo | 12 keyframes, 2 character sheets | FLUX.2 / Gemini image |
| `pipeline/shots.py` | keyframes, timing | 12 clips | Wan-class i2v (optional) |
| `pipeline/music.py` | storyboard, timing | 12 candidates, `score.wav` | ACE-Step (optional) |
| `pipeline/assemble.py` | clips, cards, audio | two MP4s, subtitles | no |

Narration runs before images on purpose: the measured length of each Amharic
line decides how long its shot is, inside the 90-second ceiling. See
[`ARCHITECTURE.md`](ARCHITECTURE.md).

The performance is cached at natural pace in `outputs/audio/tts/` and re-timed
afterwards, so `voices.narrator.speed` changes the pace without another TTS call.
Two other fields exist for revisions that should not cost a full rebuild:
`style.grades` (an eq correction per scene, applied to every clip in it) and a
per-shot `keyframe.negative` (fixes one frame's defect without invalidating the
other eleven).

## Where things land

```
outputs/
  vertical.mp4    the film, 1080x1920
  horizontal.mp4  the same film, derived widescreen
  subs/           burned-in ASS + film.en.srt sidecar
  plan.json       every prompt, seed and wrapped subtitle line
  audio/          tts/ (natural pace), narration/ (re-timed), radio cut, score, mix
  keyframes/      one still per shot
  clips/          one clip per shot
runs.jsonl        one line per model call: stage, provider, model, seconds, cost
```

Media is git-ignored: it is rebuildable, and 67 MB of mock footage does not
belong in git. `runs.jsonl` is committed, because the log is evidence.

## The rules this film follows

A real person is depicted, in paint, and voiced. Her children consented, in
writing, before anything was generated; the record and the limits of that
consent are in [`ETHICS.md`](ETHICS.md). Her photograph is a likeness reference
only - it never appears on screen, is never published, and is not committed.
The pipeline refuses to run while `meta.consent.status` is `pending`.

## Reading order

- [`DESIGN.md`](DESIGN.md) - why the film looks and sounds the way it does
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - how the pipeline is put together
- [`EXPERIMENTS.md`](EXPERIMENTS.md) - the eighteen decisions that were tested
- [`FAILURES.md`](FAILURES.md) - what broke, and what I changed because of it
- [`COSTS.md`](COSTS.md) - measured and projected spend
- [`ETHICS.md`](ETHICS.md) - consent, likeness, disclosure, withdrawal
