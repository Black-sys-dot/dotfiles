#!/usr/bin/env python3
"""Two-column fastfetch for kitty, with per-line image icons.

fastfetch cannot lay modules out in columns, so this runs fastfetch for the data
and lays the result out itself: 4x2-cell icons on the left of each entry,
two balanced columns, one blank row per entry (the icon spans two rows).

Fallback: in a terminal without the kitty graphics protocol it just prints the
same text without the images.
"""

import base64
import os
import re
import subprocess
import sys

HOME = os.path.expanduser('~')
CFG = os.path.join(HOME, '.config/fastfetch')
ICONS = os.path.join(CFG, 'icons')
LOGO = os.path.join(CFG, 'logo.png')

ESC = '\x1b'
SEP = '\x01'

LOGO_CELLS = 34        # logo footprint in cells (aspect-matched to logo.png)
LOGO_ROWS = 40
LOGO_GAP = 4           # logo -> table
ICON_COLS = 6
ICON_ROWS = 3
COL_GAP = 8            # left column -> right column
LOGO_SHIFT = 4         # nudge the artwork left of the centred block
MIN_MARGIN = 2         # left margin when the composition is centred

STRUCTURE = ('title:separator:os:host:kernel:uptime:packages:shell:display:de:wm:'
             'wmtheme:theme:icons:font:cursor:terminal:terminalfont:cpu:gpu:'
             'memory:swap:disk:localip:battery:locale:colors')

KEY_ICON = {
    'os': 'os', 'host': 'host', 'kernel': 'kernel', 'uptime': 'uptime',
    'packages': 'packages', 'shell': 'shell', 'display': 'display',
    'desktop environment': 'de', 'window manager': 'wm', 'wm theme': 'wmtheme',
    'theme': 'theme', 'icons': 'icons', 'font': 'font', 'cursor': 'cursor',
    'terminal': 'terminal', 'terminal font': 'terminalfont', 'cpu': 'gpu2',
    'gpu 1': 'gpu1', 'gpu 2': 'gpu2', 'memory': 'memory', 'swap': 'swap',
    'disk': 'disk', 'local ip': 'localip', 'battery': 'battery',
    'locale': 'locale',
}

ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
GOTO = re.compile(r'\x1b\[\d*G')


def vlen(s):
    return len(ANSI.sub('', s))


def kitty_supported():
    return 'kitty' in os.environ.get('TERM', '') or os.environ.get('KITTY_WINDOW_ID')


def img_escape(idx, path, cols, rows):
    b64 = base64.b64encode(path.encode()).decode()
    return f'{ESC}_Ga=T,f=100,t=f,i={idx},c={cols},r={rows},C=1,q=2;{b64}{ESC}\\'


def collect():
    env = dict(os.environ)
    env.setdefault('COLUMNS', '0')
    out = subprocess.run(
        ['fastfetch', '--logo', 'none', '--key-type', 'string',
         '--separator', SEP, '-s', STRUCTURE],
        capture_output=True, text=True, env=env,
    ).stdout
    lines = [GOTO.sub('', ln).rstrip() for ln in out.split('\n')]
    entries, extras = [], []
    for ln in lines:
        if not ANSI.sub('', ln).strip():
            continue
        if SEP in ln:
            key, val = ln.split(SEP, 1)
            base = ANSI.sub('', key).strip().lower().split(' (')[0]
            entries.append((key.strip(), val.strip(), KEY_ICON.get(base, '')))
        else:
            extras.append(ln.strip())
    return entries, extras


def icon_cell(entry, col, idx, show_images):
    """Drawn on the row above the text so the text sits centred on the icon."""
    if not show_images:
        return ''
    icon = entry[2]
    if not icon:
        return ''
    path = os.path.join(ICONS, icon + '.png')
    if not os.path.exists(path):
        return ''
    return f'{ESC}[{col + 1}G' + img_escape(idx, path, ICON_COLS, ICON_ROWS)


def text_cell(entry, keyw, col, show_images):
    key, val, _ = entry
    return (f'{ESC}[{col + 1}G{ESC}[{ICON_COLS}C' + key +
            ' ' * max(0, keyw - vlen(key)) + ': ' + val)


def term_size():
    try:
        import fcntl, struct, termios
        rows, cols, _, _ = struct.unpack('HHHH', fcntl.ioctl(1, termios.TIOCGWINSZ, b'\0' * 8))
        if rows and cols:
            return rows, cols
    except Exception:
        pass
    return 24, 80


def main():
    images = bool(kitty_supported())
    entries, extras = collect()
    if not entries:
        return 1

    rows_avail, cols_avail = term_size()

    half = (len(entries) + 1) // 2
    left, right = entries[:half], entries[half:]
    lkw = max(vlen(k) for k, _, _ in left)
    rkw = max(vlen(k) for k, _, _ in right) if right else 0
    lmax = max((vlen(v) for _, v, _ in left), default=0)
    rmax = max((vlen(v) for _, v, _ in right), default=0)

    left_width = ICON_COLS + 1 + lkw + 2 + lmax
    right_width = (ICON_COLS + 1 + rkw + 2 + rmax) if right else 0

    def total(gap):
        return LOGO_CELLS + LOGO_GAP + left_width + ((gap + right_width) if right else 0)

    gap = COL_GAP
    if total(gap) > cols_avail - 2 * MIN_MARGIN:
        gap = 2
    if total(gap) > cols_avail - 2 * MIN_MARGIN:
        right = []                     # too narrow for two columns -> single column
        right_width = 0
        gap = 0
    block = total(gap)

    # centre the whole composition
    margin = max(MIN_MARGIN, (cols_avail - block) // 2)
    logo_col = max(MIN_MARGIN, margin - LOGO_SHIFT)
    text_col = margin + LOGO_CELLS + LOGO_GAP
    right_col = text_col + left_width + gap

    # first line: logo (does not move the cursor) + title, side by side
    head = f'{ESC}[{logo_col + 1}G'
    if images and os.path.exists(LOGO):
        head += img_escape(999, LOGO, LOGO_CELLS, LOGO_ROWS)
    if extras:
        head += f'{ESC}[{text_col + 1}G{extras[0]}'

    lines = [head]
    if len(extras) > 1:
        lines.append(f'{ESC}[{text_col + 1}G{extras[1]}')
    lines.append('')

    for i in range(max(len(left), len(right))):
        icons = []
        if i < len(left):
            icons.append(icon_cell(left[i], text_col, i + 1, images))
        if i < len(right):
            icons.append(icon_cell(right[i], right_col, 100 + i, images))
        if images:
            lines.append(''.join(icons))     # icon spans this row + text row + 1

        texts = []
        if i < len(left):
            texts.append(text_cell(left[i], lkw, text_col, images))
        if i < len(right):
            texts.append(text_cell(right[i], rkw, right_col, images))
        lines.append(''.join(texts))
        if images:
            lines.append('')                 # bottom padding row

    for extra in extras[2:]:
        lines.append(f'{ESC}[{text_col + 1}G{extra}')

    sys.stdout.write('\n'.join(lines).rstrip('\n') + '\n')
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        rc = 1
    if rc not in (0, None):
        subprocess.run(['fastfetch'])   # fallback: plain fetch rather than nothing
    sys.exit(0)
