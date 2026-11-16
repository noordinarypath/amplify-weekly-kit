#!/usr/bin/env python3
"""Team NOP Weekly builder.

Commands:
  python3 -I tnw_build.py desk <desk-data.json> <YYYY-MM-DD issue date>
      Prints a review table of placed travelers (name, unit, facility, start, end, bday)
      plus draft roster/upcoming/birthday lists, for the writer to check.
  python3 -I tnw_build.py build <content.json> <assets_dir> <out_dir>
      Renders roster.png, map.png, newteam.png (if new people), then out/email.html,
      out/preview.html, out/manifest.json.

assets_dir must contain: banner.png, tips.jpg, eap.png, hub.png, signoff.jpg, bday.png,
newteam_src.png (the original "New to the team graphic"), and fonts/KaushanScript-Regular.ttf.
Needs: Pillow, google-chrome, node with us-atlas@3 d3-geo@3 topojson-client@3 installed in
<out_dir>/../node (the build installs them if missing).

content.json fields:
  date_long   "Friday, November 20"
  hello       [html paragraphs]
  news        [{"title": "...", "emoji": "&#129411;", "html": ["<p-level html>", ...]}]
  new_people  [{"name": "Seth", "specialty": "Cath Lab"}]   (empty list = no section)
  welcome     "html line under the new-people graphic"
  roster      [{"name": "Lizzie", "specialty": "PACU"}]     (working now)
  upcoming    [{"name": "Sidney", "specialty": "Peds"}]     (future start)
  pins        [{"label": "Reno, NV", "lat": 39.53, "lon": -119.81}]  (one per traveler working now)
  map_line    "html line under the map"
  birthdays   [{"name": "Erik", "date": "December 2"}]      (empty = no section)
"""
import datetime as dt, hashlib, html, json, os, random, re, shutil, subprocess, sys
from PIL import Image

NAVY, TEAL, LIGHT = '#06567F', '#3BC1C8', '#BDECF4'
HUB_URL = 'https://www.noordinarypath.com/teamnophub'
CHROME = shutil.which('google-chrome') or shutil.which('chromium') or 'google-chrome'

# ---------------------------------------------------------------- desk review
def parse_md(s):
    s = (s or '').strip()
    if re.fullmatch(r'\d{8}', s):
        return int(s[:2]), int(s[2:4])
    m = re.match(r'(\d{1,2})[/-](\d{1,2})', s)
    return (int(m.group(1)), int(m.group(2))) if m else None

def desk(path, issue):
    d = json.load(open(path))
    today = dt.date.fromisoformat(issue)
    print(f"desk savedAt: {d.get('savedAt')}")
    print('name | unit | facility | start | end | bday(m/d)')
    bdays = []
    for t in d.get('placed', []):
        md = parse_md(t.get('bday'))
        print(f"{t.get('name')} | {t.get('unit')} | {(t.get('facility') or '').strip()} | {t.get('start')} | {t.get('end')} | {md}")
        if md:
            for y in (today.year, today.year + 1):
                try:
                    b = dt.date(y, *md)
                except ValueError:
                    continue
                if 0 <= (b - today).days <= 30:
                    bdays.append((b, t['name'].split()[0]))
    print('\nBirthdays in next 30 days (first name, date):')
    for b, n in sorted(bdays):
        print(f"  {n} - {b.strftime('%B')} {b.day}")
    print('\nDecide working-now vs upcoming from start dates (no year usually means the most recent sensible year).')

# ---------------------------------------------------------------- renderers
def shot(html_path, png_path, w=1200, h=800):
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--allow-file-access-from-files', '--hide-scrollbars',
                    f'--window-size={w},{h}', f'--screenshot={png_path}', 'file://' + os.path.abspath(html_path)],
                   check=True, capture_output=True)

def li(p):
    return f"<li><b>{html.escape(p['name'])}</b> - {html.escape(p['specialty'])}</li>"

def render_roster(c, work):
    people = c['roster']
    half = (len(people) + 1) // 2
    n = len(people)
    fs = 34 if n <= 14 else 30 if n <= 18 else 26
    up = ''
    if c.get('upcoming'):
        up = ('<div class="up"><h2>Upcoming</h2><p>' +
              ' &nbsp;&bull;&nbsp; '.join(f"{html.escape(p['name'])} - {html.escape(p['specialty'])}" for p in c['upcoming']) + '</p></div>')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;width:1200px;height:800px;background:{NAVY};font-family:Poppins,Arial;color:#fff;position:relative;overflow:hidden}}
h1{{margin:0;padding-top:48px;text-align:center;font-size:64px;font-weight:700}}
.cols{{display:flex;justify-content:center;gap:90px;margin-top:36px}}
ul{{margin:0;padding:0;list-style:none}} li{{font-size:{fs}px;line-height:1.7}} li b{{font-weight:600}}
li:before{{content:"\\2022";color:{TEAL};margin-right:16px}}
.up{{text-align:center;margin-top:28px}} .up h2{{margin:0 0 6px;font-size:34px;font-weight:600;color:{TEAL}}} .up p{{margin:0;font-size:30px}}
.bar{{position:absolute;left:0;right:0;bottom:0;height:14px;background:{TEAL}}}
</style></head><body><h1>Team NOP Current Roster</h1>
<div class="cols"><ul>{''.join(li(p) for p in people[:half])}</ul><ul>{''.join(li(p) for p in people[half:])}</ul></div>
{up}<div class="bar"></div></body></html>'''
    open(f'{work}/roster.html', 'w').write(page)
    shot(f'{work}/roster.html', f'{work}/roster.png')

MAP_JS = r'''
import fs from 'fs'; import { createRequire } from 'module';
import { geoAlbersUsa, geoPath } from 'd3-geo'; import { feature, mesh } from 'topojson-client';
const require = createRequire(import.meta.url); const us = require('us-atlas/states-10m.json');
const pins = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const proj = geoAlbersUsa().scale(1300).translate([487.5, 305]); const path = geoPath(proj);
const nation = path(feature(us, us.objects.nation)); const states = path(mesh(us, us.objects.states, (a, b) => a !== b));
const seen = new Map(); const missed = [];
for (const p of pins) { const xy = proj([p.lon, p.lat]); if (!xy) { missed.push(p.label); continue; }
  const k = xy.map(v => Math.round(v / 6)).join(','); if (!seen.has(k)) seen.set(k, { x: xy[0], y: xy[1], n: 0 }); seen.get(k).n++; }
const dots = [...seen.values()].map(d => `<circle cx="${d.x.toFixed(1)}" cy="${d.y.toFixed(1)}" r="${d.n > 1 ? 11 : 9}" fill="#0B5A8C" stroke="#fff" stroke-width="3"/>` +
  (d.n > 1 ? `<text x="${d.x.toFixed(1)}" y="${(d.y + 4.5).toFixed(1)}" text-anchor="middle" font-family="Poppins" font-weight="700" font-size="12" fill="#fff">${d.n}</text>` : '')).join('');
fs.writeFileSync(process.argv[3], `<!doctype html><html><head><style>body{margin:0;background:#fff;width:1200px;height:800px;font-family:Poppins,Arial}
h1{margin:0;position:absolute;top:50px;left:0;right:0;text-align:center;color:#3BC1C8;font-size:62px;font-weight:700;line-height:1}
svg{position:absolute;left:100px;top:150px}</style></head><body><h1>Where is Team NOP right now?</h1>
<svg width="1000" height="626" viewBox="0 0 975 610"><path d="${nation}" fill="#A3D5FA"/><path d="${states}" fill="none" stroke="#7FB3D9" stroke-width="1"/>${dots}</svg></body></html>`);
console.log('pins plotted:', seen.size, missed.length ? 'NOT PLOTTED (outside lower 48/AK/HI): ' + missed.join('; ') : '');
'''

def render_map(c, work):
    node_dir = os.path.join(work, 'node')
    os.makedirs(node_dir, exist_ok=True)
    if not os.path.isdir(os.path.join(node_dir, 'node_modules', 'us-atlas')):
        subprocess.run('npm init -y >/dev/null && npm i us-atlas@3 d3-geo@3 topojson-client@3 >/dev/null 2>&1',
                       shell=True, cwd=node_dir, check=True)
    open(f'{node_dir}/map.mjs', 'w').write(MAP_JS)
    json.dump(c['pins'], open(f'{work}/pins.json', 'w'))
    r = subprocess.run(['node', 'map.mjs', os.path.abspath(f'{work}/pins.json'), os.path.abspath(f'{work}/map.html')],
                       cwd=node_dir, check=True, capture_output=True, text=True)
    print(r.stdout.strip())
    shot(f'{work}/map.html', f'{work}/map.png')

def render_newteam(c, assets, work):
    src = Image.open(f'{assets}/newteam_src.png').convert('RGB')
    W, H = src.size
    src.crop((round(W * .547), round(H * .292), round(W * .97), round(H * .842))).save(f'{work}/sticker.png')
    people = c['new_people']
    n = len(people)
    size = 96 if n == 1 else 74 if n <= 2 else 60 if n <= 4 else 46
    lh = 1.35 if n <= 3 else 1.2
    random.seed(7)
    colors = ['#FF3B5C', TEAL, '#FFC93C', NAVY, '#FF8A3D', '#ffffff']
    conf = []
    for _ in range(900):
        if len(conf) >= 60:
            break
        x, y = random.randint(0, 1200), random.randint(0, 800)
        if not (x < 70 or x > 1150 or y < 34 or y > 748 or (y < 230 and (x < 170 or x > 1060))):
            continue
        w, h = random.choice([(10, 22), (14, 14), (8, 26), (12, 12)])
        r = '50%' if w == h and random.random() < .5 else '2px'
        conf.append(f'<i style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{random.choice(colors)};border-radius:{r};transform:rotate({random.randint(0,180)}deg)"></i>')
    names = ''.join(f'<div class="n" style="font-size:{size}px;line-height:{lh}">{html.escape(p["name"])}<span>, {html.escape(p["specialty"])}</span></div>' for p in people)
    font = os.path.abspath(f'{assets}/fonts/KaushanScript-Regular.ttf')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:K;src:url(file://{font})}}
body{{margin:0;width:1200px;height:800px;background:{LIGHT};font-family:Poppins,Arial;position:relative;overflow:hidden}}
i{{position:absolute;display:block;opacity:.9}}
h1{{position:absolute;top:44px;left:0;right:0;margin:0;text-align:center;font-size:92px;font-weight:700;color:#fff;text-shadow:0 4px 14px rgba(6,86,127,.35)}}
.sub{{position:absolute;top:158px;right:150px;font-size:30px;font-weight:600;color:#fff;text-shadow:0 2px 8px rgba(6,86,127,.35)}}
.names{{position:absolute;left:70px;top:250px;width:560px;height:480px;display:flex;flex-direction:column;justify-content:center}}
.n{{font-family:K;color:#111}} .n span{{font-size:.7em}} .st{{position:absolute;right:30px;top:250px;width:560px}}
</style></head><body>{''.join(conf)}<h1>New to Team NOP</h1><div class="sub">(since the last issue!)</div>
<div class="names">{names}</div><img class="st" src="file://{os.path.abspath(work)}/sticker.png"></body></html>'''
    open(f'{work}/newteam.html', 'w').write(page)
    shot(f'{work}/newteam.html', f'{work}/newteam.png')

def to_jpg(src, dst, w):
    im = Image.open(src).convert('RGB')
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(dst, quality=85, optimize=True)

# ---------------------------------------------------------------- email
def h2(t):
    return (f'<tr><td style="padding:26px 28px 8px;font-family:Arial,Helvetica,sans-serif;"><div style="font-size:20px;font-weight:bold;'
            f'color:{NAVY};border-bottom:3px solid {TEAL};padding-bottom:6px;">{t}</div></td></tr>')

def p(t, extra=''):
    return f'<tr><td style="padding:6px 28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.55;color:#222;{extra}">{t}</td></tr>'

def img(key, w, src, alt, href=None, pad='14px 28px'):
    tag = f'<img src="{src(key)}" width="{w}" alt="{html.escape(alt)}" style="display:block;width:{w}px;max-width:100%;height:auto;border:0;margin:0 auto;">'
    if href:
        tag = f'<a href="{href}">{tag}</a>'
    return f'<tr><td align="center" style="padding:{pad};">{tag}</td></tr>'

def side(key, w, src, alt, right_html, href=None):
    tag = f'<img src="{src(key)}" width="{w}" alt="{html.escape(alt)}" style="display:block;width:{w}px;height:auto;border:0;">'
    if href:
        tag = f'<a href="{href}">{tag}</a>'
    return (f'<tr><td style="padding:8px 28px;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td width="{w + 10}" valign="top">{tag}</td>'
            f'<td valign="middle" style="padding-left:18px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.55;color:#222;">{right_html}</td></tr></table></td></tr>')

def email(c, order, src):
    R = [img('banner', 640, src, 'Team NOP News', pad='0'),
         f'<tr><td bgcolor="{NAVY}" align="center" style="background-color:{NAVY};padding:9px;font-family:Arial,Helvetica,sans-serif;">'
         f'<font color="#ffffff" style="font-size:14px;letter-spacing:1px;"><b>TEAM NOP WEEKLY</b> &nbsp;|&nbsp; {c["date_long"]}</font></td></tr>']
    for i, para in enumerate(c['hello']):
        R.append(p(para, 'padding-top:22px;font-size:16px;font-weight:bold;' if i == 0 else ''))
    for item in c.get('news', []):
        R.append(h2(f"{item.get('emoji', '')} {item['title']}".strip()))
        for para in item['html']:
            R.append(p(para))
    if 'newteam' in order:
        R.append(h2('&#127881; New to Team NOP'))
        alt = 'New to Team NOP: ' + ', '.join(f"{x['name']}, {x['specialty']}" for x in c['new_people']) + '. Welcome to the team!'
        R.append(img('newteam', 584, src, alt, pad='8px 28px 4px'))
        R.append(p(c['welcome'], 'text-align:center;'))
    R.append(img('roster', 584, src, 'Team NOP Current Roster: ' + ', '.join(f"{x['name']} {x['specialty']}" for x in c['roster'])))
    R.append(img('map', 584, src, 'Where is Team NOP right now?'))
    R.append(p(c['map_line'], 'text-align:center;'))
    if c.get('birthdays'):
        R.append(h2('&#127874; Upcoming Birthdays'))
        lines = '<br>'.join(f"<b>{html.escape(b['name'])}</b> - {html.escape(b['date'])}" for b in c['birthdays'])
        R.append(side('bday', 220, src, 'Happy Birthday', f'<span style="font-size:17px;line-height:1.8;">{lines}</span>'))
    R.append(img('tips', 560, src, 'Helpful Tips: time entry due Sunday at noon, missed break notes, BCBS digital cards, call me if you have not heard back', pad='26px 28px 10px'))
    R.append(h2('&#128153; You Always Have EAP'))
    R.append(side('eap', 240, src, 'HealthCare EAP 800-225-2527 or 800-252-4555',
                  'Whether or not you&rsquo;re on our health insurance, <b>everyone</b> has access to EAP. It helps with professional <i>or</i> personal stuff. '
                  'It&rsquo;s 100% confidential and there&rsquo;s no cost to you. If you need to talk to someone about anything, please call them.'
                  '<br><br><b>800-225-2527</b> or <b>800-252-4555</b>'))
    R.append(h2('&#128279; Team NOP Hub'))
    R.append(side('hub', 180, src, 'Team NOP Traveler Hub',
                  f'Looking for an Atlas link? Benefits, Traveler Portal, time entry? It&rsquo;s all in one place at the '
                  f'<a href="{HUB_URL}" style="color:{NAVY};font-weight:bold;">Team NOP Hub</a>.', href=HUB_URL))
    R.append(img('signoff', 520, src, 'As always, thank you for allowing me to be a part of your professional and personal journey. Have a wonderful week! Kristin', pad='26px 28px 30px'))
    return ('<div style="background:#EEF6F8;padding:0;margin:0;"><table width="640" align="center" cellpadding="0" cellspacing="0" '
            'style="width:640px;max-width:640px;background:#ffffff;border-collapse:collapse;">' + ''.join(R) + '</table></div>')

def build(content_path, assets, out):
    c = json.load(open(content_path))
    work = os.path.join(out, 'work')
    img_dir = os.path.join(out, 'img')
    os.makedirs(work, exist_ok=True); os.makedirs(img_dir, exist_ok=True)
    render_roster(c, work)
    render_map(c, work)
    order = ['banner']
    if c.get('new_people'):
        render_newteam(c, assets, work); order.append('newteam')
    order += ['roster', 'map']
    if c.get('birthdays'):
        order.append('bday')
    order += ['tips', 'eap', 'hub', 'signoff']
    srcs = {'banner': (f'{assets}/banner.png', 1280), 'newteam': (f'{work}/newteam.png', 1200), 'roster': (f'{work}/roster.png', 1200),
            'map': (f'{work}/map.png', 1200), 'bday': (f'{assets}/bday.png', 600), 'tips': (f'{assets}/tips.jpg', 800),
            'eap': (f'{assets}/eap.png', 800), 'hub': (f'{assets}/hub.png', 600), 'signoff': (f'{assets}/signoff.jpg', 800)}
    for k in order:
        to_jpg(srcs[k][0], f'{img_dir}/{k}.jpg', srcs[k][1])
    cid = {k: f'cid:att{i}' for i, k in enumerate(order)}
    body = email(c, order, lambda k: cid[k])
    bad = [ch for ch in ('—', '–', '&mdash;', '&ndash;') if ch in body]
    if bad:
        sys.exit(f'BUILD FAILED: dash characters found {bad}. Replace with " - " or commas.')
    open(f'{out}/email.html', 'w').write(body)
    open(f'{out}/preview.html', 'w').write('<!doctype html><meta charset="utf-8"><body style="margin:0">' + email(c, order, lambda k: f'img/{k}.jpg'))
    man = []
    for i, k in enumerate(order):
        path = os.path.abspath(f'{img_dir}/{k}.jpg')
        man.append({'cid': f'att{i}', 'filename': f'{k}.jpg', 'mimeType': 'image/jpeg', 'inline': True,
                    'content': 'sha256:' + hashlib.sha256(open(path, 'rb').read()).hexdigest() + ':' + path})
    json.dump(man, open(f'{out}/manifest.json', 'w'), indent=1)
    shot(f'{out}/preview.html', f'{out}/shot.png', 700, 4600)
    print('BUILD OK. images:', order)

if __name__ == '__main__':
    if sys.argv[1] == 'desk':
        desk(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'build':
        build(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
