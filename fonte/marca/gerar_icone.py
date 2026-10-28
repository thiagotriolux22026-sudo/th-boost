"""Gera "Th Boost.ico" (varios tamanhos) a partir do desenho em emblema.py, usando o Chromium do Playwright."""
import asyncio, struct, sys, io, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emblema import icone
from playwright.async_api import async_playwright
from PIL import Image
TAMANHOS = [16, 24, 32, 48, 64, 128, 256]
async def renderizar():
    res = {}
    async with async_playwright() as pw:
        import os as _o
        b = await pw.chromium.launch(executable_path='/opt/pw-browsers/chromium') if _o.path.exists('/opt/pw-browsers/chromium') else await pw.chromium.launch()
        for t in TAMANHOS:
            svg = icone(simples=t <= 32)
            pg = await b.new_page(viewport={'width': t, 'height': t})
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg width=\'{t}\' height=\'{t}\' ", 1)}</body></html>')
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
destino = sys.argv[1]
montar_ico(pngs, destino)
# conferência: abre o .ico de volta e monta uma folha de prévia
ico = Image.open(destino); print('tamanhos no .ico:', sorted(ico.info.get('sizes', [])))
folha = Image.new('RGBA', (256 + 128 + 64 + 48 + 32 + 24 + 16 + 8 * 8, 270), (30, 32, 38, 255)); x = 8
for t in sorted(pngs, reverse=True):
    im = Image.open(io.BytesIO(pngs[t])).convert('RGBA'); folha.alpha_composite(im, (x, 8)); x += t + 8
folha.save(sys.argv[2])
