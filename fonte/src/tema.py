# ---------------- v9.2: cor do painel ----------------
# O painel inteiro (botões, destaques, gráficos, logo e degradês) é azul por padrão. "Cor do painel" gira o tom de todas
# essas cores juntas (no espaço OKLCH, que guarda o brilho que o olho vê: o texto continua legível em qualquer cor).
# Verde, amarelo e vermelho de aviso e os cinzas não mudam. A escolha fica em CONFIG["tema_tr"] (graus, -180 a 180).

TEMA_CORES = (("azul", "Azul", 0), ("ciano", "Ciano", -45), ("verde", "Verde", -107), ("dourado", "Dourado", -171),
              ("laranja", "Laranja", 151), ("vermelho", "Vermelho", 128), ("rosa", "Rosa", 97), ("roxo", "Roxo", 47))


def tema_valida(v):
    """Graus do giro, de -180 a 180 (inteiro), ou None se não for um número. Função pura."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        return None
    v = int(round(v)) % 360
    return v - 360 if v > 180 else v


def tema_tr():
    v = tema_valida(CONFIG.get("tema_tr"))
    return v or 0


def _rgb_linear(L, A, B):
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def _croma_max(L, h):
    """A cor mais forte que a tela mostra neste brilho e neste tom (OKLCH)."""
    lo, hi = 0.0, 0.4
    for _ in range(22):
        c = (lo + hi) / 2
        if all(-1e-6 <= x <= 1 + 1e-6 for x in _rgb_linear(L, c * math.cos(h), c * math.sin(h))):
            lo = c
        else:
            hi = c
    return lo


TEMA_L0, TEMA_H0 = 0.638, math.radians(256.9)  # o azul do painel (#3389fa)


def tema_tc(tr):
    """v9.6: quanto as cores ficam mais fortes no tom escolhido. O azul do painel já está no máximo que a tela mostra;
    vermelho, rosa e roxo aceitam bem mais. Sem isso, o vermelho ficava "clarinho". 1 = igual ao azul. Função pura."""
    tr = tema_valida(tr) or 0
    if not tr:
        return 1.0
    r = _croma_max(TEMA_L0, TEMA_H0 + math.radians(tr)) / _croma_max(TEMA_L0, TEMA_H0)
    return round(max(1.0, min(1.4, r)), 3)


def html_com_tema(html):
    """A página já chega com a cor escolhida (sem piscar azul ao abrir)."""
    tr = tema_tr()
    if not tr:
        return html
    tc = tema_tc(tr)
    extra = f";--tc:{tc:g}" if tc != 1 else ""
    return html.replace('<html lang="pt-BR">', f'<html lang="pt-BR" style="--tr:{tr}deg{extra}">', 1)


def _oklab(r, g, b):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _srgb(L, A, B):
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)

    def gam(c):
        c = min(1.0, max(0.0, c))
        return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(gam(c) for c in rgb)


def tom_hex(cor, tr):
    """Gira o tom de uma cor '#rrggbb' (igual ao que o painel faz com as cores azuis). Função pura."""
    if not tr or not re.fullmatch(r"#[0-9a-fA-F]{6}", cor or ""):
        return (cor or "").lower()
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    L, A, B = _oklab(r, g, b)
    c, h = math.hypot(A, B) * tema_tc(tr), math.atan2(B, A) + math.radians(tr)
    return "#" + "".join(f"{round(x * 255):02x}" for x in _srgb(L, c * math.cos(h), c * math.sin(h)))
