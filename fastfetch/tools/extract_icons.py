import re, os, subprocess

import sys
SHEET = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/Downloads/Kawaii Anime System Monitor Icon Sheet.png')
OUT = os.path.expanduser('~/.config/fastfetch/icons')
os.makedirs(OUT, exist_ok=True)

names = ['os', 'host', 'kernel', 'uptime', 'packages', 'shell',
         'display', 'de', 'wm', 'wmtheme', 'theme', 'icons',
         'font', 'cursor', 'terminal', 'terminalfont', 'gpu1', 'gpu2',
         'memory', 'swap', 'disk', 'localip', 'battery', 'locale']

comps = []
_cc = subprocess.run(
    ['magick', SHEET, '-background', 'white', '-alpha', 'remove', '-alpha', 'off',
     '-colorspace', 'Gray', '-threshold', '94%',
     '-define', 'connected-components:verbose=true',
     '-define', 'connected-components:area-threshold=1000',
     '-connected-components', '8', 'null:'],
    capture_output=True, text=True)
_cc = (_cc.stderr or '') + (_cc.stdout or '')
for line in _cc.splitlines():
    line = line.strip()
    if not line:
        continue
    m = re.match(r'^(\d+): (\d+)x(\d+)\+(\d+)\+(\d+) ([\d.]+),([\d.]+) (\d+) (.*)$', line)
    if not m:
        continue
    cid, w, h, x, y, cx, cy, area, color = m.groups()
    if color == 'gray(255)' and int(area) > 200000:
        continue  # background
    comps.append(dict(id=int(cid), w=int(w), h=int(h), x=int(x), y=int(y),
                      cx=float(cx), cy=float(cy), area=int(area)))

W, H = 1347, 1168
cw, ch = W / 6.0, H / 4.0
report = []
for r in range(4):
    for c in range(6):
        x0, x1 = c * cw, (c + 1) * cw
        y0, y1 = r * ch, (r + 1) * ch
        in_cell = [p for p in comps
                   if x0 <= p['cx'] < x1 and y0 <= p['cy'] < y1]
        # art = biggest component in the cell; captions are small text (~<1200 px)
        art = max(in_cell, key=lambda p: p['area'])
        name = names[r * 6 + c]
        report.append((r, c, name, art))

print(f"{'cell':8} {'name':12} {'bbox':28} {'area':>7}  cw x ch")
for r, c, name, a in report:
    print(f"r{r}c{c:<6} {name:12} {a['w']}x{a['h']}+{a['x']}+{a['y']:<12} {a['area']:>7}")

for r, c, name, a in report:
    m = 2
    x = a['x'] - m
    y = a['y'] - m
    w = a['w'] + 2 * m
    h = a['h'] + 2 * m
    out = os.path.join(OUT, f'{name}.png')
    # normalise aspect so every icon reads the same size in the cell box
    crop = []
    aspect = w / h
    target = 216 / 240.0          # exact cell-box aspect -> every icon fills it
    if aspect > target:
        nw = max(1, int(round(h * target)))
        crop = ['-gravity', 'center', '-crop', f'{nw}x{h}+0+0', '+repage']
    elif aspect < target:
        nh = max(1, int(round(w / target)))
        crop = ['-gravity', 'center', '-crop', f'{w}x{nh}+0+0', '+repage']
    cmd = ['magick', SHEET, '-crop', f'{w}x{h}+{x}+{y}', '+repage'] + crop + [
           '-resize', '212x236',
           '-background', 'none', '-gravity', 'center', '-extent', '216x240',
           '-background', 'black', '-alpha', 'background',
           '-strip',
           out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print('FAIL', name, p.stderr[:300])
print('--- done, files:', len(os.listdir(OUT)))
