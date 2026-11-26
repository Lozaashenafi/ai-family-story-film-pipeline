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

## 13. A watch, six toes, and a girl who aged backwards

**Symptom:** three testers, three different frames. At 00:28 the girl walking in
fog wore a modern wristwatch and two bracelets; B2's feet had six toes on one
foot; C2 returned a six- or seven-year-old with a white paper border around the
picture, an hour after C1 had painted her at thirteen.

**Cause:** the style negative already said "modern technology" and "extra
fingers", and neither reached these frames. More importantly, the girl's
reference sheet is still the standing, round-faced child the first build used,
so any prompt that asks for a close or young-looking figure snaps back to that
child regardless of the words "thirteen-year-old" in the text. The watch was a
model habit: a bare wrist is not described unless it is described.

**Fix:** per-shot negatives in the contract (`keyframe.negative`), appended to the
style negative and included in the cache key, so one bad frame is repaired
without invalidating the other eleven. B1 was re-painted with "bare wrists with
no watch and no bracelet"; B2 with "five toes on each foot, both hands out of
frame"; C2 with "no paper border" and, after two more seeds, without the
reference sheet at all. C2's seed 31022 is the first take that was both a
thirteen-year-old and borderless.

**Result:** watch and bracelets gone; five toes per foot; C2 is a tall,
long-limbed girl with no frame around her. A3's hand could not be re-painted:
the Cloudflare account hit its 10,000-neuron daily allowance on the last attempt
(`HTTP 429`, code 4006), so the shot was re-framed instead - the Ken Burns now
starts at 1.24x and drifts up, which turns the extra fingers into a sliver at the
corner. B2's final take still has her hands and a knitted red wrap at the top
edge. Both are recorded in `DESIGN.md` as known defects, not as fixed.

**Lesson:** at this model size the reference sheet beats the prompt for age and
pose, so the sheet is the thing to redo; and a daily free allowance can end a
repair mid-sweep, which is why the fixes that needed no model call (crop,
grade, re-time) are worth planning for.

## 14. The opening second was silent

**Symptom:** a tester thought his phone's audio had broken before the first line.
Measured, he was nearly right: the score's first second averaged -47.7 dB.

**Cause:** two small decisions compounding. `synth_cue` mixed three sines at
`gain_db: -6` and then `afade=t=in:d=1.2`, and the bed was never normalised
before the mix, so the score sat roughly 25 dB under the narration and its first
1.2 s were a ramp from nothing. The ducking then held it down further.

**Fix:** the assembled bed is normalised as a whole to -27 LUFS after the cues
are placed (two-pass `loudnorm`, linear), the first cue fades in over 0.15 s
instead of 1.2 s, and the first cue's gain rose from -6 to -3 dB. Normalising the
bed rather than each cue keeps the intended arc - cold, urgent, warm, thinning.

**Result:** the opening second measures -26.7 dB mean instead of -47.7, and the
ducked master still lands at -13.75 LUFS / -1.00 dBTP.

**Lesson:** "there is music" is a measurable claim. Check the level where the
audience starts listening, not the level of the project as a whole.

## 15. Slow narration was mostly dead air

**Symptom:** two testers independently said the narration was slow. It measured
1.24 words per second, but the words themselves were not the problem.

**Cause:** `silencedetect` on the new A4 take found a 1.75 s pause inside the
line and 4.7 s of near-silence after it. The existing `normalise()` trimmed only
silence below -42 dB, and the model's room tone sits above that, so most of the
tail survived. The first cut paid for this with picture: A1 was trimmed from 6 s
to 2.8 s and C1 from 8 s to 4.7 s to stay under 90 s.

**Fix:** a tempo pass after the TTS cache - any pause longer than 0.55 s is cut
back to 0.30 s, then `atempo=1.10`. Pitch and timbre are untouched, the paid
performance is kept, and `voices.narrator.speed` re-times it without a new call.
Speech fell from 67.1 s to 59.7 s, and the shots got their designed lengths back.

**Result:** the film is still exactly 90.0 s, but A1 now holds 6.0 s instead of
2.8 s, and the slowest shot in the film is A4 at 7.8 s rather than an artefact of
a 4.7 s tail.

**Lesson:** when speech feels slow, measure the gaps before changing the rate.
Half of this fix cost nothing and the other half cost one number.

## 16. A one-line grade edit broke the whole stage

**Symptom:** `make shots` died on A1 with
`Unable to choose an output format for 'noise=...'` - FFmpeg was treating the
tail of the filter chain as an output filename.

**Cause:** the filter chain was written as adjacent string literals so Python
would concatenate them into one `-vf` argument. Inserting
`f"{grade}," if grade else ""` as a new element of the call split the chain into
two positional arguments, so `-vf` received only the first half.

**Fix:** the chain is built as one variable, appending the grade and then the
grain, and passed as a single argument. The stage now names the variable `chain`
so the next edit has somewhere obvious to go.

**Result:** all twelve clips re-rendered in 121 s with the scene grades applied.

**Lesson:** `-vf` takes exactly one argument. Adjacent literals are a trap the
moment a conditional enters the list - and `assemble` will happily build from
stale clips if the durations are not checked, which is how the broken run still
produced a 90 s file before the fix.

## 17. The reference was never used, and then it ate the film

**Symptom:** two written reviews of the same cut named opposite faults. One said
the style swings between watercolour and semi-real, and that the girl's hair, age
and skin tone change shot to shot. The other said every shot had become a
standing, full-body, front-facing portrait.

**Cause:** two bugs in a row.

1. `reference_for()` only consulted `characters[].source_photo`. The girl has no
   photograph, so `outputs/refs/girl_sheet.png` was generated, cached, paid for -
   and then never handed to a single shot. Twelve prompts each described her
   independently, which is precisely the drift reviewer 2 catalogued. The
   grandmother was consistent because her shots *did* have a photo to edit.
2. Fixing that exposed the second problem: FLUX.2 in edit mode treats the
   reference as a layout, not as a face. Given a full-length sheet, it returned a
   full-length figure in every scene. A2 lost its crouch, A1 its empty hut, B1
   its walk, B2 its feet, C2 its close-up. Twelve standing portraits in twelve
   costumes, one per beat of the story.

**Fix:** the sheet is now the reference (photo only when no sheet exists), sheets
are cropped to a face by `sheet_crop`, and `use_reference` became a rule -
reference where the face is the subject, text where the frame is.

**Result:** the full batch was run twice, 23 image calls, and rolled back both
times. The frames were recovered from the previous clip renders and re-rendered
under a single finish pass. The corrected rules are in the contract, unrun,
waiting on image quota.

**Lesson:** a generated artifact is not used until something reads it. A sheet
that is never referenced is a cost with no behaviour, and the fix for
inconsistency can be a worse film than the inconsistency - twelve correct frames
that all look the same are not a film.

## 18. `--only` on narration rewrote the whole timing file

**Symptom:** after re-recording two lines with `--only A2,C1`, `timing.json` had
`narration_s: 0.00` for the other nine shots, and every shot had snapped back to
its storyboard length (B2 8.43 s -> 6.00 s).

**Cause:** the layout step builds `timings` from the loop over shots, and the
loop skips everything outside `--only`. The skipped lines were therefore treated
as silent, and the film was re-cut as if eight lines had been deleted.

**Fix:** the stage now measures every processed narration wav that already exists
before it speaks anything, so a partial re-record re-times one line and leaves
the layout of the other eight intact.

**Result:** 90.0 s total, 59.8 s of speech, shot durations identical to the
previous cut.

**Lesson:** `--only` is a cache key, not a scope for the output. Any stage that
derives a whole-film artifact must read the untouched shots from disk, or a
one-line edit silently becomes a different film.

## 19. The haze that looked like a fogged lens

**Symptom:** the first atmosphere pass washed every frame it touched, including
the subject, and read as condensation on the glass rather than mist in the air.

**Cause:** a full-frame blurred copy at 18-28% opacity is a global veiling: it
lifts the blacks of the foreground along with the sky.

**Fix:** strength dropped to 12% and the layer restricted to the three shots
where the scene already contains fog (B1, B3, B4). A1's smoke and C1's dust were
dropped - smoke needs a plume, not a veil.

**Result:** a perceptible drift between frames, no visible flattening.

**Lesson:** an atmosphere effect has to be placed where the air is, not laid over
the whole frame. The first version was invisible at 18% and destructive at 28%,
which means the usable range was narrow and the effect was the wrong one.
