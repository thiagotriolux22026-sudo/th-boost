# ---------------- mouse: reconhecer a marca e o modelo ----------------
#
# Para cada mouse USB ou Bluetooth o Windows guarda o código do fabricante (VID), o código do produto (PID) e o texto que o
# próprio mouse informa ("G502 HERO Gaming Mouse", por exemplo). O Th Boost só LÊ esses dados e tenta reconhecer a marca e o
# modelo. Nem todo mouse informa o modelo: os sem fio com receptor (Logitech Unifying e Lightspeed, por exemplo) aparecem só
# como "USB Receiver". Nesse caso a pessoa escolhe o modelo à mão e o Th Boost lembra da escolha. Nada é gravado no mouse.
# A imagem é uma ilustração própria do Th Boost (o programa não traz fotos de produtos, que têm dono): cada modelo conhecido tem
# o seu formato, cores, botões laterais, cabo e luz; os outros caem num formato parecido. A pessoa também pode usar a FOTO DELA
# do mouse (um arquivo do computador), que fica guardada só neste PC.

# marca: (cor do destaque na ilustração, é marca de mouse gamer?)
MARCAS_MOUSE = {
    "Logitech": ("#00b8fc", True), "Razer": ("#44d62c", True), "SteelSeries": ("#ff5200", True),
    "Corsair": ("#ffd400", True), "ASUS": ("#ff2d46", True), "HyperX": ("#e4002b", True),
    "Redragon": ("#e11d2e", True), "Glorious": ("#e9e9ee", True), "Zowie": ("#e5202e", True),
    "Cooler Master": ("#a855f7", True), "Roccat": ("#35c0a8", True), "Mad Catz": ("#ff7a00", True),
    "Pulsar": ("#22d3ee", True), "Finalmouse": ("#e9e9ee", True), "Lamzu": ("#f472b6", True),
    "Attack Shark": ("#fb923c", True), "Endgame Gear": ("#facc15", True), "Vaxee": ("#60a5fa", True),
    "Havit": ("#f97316", True), "Fortrek": ("#ef4444", True), "Warrior": ("#ef4444", True), "A4Tech": ("#f43f5e", True),
    "Microsoft": ("#7fba00", False), "Dell": ("#3b82f6", False), "HP": ("#38bdf8", False), "Lenovo": ("#ef4444", False),
    "Genius": ("#f59e0b", False), "Rapoo": ("#34d399", False), "Multilaser": ("#3b82f6", False), "Trust": ("#e5e7eb", False),
}
COR_PADRAO_MOUSE = "#3389fa"  # v8.9: azul do tema (antes vermelho); as marcas continuam com a cor delas

# código do fabricante (VID) -> marca. Só os que são do fabricante mesmo (chips genéricos de OEM ficam de fora).
VID_MARCAS = {"046d": "Logitech", "1532": "Razer", "1038": "SteelSeries", "1b1c": "Corsair", "0b05": "ASUS",
              "045e": "Microsoft", "413c": "Dell", "03f0": "HP", "17ef": "Lenovo", "0458": "Genius", "2516": "Cooler Master",
              "24ae": "Rapoo", "1e7d": "Roccat", "09da": "A4Tech", "0738": "Mad Catz"}

# palavras que aparecem no texto que o mouse informa (a marca ou uma linha famosa dela)
_TOKENS_MARCA = [
    (r"\blogitech\b|\blogi\b|lightspeed|unifying|\bmx (master|anywhere|vertical)\b|"
     r"\bg ?pro\b|\bg(102|203|300s?|304|305|402|502|600|602|603|604|703|900|903)\b", "Logitech"),
    (r"\brazer\b|deathadder|basilisk|lancehead|mamba|\bnaga\b|\bviper\b|orochi|abyssus|diamondback", "Razer"),
    (r"steelseries|\brival ?\d|\bsensei\b|aerox", "SteelSeries"),
    (r"corsair|dark ?core|scimitar|harpoon|ironclaw|nightsword|katar|\bm65\b|\bsabre\b", "Corsair"),
    (r"\basus\b|\brog\b|tuf gaming|gladius|chakram|pugio|spatha|keris", "ASUS"),
    (r"hyperx|pulsefire", "HyperX"), (r"redragon", "Redragon"), (r"glorious|\bmodel [od]\b", "Glorious"),
    (r"zowie|benq", "Zowie"), (r"cooler ?master|\bmm7\d\d\b", "Cooler Master"), (r"roccat|\bkone\b|\bburst\b", "Roccat"),
    (r"mad ?catz", "Mad Catz"), (r"pulsar", "Pulsar"), (r"finalmouse", "Finalmouse"), (r"lamzu", "Lamzu"),
    (r"attack ?shark", "Attack Shark"), (r"endgame", "Endgame Gear"), (r"vaxee", "Vaxee"), (r"havit", "Havit"),
    (r"fortrek", "Fortrek"), (r"warrior", "Warrior"), (r"a4 ?tech|bloody", "A4Tech"),
    (r"intellimouse|sculpt|\bmicrosoft\b", "Microsoft"), (r"\bdell\b", "Dell"), (r"\bhp\b|hewlett", "HP"),
    (r"lenovo", "Lenovo"), (r"genius", "Genius"), (r"rapoo", "Rapoo"), (r"multilaser", "Multilaser"), (r"\btrust\b", "Trust"),
]
_TOKENS_MARCA = [(re.compile(p, re.I), m) for p, m in _TOKENS_MARCA]

# textos que o Windows usa para qualquer mouse: não dizem o modelo
_GENERICOS_MOUSE = ("input device", "entrada usb", "dispositivo de entrada", "hid-compliant", "hid compliant", "compatível com hid",
                    "compativel com hid", "composite", "composto", "usb receiver", "receptor usb", "ps/2", "standard system",
                    "padrão do sistema", "padrao do sistema", "(standard", "human interface", "interface humana", "generic",
                    "genérico", "generico", "unknown", "desconhecido", "usb device", "dispositivo usb", "mouse compat",
                    "dispositivo hid", "hid device")
_RE_VIRTUAL = re.compile(r"virtual|vmware|vbox|parallels|qemu|hyper-v|remote desktop|terminal server|\brdp\b|"
                         r"área de trabalho remota|area de trabalho remota|synthetic", re.I)
_RE_TOUCHPAD = re.compile(r"touchpad|synaptics|\belan(tech)?\b|trackpad|trackpoint|pointing stick|precision touch", re.I)
_RE_RECEPTOR = re.compile(r"receiver|receptor|dongle|unifying|lightspeed|2\.4 ?g", re.I)
_RE_SEMFIO = re.compile(r"wireless|sem fio", re.I)
_RE_VID_USB = re.compile(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", re.I)
_RE_VID_BT = re.compile(r"VID&([0-9A-F]{4})([0-9A-F]{4})_PID&([0-9A-F]{4})", re.I)
_RE_ESPORTIVO = re.compile(r"viper|\bg ?pro\b|superlight|model [od]\b|zowie|\bec[12]\b|\bfk[12]\b|xm1|pulsar|finalmouse|lamzu|"
                           r"attack ?shark|vaxee|\bg(102|203|304|305|403|703)\b|aerox|orochi|harpoon|pulsefire|endgame", re.I)
_RE_ERGONOMICO = re.compile(r"deathadder|g502|g402|g602|g603|g604|g903|rival ?600|scimitar|\bnaga\b|\bkone\b|mx (master|vertical)|"
                            r"mamba|basilisk|nightsword|gladius|chakram|dark ?core|ironclaw|\bm65\b|\bm711\b", re.I)

PS_MOUSE = (
    "$m=@();"
    "foreach($d in @(Get-PnpDevice -Class Mouse -PresentOnly -ErrorAction SilentlyContinue | Select-Object -First 8)){"
    "$c=@();$id=$d.InstanceId;"
    "for($i=0;$i -lt 3 -and $id;$i++){"
    "$p=@{};"
    "foreach($k in @('DEVPKEY_Device_BusReportedDeviceDesc','DEVPKEY_Device_Manufacturer','DEVPKEY_NAME','DEVPKEY_Device_Parent')){"
    "try{$p[$k]=(Get-PnpDeviceProperty -InstanceId $id -KeyName $k -ErrorAction Stop).Data}catch{$p[$k]=$null}};"
    "$c+=@{id=$id;desc=$p['DEVPKEY_Device_BusReportedDeviceDesc'];fab=$p['DEVPKEY_Device_Manufacturer'];nome=$p['DEVPKEY_NAME']};"
    "$id=$p['DEVPKEY_Device_Parent']};"
    "$m+=@{cadeia=$c}};"
    "ConvertTo-Json -Compress -Depth 6 @{mouses=$m}"
)


def nomes_marcas_mouse():
    return sorted(MARCAS_MOUSE)


def _texto_mouse(x, limite=60):
    """Texto vindo do Windows ou da tela: sem caracteres de controle nem < >, uma linha só."""
    if not isinstance(x, str):
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f<>]", " ", x)).strip()[:limite]


def _generico_mouse(t):
    b = t.lower()
    return not t or any(g in b for g in _GENERICOS_MOUSE)


def _limpar_modelo_mouse(texto, marca=""):
    """'Razer DeathAdder V2 Gaming Mouse' -> 'DeathAdder V2'. Devolve '' quando o texto é genérico ou não sobra nada."""
    t = _texto_mouse(texto)
    if _generico_mouse(t):
        return ""
    t = re.sub(r"\(.*?\)", " ", t)
    if marca:
        t = re.sub(r"^\s*" + re.escape(marca) + r"\b[\s\-_:]*", "", t, flags=re.I)
    t = re.sub(r"\b(gaming|game|wireless|wired|optical|usb|hid|compliant|device|mouse|mice|receiver|dongle|bluetooth|"
               r"2\.4 ?g(hz)?)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -_:,.")
    return t[:40] if len(t) >= 2 else ""


def _vid_pid_mouse(ids):
    for i in ids:
        m = _RE_VID_USB.search(i)
        if m:
            return m.group(1).lower(), m.group(2).lower()
    for i in ids:
        m = _RE_VID_BT.search(i)
        if m and m.group(1) == "0002":  # 0002 = código de fabricante da USB-IF; 0001 seria da Bluetooth SIG
            return m.group(2).lower(), m.group(3).lower()
    return "", ""


def _marca_pelos_textos(textos):
    for t in textos:
        for rx, marca in _TOKENS_MARCA:
            if rx.search(t):
                return marca
    return ""


def _entrada_mouse(e):
    """Uma entrada 'mouse' do Windows (com a cadeia de dispositivos pai) -> o que dá para dizer sobre ela."""
    cadeia = _lista(e.get("cadeia")) if isinstance(e, dict) else []
    if not cadeia:
        return None
    ids = [str(c.get("id") or "") for c in cadeia]
    descs = [_texto_mouse(c.get("desc")) for c in cadeia]
    nomes = [_texto_mouse(c.get("nome")) for c in cadeia]
    fabs = [_texto_mouse(c.get("fab")) for c in cadeia]
    todos = [t for t in descs + nomes + fabs if t]
    vid, pid = _vid_pid_mouse(ids)
    usb = any(i.upper().startswith("USB\\") for i in ids)
    bt = any("BTH" in i.upper() for i in ids)
    virtual = vid == "0e0f" or any(_RE_VIRTUAL.search(t) for t in todos) or any(i.upper().startswith(("ROOT\\", "VMBUS")) for i in ids)
    touch = any(_RE_TOUCHPAD.search(t) for t in todos)
    # o texto do produto: o primeiro que não é genérico (o próprio mouse informa; o nome do Windows vem depois)
    produto = next((t for t in descs + nomes if t and not _generico_mouse(t)), "")
    # fabricante só vale se não for o "Microsoft"/"(Standard ...)" que o Windows põe em qualquer mouse
    fab_util = [f for f in fabs if f and not _generico_mouse(f) and f.lower() not in ("microsoft", "microsoft corporation")]
    marca = _marca_pelos_textos([t for t in descs + nomes if t and not _generico_mouse(t)] + fab_util) or VID_MARCAS.get(vid, "")
    modelo = _limpar_modelo_mouse(produto, marca)
    if modelo and marca and modelo.lower() == marca.lower():
        modelo = ""
    junto = " ".join(todos)
    conexao = ("Bluetooth" if bt else "Sem fio (receptor USB)" if _RE_RECEPTOR.search(junto)
               else "Sem fio" if _RE_SEMFIO.search(junto) else "USB" if usb else "")
    return {"externo": (usb or bt) and not virtual and not touch, "virtual": virtual, "touchpad": touch, "marca": marca,
            "modelo": modelo, "vid": vid, "pid": pid, "conexao": conexao,
            "receptor": bool(_RE_RECEPTOR.search(junto) and not bt)}


# ---- perfis por modelo: como desenhar o mouse e o que se sabe com segurança sobre ele ----
# forma: pequeno | simples | esportivo | ergonomico (os 4 desenhos do Th Boost)
# corpo/lateral: cor do topo e das laterais da carcaça; laterais: botões do polegar (0 a 3); dpi: botão de DPI atrás da roda;
# rgb: faixa de luz na cor da marca; fio: '' (sem fio), 'liso' ou 'trancado'; logo: 'neon' (esportivo) ou 'discreto' (escritório).
# 'dados' só leva o que a ficha do fabricante ou do anúncio do produto diz; sem certeza, fica vazio.
PERFIS_MOUSE = [
    ("Redragon", r"\bg105\b", {"forma": "ergonomico", "corpo": "#17171c", "lateral": "#0c0c0f", "laterais": 2, "dpi": True, "rgb": True,
                                "fio": "trancado", "logo": "neon",
                                "dados": ["8 botões programáveis", "Sensor óptico com DPI ajustável até 8000", "Cabo USB trançado",
                                          "Luz RGB com vários efeitos", "Formato ergonômico para a mão direita"]}),
    ("Logitech", r"\bm170\b", {"forma": "pequeno", "corpo": "#8c9199", "lateral": "#16171b", "laterais": 0, "dpi": False, "rgb": False,
                                "fio": "", "logo": "discreto", "semfio": True, "dois": True,
                                "dados": ["Sem fio 2.4 GHz com receptor USB", "Sensor óptico de 1000 DPI",
                                          "Formato compacto para destros e canhotos"]}),
    ("Logitech", r"\bg502\b", {"forma": "ergonomico", "corpo": "#1c1c21", "lateral": "#0e0e11", "laterais": 3, "dpi": True, "rgb": True,
                                "fio": "liso", "logo": "neon", "dados": []}),
    ("Logitech", r"\bg(203|102)\b", {"forma": "esportivo", "corpo": "#1b1b20", "lateral": "#0e0e11", "laterais": 2, "dpi": True,
                                     "rgb": True, "fio": "liso", "logo": "neon", "dados": []}),
    ("Logitech", r"\bg ?pro\b|superlight", {"forma": "esportivo", "corpo": "#202026", "lateral": "#101013", "laterais": 2, "dpi": False,
                                             "rgb": False, "fio": "", "logo": "neon", "semfio": True, "dados": []}),
    ("Razer", r"deathadder", {"forma": "ergonomico", "corpo": "#1a1a1f", "lateral": "#0d0d10", "laterais": 2, "dpi": True, "rgb": True,
                              "fio": "liso", "logo": "neon", "dados": []}),
    ("Redragon", r".*", {"forma": "ergonomico", "corpo": "#17171c", "lateral": "#0c0c0f", "laterais": 2, "dpi": True, "rgb": True,
                         "fio": "liso", "logo": "neon", "dados": []}),
]
_PERFIS_MOUSE = [(m, re.compile(rx, re.I), p) for m, rx, p in PERFIS_MOUSE]
_RE_COR = re.compile(r"^#[0-9a-f]{6}$", re.I)


def perfil_do_mouse(marca, modelo):
    """O perfil de desenho do modelo, ou None se o modelo não é conhecido (aí vale o formato por marca)."""
    marca, modelo = (marca or "").strip(), (modelo or "").strip()
    for m, rx, p in _PERFIS_MOUSE:
        generico = rx.pattern == r".*"  # o perfil geral da marca vem por último
        if marca and marca != m:
            continue
        if generico:
            if marca == m:
                return dict(p)
            continue
        if modelo and rx.search(modelo):
            return dict(p)
    return None


def chave_do_mouse(marca, modelo):
    """Identifica o modelo para guardar a foto dele: minúsculas, só letras e números."""
    t = re.sub(r"[^a-z0-9]+", " ", f"{marca or ''} {modelo or ''}".lower()).strip()
    return t[:60] if len(t) >= 2 else ""


FOTO_MAX = 300 * 1024  # bytes: a tela reduz a foto antes de mandar


def foto_tipo(dados):
    """png, jpeg ou webp pelos primeiros bytes (a extensão e o Content-Type não valem). '' se for outra coisa."""
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if dados[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _pasta_fotos():
    return os.environ.get("TOTIMIZE_FOTOS") or os.path.join(_pasta_dados(), "mouse_fotos")


def _arq_foto(chave):
    return os.path.join(_pasta_fotos(), hashlib.sha1(chave.encode("utf-8")).hexdigest()[:20] + ".img")


def foto_do_mouse(chave):
    """(bytes, tipo) da foto guardada para este modelo, ou None."""
    if not chave:
        return None
    try:
        with open(_arq_foto(chave), "rb") as f:
            dados = f.read(FOTO_MAX + 1)
    except OSError:
        return None
    tipo = foto_tipo(dados)
    return (dados, tipo) if tipo and len(dados) <= FOTO_MAX else None


def foto_guardar(chave, dados):
    """Guarda a foto (já conferida pelos primeiros bytes e pelo tamanho). Devolve '' se deu certo ou o motivo da recusa."""
    if not chave:
        return "Escolha a marca ou o modelo do mouse antes de usar uma foto."
    if not isinstance(dados, (bytes, bytearray)) or not dados:
        return "A foto veio vazia."
    if len(dados) > FOTO_MAX:
        return "A foto é grande demais (máximo 300 KB). Escolha outra ou reduza o tamanho."
    if not foto_tipo(bytes(dados)):
        return "Use uma foto PNG, JPG ou WEBP."
    try:
        os.makedirs(_pasta_fotos(), exist_ok=True)
        pasta = _pasta_fotos()
        outras = [n for n in os.listdir(pasta) if n.endswith(".img") and n != os.path.basename(_arq_foto(chave))]
        if len(outras) >= 30:  # pasta não cresce sem fim: apaga as mais antigas
            outras.sort(key=lambda n: os.path.getmtime(os.path.join(pasta, n)))
            for n in outras[: len(outras) - 29]:
                os.remove(os.path.join(pasta, n))
        tmp = _arq_foto(chave) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(bytes(dados))
        os.replace(tmp, _arq_foto(chave))
    except OSError:
        return "Não consegui guardar a foto neste computador."
    return ""


def foto_apagar(chave):
    try:
        os.remove(_arq_foto(chave))
        return True
    except OSError:
        return False


def link_busca_foto(marca, modelo):
    """Endereço de busca de imagens para a pessoa achar a foto do mouse dela (abre no navegador, ela escolhe e salva)."""
    t = f"{marca or ''} {modelo or ''} mouse".strip()
    return "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(t[:80])


def formato_do_mouse(marca, modelo):
    """Qual ilustração usar: 'esportivo' (leve e baixo), 'ergonomico' (grande, com apoio para o polegar) ou 'simples'."""
    perfil = perfil_do_mouse(marca, modelo)
    if perfil:
        return perfil["forma"]
    t = f"{marca} {modelo}"
    if _RE_ERGONOMICO.search(t):
        return "ergonomico"
    if _RE_ESPORTIVO.search(t):
        return "esportivo"
    return "esportivo" if (MARCAS_MOUSE.get(marca) or ("", False))[1] else "simples"


def _nome_do_mouse(marca, modelo):
    return " ".join(x for x in (marca, modelo) if x)


def _mouse_vazio():
    return {"achado": False, "nome": "", "marca": "", "modelo": "", "vid": "", "pid": "", "conexao": "", "formato": "simples",
            "cor": COR_PADRAO_MOUSE, "confianca": "nenhuma", "origem": "windows", "outros": [], "touchpad": False,
            "receptor": False, "dica": ""}


def analisar_mouse(d):
    """Transforma o que o Windows disse sobre os mouses em marca e modelo (função pura, testável)."""
    res = _mouse_vazio()
    if not isinstance(d, dict):
        return res
    ents = [x for x in (_entrada_mouse(e) for e in _lista(d.get("mouses"))) if x]
    externos = [x for x in ents if x["externo"]]
    if not externos:
        res["touchpad"] = any(x["touchpad"] for x in ents)
        res["dica"] = ("Só encontrei o touchpad do notebook. Conecte um mouse e toque em Atualizar."
                       if res["touchpad"] else "Não encontrei nenhum mouse conectado.")
        return res

    def pontos(x):
        return (4 if x["marca"] and x["modelo"] else 2 if x["marca"] else 1 if x["modelo"] else 0) + (1 if x["vid"] else 0)
    melhor = max(externos, key=pontos)
    vistos, outros = {_nome_do_mouse(melhor["marca"], melhor["modelo"]) or (melhor["vid"], melhor["pid"])}, []
    for x in externos:
        chave = _nome_do_mouse(x["marca"], x["modelo"]) or (x["vid"], x["pid"])
        if x is not melhor and chave not in vistos:
            vistos.add(chave)
            outros.append(_nome_do_mouse(x["marca"], x["modelo"]) or f"Mouse {x['vid'].upper()}:{x['pid'].upper()}".strip(": "))
    marca, modelo = melhor["marca"], melhor["modelo"]
    res.update(achado=True, marca=marca, modelo=modelo, vid=melhor["vid"].upper(), pid=melhor["pid"].upper(),
               conexao=melhor["conexao"], receptor=melhor["receptor"], outros=outros[:4],
               confianca="alta" if marca and modelo else ("media" if marca else "baixa"))
    if marca and not modelo and melhor["receptor"]:
        res["dica"] = ("O Windows só informa o fabricante do receptor sem fio, não o modelo do mouse. "
                       "Escolha o modelo abaixo e o Th Boost lembra.")
    elif marca and not modelo:
        res["dica"] = "O Windows informou a marca, mas não o modelo deste mouse. Dá para escolher o modelo abaixo."
    elif not marca and not modelo:
        res["dica"] = "Este mouse não informa marca nem modelo ao Windows. Dá para escolher à mão abaixo."
    return res


def combinar_mouse(det, manual=None):
    """Junta o que o Windows achou com a escolha manual da pessoa (a escolha manual vale mais). Sempre devolve o mesmo formato."""
    d = dict(det) if isinstance(det, dict) else _mouse_vazio()
    if isinstance(manual, dict) and (manual.get("marca") or manual.get("modelo")):
        d.update(achado=True, marca=manual.get("marca") or "", modelo=manual.get("modelo") or "", origem="manual",
                 confianca="manual", dica="")
    d["nome"] = _nome_do_mouse(d["marca"], d["modelo"]) or ("Mouse conectado" if d["achado"] else "")
    d["formato"] = formato_do_mouse(d["marca"], d["modelo"])
    d["cor"] = (MARCAS_MOUSE.get(d["marca"]) or (COR_PADRAO_MOUSE, False))[0]
    d["perfil"] = perfil_do_mouse(d["marca"], d["modelo"])
    d["chave"] = chave_do_mouse(d["marca"], d["modelo"])
    d["foto"] = False
    return d


def manual_mouse_valido(marca, modelo):
    """Confere a escolha vinda da tela. Devolve {'marca','modelo'} limpo ou None se for inválida. Vazio = voltar ao automático."""
    if marca is None:
        marca = ""
    if not isinstance(marca, str) or not isinstance(modelo, str) and modelo is not None:
        return None
    if marca and marca not in MARCAS_MOUSE:
        return None
    modelo = _texto_mouse(modelo or "", 40)
    if marca and modelo.lower().startswith(marca.lower() + " "):
        modelo = modelo[len(marca) + 1:].strip()
    return {"marca": marca, "modelo": modelo}


def ler_mouse():
    """Pergunta ao Windows quais mouses estão conectados. Devolve a análise ou None."""
    cod, saida = powershell(PS_MOUSE, tempo=60)
    if cod != 0 or not saida.strip():
        return None
    try:
        dados = json.loads(saida)
    except ValueError:
        return None
    return analisar_mouse(dados)


class MouseIdMixin:
    """A página Mouse e Precisão: reconhece o mouse em segundo plano e aplica o perfil competitivo."""

    def mouse_iniciar_estado(self):
        self.mouse_id = {"estado": "nenhum", "dados": None, "quando": 0.0}

    def mouse_agora(self, forcar=False):
        m = self.mouse_id
        if not forcar and m["estado"] == "pronto" and time.time() - m["quando"] < 300:
            return m["dados"]
        try:
            m["dados"] = ler_mouse()
            m["estado"] = "pronto" if m["dados"] else "erro"
        except Exception:
            m["dados"], m["estado"] = None, "erro"
        m["quando"] = time.time()
        return m["dados"]

    def mouse_ler(self, forcar=False):
        m = self.mouse_id
        if m["estado"] == "lendo" or REG is None:
            return
        if not forcar and m["estado"] == "pronto" and time.time() - m["quando"] < 300:
            return
        m["estado"] = "lendo"
        threading.Thread(target=lambda: self.mouse_agora(True), daemon=True).start()

    def mouse_lista(self):
        m = self.mouse_id
        if m["estado"] in ("nenhum", "erro") and REG is not None and time.time() - m["quando"] > 20:
            self.mouse_ler()
        dados = combinar_mouse(m["dados"], CONFIG.get("mouse_manual"))
        try:
            arq = _arq_foto(dados["chave"]) if dados["chave"] and foto_do_mouse(dados["chave"]) else ""
            dados["foto"] = int(os.path.getmtime(arq)) if arq else False  # a tela usa o número para recarregar quando a foto muda
        except OSError:
            dados["foto"] = False
        return {"estado": m["estado"] if REG is not None else "previa", "win": REG is not None,
                "dados": dados, "marcas": nomes_marcas_mouse(),
                "manual": CONFIG.get("mouse_manual") or {"marca": "", "modelo": ""}}

    def _mouse_atual(self):
        return combinar_mouse(self.mouse_id["dados"], CONFIG.get("mouse_manual"))

    def mouse_foto_atual(self):
        """(bytes, tipo) da foto que a pessoa guardou para o mouse mostrado agora, ou None."""
        return foto_do_mouse(self._mouse_atual()["chave"])

    def mouse_foto_guardar(self, dados):
        """Guarda a foto do mouse mostrado agora. Devolve '' se deu certo ou o motivo da recusa (já em português)."""
        d = self._mouse_atual()
        erro = foto_guardar(d["chave"], dados)
        if not erro:
            self.msg(f"Foto guardada para {d['nome'] or 'o mouse'}. Ela aparece no lugar do desenho.")
        return erro

    def mouse_foto_remover(self):
        d = self._mouse_atual()
        if foto_apagar(d["chave"]):
            self.msg("Foto removida: voltou o desenho do Th Boost.")

    def mouse_buscar_foto(self):
        """Abre a busca de imagens do mouse no navegador. O Th Boost não baixa nada: a pessoa escolhe e salva a foto."""
        d = self._mouse_atual()
        if not d["chave"]:
            return self.msg("Escolha a marca ou o modelo do mouse primeiro.")
        try:
            abrir_link(link_busca_foto(d["marca"], d["modelo"]))
            self.msg("Abrindo a busca de imagens. Salve a foto que gostar e use \"Usar minha foto\".")
        except Exception:
            self.msg("Não consegui abrir o navegador.")

    def mouse_definir_manual(self, marca, modelo):
        v = manual_mouse_valido(marca, modelo)
        if v is None:
            raise ValueError("escolha inválida")
        if v["marca"] or v["modelo"]:
            CONFIG["mouse_manual"] = v
            self.msg(f"Mouse escolhido: {_nome_do_mouse(v['marca'], v['modelo'])}.")
        else:
            CONFIG.pop("mouse_manual", None)
            self.msg("Mouse: voltei a reconhecer sozinho.")
        salvar_config()

    def _perfil_itens(self, chave, itens, ligar):
        """v9.1: liga os ajustes de um perfil lembrando quais ELE ligou; ao desligar, desfaz só esses (o que você já tinha
        ligado antes continua ligado) e não desfaz o que o outro perfil (mouse/teclado) ainda usa."""
        avisos, feitos = [], []
        outro = "teclado" if chave == "mouse" else "mouse"
        with TRAVA_AJ:
            bk = _backup()
            legado = ("perfil_" + chave) not in bk
            meus = [i for i in (bk.get("perfil_" + chave) or []) if isinstance(i, str)]
            do_outro = set(i for i in (bk.get("perfil_" + outro) or []) if isinstance(i, str))
            outro_legado = ("perfil_" + outro) not in bk
        if not ligar and legado:  # ligado por uma versão antiga (sem a lista): desfaz o perfil inteiro
            meus = [i for i, _ in itens]
            if outro_legado:  # o outro perfil também é antigo: se ele parece ligado, o USB fica com ele
                itens_outro = {"mouse": ("mouse_acel",), "teclado": ("teclado_rapido", "teclas_aderencia")}[outro]
                try:
                    if all(POR_ID[i].estado() is True for i in itens_outro):
                        do_outro.add("mouse_usb")
                except Exception:
                    pass
        for ident, rotulo in itens:
            a = POR_ID[ident]
            try:
                if ligar:
                    if a.estado() is True:
                        feitos.append(rotulo)
                        if ident in do_outro and ident not in meus:
                            meus.append(ident)  # dividido com o outro perfil: só sai quando os dois desligarem
                        continue
                elif ident not in meus or ident in do_outro:
                    continue  # não foi este perfil que ligou (ou o outro perfil ainda precisa dele)
                if a.precisa_admin and not e_admin():
                    avisos.append(f"{a.titulo} precisa de Administrador (feche e abra o Th Boost pelo atalho)")
                    continue
                a.ligar() if ligar else a.desligar()
                feitos.append(rotulo)
                if ligar and ident not in meus:
                    meus.append(ident)
                elif not ligar:
                    meus = [i for i in meus if i != ident]
            except OSError as erro:
                avisos.append(f"{a.titulo}: {erro}")
        with TRAVA_AJ:
            bk = _backup()
            if ligar:
                bk["perfil_" + chave] = meus
            else:
                bk.pop("perfil_" + chave, None)  # desligado: o que sobrou na lista era dividido com o outro perfil
            _guardar_backup()
        return avisos, feitos

    def t_mouse_perfil(self, ligar):
        """Perfil competitivo: sem aceleração do ponteiro, velocidade 10 (a do Windows, 1 para 1) e USB sem suspensão."""
        avisos, feitos = self._perfil_itens("mouse", (("mouse_acel", "sem aceleração"), ("mouse_usb", "USB sem suspensão")), ligar)
        if ligar:
            antes = velocidade_mouse()
            if antes != 10:
                with TRAVA_AJ:
                    _backup()["mouse_vel_antes"] = antes
                    _guardar_backup()
                definir_velocidade_mouse(10)
            feitos.append("velocidade 10/20")
        else:
            with TRAVA_AJ:
                antes = _backup().pop("mouse_vel_antes", None)
                _guardar_backup()
            if isinstance(antes, int) and not isinstance(antes, bool) and 1 <= antes <= 20:
                definir_velocidade_mouse(antes)
        self.atualizar_aj()
        if ligar:
            texto = "Perfil de mouse competitivo ligado: " + ", ".join(feitos) + "."
        else:
            texto = "Perfil de mouse competitivo desligado: o mouse voltou ao que era antes."
        return texto + (" Atenção: " + "; ".join(avisos) + "." if avisos else "")

    def t_teclado_perfil(self, ligar):
        """Teclado rápido: a tecla segurada repete sem espera, nada de aviso de acessibilidade no meio do jogo e USB sem suspensão."""
        avisos, feitos = self._perfil_itens("teclado", (("teclado_rapido", "repetição sem espera"),
                                                         ("teclas_aderencia", "sem avisos de Shift"),
                                                         ("mouse_usb", "USB sem suspensão")), ligar)
        self.atualizar_aj()
        if ligar:
            texto = "Teclado rápido ligado: " + ", ".join(feitos) + "."
        else:
            texto = "Teclado rápido desligado: o teclado voltou ao que era antes."
        return texto + (" Atenção: " + "; ".join(avisos) + "." if avisos else "")

    def teclado_perfil(self, ligar):
        if REG is None:
            return self.msg("O teclado rápido só funciona no Windows.")
        self.msg("Ligando o teclado rápido..." if ligar else "Desligando o teclado rápido...")
        self.em_fundo(lambda: self.t_teclado_perfil(ligar))

    def mouse_perfil(self, ligar):
        if REG is None:
            return self.msg("O perfil de mouse só funciona no Windows.")
        self.msg("Ligando o perfil de mouse competitivo..." if ligar else "Desligando o perfil de mouse competitivo...")
        self.em_fundo(lambda: self.t_mouse_perfil(ligar))
