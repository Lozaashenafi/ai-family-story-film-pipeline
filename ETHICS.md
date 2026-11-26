# Ethics

This file is the consent gate for the pipeline. `pipeline/keyframes.py` refuses to run unless
`meta.consent.status` in `storyboard.json` is `recorded`, and that value is only set once the
record below is accurate. Subject: my late grandmother.

## 1. Who is in this film

An Ethiopian woman, born in a rural Amhara highland village, married off as a child, who left the
arranged marriage in the night and walked and rode to Addis Ababa, where she lived the rest of her
life. She died before this film was made. She is not named in the film, in the subtitles, on the end
cards, or in the public post. The film calls her "my grandmother" and nothing more.

This is my family's story, told from inside my family, by her grandchild. It is not an
anthropological account of child marriage, and it does not generalise from her to anyone else.

## 2. What consent was obtained

Under the Ethiopian Civil Code (Proclamation 165/1960), Articles 27–30, the right over a person's
image belongs to that person and, after death, passes to their relatives, who enforce it against
uses that would harm the deceased's honour or reputation (Art. 30). The Personal Data Protection
Proclamation 1321/2024 treats a deceased person's data as protected for ten years after death, with
the lawful heir able to exercise those rights. Consent therefore had to come from her children.

It did.

| Field | Record |
| --- | --- |
| Consent given by | Her two eldest living children — my parent, and my parent's elder sibling. Both were asked in person, in Amharic, and both agreed. |
| Where the signed copies are | Held by the family, offline. Not in this repository: a public file naming living people who consented to a film about their mother is itself a privacy problem. |
| Referred to in code as | `meta.consent.status = "recorded"` in `storyboard.json`. |
| Date recorded | 25 November 2026, before any keyframe was generated. |

What they were shown and agreed to, item by item:

1. **The depiction.** A generated, painted likeness of her — informed by the one surviving family
   photograph — as a girl of about thirteen and as a woman of about seventy.
2. **The words.** A first-person Amharic narration written by me and placed in her mouth. They know
   it is my reconstruction of what she might have said, not a recording of anything she said.
3. **The invented detail.** Which parts of the story are family memory and which are mine are listed
   in §4, and they were told this before agreeing.
4. **The distribution.** Submission to the 10 Academy AI content generation assignment; publication
   of a vertical and a horizontal cut on my own public accounts; a public post about how it was
   made.
5. **The condition they set.** She is not named. No village name, no wedding date, no photograph of
   her face is published. The film's disclosure card says the images, music and narration are
   generated.

Scope not covered, and therefore not done: no sale or licensing, no use of her image or voice in any
other project, no inclusion of the source photograph in a training set, no photorealistic
reconstruction, no depiction of her death, and no depiction of the marriage itself beyond a shadow
on a wall and a folded shawl.

## 3. The likeness, specifically

This is the riskiest part of the film and it gets its own safeguards.

- **The look is illustration, not photograph.** Gouache and ink on coarse paper. A viewer cannot
  mistake a frame for a real photograph of her, and the platforms' "realistic depiction" trigger for
  mandatory AI labelling is not met — although the film is labelled anyway (§6).
- **The photograph is a reference, not a source image.** It goes to the image model at low strength
  to carry bone structure and brow, and is never composited into a frame. It is stored at
  `assets/refs/grandmother_source.png` (see `assets/refs/README.md`) and never appears in `outputs/`.
- **No hands are animated by the video model.** Wan 2.2 reliably mangles hands; a mutilated hand on
  an image meant to honour a woman who worked with hers would be a small insult repeated in every
  frame. The two shots that feature hands are stills with a slow Ken Burns move.
- **One face, one seed.** The grandmother character uses seed 2202 and a fixed character
  description everywhere, so the face is the same face shot to shot and she does not drift into a
  stranger across twelve cuts.
- **She is small in her own film.** No shot is built to make her look heroic or pitiable. C1 puts her
  at the edge of a busy street, not at its centre.

## 4. Where memory ends and I begin

Told plainly, because a film that says "this is her story" when half of it is mine is the actual
ethical failure here.

From the family, as told to me: the arranged marriage at about thirteen; the henna; the red wedding
shawl; leaving at night on foot; the highland road; arriving in Addis with nothing; the marriage she
chose afterwards; the coffee ceremony she presided over until the end; the scar on her knuckles.

Mine, invented for the film: every line of narration. The specific tear in A3, the abandoned shawl
in B3, the exact time of day, the weather, the "it is your fate" line given to the elder in A4, and
the granddaughter's presence in the final shot. The bus is invented twice over: it appears in B4 and
the revised C1 now says it took her to Addis, though she never described how she travelled. The
revised A4 also says the elders decided the marriage, which is the film's reading of the family's
"arranged" rather than a detail anyone told me. The Amharic is mine; she spoke Amharic, but these
are not her sentences.

Not in the film at all: her name, her village, the year, the husband's family, and what happened to
her in the first years in the city. Those belong to her children, not to a public video.

## 5. The voice

The narration is synthesised — Gemini TTS, a single Amharic voice, no real person's voice is cloned
or imitated. It is not her voice and the film never claims it is; the disclosure card says the
narration is generated. Nobody was recorded for this film, so no voice consent was needed beyond the
depiction consent in §2.

Language decisions, since they are part of the ethics and not just the edit: she is voiced in
Amharic, the language she actually spoke, because a film about her spoken in English would be a
performance of her rather than a memory of her. The subtitles are English so that my cousins who do
not read Amharic can follow, and so the cohort can. The dedication card carries the Amharic line and
an English rendering beneath it.

## 6. Disclosure

- Two seconds of black card at the end of every export: "This film was made with AI. Images, music
  and narration were generated." in English, with one Amharic line.
- The platform's own AI-content label is set on each upload, on every platform, whether or not the
  platform requires it for stylised content.
- The public post says what was generated and what was family memory, in that order, and links to
  this file.
- `EXPERIMENTS.md` and `runs.jsonl` record every model, prompt and seed, so the claim is checkable
  rather than a promise.

## 7. Data handling

- The source photograph lives on my machine and, if this repository stays private, in this
  repository. If it is ever made public, the photo is added to `.gitignore` and stays local.
- It goes to exactly one third party: the image generation provider, as a reference image, under
  that provider's standard terms. Not to any other service, and not into any dataset.
- Generated frames, audio and the final cuts sit in `outputs/` and are public because the film is
  public. `outputs/` can be rebuilt from `storyboard.json` alone, which is why it is not the record
  of anything.
- No analytics, no tracking, no pixel on the film's pages.

## 8. If they change their mind

The family can withdraw at any point, for any reason, without explaining it. Withdrawal means: set
`meta.consent.status` back to `"pending"` (which makes the keyframe stage refuse to run), delete
`outputs/`, delete `assets/refs/grandmother_source.png`, take down the uploads, and delete the
public post. That order matters — the exports go first, the source photograph second, the pipeline
gate third.

Anyone in the family reading this should know that the take-down is not an argument and I will not
ask why.

## 9. What this film could still get wrong

- Her children may remember it differently than I have written it. Their version wins, and I will
  change the narration before publishing if they say so.
- A film about a child bride risks turning a woman into a symbol of the thing that was done to her.
  The two shots that exist to prevent this are C2, where she is allowed to be glad, and D1, where she
  is old and presiding over her own coffee ceremony.
- Publishing a family's private history as a public portfolio piece is a real cost. The mitigations
  are that she is unnamed, that the invented parts are labelled in §4, and that the film points back
  at the viewer — go and ask your own elder — rather than at her.
