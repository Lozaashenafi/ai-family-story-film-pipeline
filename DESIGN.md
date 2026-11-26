# Design

## The audience, and what the film owes them

Two audiences, in this order: my mother's generation, who knew her, and my
cousins born in Addis and abroad, who know her name and nothing else. Then the
cohort.

What that changes: the film cannot be a biography, because I do not have the
facts of one. It is one decision, dramatised, and it ends on the living. A
cousin who never met her should finish it knowing one true thing about her and
wanting to ask an elder for the rest.

## Shape

Four scenes, twelve shots, 82 s of picture and 8 s of end cards.

| # | scene | shot | len | mode | why it exists |
|---|-------|------|-----|------|----------------|
| 1 | A | A1 extreme wide, hut at night | 6.0 s | Wan | where and when, with the celebration off-frame pressing in |
| 2 | A | A2 medium, girl against the wall | 7.0 s | Ken Burns | she is a child, dressed for someone else's decision |
| 3 | A | A3 close, one tear in lamplight | 6.4 s | Ken Burns | the moment she understands what is happening |
| 4 | A | A4 insert, an elder's shadow | 7.8 s | Ken Burns | the institution, as a shadow, without a face |
| 5 | B | B1 wide, fog on the path | 7.0 s | Wan | the decision as an image, not a line |
| 6 | B | B2 insert, bare feet, blood | 8.4 s | Ken Burns | what running actually costs; no romanticising |
| 7 | B | B3 close, shawl abandoned | 6.2 s | Ken Burns | the vow, said with an object |
| 8 | B | B4 extreme wide, the valley | 7.9 s | Wan | distance: the valley behind, the city unseen |
| 9 | C | C1 wide, Addis in gold | 7.7 s | Ken Burns | the hard cut from fog to gold is the film's turn |
| 10 | C | C2 close, first smile | 5.4 s | Ken Burns | the one shot where she is allowed to be glad |
| 11 | D | D1 close, coffee ceremony | 6.4 s | Wan | the match cut: the same face, sixty years on |
| 12 | D | D2 insert, two hands | 5.9 s | Ken Burns | memory lives in hands; pull back to the granddaughter |

Nothing runs longer than eight and a half seconds and nothing repeats a beat.
The two shots that carry the most meaning - the tear and the hands - are the
cheapest and stillest in the film, which is the argument for the hybrid
approach: motion where it adds, stillness everywhere else. The lengths above are
the measured ones in `outputs/audio/timing.json` after the revision the testers
asked for; the contract still carries each shot's intent, and the stage takes the
larger of the two. A1 now holds its full six seconds instead of being crushed to
2.8 s to pay for slow speech.

The `mode` column is the intent, not what ran. This build had no video endpoint
(the Cloudflare account exposes 52 AI models and none of them generate video),
so all twelve shots went through the local treatment in `shots.py`: an eased
camera move, a handheld drift, a small light flicker and fixed-seed grain. That
makes a still read as filmed; it cannot make smoke, steam or cloth move, which
is what the four Wan shots were for.

Each scene also carries a grade in the contract (`style.grades`), applied to
every clip in that scene: A is held neutral, B is dropped 0.02 in brightness,
desaturated to 0.80 and given more contrast, C is left warm. One tester said the
film painted running away as beautiful and lost the fear; the grade is the cheap
half of that answer, because it re-grades the scene without repainting frames
that already read. The other half is in the writing and the performance of C1:
she arrives dazed and clutching the shawl, not in awe.

## Look

Hand-painted gouache and ink on coarse paper. This is a likeness safeguard
first: a painting of my grandmother is a depiction, not a resurrection, and it
cannot be mistaken for a photograph of her. It is also the only way to keep one
person recognisable across twelve independently generated frames - the style
block does the work that a consistent camera crew would do.

Colour is carried by scene, not by shot: cold indigo with one amber lamp (A),
slate-blue fog (B), warm gold and terracotta (C), honey lamplight and deep
green (D). Inside a scene the palette string is identical in every prompt, so
the cuts read as one night, one dawn, one afternoon, one room.

The one real photograph is used at low strength as an image-to-image reference,
for face structure and the age in her features. It is never composited, never
shown, never published. The girl is generated from the written description
alone: a photograph of her at seventy cannot tell a model what she looked like
at thirteen, and inventing a young face from the old one would be a different
kind of lie. She shares a seed, not a face - the film cuts from her to her older
self at the same angle and lets the audience do the recognition.

## Sound

**One narrator.** An older woman, unhurried, close to the microphone, speaking
Amharic as if to one person in the room. A second voice for the ending was
considered and rejected: the film is one woman remembering, and two voices would
turn it into a dialogue it is not. The voice is `Kore` in the contract, with the
style instruction beside it, so changing the performance is a one-line edit.

**The narration is first person and invented.** I do not know what she said that
night. The words are the shape of the story as my family tells it, not a record.
`ETHICS.md` lists exactly which details are remembered and which are invented,
and the film's disclosure card does not pretend otherwise.

**Pace.** Testers said the narration was slow, and the measurement agreed: the
first cut ran at 1.24 words per second, with the model leaving up to 4.7 s of
dead air at the end of a line and 1.8 s inside one. The revision cuts any pause
longer than 0.55 s back to a 0.3 s beat and plays the result 10% faster with
`atempo`, which changes duration but not pitch. That took 83 words from 67.1 s
to 59.7 s and gave the opening shot its length back. It is a post pass keyed on
the voice file, so pace can be changed again without paying for TTS twice.

**Score** is four cues, one per scene, and it carries the arc: C minor with a
distant frame drum (a room she cannot leave), D minor ostinato (fear with
forward motion), F major swell (the exhale in Addis), F major returning thinned
to one plucked note (the last line lands in near-silence). The opening theme
returns at the end because the ending is the opening, paid off.

The first cut was effectively silent for its opening second: the synthesised bed
measured -47 dB mean, faded in over 1.2 s, and one tester thought his phone's
audio had broken. The bed is now normalised as a whole to -27 LUFS before the
mix, with a 0.15 s fade-in on the first cue, so the film opens on a low hum and
the cue-to-cue arc survives. The voice still owns the mix: the final ducked
master measures -13.8 LUFS at -1 dBTP.

The mix is a sidechain duck, not a static level: the score drops when she speaks
and comes back in the gaps, with a slow 1.5 s release so it never pumps. Target
-14 LUFS / -1 dBTP, measured twice - once to normalise, once to verify.

## Text on screen

Subtitles are English, from the contract's `subtitle` field: a translation, not
a transcript, and written to be read in the time the line takes, wrapped to two
lines of about forty characters at the lower third, clear of the safe area on a
phone. The narration stays Amharic; nothing is dubbed over it.

Two end cards. The dedication is Amharic first (`ለአያቴ...`) with the English
under it. The second says plainly that images, music and narration were
generated, in English and Amharic, in the same type.

## One master, two exports

The film is composed for 9:16, because it will be watched on a phone, once, by
people who are standing up. The 16:9 export is derived: the vertical frame stays
sharp in the centre and the sides are filled with a blurred, dimmed extension of
the same image. It looks deliberate, it costs one FFmpeg pass, and it does not
pretend the horizontal cut was designed shot by shot. Composing twice would have
doubled image and video spend for a secondary deliverable.

## User test 1 - three friends, the 90 s cut

Three friends watched the vertical cut alone, on a phone, with no context beyond
the six questions below. They are not family, so this round tests whether the
story communicates at all; the family screening is still to come. Their replies
were collected in writing (WhatsApp and Telegram), are kept with the consent
record rather than published, and are summarised here in their own words.

**The questions asked**

1. Was the story clear and easy to understand?
2. How did the video make you feel?
3. Did the visuals match the story and narration?
4. Was there any scene that felt confusing, boring, or out of place?
5. Which part was most memorable to you?
6. What would you improve?

### What they said

**Tester 1** - *"Such a great and inspiring story... the only flaw I saw was that
the narration was slow. If it's a bit faster it will be great."*

**Tester 2** (the longest reply, quoted in full because every line changed the
edit)

- *Clear?* Yes. *"The girl was sentenced to an arranged marriage, and she wanted
to escape it. She chose the unknown yet free path of her future over the known
but imprisoning path of her past... She moved to the city with nothing."*
- *Feeling?* Sympathetic, and it raised something the film did not intend:
*"we don't discuss much about early marriage as part of the family of harmful
things done to girls... we neglect the quieter but still potent damage of
altering someone's life path without their consent."*
- *Visuals?* *"Kinda... running away and trying to build your life from scratch
is one of the scariest things you could possibly do. I don't think the visuals
capture that fear and confusion and uncertainty. They paint... a very positive
image of it, which distances it from reality and prevents depth."*
- *Problems?* *"The vocal narration should be done by an actual human. The AI
butchered it a bit. For instance, at 00:09, it took me four listens to know that
it was 'እንሶስላ ሲኳሉ'."* Also: *"a humming background instrumental music would
enhance the experience... the dead silence made me think for a second that the
sound of my device wasn't working."* And three image errors: *"At 00:28, she's
wearing a modern watch. At many points, she seems to have an extra one or two
toes, or her fingers are disproportionate. On the second city picture of hers,
she looks much younger and shorter."*
- *Most memorable?* *"The part where she was looking down from a small hill to an
approaching car"* - B4.
- *Improve?* Fix those, *"narrate it myself"*, and *"bridge the gap between the
visuals"*.

**Tester 3**

- *Clear?* Yes, *"easy to comprehend... possible to follow the story without
being sidetracked."*
- *Feeling?* *"A sense of hope... sad for what the main character went through
but really happy and hopeful when seeing how she triumphed over her past."*
- *Visuals?* Yes, they matched.
- *Problems?* *"At times the girl would not match the age she was shown as, for
example when the girl came to Addis Ababa she looked younger in a picture that
was taken of her compared to the scene when she first arrived."*
- *Most memorable?* *"How she grew old and became someone who overcame her past
so she could stand today... it really has me thinking about how I myself can
change my life for the better."*
- *Improve?* *"The pacing: how was this girl's journey from her village to Addis
Ababa? Or what exactly are the 'chains' set on her as a female in her village?"*
Those two additions, she said, would *"pin how grave the situation was and in
turn have the ending further shine."*

### What this revision changed

| Note | Change | Where |
|------|--------|-------|
| Narration too slow (1, 2) | Pauses over 0.55 s cut to 0.3 s, then 1.10x tempo; 67.1 s of speech became 59.7 s | `pipeline/narration.py`, `voices.narrator.speed` |
| Word at 00:09 unintelligible (2) | A3 rewritten without the relative verb that was misheard: *"There was henna on my hands..."* | `storyboard.json` A3 |
| Dead silence at the start (2) | Bed normalised to -27 LUFS, first cue fades in over 0.15 s; opening second went from -47.7 dB to -26.7 dB | `pipeline/music.py` |
| Watch and bracelets at 00:28 (2) | B1 repainted with bare wrists; per-shot negative for jewellery | `storyboard.json` B1 |
| Six toes (2) | B2 repainted; five toes on each foot | `storyboard.json` B2 |
| Disproportionate fingers (2) | A3 re-framed so the hand leaves the shot | `storyboard.json` A3 `kenburns` |
| She ages backwards in Addis (2, 3) | C2 repainted as a tall thirteen-year-old, no paper border; seed 31022 | `storyboard.json` C2 |
| `"chains"` never named (3) | A4 now says the elders decided the marriage and gave her a man she did not know | `storyboard.json` A4 |
| Journey to Addis missing (3) | C1 now opens with the bus that took her there | `storyboard.json` C1 |
| Escape looks too pretty (2) | Scene B desaturated and darkened by a contract grade; C1's awe replaced with exhaustion | `style.grades`, `storyboard.json` C1 |

### What was not adopted, and why

- **A human narrator.** Both the brief and this build require generated
narration, and the words are invented in her voice, so a human performer would
have to consent to speaking a dead woman's invented first person. Instead the
specific unintelligible line was rewritten and the pace fixed. If a family
member ever wants to record it, the contract's `voices` block is where that
voice would live.
- **More plot.** Tester 3's two asks were answered inside existing shots rather
than with new ones: the film is at the 90 s ceiling, and a new scene would have
cost the stillness that testers 1 and 3 both responded to. The chains are named
in A4, shown in A2, and felt in B2.
- **Re-recording the voice entirely.** Three lines were re-spoken; the other
eight were kept, because each TTS call is metered and the performance was not
the problem - the pauses and the one word were.

### Known defects in this cut

- A3's keyframe still contains the hand; the shot's reframing hides all but a
sliver in the lower-left corner. Cropping any tighter loses her hair.
- B2's frame still contains her hands and a knitted red wrap at the top edge;
the Ken Burns crop keeps them at the boundary. Repainting it needs image quota
that ran out on the day.
- C2 reads about ten or eleven rather than thirteen, and younger than C1. The
paper border and the child proportions are gone, but the reference sheet still
pulls the face young.
- A4's lamp renders as a caged electric bulb rather than a kerosene lamp. Nobody
in the test flagged it, and the frame is otherwise the strongest in scene A, but
it is the same class of error as the wristwatch.
- The root cause of the age drift is `outputs/refs/girl_sheet.png`: it is still
the standing, round-faced child the film was first built from. Regenerating it
as a seated thirteen-year-old would fix A2, C1 and C2 together, and would
invalidate every keyframe that uses the girl. That is the next revision.

### Still to do

The family screening - my mother, one of her siblings, one cousin from the Addis
generation - asks a different question: does the face read as her, does the
voice feel like her, is any invented detail wrong in a way that hurts. The same
three friends will be asked the six questions again on this cut, and their
second answers will be appended here rather than replacing the first.
