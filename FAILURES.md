# Failures

What broke while building this, why, and what changed because of it. Kept
because the fixes are the interesting part, and because a pipeline that claims
to have had no failures is a pipeline nobody ran.

## 1. FFmpeg without `drawtext`

**Symptom:** `make mock` died in `keyframes` with exit 234 and
`Error opening output file .../girl_sheet.png`.

**Cause:** the static FFmpeg 7.0.2 in `.tools/` is built without freetype, so
the `drawtext` filter does not exist. `common._find` preferred `.tools/` over the
imageio-ffmpeg binary, which does have freetype.

**Fix:** the resolver now prefers a build with text and libass (`$FFMPEG`, then
imageio-ffmpeg, then `.tools`, then `PATH`), and `mock_image` checks
`has_filter("drawtext")` before using it. Text on screen moved to libass/ASS
entirely, which is better for Amharic shaping anyway.

## 2. A lavfi source used as a filter

**Symptom:** the same run failed with `Simple filtergraph was expected to have
exactly 1 input and 1 output. However, it had 0 input(s)`.

**Cause:** `gradients` is a filter *source*. It was written into `-vf` while a
dummy `color=` input was supplied, so the graph had an input nothing consumed.

**Fix:** `gradients` is now the `-i` source and the rest of the chain is `-vf`.
Obvious in hindsight; two minutes of reading the filter list would have avoided
it, and now `has_filter` is a first-class helper.

## 3. The first assembly was 90.5 seconds

**Symptom:** `! the film is 90.5s, over the 90s ceiling` on the first full run.

**Cause:** narration padding (0.6 s lead + 0.9 s tail) was added to every
narrated shot and never reconciled with the brief.

**Fix:** pads trimmed to 0.5 / 0.8, and `narration.py` now trims slack from shots
that have it - last shot first, never below `speech + pads` - until the film fits.
The build reports each trim. If it still cannot fit, it says so and ships a
warning instead of silently exceeding the ceiling.

## 4. Every mock frame looked like scene A

**Symptom:** B4, a cold slate-blue valley, rendered warm orange.

**Cause:** `generate()` in `keyframes.py` called `mock_image(..., scene="A")`
while the shot's scene was available but not passed through.

**Fix:** `scene` is a parameter threaded from the shot. Found by extracting a
frame and looking at it, which is the argument for looking at output rather than
trusting a green log.

## 5. No Wan model on Workers AI

**Symptom:** the plan assumed Wan 2.2 i2v was available with the Cloudflare
token that generates images. It is not: Workers AI hosts FLUX for images, while
the Wan models in Cloudflare's catalog are third-party entries with their own
access.

**Fix:** two adapters with one contract - `CF_VIDEO_MODEL` (any catalog video
model id) or a self-hosted `WAN_ENDPOINT` (Wan 2.2 i2v on Kaggle or a rented
GPU). Without either, `shots.py` animates the keyframes with Ken Burns and logs
`status: "fallback"` for the four `wan` shots.

**Still open:** the real video path has not been executed end to end, because
there is no endpoint in this environment. It is the one part of the pipeline I
would not claim works until it runs. The mock and fallback paths are verified.

## 6. ACE-Step has no hosted API

**Symptom:** the plan said "ACE-Step, 3 candidates per cue", and there is nothing
to POST to.

**Fix:** same pattern as video: `MUSIC_ENDPOINT` points at an ACE-Step inference
server, contract documented in `ARCHITECTURE.md`. Without it, `music.py` writes a
deterministic synthesised bed from each cue's key, tempo and gain - correct shape,
correct lengths, honest placeholder - and logs the fallback.

## 7. Ambience is written but not generated

**Symptom:** every shot has an `ambience` string (`wind in grass`, `a horn`, `room
tone`), and nothing consumes it.

**Cause:** scope. A fourth generative capability (sound effects) would have added
an endpoint, a provider, a cache key and a mix layer in a three-day build, for
texture the score already covers.

**Decision:** the strings stay in the contract as notes for the next take, and
the gap is stated in `ARCHITECTURE.md` rather than dressed up. The mix is score
plus voice, and that is what the loudness numbers describe.

## 8. Disk

**Symptom:** 4.3 GB free on the build machine, 99% full, with real video about to
be generated.

**Fix:** nothing heavy runs locally. Wan output is conformed and the raw file is
deleted immediately (`clips/<shot>.raw.mp4`); the mock render is the largest
local artifact at 303 MB for the whole `outputs/`. Real video generation belongs
on Kaggle where the GPU and the disk are.

## 9. A speech-rate guess stood in for a measurement

**Symptom:** `script.py` projected narration length at 2.2 words per second, and
the mock tone's length came from that same guess, so every timing in the first
build was circular.

**Cause:** the key arrived late, so no real Amharic speech had ever been timed.

**Fix:** the real run happened. Eleven lines measured **1.24 words/s**, against
the 2.2 guess - the guess was 44% optimistic, and only the measured audio sets
the edit. D2 needed a second day: the free tier allows ten TTS requests per day
and the film needs eleven, so `make narration` stopped there with `429`. The
stage resumed from cache instead of re-speaking A2-D1, and D2 was spoken from a
key in another Google Cloud project, whose allowance is separate.

The measured speech then overflowed the ceiling: 91.4 s, with every shot already
at `speech + pads`. Shrinking the tail from 0.8 s to 0.6 s recovered the 1.4 s
and the film closed at 90.0 s, which is legal but leaves no margin - the honest
fix for the next revision is fewer words, not less padding.

**Lesson:** budget a provider quota like a dependency. Eleven lines against a
ten-a-day cap is a two-day build, and the stage had to be made resumable *before*
it was discovered, not after.

## 10. The image provider I designed around does not exist on the free tier

**Symptom:** `make keyframes` failed twice: Gemini image returned `429` with
`free_tier_requests, limit: 0`, and the Cloudflare fallback returned `HTTP 400:
Additional or unevaluated properties '/seed, /width, /height' not allowed`.

**Cause:** two separate mistakes. Gemini's image model is paid-only, which the
pricing assumption in `COSTS.md` did not catch. flux-1-schnell's Workers AI
schema accepts only `prompt` and `steps`, and returns a 1024x1024 square, so a
9:16 master could only be cropped out of it.

**Fix:** switched to FLUX.2 klein 4B, which takes multipart form data with
`width`, `height`, `seed` and up to four `input_image_N` references - so a frame
is composed for 9:16 and the photograph can still guide the painting. The 4B
model keeps 14 frames inside the daily free neuron allowance that the 9B model
would have blown in six.

**Lesson:** capabilities are not interchangeable, and a fallback is only a
fallback if it has been called once. Both endpoints were exercised for real
before the stage was considered working.

## 11. Bursts look like content failures

**Symptom:** TTS refused B2 with `finishReason: OTHER` and no audio; the same
line succeeded untouched a minute later. Later the same day the endpoint
returned an explicit `429` with a ten-per-day limit.

**Cause:** one quota, two error shapes. `OTHER` arrives with HTTP 200, so the
first version retried after 2 s and 4 s - too soon to clear anything - and the
stage aborted on a line that was fine. The 3.0 s per-call burst also spent the
daily allowance faster than it needed to.

**Fix:** TTS retries now back off 15/30/60 s, and requests are spaced 6 s apart.
Neither makes a real quota problem disappear, but both turn a false content
failure into a wait, and the cache means a resumed run costs nothing.

**Lesson:** an HTTP 200 can still describe a quota error. The log line, not the
status code, is what tells you which failure you have.

## 12. Three hands on one girl

**Symptom:** the first A2 keyframe (seed 31002) looked fine as a contact-sheet
thumbnail and wrong at full size: a hennaed hand on each knee, a third hand
folded beneath them, and fused fingers where the hands met.

**Cause:** the prompt asked for "hennaed palms open on her lap", which puts four
separate limb shapes into the brightest part of a 1080x1920 frame. The shot is
also generated with the girl's reference sheet attached, and that sheet is a
standing pose with crossed hands, so the model was composing two poses at once.

**Fix:** re-posed the shot in the contract - "both hennaed hands folded quietly
together on one knee, fingers interlocked, exactly two hands" - and then swept
seeds instead of rewriting the prompt again. Twelve extra frames: ten on
FLUX.2 klein 4B (two through the stage, eight as probes) and two on the 9B
model. Of those, seed 31014 held both the seated corner and a two-hand pose.

**Result:** two hands at output size, and the A2 clip and both exports rebuilt
from the new frame. The probes are in `runs.jsonl` with their seeds, so the
chosen one is reproducible with `make keyframes --force`.

**Lesson:** inspect a still at the size the audience sees it, and treat a
reference sheet as a composition instruction as well as a likeness one. It
cost about $0.07 to learn that, roughly 2% of the project's image spend.
