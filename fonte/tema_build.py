# v9.3: "Cor do painel". Na hora de montar o th_boost.py, as cores azuis do ui.html viram cores que giram junto com
# a variável CSS --tr (graus). Com --tr:0deg tudo fica exatamente como antes (azul); trocando --tr o painel inteiro
# muda de cor na hora. Verde, vermelho e amarelo (avisos) e os cinzas não mudam.
import colorsys
import re

COR = re.compile(r'#[0-9a-fA-F]{6}(?![0-9a-zA-Z_-])|rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+%?)\s*)?\)')


def _rgb(m):
    t = m.group(0)
    if t.startswith('#'):
        h = t[1:]
        return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], None
    r, g, b, a = m.group(1), m.group(2), m.group(3), m.group(4)
    return [int(r) / 255, int(g) / 255, int(b) / 255], a


def azul(r, g, b):
    """Da família do azul do painel (inclui o anil/roxo-azulado dos degradês). Cinzas levemente azulados ficam de fora."""
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 188 <= h * 360 <= 265 and (max(r, g, b) - min(r, g, b)) >= 0.12


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklch(r, g, b):
    """sRGB (0..1) -> OKLCH (L 0..1, C, H em graus). O OKLCH guarda o brilho que o olho vê: girar o tom não deixa
    o amarelo claro demais nem o azul escuro demais (o texto continua legível em qualquer cor)."""
    r, g, b = _lin(r), _lin(g), _lin(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    import math
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def css_giro(r, g, b, a=None):
    L, C, H = oklch(r, g, b)
    alfa = '' if a is None else f' / {a}'
    return f'oklch({L:.4f} {C:.4f} calc({H:.2f}deg + var(--tr)){alfa})'


def _troca_css(txt):
    def f(m):
        (r, g, b), a = _rgb(m)
        if not azul(r, g, b):
            return m.group(0)
        if a is not None and a.endswith('%'):
            a = str(float(a[:-1]) / 100)
        return css_giro(r, g, b, a)
    return COR.sub(f, txt)


SVG_ATTR = re.compile(r'\s(stop-color|fill|stroke|flood-color)="(#[0-9a-fA-F]{6})"')


def _troca_tags_svg(s):
    """Atributos de cor do SVG não aceitam var(): passam para style="" (só os azuis)."""
    def tag(m):
        t = m.group(0)
        decl = []

        def at(x):
            (r, g, b), _ = _rgb(re.match(COR, x.group(2)))
            if not azul(r, g, b):
                return x.group(0)
            decl.append(f'{x.group(1)}:{css_giro(r, g, b)}')
            return ''
        t2 = SVG_ATTR.sub(at, t)
        if not decl:
            return t
        if ' style="' in t2:
            return t2.replace(' style="', ' style="' + ';'.join(decl) + ';', 1)
        fim = '/>' if t2.endswith('/>') else '>'
        return t2[:-len(fim)] + f' style="{";".join(decl)}"' + fim
    return re.sub(r'<(?:stop|path|circle|rect|ellipse|line|polyline|polygon|g|text|feFlood|use)\b[^<>]*?/?>', tag, s)


# Cores usadas em JS (canvas, partículas) não aceitam var(): passam pela função tom() na hora de desenhar.
JS_TOM = [
    ("{d:sr.cpu,cor:'#3389fa'}", "{d:sr.cpu,cor:tom('#3389fa')}"),
    ("{d:sr.down,cor:'#3389fa'}", "{d:sr.down,cor:tom('#3389fa')}"),
    ("{d:sr.ram,cor:'#d1e5fe'}", "{d:sr.ram,cor:tom('#d1e5fe')}"),
    ("{d:sr.up,cor:'#d1e5fe'}", "{d:sr.up,cor:tom('#d1e5fe')}"),
    ("c=mmHex(cor)?cor:'#3389fa'", "c=mmHex(cor)?cor:tom('#3389fa')"),
    ("const cor=pick(XPAL[tipo==='burst'?'burst':X.fase]||XPAL.idle);", "const cor=tom(pick(XPAL[tipo==='burst'?'burst':X.fase]||XPAL.idle));"),
]
# Cores em JS que vão parar dentro de CSS (style="--c:..."): viram texto CSS que gira sozinho.
JS_CSS = ["'#493dff'],['Otimização Extrema'", "'#3b88ff'],['Jogos'", "'#3b8cf6'],['Processos'", "'#5cb3f6']]"]


def temar(s):
    # 1) blocos <style>
    s = re.sub(r'(<style[^>]*>)([\s\S]*?)(</style>)', lambda m: m.group(1) + _troca_css(m.group(2)) + m.group(3), s)
    # 2) atributos style="..." (no HTML e nos modelos do JS)
    s = re.sub(r'(\sstyle=")([^"]*)(")', lambda m: m.group(1) + _troca_css(m.group(2)) + m.group(3), s)
    s = re.sub(r"(\sstyle=')([^']*)(')", lambda m: m.group(1) + _troca_css(m.group(2)) + m.group(3), s)
    # 3) cores dos SVG (logo, ícones, degradês)
    s = _troca_tags_svg(s)
    # 4) JS
    for a, b in JS_TOM:
        assert s.count(a) >= 1, a
        s = s.replace(a, b)
    for a in JS_CSS:
        assert s.count(a) == 1, a
        hexa = a[1:8]
        r, g, b = [int(hexa[1:][i:i + 2], 16) / 255 for i in (0, 2, 4)]
        s = s.replace(a, "'" + css_giro(r, g, b) + "'" + a[9:], 1)
    return s


def sobras(s):
    """Azuis que ficaram de fora (para conferir)."""
    out = []
    for m in COR.finditer(s):
        (r, g, b), _ = _rgb(m)
        if azul(r, g, b):
            out.append(s[max(0, m.start() - 70):m.end() + 10].replace('\n', ' '))
    return out
