"""Emblema do Th Boost v8: um "T" cromado inclinado, anel vermelho neon e faiscas (estilo logo gamer).
Usado pela interface (animado) e pelo icone (.ico / favicon)."""

# o T (sem inclinar): barra de cima + haste; a inclinacao e feita por transform
T_PATH = "M17 27H83L80.6 41H57.5V75H42.5V41H14.6Z"
INCLINA = "translate(50 50) skewX(-11) translate(-50 -50)"


def defs(n, glow=True):
    return f'''<defs>
<linearGradient id="gC{n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".3" stop-color="#e9eef7"/><stop offset=".47" stop-color="#8e96aa"/><stop offset=".52" stop-color="#f4f6fb"/><stop offset=".8" stop-color="#b9bfce"/><stop offset="1" stop-color="#6f7587"/></linearGradient>
<radialGradient id="gF{n}" cx=".5" cy=".42" r=".66"><stop offset="0" stop-color="#3b0b14"/><stop offset=".6" stop-color="#16060a"/><stop offset="1" stop-color="#070203"/></radialGradient>
<linearGradient id="gA{n}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb1a8"/><stop offset=".45" stop-color="#ff2d3d"/><stop offset="1" stop-color="#9c0f24"/></linearGradient>
<linearGradient id="gS1{n}" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset=".12" stop-color="#ffffff"/><stop offset=".55" stop-color="#ff6b6b"/><stop offset="1" stop-color="#ff2d3d" stop-opacity="0"/></linearGradient>
<linearGradient id="gS2{n}" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset=".12" stop-color="#ffffff"/><stop offset=".55" stop-color="#ff6b6b"/><stop offset="1" stop-color="#ff2d3d" stop-opacity="0"/></linearGradient>
{f'<filter id="fB{n}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.4"/></filter>' if glow else ''}
</defs>'''


def faiscas(n):
    # duas lascas de luz que cortam o anel (canto de cima, a direita, e canto de baixo, a esquerda)
    return (f'<path d="M95 5 L47 40 L50.5 44.5Z" fill="url(#gS1{n})"/>'
            f'<path d="M5 95 L53 60 L49.5 55.5Z" fill="url(#gS2{n})"/>')


def letra(n, glow=True, escala=1.0):
    t = f'translate(50 50) scale({escala}) translate(-50 -50)'
    g = (f'<path d="{T_PATH}" fill="none" stroke="#ff2d3d" stroke-width="5" stroke-linejoin="round" filter="url(#fB{n})" opacity=".85"/>' if glow else '')
    return (f'<g transform="{t}"><g transform="{INCLINA}">{g}'
            f'<path d="{T_PATH}" fill="#1b0508" stroke="#1b0508" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="{T_PATH}" fill="url(#gC{n})" stroke="url(#gC{n})" stroke-width="1" stroke-linejoin="round"/>'
            + ('<path d="M19.5 29.2H80.5" stroke="#ffffff" stroke-width="1.3" stroke-linecap="round" opacity=".9"/>'
               '<path d="M45 45V72" stroke="#ffffff" stroke-width="1" stroke-linecap="round" opacity=".5"/>' if glow else '')
            + '</g></g>')


def emblema_animado():
    """Versao da interface: o anel gira (classes .orb e .orb2 ficam no CSS). {n} vira um numero por instancia."""
    n = "{n}"
    return (f'<svg viewBox="0 0 100 100">{defs(n)}'
            f'<circle cx="50" cy="50" r="46" fill="url(#gF{n})"/>'
            f'<circle cx="50" cy="50" r="43" fill="none" stroke="#5c0f1c" stroke-width="3"/>'
            f'<circle cx="50" cy="50" r="43" fill="none" stroke="#ff3b47" stroke-width="1.4" opacity=".85"/>'
            f'<g class="orb"><circle cx="50" cy="50" r="43" fill="none" stroke="#ff2d3d" stroke-width="8" stroke-linecap="round" stroke-dasharray="78 193" filter="url(#fB{n})" opacity=".9"/>'
            f'<circle cx="50" cy="50" r="43" fill="none" stroke="url(#gA{n})" stroke-width="3.6" stroke-linecap="round" stroke-dasharray="78 193"/></g>'
            f'<g class="orb2"><circle cx="50" cy="50" r="35" fill="none" stroke="#ffd0d0" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="22 198"/></g>'
            f'{faiscas(n)}{letra(n, True, 0.9)}</svg>')


def icone(simples=False):
    """Icone quadrado (arquivo .ico e favicon). simples=True tira brilhos que somem em tamanhos pequenos."""
    n = "i"
    glow = not simples
    ring = 3.4 if not simples else 6.5
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{defs(n, glow)}'
            f'<rect x="1.5" y="1.5" width="97" height="97" rx="22" fill="url(#gF{n})" stroke="#5c0f1c" stroke-width="1.6"/>'
            + (f'<circle cx="50" cy="50" r="40" fill="none" stroke="#ff2d3d" stroke-width="8" filter="url(#fB{n})" opacity=".85"/>' if glow else '')
            + f'<circle cx="50" cy="50" r="40" fill="none" stroke="url(#gA{n})" stroke-width="{ring}"/>'
            + (faiscas(n) if glow else
               '<path d="M92 8 L50 40 L53 44Z" fill="#ffd0d0"/><path d="M8 92 L50 60 L47 56Z" fill="#ffd0d0"/>')
            + f'{letra(n, glow, 0.86 if glow else 0.92)}</svg>')


if __name__ == "__main__":
    import sys
    open(sys.argv[1], "w", encoding="utf-8").write(icone())
