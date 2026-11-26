# Experiments

Ten decisions that were tested rather than assumed. Each one lists what was
measured, and what the pipeline does because of it. Commands are the ones that
actually ran; numbers come from this machine (Ubuntu 24.04, Python 3.12, FFmpeg
9.0.2 via imageio-ffmpeg).

## 1. Is a strict schema worth it?

**Hypothesis:** `additionalProperties: false` everywhere plus required fields will
catch the mistakes that actually cost money, before a model call.

**Test:** three mutations of the valid storyboard, validated directly.

```
delete shots[0].reason   -> 1 error: 'reason' is a required property
shots[0].duration_s = 99 -> 1 error: 99 is greater than the maximum of 12
storyboard.extra = 1     -> 1 error: Additional properties are not allowed
```

**Result:** all three caught, exit code 1, before any work. Two more mutations -
an unknown character id and a music cue pointing at a renamed shot - are caught
by semantic checks in `load_storyboard`, which the schema cannot express.

**Decision:** validation runs in `stage_cli`, so no stage can bypass it, including
with `--force`.

## 2. Can a consent rule live in code instead of in a paragraph?

**Hypothesis:** if consent is only written in `ETHICS.md`, a tired 2 a.m. build
will ignore it.

**Test:** set `meta.consent.status = "pending"` and call `require_consent`.

```
error: keyframes: refusing to run. meta.consent.status is 'pending' ...
exit 1
```

**Result:** every stage refuses, including the ones that only read the file.

**Decision:** the gate lives in `stage_cli`, not in one stage, and `ETHICS.md`
describes the same rule in human language.

## 3. Amharic text: drawtext or libass?

**Hypothesis:** Amharic end cards need Ge'ez shaping, which a plain font call
does not guarantee.

**Test:** rendered the AI-disclosure card through libass (`ass=...`) with Noto
Sans Ethiopic, extracted a frame at 86.5 s, and looked at it.

**Result:** `ይህ ፊልም በAI ቴክኖሎጂ የተሰራ ነው።` shaped correctly, with the fidel joined
and the right margin even. The static FFmpeg build in `.tools/` also turned out
to have no `drawtext` at all (no freetype), which settled the argument.

**Decision:** all on-screen text - subtitles, cards - is rendered as ASS through
libass. `mock_image` checks `has_filter("drawtext")` and skips its label rather
than crashing.

## 4. Voice first or picture first?

**Hypothesis:** Amharic line length is unpredictable enough that dubbing to a
locked picture would force either rushed speech or overlong shots.

**Test:** laid out the timeline with `duration = max(contract, speech + 0.5 + 0.8)`
for all 11 narrated shots and summed it.

**Result:** 90.5 s - half a second over the brief's ceiling, from pads alone.

**Decision:** narration runs before images, and `narration.py` trims slack from
shots that have it (last first, never below the speech) until the film fits. The
first full mock build reported 90.0 s with one 0.2 s trim on D2. The speech rate
guess in `script.py` (2.2 words/s) is only used for planning warnings; the edit
uses whatever audio the stage actually produced.

## 5. Ken Burns without judder

**Hypothesis:** `zoompan` on a 1080x1920 still steps by whole pixels and visibly
jitters on a slow push.

**Test:** rendered a pan and a push two ways - directly on the 1080-wide frame,
and from a 2160x3840 upscale with the output crop taken from that.

**Result:** the direct version judders at 1.0 -> 1.08 over seven seconds; the
upscaled version is smooth because the motion is expressed in sub-pixel steps of
the larger frame.

**Decision:** every Ken Burns shot is rendered from a 2x frame. Cost: about 3.5 s
per shot at `veryfast`, 56 s for all twelve clips.

## 6. Does two-pass loudness survive a duck?

**Hypothesis:** one-pass `loudnorm` would pump the music back up in the gaps,
undoing the sidechain.

**Test:** mixed score and voice through `sidechaincompress`, normalised in two
passes (measure, then apply linearly), then measured the result.

```
mix: -14.00 LUFS, true peak -4.84 dBTP
```

**Result:** target hit exactly, peaks well under the -1 dBTP ceiling, and the
ducking curve is intact because the gain is linear, not dynamic.

**Decision:** `assemble.py` always measures before it normalises, and prints the
post-export measurement so the claim is checkable from the log.

## 7. Ducking parameters belong in the contract

**Hypothesis:** mix parameters tuned in code get re-guessed in every session.

**Test:** the contract carries `threshold 0.02, ratio 6, attack 300 ms, release
1500 ms`, and `assemble.py` reads them straight into the filter string.

**Result:** re-tuning means editing JSON and re-running `make assemble` - about
three minutes, no model calls, no code change.

**Decision:** nothing about the mix is hard-coded; same for loudness targets and
for cue gains.

## 8. Is the mock mode actually deterministic?

**Hypothesis:** without byte-identical output, mock mode is useless for diffing
and for CI.

**Test:** generated `outputs/keyframes/A1.png`, re-ran with `--force`, compared
hashes.

```
3aff4050be5356b88cbda546a0891e3b8b26d966280d2eb288355730bda562aa  A1.png
3aff4050be5356b88cbda546a0891e3b8b26d966280d2eb288355730bda562aa  A1.png
```

**Result:** identical. Gradients are seeded, grain is FFmpeg's temporal noise but
rendered from a fixed frame count, and nothing depends on the clock.

**Decision:** `make mock` is the reference build: a clean clone can be verified
without a single key.

## 9. How wide is a cache invalidation?

**Hypothesis:** a good key means editing one line re-renders one line, not the
film.

**Test:** re-ran `pipeline.keyframes` unchanged, then edited A1's prompt in
`storyboard.json` and re-ran with `--dry-run --only A1,A2,B3`.

**Result:** unchanged run: 12/12 cached, 0.0 s, 0 model calls. After the edit:
`A1: would generate`, `A2: cached`, `B3: cached` - one prompt invalidates one
keyframe (and the clip that hashes it), and nothing else.

**Decision:** keys are semantic (prompt, seed, reference hash, duration) and each
artifact carries its key in a sidecar `.key` file, so the cache is inspectable
with `cat`.

## 10. Two exports, how much do they really cost?

**Hypothesis:** composing 12 shots twice is the honest way to get a real 16:9
cut, and maybe it is cheap enough to justify.

**Test:** counted the work: 12 extra keyframes, 4 extra video generations, a
second edit decision list, and a second set of subtitle positions.

**Result:** roughly double the image and video spend and a second art-direction
pass, for a derivative of a film designed for a phone. The 16:9 export from the
vertical master costs one FFmpeg pass (about 60 s) and 26 MB.

**Decision:** one master, two exports, with the horizontal frame built from a
blurred extension of the vertical. The compromise is visible, and `DESIGN.md`
says so instead of hiding it.

## 11. Which image model can actually paint a 9:16 frame?

**Hypothesis:** Gemini's image model, which accepts the reference photo as an
edit instruction, is the right default; FLUX is the cheaper fallback.

**Test:** requested one frame from each. Gemini returned `429` with
`free_tier_requests, limit: 0` - image generation is paid-only. flux-1-schnell
returned `HTTP 400: Additional or unevaluated properties '/seed, /width,
/height' not allowed`, and only makes a 1024x1024 square. FLUX.2 klein takes
multipart input with `prompt`, `width`, `height`, `seed` and up to four
`input_image_N` references.

**Result:** the catalog order was backwards. FLUX.2 klein 4B painted all 14
frames (12 shots + 2 reference sheets) in 138 s at 1080x1920, including the two
photo-referenced shots, and the whole run fitted inside the 10,000-neuron free
allowance. The 9B model costs ~1,363 neurons for the first megapixel against
~26 per 512px tile on 4B, i.e. about five times more per frame.

**Decision:** FLUX.2 klein 4B is the default (`CF_IMAGE_MODEL`), Gemini image is
the fallback for accounts without a Cloudflare token. The reference photo is
sent only as a 512x512 JPEG tile, and only for the shots that name her.

## 12. Does the likeness survive a painted edit?

**Hypothesis:** a 512px reference plus a written description keeps her face
recognisable without reproducing the photograph.

**Test:** compared D1 and D2 against `grandmother_source.png` at full size.

**Result:** both carry her silver hair, brow, nose and the age in her features;
D1 sits her at a coffee ceremony as prompted. D2 is closer than asked for: the
prompt describes a close-up of two hands, and the model instead restaged the
photograph's sofa pose, shawl and smile. It reads as her, and it is a painting
rather than a composite, but the two-hand image the narration implies is absent.

**Decision:** keep D2 as painted - it is the stronger closing frame - and record
the deviation here rather than pretending the prompt was followed. If the family
prefers the literal hands shot, the fix is one prompt edit and one regeneration,
and the cache invalidates exactly one clip.

## 13. What is the real Amharic speech rate?

**Hypothesis:** 2.2 words per second, the number `script.py` uses for warnings.

**Test:** measured all eleven lines Gemini TTS produced (A2-D2) from the trimmed
24 kHz WAVs. D2 came a day after the others, from a key in a second project with
its own daily allowance.

**Result:** 83 spoken words in 67.1 s of audio, or **1.24 words/s** - Amharic
words are long, and the instruction deliberately leaves room for pauses. The
line lengths were written for the 2.2 guess, so every shot needs more time than
its storyboard intent: the first eleven-line timing came to 91.4 s against a
90 s ceiling. Six shots gave up 12.9 s of slack and the film closed at 90.0 s,
but the last two seconds of breathing room had to come from the stage itself:
the gap after each line dropped from 0.8 s to 0.6 s, which recovered the 1.4 s
overrun without touching the words or 90 s of picture.

**Decision:** keep generating narration first. The measured numbers, not the
guess, set the edit; `script.py` only warns. With the script this tight, the
next revision should cut a line rather than squeeze the padding again.

## 14. Making a still read as filmed

**Hypothesis:** the first cut felt like a slideshow not because the camera moves
were wrong but because every shot made the same move: a linear push at constant
speed, with nothing else moving in frame.

**Test:** re-rendered A4 four ways and compared frames at 0 s, 4.5 s and 9 s -
linear vs smoothstep easing, with and without handheld drift, flicker and grain.
Then checked what a video endpoint would cost instead: `GET /ai/models/search`
on the Cloudflare account returns 52 models, none of them video, so image-to-video
would need a new paid account.

**Result:** easing alone changes the read most - a smoothstep move is 50% faster
mid-shot and settles at both ends, so the frame stops feeling like it is on rails.
Drift, flicker and grain add the rest at the cost of bitrate: grain roughly doubles
a clip at `crf 18`, so the shipped settings are `c0s=3` at `crf 20`. Twelve clips
now take 106.8 s to render (was 83.3 s) and total 43 MB (was 38 MB); the vertical
export is 68.3 MB (was 50.1 MB). The grain seed is fixed per shot, so a re-run is
byte-identical and the "deterministic Ken Burns" claim still holds.

**Decision:** ship it, and say plainly what it is not. This is a filmed painting,
not animation: smoke, steam and cloth are still frozen, and the four `wan` shots
are logged as `fallback` because no endpoint exists. Real motion means paying for
four i2v clips (about 30 s of generated video) and accepting that a model may warp
a painted face; the pipeline already supports it via `WAN_ENDPOINT`, so it is a
configuration change, not a rewrite.

## 15. What actually holds a shot's composition

**Hypothesis:** A2's three-handed frame was a prompt problem, so rewording the
hands would be enough and the seed could stay.

**Test:** twelve frames of A2 over eleven seeds at 1080x1920 with the character
reference sheet attached - ten on FLUX.2 klein 4B and two on the 9B model -
compared at 1:1 and at the size the shot occupies in the film. Three prompt wordings: hands folded on
one knee, hands in shadow, hands tucked into the shawl.

**Result:** only three of the eleven kept the seated corner the shot is written
for (31013, 31014, 31016); the rest returned the reference sheet's standing
chibi pose, whatever the wording said. The 9B model was more reference-locked
than the 4B, not less. Fingers changed with every seed, but composition did not
change with the prompt as reliably as it changed with the seed.

**Decision:** the seed is the composition control here, and the reference sheet
outranks prompt text at this model size. Seed 31014 ships because it holds the
corner and draws two hands. Repainting the girl's sheet as a seated gouache
portrait would fix this class of error properly, but it invalidates nine
keyframes and their clips, so it is recorded as the next revision instead of
being done blind the night before the deadline.

## 16. Does a faster narrator need a new voice take?

**Hypothesis:** the fix for "the narration is slow" is to regenerate the lines
with a brisker style instruction, since the model decides the pace.

**Test:** first measured where the time actually goes. `silencedetect` on the
eleven voice files found 1.75 s of dead air inside the new A4 line and 4.7 s
after it; the other lines had similar, smaller tails. Then compared three ways to
fix it: re-prompt the TTS (11 new calls, new performance, new risk), apply
`atempo` to the cached audio (one FFmpeg pass, rhythm preserved, 10 TTS calls
saved), or both.

**Result:** `atempo=1.10` alone took 67.1 s of speech to 61.0 s, and compressing
pauses longer than 0.55 s took it to 59.7 s at the same tempo. Pitch and formants
are untouched - `atempo` is a WSOLA time-stretch, not a resample - so it is still
the same take, just tighter. Re-prompting would also have cost a day of TTS quota
and changed eight lines that two testers had no complaint about.

**Decision:** tempo and pause compression are a post pass, keyed on the voice
file and the `speed` field, so the performance is paid for once. Changing pace
again is a one-line contract edit and one second of CPU. Three lines were
re-spoken anyway, because their words changed (A3, A4, C1); the other eight were
not touched.

## 17. How quiet is the score, really?

**Hypothesis:** the music was present from frame one, so the tester who thought
his audio was broken must have been mistaken.

**Test:** `volumedetect` on the first second of `score.wav`, and again on the
first four seconds. Then the same after normalising the assembled bed.

**Result:** -47.7 dB mean in the first second, -42.8 dB over the first four. The
bed was not missing, it was buried: three sines at -6 dB, faded in over 1.2 s,
never normalised, then ducked. After a whole-bed two-pass `loudnorm` to -27 LUFS
and a 0.15 s fade-in, the first second measures -26.7 dB and the master still
sits at -13.75 LUFS.

**Decision:** normalise the bed as a whole, not each cue, because the cue-to-cue
arc (C minor held, D minor urgent, F major warm, F major thinning) is the score.
Normalising per cue would flatten it to four equally loud pieces.

## 18. Can one negative prompt fix one frame?

**Hypothesis:** the global style negative is too blunt for defects that appear
in a single frame, and per-shot negatives can repair them without a full repaint.

**Test:** added `keyframe.negative` to the contract, appended it to the style
negative, and put it in the keyframe cache key. Re-painted B1 (watch, bracelets),
B2 (toes, hands, bracelet), C2 (paper border, child proportions) and A3 (fingers)
with shot-specific negatives.

**Result:** B1's watch and both bracelets disappeared on the first try; B2's six
toes became five. C2's paper border survived three takes and only went away when
the character reference was dropped - the border was coming from the reference
sheet's "print" look, not from the prompt. A3's hand survived the negative as
well, and the quota ran out before another seed could be tried.

**Decision:** per-shot negatives stay - they are cheap, they are in the cache
key, and they fixed two of four defects outright. The two that failed are
evidence that at 4B the image reference outranks negative text, which is the same
lesson as experiment 15 from the other direction.

## 19. Is the style split a prompt problem or a source problem?

**Hypothesis:** the same style block on all twelve shots should produce one look,
so a split means something else is varying - most likely the image reference.

**Test:** reviewed which shots had drifted. Every frame the reviewer called
semi-photoreal (A3, B1, B2, C1, C2) had been painted from a different prompt
wording of the character; every frame called watercolour (A1, A4, B3, B4, D1)
was either an establishing shot with no character or a shot with a reference.
Then the style block was rewritten to remove *"painterly realism"* and *"shallow
depth of field"* - both of which ask for a photograph - and the whole batch was
repainted with the sheet as reference.

**Result:** the rewrite plus a reference did unify the look: all twelve frames
came back as one painting style, with the same hair, the same age, the same
clothes. It also flattened every composition into a standing portrait, which was
worse than the drift. A second batch with a face-cropped sheet and text-only
prompts on the wide shots could not be completed - image quota ran out mid-batch.

**Decision:** the split is a *source* problem, not a prompt problem: one model,
two input modes (text-to-image and image-edit) produce two aesthetics. The
practical fix is to pick one mode per shot by what the frame is for, and to run
one film-wide finish pass so the two modes land in the same family.

## 20. How much painterly finish does a photographic frame need?

**Hypothesis:** a median blur plus a small saturation cut is enough to bring a
semi-real frame into the watercolour family without destroying the faces.

**Test:** swept `median` radius and saturation on recovered B1, A2 and C2 frames,
viewing stills at 540 px wide.

**Result:** `median=3` removed the pore-level detail that made the frames read as
renders, and `unsharp=5:5:0.35` returned enough edge to keep the eyes and the
cloth pattern from going plastic. Radius 5 erased the tibeb embroidery and the
henna dots. Saturation below 0.85 turned the warm Addis shots grey.

**Decision:** `median=3,eq=saturation=0.88:contrast=1.03,unsharp=5:5:0.35` as
`style.finish`, applied to all twelve shots after the move and before the grain.
It is one string in the contract, so the whole film's look is now one line.

## 21. Can a blurred-veil shader stand in for moving weather?

**Hypothesis:** with no video endpoint, a drifting blurred copy of the frame can
give a still the micro-motion the second round asked for.

**Test:** `haze` at 0.18 on A1, 0.22 on B1 and B4, 0.24 on B3, 0.10 on C1,
comparing frames 4-5 s apart.

**Result:** at 0.18 the veil was invisible on A1 and a mild flattening on B1; at
0.28 it clearly read as fog on a lens rather than fog in the air, and cost 12-14 s
per shot. At 0.12 the drift is perceptible between frames and the blacks stay put.

**Decision:** keep it at 0.12 on the three shots that actually contain fog, and
nowhere else. The honest version of this note needs image-to-video, which the
build has no endpoint for; `haze` is the local substitute, not the fix.
