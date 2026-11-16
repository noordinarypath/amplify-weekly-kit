# Amplify Weekly -- Friday automation runbook

Kristin Farnsworth (Atlas MedStaff) sends **Amplify Weekly** to Atlas recruiters. Every Friday morning a scheduled run writes the next issue and emails it to her Atlas inbox (`kfarnsworth@atlasmedstaff.com`). An Outlook rule moves anything with "Amplify Weekly" in the subject to her **Ready to Send** folder. She reviews it, edits if needed, forwards it to the recruiter list, and sends. **Never send to anyone but her.**

This file is the source of truth for the run. Follow it top to bottom.

---

## 1. Set up

1. Clone this repo (`noordinarypath/amplify-weekly-kit`) into the working directory. Pillow must be importable (`pip install --break-system-packages pillow` if not).
2. Read `issues.json`. The newest entry gives the last issue number, date, and topics. The new issue number = last + 1. The **coverage window** = the day after the last issue's `covers_through` date through today.

## 2. Gather the week's material (Amplify only)

Sources, in this order:
1. **Claude Project "Amplify - AI Enablement Role"**: call `project_info`, then read every doc created in the coverage window. Expect Open Lab transcripts and attendance CSVs, Open Lab agendas and work logs, Bullhorn meeting recaps, and handoff docs. Also read `claude/MeetingRecap_*` docs updated in the window.
2. **Past chats in the project**: `recent_chats` with `after` = start of the coverage window. Open the ones about Amplify, Open Lab, Transcribe, Bullhorn, prompts, or the newsletter, and pull what Kristin tested, found, or decided.
3. **Memory** (`/projects/019d187c-2a0c-77d1-99c1-9db4ffe8083b/overview.md`, `learnings.md`, `ways-of-working.md`) for background only.

Ignore anything about her job search, No Ordinary Path, family, Toro evaluation details, or leadership politics. None of it belongs in a recruiter newsletter.

Good newsletter material: Open Lab recaps (prompts shown, peer tips, questions asked), new or fixed Amplify features, known bugs and workarounds, prompts Kristin tested, Bullhorn updates that change what recruiters can do, peer wins, and the next Open Lab date (Tuesdays).

Do not repeat material listed under `topics` or `covered` for earlier issues in `issues.json`, unless something changed (for example, a bug got fixed).

If there's no Open Lab transcript for the window, write the issue from what exists and say so in the review notes. If there's nothing worth sending, skip the newsletter and send only the review-notes email explaining why.

## 3. Editorial rules (non-negotiable)

- Write in Kristin's first person: conversational but professional, practical, warm, short sentences. "I" and "you."
- **No em dashes or en dashes.** Use " -- " (double hyphen). The build fails if any remain.
- No attendance numbers. No leadership names (Steve Ryan, Joel Kozisek, Lindsey Martin, Aaron Daly, Mandy Sudbeck in a leadership context). No Bullhorn staff names. "Our Bullhorn AI advisor" is fine.
- Never a bragging vehicle. Credit peers by first name in Rising Tide.
- No traveler names, facility names, addresses, or candidate details. Anonymize win stories.
- Do not feature Meghan Patton or her desk-recovery prompt.
- Quote prompts word for word in `prompt` blocks so recruiters can copy them.
- State limitations plainly ("can't do yet"). Never promise dates for features that aren't live.
- Keep it skimmable: roughly 400 to 700 words of copy. Cut rather than pad.
- Use HTML entities for curly quotes and apostrophes (`&rsquo;`, `&ldquo;`, `&rdquo;`) and `&amp;` for &. `<strong>` and `<em>` are allowed inside text.

## 4. Write content.json

Copy `content_example.json` as the shape. Top-level fields:
- `issue` (int), `date` ("MM/DD/YYYY", today's date), `subject` ("Amplify Weekly | M/D | Topic, Topic, Topic")
- `topics`: exactly 3 short topic labels (they print on the banner; keep each under about 22 characters)
- `blocks`: ordered list of blocks

**Block types:**
| type | fields | use for |
|---|---|---|
| `intro` | text | 1 to 2 opening sentences |
| `section_header` | title, icon?, icon_width?, subtitle? | section titles (Quick Updates, feature sections) |
| `graphic` | asset, width, alt, caption? | centered section graphic with an optional blue caption |
| `subhead` | text | bold subheading inside a section |
| `paragraph` | text | short paragraph |
| `bullets` | items[] | bullet list |
| `box_bullets` | items[] | bullet list in a light blue box (cheat sheets, steps) |
| `prompt` | text | copyable prompt box (no surrounding quotes needed) |
| `callout` | style (warning/info/navy/teal), title?, text | warnings, reminders |
| `icon_card` | icon, title, text, icon_width? | short update with an icon on the left |
| `try_it` | items[], title? | "Practice Makes Progress" try-it box |
| `rising_tide` | items[] | Rising Tide banner + peer tips |
| `win` | text, title? | Win of the Week (navy box) |
| `next_open_lab` | title, text | teal bar with the next Open Lab |
| `divider` | -- | thin line between major sections |

**Assets** (in `assets/`), and when to use them:
- `amplify.png`: sparkle icon, Quick Updates header (icon_width 40)
- `buffering.png`: "coming soon" / in-progress features (icon_card)
- `bullhorn.png`: Bullhorn update cards (icon_card, icon_width 64)
- `keyboard.png`: typing, notes, or prompt-writing sections (icon_width 72)
- `promptdrop.png`: Weekly Prompt Drop graphic over the main prompt section (width 300)
- `openlab.png`: Open Lab & Chat graphic over Open Lab recaps (width 220)
- `practice.png`: used automatically by `try_it`
- `videolib.png`: Video Library graphic, for sections pointing to training videos
- `risingtide.jpg`, `atlas.png`: used automatically

The footer (Teams chat button, Video Library button, Atlas logo, "-- Kristin") is added automatically. Don't add it again.

**Typical order:** intro > Quick Updates (warning callouts, icon_cards, bullets) > divider > feature section(s) > divider > Prompt Drop (prompts + try_it) > divider > Open Lab recap > rising_tide > win (optional) > next_open_lab. Skip any section that has no real content.

## 5. Build and check

```
python3 -I scripts/build.py content.json out
```
- Fix any error it raises (dashes, unknown asset or block type).
- If `google-chrome` exists, screenshot `out/preview.html` at 700px wide and look at it: banner text fits, no broken images, nothing awkward. Fix and rebuild if needed.
- Re-read the copy against Section 3 once more.

## 6. Send to Kristin

`out/manifest.json` lists the subject and inline images in order (att0, att1, ...). Send with Gmail `send_message`:
- `to`: ["kfarnsworth@atlasmedstaff.com"]
- `subject`: manifest subject
- `htmlBody`: the full contents of `out/email.html`
- `body`: "Amplify Weekly, Issue N. Open in Outlook to view the formatted version."
- `attachments`: one per manifest entry, in the same order, each with `content` = `sha256:<sha256>:<path>`, `filename`, `mimeType`, `inline: true`

Then send a second, plain-text email to the same address:
- subject: "Amplify Weekly -- review notes for Issue N"
- body: what's in the issue, what sources it came from, and a numbered **check before you send** list. Include anything uncertain (a fix you couldn't confirm, a feature status that may have changed, a tip whose attribution you inferred), anything that should be attached (cheat sheets), and any missing sources (for example, "no 11/17 Open Lab transcript in the project").

## 7. Record the issue

Append to `issues.json`: issue, date sent, covers_through (today), subject, topics, and `covered` (a short list of specific items included, such as prompts and tips, so later issues don't repeat them). Commit and push to `main` with the message "Issue N".

Finish with a short summary of what was sent.
