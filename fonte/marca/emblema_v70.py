"""Desenho do emblema Th (metal cromado dentro de um anel azul neon). Usado pela interface e pelo icone."""

# letras "TH" (H maiúsculo) em traços (caixa 100x100, centro em 50,50)
GLIFO = "M24 32H45M34.5 32V68M57 32V68M76 32V68M57 50H76"


def defs(n, glow=True):
    return f'''<defs>
<linearGradient id="gC{n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".36" stop-color="#d3ddee"/><stop offset=".5" stop-color="#8896b2"/><stop offset=".56" stop-color="#e8effb"/><stop offset="1" stop-color="#a3b1c9"/></linearGradient>
<radialGradient id="gF{n}" cx=".5" cy=".4" r=".62"><stop offset="0" stop-color="#16295a"/><stop offset="1" stop-color="#050813"/></radialGradient>
<linearGradient id="gA{n}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9bd2ff"/><stop offset=".5" stop-color="#2e80ff"/><stop offset="1" stop-color="#1239b8"/></linearGradient>
{f'<filter id="fB{n}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.4"/></filter>' if glow else ''}
</defs>'''


def letras(n, glow=True, larg=8.5, escala=0.9):
    t = f'translate(50 50) scale({escala}) translate(-50 -50)'
    g = (f'<path d="{GLIFO}" stroke="#2e80ff" stroke-width="{larg+4}" filter="url(#fB{n})" opacity=".85"/>' if glow else '')
    return (f'<g fill="none" stroke-linecap="round" stroke-linejoin="round" transform="{t}">{g}'
            f'<path d="{GLIFO}" stroke="#06112c" stroke-width="{larg+2.6}"/>'
            f'<path d="{GLIFO}" stroke="url(#gC{n})" stroke-width="{larg}"/></g>')


def emblema_animado():
    """Versão da interface: o anel gira (classes .orb e .orb2 ficam no CSS). {n} vira um número por instância."""
    n = "{n}"
    return (f'<svg viewBox="0 0 100 100">{defs(n)}'
            f'<circle cx="50" cy="50" r="46" fill="url(#gF{n})"/>'
            f'<circle cx="50" cy="50" r="44" fill="none" stroke="#0e2a63" stroke-width="3"/>'
            f'<circle cx="50" cy="50" r="44" fill="none" stroke="#2e80ff" stroke-width="1.1" opacity=".6"/>'
            f'<g class="orb"><circle cx="50" cy="50" r="44" fill="none" stroke="#2e80ff" stroke-width="8" stroke-linecap="round" stroke-dasharray="78 199" filter="url(#fB{n})" opacity=".9"/>'
            f'<circle cx="50" cy="50" r="44" fill="none" stroke="url(#gA{n})" stroke-width="4" stroke-linecap="round" stroke-dasharray="78 199"/></g>'
            f'<g class="orb2"><circle cx="50" cy="50" r="36" fill="none" stroke="#cfe3ff" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="26 200"/></g>'
            f'{letras(n)}</svg>')


def icone(simples=False):
    """Ícone quadrado (arquivo .ico e favicon). simples=True tira brilhos que somem em tamanhos pequenos."""
    n = "i"
    ring = 5.2 if not simples else 7.5
    larg = 8.5 if not simples else 10.5
    glow = not simples
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{defs(n, glow)}'
            f'<rect x="1.5" y="1.5" width="97" height="97" rx="22" fill="url(#gF{n})" stroke="#1b3f8f" stroke-width="1.6"/>'
            + (f'<circle cx="50" cy="50" r="40" fill="none" stroke="#2e80ff" stroke-width="9" filter="url(#fB{n})" opacity=".85"/>' if glow else '')
            + f'<circle cx="50" cy="50" r="40" fill="none" stroke="url(#gA{n})" stroke-width="{ring}"/>'
            + (f'<path d="M15.4 30A40 40 0 0 1 36.3 12.4" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" opacity=".6"/>' if glow else '')
            + f'{letras(n, glow, larg, 0.84 if not simples else 0.88)}</svg>')


if __name__ == "__main__":
    import sys
    open(sys.argv[1], "w", encoding="utf-8").write(icone())
