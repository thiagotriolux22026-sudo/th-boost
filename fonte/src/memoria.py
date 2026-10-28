# ---------------- memória RAM: o que existe no PC e como deixá-la mais rápida ----------------
#
# O "clock" da memória (a velocidade em MHz) é gravado na BIOS/UEFI da placa-mãe, no perfil XMP (Intel), DOCP/EXPO
# (AMD) ou AMP (AMD antigo). Nenhum programa do Windows muda isso com segurança, então o Th Boost só LÊ o que existe,
# avisa quando a memória está abaixo da velocidade do kit (ou em canal único) e leva a pessoa até a BIOS com o passo a
# passo. Nada é gravado na BIOS por aqui.

TIPOS_MEMORIA = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5"}
_VELOCIDADES = frozenset((800, 1066, 1333, 1600, 1866, 2133, 2400, 2666, 2800, 2933, 3000, 3200, 3466, 3600, 3733, 3866,
                          4000, 4133, 4266, 4400, 4800, 5200, 5600, 6000, 6400, 6800, 7200, 7600, 8000))
_CURTOS = {"316": 1600, "318": 1866, "321": 2133, "324": 2400, "426": 2666, "429": 2933, "430": 3000, "432": 3200,
           "436": 3600, "440": 4000, "548": 4800, "552": 5200, "556": 5600, "560": 6000, "564": 6400}
_TECLAS_BIOS = (("asus", "Del ou F2"), ("msi", "Del"), ("gigabyte", "Del"), ("aorus", "Del"), ("asrock", "F2 ou Del"),
                ("dell", "F2"), ("hewlett", "Esc ou F10"), ("hp", "Esc ou F10"), ("lenovo", "F2"), ("acer", "F2 ou Del"),
                ("samsung", "F2"), ("positivo", "F2 ou Del"), ("itautec", "F2 ou Del"))


def _lista(x):
    if x is None:
        return []
    return [i for i in (x if isinstance(x, list) else [x]) if isinstance(i, dict)]


def _inteiro(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def velocidade_pelo_codigo(peca):
    """Tenta ler a velocidade vendida do kit pelo código da peça (CMK16GX4M2B3200C16 -> 3200). Só uma dica."""
    p = re.sub(r"[\s_]", "", str(peca or "").upper())
    m = re.match(r"(?:KF|HX|KHX)(\d{3})[CS]\d", p)
    if m and m.group(1) in _CURTOS:
        return _CURTOS[m.group(1)]
    for t in re.findall(r"(?<!\d)(\d{4})(?!\d)", p):
        if int(t) in _VELOCIDADES:
            return int(t)
    return 0


def _perfil_da_placa(cpu):
    c = (cpu or "").lower()
    if "ryzen" in c or "epyc" in c or "threadripper" in c:
        return "DOCP ou EXPO (em algumas placas chama XMP)"
    if "amd" in c or "athlon" in c or "phenom" in c or re.search(r"\bfx\b", c):
        return "XMP ou AMP"
    if "intel" in c or "core" in c or "pentium" in c or "celeron" in c:
        return "XMP"
    return "XMP, DOCP ou EXPO"


def _tecla_da_bios(fabricante):
    f = (fabricante or "").lower()
    return next((t for k, t in _TECLAS_BIOS if k in f), "Del ou F2")


def analisar_memoria(d, cpu="", notebook=False):
    """Transforma o que o Windows disse sobre os pentes de memória em números e avisos (função pura, testável)."""
    if not isinstance(d, dict):
        return None
    mods = []
    for m in _lista(d.get("modulos")):
        cap = _inteiro(m.get("Capacity")) / 1024 ** 3
        if cap <= 0:
            continue
        peca = str(m.get("PartNumber") or "").strip()[:40]
        mods.append({"slot": str(m.get("DeviceLocator") or m.get("BankLabel") or "").strip()[:24],
                     "gb": int(cap) if abs(cap - round(cap)) < 0.05 else round(cap, 1),
                     "mhz_atual": _inteiro(m.get("ConfiguredClockSpeed")), "mhz_spd": _inteiro(m.get("Speed")),
                     "tipo": TIPOS_MEMORIA.get(_inteiro(m.get("SMBIOSMemoryType")), ""),
                     "fab": str(m.get("Manufacturer") or "").strip()[:24], "peca": peca,
                     "mhz_codigo": velocidade_pelo_codigo(peca)})
    if not mods:
        return None
    placa = (_lista(d.get("placa")) or [{}])[0]
    slots = sum(_inteiro(x.get("MemoryDevices")) for x in _lista(d.get("matriz")))
    total = sum(m["gb"] for m in mods)
    tipo = next((m["tipo"] for m in mods if m["tipo"]), "")
    atuais = [m["mhz_atual"] or m["mhz_spd"] for m in mods if (m["mhz_atual"] or m["mhz_spd"])]
    vel_atual = min(atuais) if atuais else 0
    vel_spd = max([m["mhz_spd"] for m in mods] or [0])
    vel_cod = max([m["mhz_codigo"] for m in mods] or [0])
    vel_kit, fonte = (vel_spd, "spd") if vel_spd >= vel_cod else (vel_cod, "codigo")
    abaixo = bool(vel_atual and vel_kit and vel_atual < vel_kit * 0.93)
    canal = "unico" if len(mods) == 1 else ("duplo" if len(mods) >= 2 else "?")
    perfil = _perfil_da_placa(cpu)
    ach = []
    if abaixo:
        base = "o kit informa" if fonte == "spd" else "pelo código da peça, o kit parece ser de"
        ach.append({"id": "abaixo", "nivel": "aviso", "titulo": f"A memória roda a {vel_atual} MHz, mas {base} {vel_kit} MHz",
                    "texto": f"É muito comum: o PC liga a memória na velocidade básica até você ativar o perfil {perfil} na BIOS. "
                             "Ativar é de graça e costuma dar mais FPS e menos travadas, principalmente com vídeo integrado ou processador AMD."})
        if notebook:
            ach.append({"id": "notebook", "nivel": "info", "titulo": "Em notebook, a BIOS quase nunca tem essa opção",
                        "texto": "Muitos notebooks travam a velocidade da memória. Se a BIOS não mostrar XMP, não há o que fazer por software."})
    if canal == "unico":
        ach.append({"id": "canal", "nivel": "aviso", "titulo": "Só 1 pente de memória (canal único)",
                    "texto": "Com 2 pentes iguais (canal duplo) a memória entrega até o dobro de largura de banda. Em jogos, é um dos upgrades "
                             "que mais ajudam, principalmente com vídeo integrado. Se for comprar, leve 2 pentes iguais do mesmo kit."})
    if len({(m["gb"], m["mhz_spd"]) for m in mods}) > 1:
        ach.append({"id": "misto", "nivel": "info", "titulo": "Os pentes são diferentes entre si",
                    "texto": "Quando os pentes têm tamanho ou velocidade diferentes, o PC roda todos na velocidade do mais lento."})
    if slots and slots > len(mods):
        ach.append({"id": "livres", "nivel": "info", "titulo": f"{slots - len(mods)} slot(s) de memória livre(s)",
                    "texto": "Dá para colocar mais pentes (iguais aos que já estão) sem tirar os atuais."})
    if not abaixo and canal != "unico":
        ach.append({"id": "ok", "nivel": "ok", "titulo": "Memória na velocidade do kit" if vel_atual else "Memória lida",
                    "texto": (f"Rodando a {vel_atual} MHz" + (f" em canal duplo." if canal == "duplo" else ".")) if vel_atual else ""})
    return {"estado": "pronto", "total_gb": total, "tipo": tipo, "modulos": mods, "slots": slots, "vel_atual": vel_atual,
            "vel_kit": vel_kit, "fonte": fonte, "abaixo": abaixo, "canal": canal, "perfil": perfil,
            "placa": " ".join(str(placa.get(k) or "").strip() for k in ("Manufacturer", "Product")).strip()[:60],
            "tecla": _tecla_da_bios(placa.get("Manufacturer")), "notebook": bool(notebook), "achados": ach}


def ler_memoria():
    """Lê pentes, slots e placa-mãe pelo Windows. Devolve a análise ou None."""
    cod, saida = powershell(
        "$m=@(Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator,BankLabel,Capacity,Speed,ConfiguredClockSpeed,"
        "SMBIOSMemoryType,Manufacturer,PartNumber);"
        "$a=@(Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices);"
        "$b=@(Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product);"
        "ConvertTo-Json -Compress -Depth 4 @{modulos=$m;matriz=$a;placa=$b}", tempo=30)
    if cod != 0 or not saida.strip():
        return None
    try:
        dados = json.loads(saida)
    except ValueError:
        return None
    return analisar_memoria(dados, nome_do_processador(), tem_bateria())


class MemoriaMixin:
    """A página Memória RAM: leitura em segundo plano e o atalho para reiniciar direto na BIOS."""

    def memoria_iniciar_estado(self):
        self.memoria = {"estado": "nenhum", "dados": None, "quando": 0.0}

    def memoria_agora(self, forcar=False):
        """Lê (ou reaproveita a leitura de até 10 minutos). Roda na thread de quem chamou."""
        m = self.memoria
        if not forcar and m["estado"] == "pronto" and time.time() - m["quando"] < 600:
            return m["dados"]
        try:
            m["dados"] = ler_memoria()
            m["estado"] = "pronto" if m["dados"] else "erro"
        except Exception:
            m["dados"], m["estado"] = None, "erro"
        m["quando"] = time.time()
        return m["dados"]

    def memoria_ler(self, forcar=False):
        m = self.memoria
        if m["estado"] == "lendo" or REG is None:
            return
        if not forcar and m["estado"] == "pronto" and time.time() - m["quando"] < 600:
            return
        m["estado"] = "lendo"

        def tarefa():
            self.memoria_agora(True)
        threading.Thread(target=tarefa, daemon=True).start()

    def memoria_lista(self):
        if self.memoria["estado"] in ("nenhum", "erro") or time.time() - self.memoria["quando"] > 600:
            self.memoria_ler()
        m = self.memoria
        return {"estado": m["estado"], "dados": m["dados"], "admin": e_admin(), "win": REG is not None}

    def t_memoria_bios(self):
        if REG is None:
            return "Disponível só no Windows."
        tecla = (self.memoria.get("dados") or {}).get("tecla") or "Del ou F2"
        if not e_admin():
            return f"Reiniciar direto na BIOS precisa de Administrador. Abra o Th Boost pelo atalho, ou reinicie o PC e aperte {tecla} várias vezes assim que ele ligar."
        cod, _ = executar(["shutdown", "/r", "/fw", "/t", "30", "/c", "Th Boost: reiniciando na BIOS para ativar o perfil da memória."])
        if cod != 0:
            return f"Este PC não aceitou reiniciar direto na BIOS (isso só existe em PC com UEFI). Reinicie normalmente e aperte {tecla} várias vezes assim que ele ligar."
        return "Reiniciando na BIOS em 30 segundos. Salve o que estiver aberto. Para desistir, aperte Cancelar."

    def memoria_bios(self):
        self.em_fundo(self.t_memoria_bios)

    def t_memoria_bios_cancelar(self):
        if REG is None:
            return "Disponível só no Windows."
        cod, _ = executar(["shutdown", "/a"])
        return "Reinício cancelado." if cod == 0 else "Não havia reinício agendado."

    def memoria_bios_cancelar(self):
        self.em_fundo(self.t_memoria_bios_cancelar)
