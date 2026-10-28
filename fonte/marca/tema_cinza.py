"""Tema cinza-azulado (ardosia) do Th Boost: troca o vermelho/carmim do programa pelo cinza #546073.

cinza(texto) recolore cores #rrggbb e rgb()/rgba() que estao na faixa carmim/vermelho (matiz 295-360).
Com tudo=True tambem pega o vermelho puro e o salmao (matiz 0-16), usado no emblema/icone.
Vermelho de ALERTA (matiz 0-16, ex.: #ef4444) fica como esta no resto do programa, para erro continuar vermelho.
Rodar duas vezes nao muda nada (cores ja cinza ficam fora da faixa)."""
import os
import re
import colorsys

# o emblema/ícone só sai em cinza quando o tema cinza é pedido (THBOOST_TEMA=cinza); o padrão é vermelho
ATIVO = os.environ.get("THBOOST_TEMA", "vermelho") == "cinza"

# vermelho de ALERTA (erro, perigo): continua vermelho em qualquer tema
ALERTA = {"#ef4444", "#fca5a5", "#f87171", "#dc2626", "#b91c1c", "#fecaca", "#7f1d1d"}
_ALERTA_RGB = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in ALERTA}

# enfeites laranja/ciano (brilho "fogo" da Extrema) viram tons de ardosia; amarelo/ambar de aviso fica
DECOR = {"#ff8a3d": "#8d9bb3", "#ff7a2d": "#7f8da3", "#ff9a55": "#9aa8bf", "#ffb36b": "#aab6cb",
         "#ffc89a": "#c4ccda", "#ffd0a8": "#c4ccda", "#27e0ff": "#b4c0d4"}

_hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
_DECOR_RGB = {_hexrgb(a): _hexrgb(b) for a, b in DECOR.items()}

ALVO = 217            # matiz da ardosia (#546073 = matiz 217, saturacao 0.156, luz 0.39)
ANCORA_L = 0.59       # luz do vermelho principal (#fa3347) ...
ANCORA_N = 0.39       # ... vira a luz do #546073


def _suave(x, a, b):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mapa(r, g, b, tudo=False):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    h *= 360
    if s < 0.05 or (r, g, b) in _ALERTA_RGB:
        return None
    if not (h >= 295 or (tudo and h <= 16)):
        return None
    w = _suave(s, 0.45, 0.80)                       # 0 = cor neutra/escura, 1 = vermelho vivo
    if l >= ANCORA_L:
        la = ANCORA_N + (1 - ANCORA_N) * (l - ANCORA_L) / (1 - ANCORA_L)
    else:
        la = l * ANCORA_N / ANCORA_L
    l2 = (1 - w) * l + w * la
    s2 = min(0.24, s * (0.85 * (1 - w) + 0.165 * w))
    r2, g2, b2 = colorsys.hls_to_rgb(ALVO / 360, l2, s2)
    return round(r2 * 255), round(g2 * 255), round(b2 * 255)


def cinza(texto, tudo=False):
    n = [0]

    def _hex(m):
        h = m.group(1)
        novo = mapa(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), tudo)
        if novo is None:
            return m.group(0)
        n[0] += 1
        return "#%02x%02x%02x" % novo

    def _rgb(m):
        tri = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        novo = _DECOR_RGB.get(tri) if tudo else None
        if novo is None:
            novo = mapa(tri[0], tri[1], tri[2], tudo)
        if novo is None:
            return m.group(0)
        n[0] += 1
        return "%s%d,%d,%d" % ((m.group(1),) + novo)

    texto = re.sub(r"(?<![\w&#])#([0-9a-fA-F]{6})(?![0-9a-zA-Z])", _hex, texto)
    texto = re.sub(r"(rgba?\(\s*)(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", _rgb, texto)
    for velho, novo in DECOR.items():
        if tudo:
            n[0] += texto.count(velho)
            texto = texto.replace(velho, novo)
    cinza.conta = n[0]
    return texto


if __name__ == "__main__":
    for c in ["#fa3347", "#ff3b47", "#180e0f", "#a58b8e", "#faf4f5", "#8e0c19", "#fd9fa9", "#ef4444", "#ff6b6b", "#0b0607", "#3a2224"]:
        r = mapa(int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), tudo=False)
        print(c, "->", ("#%02x%02x%02x" % r) if r else "(igual)")
