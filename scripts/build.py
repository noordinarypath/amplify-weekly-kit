#!/usr/bin/env python3
"""Amplify Weekly builder.

Usage:  python3 -I scripts/build.py content.json [outdir]

Reads a content JSON (see content_example.json and README.md), generates the
issue banner, renders an Outlook-safe HTML email with inline (cid:) images, and
writes to outdir (default ./out):
  email.html        full HTML email, images as cid:attN
  preview.html      same email, images as relative asset paths (for screenshots)
  manifest.json     subject + ordered inline attachments (filename, path, sha256, mimeType)
Fails loudly if the copy contains em/en dashes or unknown block types/assets.
"""
import sys, os, json, re, hashlib, html
from PIL import Image, ImageDraw, ImageFont

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(KIT, 'assets')
FONT = os.path.join(KIT, 'fonts', 'SpecialElite-Regular.ttf')

NAVY = '#2B558C'; TEAL = '#3BC1C8'; LIGHT = '#E8F4F8'; INK = '#24324A'
BANNER_BLUE = (43, 85, 140)
LINKS = {
    'teams': 'https://teams.microsoft.com/l/chat/19%3Ameeting_YmJkZWRiMTItYTViMC00MTA1LTg1NGYtNDYxMTdiODRmYThh%40thread.v2/conversations?context=%7B%22contextType%22%3A%22chat%22%7D',
    'video_library': 'https://americanmedstaffing.sharepoint.com/sites/AmplifyTipsTricks',
}
F = "font-family:Calibri,'Segoe UI',Arial,sans-serif;"


def make_banner(issue, date, topics, out_path):
    bg = Image.open(os.path.join(ASSETS, 'banner_bg.jpg')).convert('RGBA')
    W, H = bg.size
    box = (int(W * .108), int(H * .17), int(W * .892), int(H * .83))
    d = ImageDraw.Draw(bg)
    d.rectangle(box, fill=BANNER_BLUE + (255,))
    f1 = ImageFont.truetype(FONT, 64)
    topics = [t.upper() for t in topics][:3]
    size2 = 50
    x0, y0, x1, y1 = box
    while size2 > 30:
        f2 = ImageFont.truetype(FONT, size2)
        if all(d.textlength(t, font=f2) <= (x1 - x0 - 112) for t in topics):
            break
        size2 -= 2
    line_h = int(size2 * 1.32)
    content = 78 + 42 + line_h * len(topics)
    ty = y0 + int(((y1 - y0) - content) / 2)
    left_txt = f'ISSUE {issue}'
    d.text((x0 + 48, ty), left_txt, font=f1, fill='white')
    dw = d.textlength(date, font=f1)
    d.text((x1 - 48 - dw, ty), date, font=f1, fill='white')
    env = Image.open(os.path.join(ASSETS, 'envelope.png'))
    l = x0 + 48 + d.textlength(left_txt, font=f1); r = x1 - 48 - dw
    bg.paste(env, (int((l + r) / 2 - env.width / 2), ty - 6), env)
    yy = ty + 120
    for t in topics:
        d.text((x0 + 56, yy), t, font=f2, fill='white'); yy += line_h
    bg.convert('RGB').save(out_path, quality=88)


class Renderer:
    def __init__(self, mode, banner_file):
        self.mode = mode; self.order = []; self.banner_file = banner_file

    def src(self, f):
        if self.mode == 'preview':
            return f if f == self.banner_file else os.path.join(ASSETS, f)
        if f not in self.order:
            self.order.append(f)
        return 'cid:att%d' % self.order.index(f)

    def img(self, f, w, alt='', center=True, link=None):
        if f != self.banner_file and not os.path.exists(os.path.join(ASSETS, f)):
            raise SystemExit(f'Unknown asset: {f}')
        t = (f'<img src="{self.src(f)}" width="{w}" alt="{html.escape(alt)}" style="display:block;width:{w}px;'
             f'max-width:100%;height:auto;border:0;outline:none;text-decoration:none;' + ('margin:0 auto;' if center else '') + '">')
        return f'<a href="{link}" style="text-decoration:none;">{t}</a>' if link else t

    # primitives
    def p(self, t, extra=''):
        return f'<p style="{F}font-size:15px;line-height:1.55;color:{INK};margin:0 0 10px;{extra}">{t}</p>'

    def ul(self, items, margin='0 0 10px', color=INK):
        lis = ''.join(f'<li style="margin:0 0 7px;">{i}</li>' for i in items)
        return f'<ul style="{F}font-size:15px;line-height:1.5;color:{color};margin:{margin};padding-left:22px;">{lis}</ul>'

    def box(self, inner, bg, border=None):
        b = f'border:2px solid {border};' if border else ''
        return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                f'<td bgcolor="{bg}" style="background:{bg};{b}border-radius:10px;padding:16px 18px;">{inner}</td></tr></table>')

    def icon_row(self, icon, w, inner):
        return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                f'<td width="{w + 16}" valign="top" style="width:{w + 16}px;padding:2px 16px 0 0;">{self.img(icon, w, center=False)}</td>'
                f'<td valign="top">{inner}</td></tr></table>')

    def row(self, inner, pad='18px 32px 0'):
        return f'<tr><td style="padding:{pad};">{inner}</td></tr>'

    # blocks
    def block(self, b):
        t = b['type']
        if t == 'intro':
            return self.row(self.p(b['text']), '24px 32px 0')
        if t == 'divider':
            return self.row(f'<div style="border-top:2px solid {LIGHT};font-size:0;line-height:0;">&nbsp;</div>', '24px 32px 0')
        if t == 'section_header':
            title = f'<div style="{F}font-size:22px;font-weight:bold;color:{NAVY};margin:4px 0 2px;">{b["title"]}</div>'
            sub = self.p(b['subtitle'], 'margin:0;') if b.get('subtitle') else ''
            inner = self.icon_row(b['icon'], b.get('icon_width', 48), title + sub) if b.get('icon') else title + sub
            return self.row(inner, '22px 32px 0')
        if t == 'graphic':
            cap = self.p(f'<strong style="color:{NAVY};">{b["caption"]}</strong>', 'text-align:center;margin:12px 0 0;') if b.get('caption') else ''
            return self.row(self.img(b['asset'], b.get('width', 260), b.get('alt', '')) + cap, '22px 32px 0')
        if t == 'subhead':
            return self.row(f'<div style="{F}font-size:17px;font-weight:bold;color:{INK};margin:0;">{b["text"]}</div>', '14px 32px 0')
        if t == 'paragraph':
            return self.row(self.p(b['text'], 'margin:0;'), '8px 32px 0')
        if t == 'bullets':
            return self.row(self.ul(b['items'], '0'), '8px 32px 0')
        if t == 'box_bullets':
            return self.row(self.box(self.ul(b['items'], '0'), LIGHT), '12px 32px 0')
        if t == 'prompt':
            return self.row(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                            f'<td bgcolor="{LIGHT}" style="background:{LIGHT};border-left:5px solid {NAVY};padding:12px 16px;'
                            f'{F}font-size:15px;line-height:1.5;color:{INK};font-style:italic;">&ldquo;{b["text"]}&rdquo;</td></tr></table>', '10px 32px 0')
        if t == 'callout':
            styles = {'warning': ('#FFF4E0', '#F2B66D', '#8A4B12', INK),
                      'info': ('#FFFFFF', TEAL, NAVY, INK),
                      'navy': (NAVY, None, '#FFFFFF', '#FFFFFF'),
                      'teal': (TEAL, None, '#FFFFFF', '#FFFFFF')}
            bg, border, tc, bc = styles[b.get('style', 'info')]
            title = f'<div style="{F}font-size:17px;font-weight:bold;color:{tc};margin:0 0 6px;">{b["title"]}</div>' if b.get('title') else ''
            text = f'<p style="{F}font-size:15px;line-height:1.55;color:{bc};margin:0;">{b["text"]}</p>'
            return self.row(self.box(title + text, bg, border), '14px 32px 0')
        if t == 'icon_card':
            inner = (f'<div style="{F}font-size:17px;font-weight:bold;color:{INK};margin:0 0 4px;">{b["title"]}</div>'
                     + self.p(b['text'], 'margin:0;'))
            return self.row(self.icon_row(b['icon'], b.get('icon_width', 64), inner), '16px 32px 0')
        if t == 'try_it':
            inner = (f'<div style="{F}font-size:17px;font-weight:bold;color:{NAVY};margin:2px 0 6px;">{b.get("title", "Try it this week")}</div>'
                     + self.ul(b['items'], '0'))
            return self.row(self.box(self.icon_row('practice.png', 130, inner), '#FFFFFF', '#CFE6EE'), '16px 32px 0')
        if t == 'rising_tide':
            return (f'<tr><td style="padding:26px 0 0;">{self.img("risingtide.jpg", 640, "The Rising Tide: your tips and discoveries help lift us all")}</td></tr>'
                    + self.row(self.ul(b['items'], '0'), '18px 32px 0'))
        if t == 'win':
            return self.block({'type': 'callout', 'style': 'navy', 'title': b.get('title', '&#127881; Win of the Week'), 'text': b['text']}).replace('14px 32px 0', '20px 32px 0')
        if t == 'next_open_lab':
            return self.row(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                            f'<td bgcolor="{TEAL}" style="background:{TEAL};border-radius:10px;padding:14px 18px;{F}font-size:16px;'
                            f'line-height:1.5;color:#FFFFFF;text-align:center;"><strong>{b["title"]}</strong><br>{b["text"]}</td></tr></table>', '18px 32px 0')
        raise SystemExit(f'Unknown block type: {t}')

    def footer(self):
        teams = self.img('openlab.png', 150, 'Amplify Open Lab Teams chat', link=LINKS['teams'])
        vid = self.img('videolib.png', 150, 'Video Library', link=LINKS['video_library'])
        return (self.row(self.p('Questions, or something you want covered? Drop it in the Amplify Teams chat or bring it to Open Lab.', 'text-align:center;margin-bottom:12px;')
                         + f'<table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;"><tr>'
                         f'<td align="center" style="padding:0 18px;">{teams}</td><td align="center" style="padding:0 18px;">{vid}</td></tr></table>', '26px 32px 0')
                + self.row(self.img('atlas.png', 150, 'Atlas MedStaff') + self.p('-- Kristin', 'text-align:center;margin:8px 0 0;color:#5B6B80;'), '22px 32px 28px'))

    def render(self, c):
        rows = [f'<tr><td style="padding:0;">{self.img(self.banner_file, 640, "Amplify Weekly Issue " + str(c["issue"]) + ": " + ", ".join(c["topics"]))}</td></tr>']
        rows += [self.block(b) for b in c['blocks']]
        rows.append(self.footer())
        inner = ''.join(rows)
        return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;"><tr><td align="center" style="padding:0;">'
                f'<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:640px;background:#FFFFFF;">{inner}</table></td></tr></table>')


def main():
    content_path = sys.argv[1]
    out = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'out')
    os.makedirs(out, exist_ok=True)
    c = json.load(open(content_path))
    raw = json.dumps(c, ensure_ascii=False)
    bad = re.findall('[—–]|&mdash;|&ndash;', raw)
    if bad:
        raise SystemExit(f'Copy contains {len(bad)} em/en dash(es). Replace with " -- ".')
    banner = os.path.join(out, 'issue_banner.jpg')
    make_banner(c['issue'], c['date'], c['topics'], banner)
    em = Renderer('email', banner)
    body = em.render(c)
    pv = Renderer('preview', banner).render(c)
    page = lambda b: f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html.escape(c["subject"])}</title></head><body style="margin:0;padding:0;background:#FFFFFF;">{b}</body></html>'
    open(os.path.join(out, 'email.html'), 'w').write(page(body))
    open(os.path.join(out, 'preview.html'), 'w').write(page(pv))
    atts = []
    for f in em.order:
        p = f if os.path.isabs(f) else os.path.join(ASSETS, f)
        atts.append({'filename': os.path.basename(p), 'path': p,
                     'sha256': hashlib.sha256(open(p, 'rb').read()).hexdigest(),
                     'mimeType': 'image/jpeg' if p.endswith('.jpg') else 'image/png'})
    json.dump({'subject': c['subject'], 'attachments': atts}, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print('OK', out)
    for i, a in enumerate(atts):
        print(f'att{i}: sha256:{a["sha256"]}:{a["path"]}  ({a["mimeType"]})')


if __name__ == '__main__':
    main()
