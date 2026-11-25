# Costs

Two numbers matter: what the reference build actually cost, and what a real
build is projected to cost. Prices below were read on 2026-11-24 and are budget
figures, not invoices.

## Measured: the reference (mock) build

```
make mock   ->  script 0.0s | narration 0.1s | keyframes 5.3s | shots 55.9s
                | music 0.5s | assemble 172.6s
                total wall clock ~4 min, $0.00, 0 model calls
outputs/ 303 MB (vertical 66.8 MB, horizontal 26.1 MB, clips, keyframes, audio)
runs.jsonl 104 lines: 100 provider=mock, 4 provider=local (FFmpeg exports)
```

Nothing here is free in the sense of being useless: it proves the whole graph,
the timings, the mix at -14.00 LUFS, the burned Amharic cards, and both exports,
without a key. It is also the state a grader can reproduce.

Mock video is heavier than real video will be: grain that encodes cheaply on a
photo is expensive on a smooth gradient, which is why the mock vertical is 67 MB
at CRF 18 while the horizontal derivation is 26 MB.

## Actual: the real build

| stage | calls | model | billed | estimate in `runs.jsonl` |
|---|---|---|---|---|
| narration | 11 of 11 | `gemini-2.5-flash-preview-tts` | free tier, 10 requests/day | $0.008 |
| character sheets | 2 | FLUX.2 klein 4B / flux-1-schnell | free tier (neurons) | $0.004 |
| keyframes | 12 + 12 revision frames | FLUX.2 klein 4B (2 on 9B) | free tier (neurons) | $0.115 |
| shots | 12 | no video endpoint, Ken Burns | local FFmpeg | $0.00 |
| music | 12 cues | no music endpoint, synthesised bed | local | $0.00 |
| **total** | | | | **≈ $0.12** |

14 images at roughly 1,500 neurons each is about 21,000 neurons against a free
allowance of 10,000 per day, which is why the 4B model was chosen over the 9B
one: the same 14 frames on 9B would have been about 24,000 neurons for $0.24.
The A2 revision added 12 more candidate frames (FAILURES.md 12), $0.07 of the
total, so read the estimate column as cost of the film plus its redo, not as the
price of one pass. Both were run against a free Workers plan, so the dollars
above are list price rather than a charge.

The estimate that mattered was video: 4 hero shots on a Wan-class endpoint were
budgeted at ~$0.30 per 5 s clip, or $1.20 for 89% of the spend. No such endpoint
was available (Cloudflare's catalog has no video model, and no self-hosted
server was rented), so all 12 shots are Ken Burns and the film cost nothing.
That is the pipeline's designed failure mode, not a silent omission: every shot
logs `fallback` or `kenburns` in `runs.jsonl`.

Cost per attempt, not per deliverable: the first real run is a draft, and a
second pass after the audience test is budgeted at the same ~$1.34. Total
projected for the assignment: **under $3**.

## What controls the spend

- **Cache.** Re-running a stage with unchanged inputs costs nothing; the log
  shows `"cached": true`. A style change costs 12 images and no audio.
- **Retry caps.** 4 attempts for TTS, 3 for images, 2 for video, with backoff.
  A 4xx is not retried at all, because a bad prompt will fail the same way
  three times.
- **Order of work.** Mock first, then narration (cheap, and it fixes the edit),
  then keyframes (cheap, and they are the thing most likely to need a redo),
  then video (expensive) only once the keyframes have been looked at.
- **Candidates with a human in the loop.** 12 music candidates cost nothing
  when self-hosted, and the winner is a file, not a rerun.
- **No video on hands.** Hands are the highest-risk animated subject and the
  cheapest to fake, so shots B2 and D2 are stills.

## Free-tier reality, measured

- **Gemini TTS**: 10 requests per day per model. The film needs 11 lines, so the
  build stopped at D2 with `429 RESOURCE_EXHAUSTED`. The quota is charged per
  Google Cloud project, not per key, so a key from a *different* project gets its
  own ten; D2 was spoken the same afternoon that way, and the ten cached lines
  were reused. Each request cost about $0.0007 at list price.
- **Gemini image**: free-tier limit is literally `0`; the model is paid-only.
  An API key alone cannot paint a frame.
- **Cloudflare Workers AI**: 10,000 neurons per day free. FLUX.2 klein 4B is
  ~250–1,500 neurons per 1080x1920 frame depending on reference use, so the
  whole film fits; the 9B model would not.
- **Video**: no Wan-class model in Cloudflare's catalog and no rented GPU, so
  this line stays $0.00 and every shot is Ken Burns.

The only line that needs real money or real GPU time is video, and the pipeline
treats it as optional so that a missing endpoint cannot block the deliverable.
