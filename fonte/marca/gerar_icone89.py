"""v8.9: gera "Th Boost.ico" (varios tamanhos) com o emblema novo (T em 3D, preto e azul), o mesmo da interface (ui.html, const EMB)."""
import asyncio, struct, sys, io, os, re
from playwright.async_api import async_playwright
from PIL import Image
UI = '/home/claude/totimize/src/ui.html'
TAMANHOS = [16, 24, 32, 48, 64, 128, 256]
s = open(UI, encoding='utf-8').read()
i0 = s.index('const EMB=`') + len('const EMB=`'); i1 = s.index('`;', i0)
EMB = s[i0:i1].replace('{n}', 'i').replace(' class="orb"', '').replace(' class="orb2"', '')
def icone(simples):
    svg = EMB
    if simples:  # pequeno: sem brilho borrado, sem anel fino e sem faiscas, para o T ficar nitido
        svg = re.sub(r'<circle[^>]*filter="url\(#fBi\)"[^>]*/>', '', svg)
        svg = re.sub(r'<path[^>]*filter="url\(#fBi\)"[^>]*/>', '', svg)
        svg = re.sub(r'<g><circle cx="50" cy="50" r="35"[^>]*/></g>', '', svg)
        svg = re.sub(r'<path d="M(95 5|5 95)[^"]*" fill="url\(#gS[12]i\)"/>', '', svg)
    return svg
async def renderizar():
    res = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for t in TAMANHOS:
            svg = icone(simples=t <= 32)
            pg = await b.new_page(viewport={'width': t, 'height': t})
            await pg.set_content('<html><body style="margin:0;background:transparent">' + svg.replace('<svg ', f"<svg width='{t}' height='{t}' ", 1) + '</body></html>')
            await pg.wait_for_timeout(120)
            res[t] = await pg.screenshot(omit_background=True, clip={'x': 0, 'y': 0, 'width': t, 'height': t})
            await pg.close()
        await b.close()
    return res
def montar_ico(pngs, destino):
    n = len(pngs); dados = b''; entradas = b''; off = 6 + 16 * n
    for t, png in sorted(pngs.items()):
        entradas += struct.pack('<BBBBHHII', t % 256, t % 256, 0, 0, 1, 32, len(png), off)
        dados += png; off += len(png)
    open(destino, 'wb').write(struct.pack('<HHH', 0, 1, n) + entradas + dados)
pngs = asyncio.run(renderizar())
montar_ico(pngs, sys.argv[1])
ico = Image.open(sys.argv[1]); print('tamanhos no .ico:', sorted(ico.info.get('sizes', [])))
folha = Image.new('RGBA', (256 + 128 + 64 + 48 + 32 + 24 + 16 + 8 * 8, 270), (238, 240, 244, 255)); x = 8
for t in sorted(pngs, reverse=True):
    im = Image.open(io.BytesIO(pngs[t])).convert('RGBA'); folha.alpha_composite(im, (x, 8)); x += t + 8
escura = Image.new('RGBA', folha.size, (24, 26, 32, 255)); x = 8
for t in sorted(pngs, reverse=True):
    im = Image.open(io.BytesIO(pngs[t])).convert('RGBA'); escura.alpha_composite(im, (x, 8)); x += t + 8
junta = Image.new('RGBA', (folha.width, 540)); junta.paste(folha, (0, 0)); junta.paste(escura, (0, 270)); junta.save(sys.argv[2])
