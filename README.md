# amplify-weekly-kit

Builder for a branded HTML email newsletter. It renders an Outlook-safe 640px email from a small content JSON, generates the issue banner, and lists the inline images to attach.

```
python3 -I scripts/build.py content.json out
```

Outputs `out/email.html` (images as `cid:attN`), `out/preview.html` (local image paths, for screenshots) and `out/manifest.json` (subject plus inline attachments in att order, with sha256). The build fails on em/en dashes, unknown block types or unknown assets.

## content.json

Top level: `issue` (int), `date` (MM/DD/YYYY), `subject`, `topics` (3 short labels printed on the banner), `blocks` (ordered list). See `content_example.json`.

| block type | fields | renders as |
|---|---|---|
| `intro` | text | opening paragraph |
| `section_header` | title, icon?, icon_width?, subtitle? | blue section title, optional icon on the left |
| `graphic` | asset, width, alt, caption? | centered graphic, optional blue caption |
| `subhead` | text | bold subheading |
| `paragraph` | text | paragraph |
| `bullets` | items[] | bullet list |
| `box_bullets` | items[] | bullet list in a light blue box |
| `prompt` | text | copyable prompt box (quotes added automatically) |
| `callout` | style (warning, info, navy, teal), title?, text | callout box |
| `icon_card` | icon, title, text, icon_width? | icon on the left, title and text on the right |
| `try_it` | items[], title? | "Practice Makes Progress" try-it box |
| `rising_tide` | items[] | Rising Tide banner + list |
| `win` | text, title? | navy "Win of the Week" box |
| `next_open_lab` | title, text | teal bar |
| `divider` | -- | thin rule |

Text fields accept `<strong>`, `<em>` and HTML entities (`&rsquo;` `&ldquo;` `&rdquo;` `&amp;`). The footer (Teams chat button, Video Library button, logo, sign-off) is added automatically.

## Assets

`amplify.png` sparkle icon (Quick Updates, width 40) / `buffering.png` coming-soon features / `bullhorn.png` Bullhorn updates (width 64) / `keyboard.png` notes or typing sections (width 72) / `promptdrop.png` Weekly Prompt Drop graphic (width 300) / `openlab.png` Open Lab recap graphic (width 220) / `videolib.png` training video sections / `practice.png`, `risingtide.jpg`, `atlas.png`, `banner_bg.jpg`, `envelope.png` used automatically.
