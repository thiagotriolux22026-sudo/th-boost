# ---------------- v9.4: gráfico leve nos jogos (junto do Modo FPS On) ----------------
# Ao ligar o Modo FPS On, o Th Boost deixa o gráfico do Valorant, do CS2 e do Roblox no mínimo (sombras, efeitos,
# texturas, detalhes e suavização), mas com a resolução em 100% (a imagem continua nítida). Ao desligar, cada item volta
# ao valor que você usava. Só mexe nos itens de gráfico (o resto do arquivo, como sensibilidade e volume, fica como está).
# O jogo precisa estar fechado: se estiver aberto, a troca espera ele fechar (o jogo regrava o arquivo ao sair).

GR_ESPERA = 4  # segundos depois que o jogo fecha antes de mexer (ele ainda está gravando o arquivo)

# ---- Valorant: GameUserSettings.ini, seção [ScalabilityGroups] (0 = baixo) ----
GR_VAL_CHAVES = ("sg.ViewDistanceQuality", "sg.AntiAliasingQuality", "sg.ShadowQuality", "sg.PostProcessQuality",
                 "sg.TextureQuality", "sg.EffectsQuality", "sg.FoliageQuality", "sg.ShadingQuality")
GR_VAL_BAIXO = dict({k: "0" for k in GR_VAL_CHAVES}, **{"sg.ResolutionQuality": "100.000000"})

# ---- CS2: cs2_video.txt (Steam\userdata\<conta>\730\local\cfg) ----
GR_CS2_BAIXO = {"setting.shaderquality": "0", "setting.r_texturefilteringquality": "0", "setting.msaa_samples": "0",
                "setting.r_csgo_cmaa_enable": "0", "setting.videocfg_shadow_quality": "0", "setting.videocfg_texture_detail": "0",
                "setting.videocfg_particle_detail": "0", "setting.videocfg_ao_detail": "0", "setting.videocfg_hdr_detail": "3",
                "setting.videocfg_fsr_detail": "0"}  # hdr 3 = "Desempenho"; fsr 0 = desligado (resolução 100%)

# ---- Roblox: GlobalBasicSettings_*.xml (qualidade 1 = a mais baixa) ----
GR_RBX_BAIXO = {"SavedQualityLevel": "1", "GraphicsQualityLevel": "1"}


def _ini_ler(t, secao, chaves):
    out, dentro = {}, False
    for ln in t.splitlines():
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            dentro = s[1:-1] == secao
            continue
        if dentro and "=" in s:
            k, v = s.split("=", 1)
            if k.strip() in chaves:
                out[k.strip()] = v.strip()
    return out


def _ini_mudar(t, secao, valores):
    """Troca (ou cria) chave=valor dentro de [secao]; valor None apaga a linha. Mantém o resto e o fim de linha."""
    nl = "\r\n" if "\r\n" in t else "\n"
    novas, feitas = [], set()
    dentro = achou = False
    fim = None  # onde termina a seção (para colocar o que falta)
    for ln in t.splitlines():
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            if dentro and fim is None:
                fim = len(novas)
            dentro = s[1:-1] == secao
            achou = achou or dentro
            novas.append(ln)
            continue
        if dentro and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in valores:
                feitas.add(k)
                if valores[k] is not None:
                    novas.append(f"{k}={valores[k]}")
                continue
        novas.append(ln)
    if dentro and fim is None:
        fim = len(novas)
    faltam = [f"{k}={v}" for k, v in valores.items() if k not in feitas and v is not None]
    if faltam and not achou:
        if novas and novas[-1].strip():
            novas.append("")
        novas += [f"[{secao}]"] + faltam
    elif faltam:
        pos = fim
        while pos > 0 and not novas[pos - 1].strip():
            pos -= 1
        novas[pos:pos] = faltam
    return nl.join(novas) + (nl if t.endswith(("\n", "\r")) or not t else "")


def gr_val_ler(t):
    return _ini_ler(t, "ScalabilityGroups", set(GR_VAL_BAIXO))


def gr_val_mudar(t, valores):
    return _ini_mudar(t, "ScalabilityGroups", valores)


def gr_cs2_ler(t):
    return {k: m.group(1) for k in GR_CS2_BAIXO for m in [re.search(r'"%s"\s+"([^"]*)"' % re.escape(k), t)] if m}


def gr_cs2_mudar(t, valores):
    """Só troca chaves que já existem no arquivo (o CS2 sempre grava todas)."""
    for k, v in valores.items():
        if v is not None:
            t = re.sub(r'("%s"\s+")([^"]*)(")' % re.escape(k), lambda m, v=v: m.group(1) + v + m.group(3), t, count=1)
    return t


def gr_rbx_ler(t):
    return {m.group(2): m.group(3) for m in re.finditer(r'<(\w+) name="(%s)">(-?\d+)</\1>' % "|".join(GR_RBX_BAIXO), t)}


def gr_rbx_mudar(t, valores):
    for k, v in valores.items():
        if v is not None:
            t = re.sub(r'(<(\w+) name="%s">)(-?\d+)(</\2>)' % re.escape(k), lambda m, v=v: m.group(1) + v + m.group(4), t, count=1)
    return t


GR_JOGOS = {
    "valorant": {"nome": "Valorant", "procs": ("valorant-win64-shipping.exe", "valorant.exe"),
                 "ler": gr_val_ler, "mudar": gr_val_mudar, "baixo": GR_VAL_BAIXO},
    "cs2": {"nome": "CS2", "procs": ("cs2.exe",), "ler": gr_cs2_ler, "mudar": gr_cs2_mudar, "baixo": GR_CS2_BAIXO},
    "roblox": {"nome": "Roblox", "procs": ("robloxplayerbeta.exe",), "ler": gr_rbx_ler, "mudar": gr_rbx_mudar, "baixo": GR_RBX_BAIXO},
}


def gr_arquivos():
    """{jogo: [arquivos de gráfico deste PC]}"""
    la = os.environ.get("LOCALAPPDATA") or ""
    out = {"valorant": [], "cs2": [], "roblox": []}
    if la:
        for sub in ("Windows", "WindowsClient"):
            out["valorant"] += glob.glob(os.path.join(la, "VALORANT", "Saved", "Config", "*", sub, "GameUserSettings.ini"))
        out["roblox"] = glob.glob(os.path.join(la, "Roblox", "GlobalBasicSettings_*.xml"))
    for raiz in _raizes_steam():
        out["cs2"] += glob.glob(os.path.join(raiz, "userdata", "*", "730", "local", "cfg", "cs2_video.txt"))
    return {k: sorted(set(v)) for k, v in out.items()}


def _gr_le_arquivo(caminho):
    with open(caminho, "rb") as f:
        b = f.read(4 * 1024 * 1024)
    for bom, cod in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if b.startswith(bom):
            return b.decode(cod), cod
    try:
        return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return b.decode("latin-1"), "latin-1"


def _gr_grava(caminho, texto, cod):
    tmp = caminho + ".thboost.tmp"
    with open(tmp, "wb") as f:
        f.write(texto.encode(cod))
    try:
        os.replace(tmp, caminho)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _gr_rodando(procs):
    try:
        for p in psutil.process_iter(["name"]):
            if (p.info.get("name") or "").lower() in procs:
                return True
    except Exception:
        pass
    return False


class GraficoMixin:
    """Gráfico leve: aplica ao ligar o Modo FPS On e devolve ao desligar (ou quando o jogo fechar)."""

    def gr_aplicar(self):
        with self.gr_trava:
            texto = self._gr_aplicar_sem_trava()
            if not getattr(self, "modo_fps", False):  # desligaram o Modo FPS On enquanto aplicava: desfaz
                return self._gr_voltar_sem_trava()
            return texto

    def gr_voltar(self, avisar=False):
        with self.gr_trava:
            return self._gr_voltar_sem_trava(avisar)

    def gr_conferir(self):
        if not self.gr["espera"]:
            return
        with self.gr_trava:
            self._gr_conferir_sem_trava()

    def gr_fechar(self):
        with self.gr_trava:
            self._gr_fechar_sem_trava()

    def gr_iniciar_estado(self):
        self.gr = {"espera": {}, "fechou_em": {}, "ultimo": 0.0, "texto": ""}  # espera: {jogo: "aplicar"|"voltar"}
        self.gr_trava = threading.RLock()
        if CONFIG.get("grafico_bk"):  # fechou com o gráfico leve aplicado: devolve (ou espera o jogo fechar)
            threading.Thread(target=lambda: self.gr_voltar(avisar=True), daemon=True).start()

    def gr_ligado(self):
        return CONFIG.get("grafico_leve", True) is not False

    def gr_estado(self):
        bk = CONFIG.get("grafico_bk") or {}
        return {"ligado": self.gr_ligado(), "aplicado": sorted({v.get("jogo") for v in bk.values() if isinstance(v, dict)}),
                "espera": dict(self.gr["espera"]), "texto": self.gr["texto"]}

    def _gr_aplicar_jogo(self, jogo, arquivos):
        """Deixa um jogo no mínimo. Guarda o valor de antes de cada item (uma vez só). Devolve quantos arquivos mudou."""
        d = GR_JOGOS[jogo]
        bk = CONFIG.setdefault("grafico_bk", {})
        feitos = 0
        for arq in arquivos:
            try:
                t, cod = _gr_le_arquivo(arq)
                antes = d["ler"](t)
                if jogo != "valorant" and not antes:
                    continue  # arquivo sem os itens de gráfico (versão diferente): não mexe
                if arq not in bk:
                    bk[arq] = {"jogo": jogo, "antes": {k: antes.get(k) for k in d["baixo"]}}
                    try:  # cópia inteira do arquivo, por garantia
                        pasta = os.path.join(os.environ.get("LOCALAPPDATA") or pasta_do_programa(), "ThBoost", "grafico")
                        os.makedirs(pasta, exist_ok=True)
                        nome = f"{jogo}_{hashlib.sha256(arq.lower().encode()).hexdigest()[:10]}_{os.path.basename(arq)}"
                        shutil.copy2(arq, os.path.join(pasta, nome))
                    except OSError:
                        pass
                novo = d["mudar"](t, d["baixo"])
                if novo != t:
                    _gr_grava(arq, novo, cod)
                feitos += 1
            except OSError:
                bk.pop(arq, None)
        salvar_config()
        return feitos

    def _gr_voltar_jogo(self, jogo):
        d = GR_JOGOS[jogo]
        bk = CONFIG.get("grafico_bk") or {}
        feitos = 0
        for arq, info in list(bk.items()):
            if not isinstance(info, dict) or info.get("jogo") != jogo:
                continue
            try:
                if os.path.isfile(arq):
                    t, cod = _gr_le_arquivo(arq)
                    antes = {k: v for k, v in (info.get("antes") or {}).items() if k in d["baixo"]}
                    if jogo != "valorant":  # nos outros só se troca o que existe
                        antes = {k: v for k, v in antes.items() if v is not None}
                    novo = d["mudar"](t, antes)
                    if novo != t:
                        _gr_grava(arq, novo, cod)
                feitos += 1
                bk.pop(arq, None)
            except OSError:
                continue  # arquivo preso (somente leitura, aberto): tenta de novo depois
        if not bk:
            CONFIG.pop("grafico_bk", None)
        salvar_config()
        return feitos

    def _gr_aplicar_sem_trava(self):
        """Modo FPS On ligou."""
        if not self.gr_ligado():
            return ""
        arqs = gr_arquivos()
        feitos, esperam = [], []
        for jogo, lista in arqs.items():
            if not lista:
                continue
            if _gr_rodando(GR_JOGOS[jogo]["procs"]):
                self.gr["espera"][jogo] = "aplicar"
                esperam.append(GR_JOGOS[jogo]["nome"])
            elif self._gr_aplicar_jogo(jogo, lista):
                self.gr["espera"].pop(jogo, None)
                feitos.append(GR_JOGOS[jogo]["nome"])
        partes = []
        if feitos:
            partes.append("Gráfico leve: " + ", ".join(feitos) + " no mínimo (resolução continua 100%).")
        if esperam:
            partes.append(", ".join(esperam) + (" está aberto" if len(esperam) == 1 else " estão abertos") +
                          ": o gráfico leve entra quando fechar (feche e abra o jogo de novo).")
        self.gr["texto"] = " ".join(partes[1:]) if esperam and feitos else (" ".join(partes) if esperam else "")  # na tela: só o que espera
        return " ".join(partes)

    def _gr_voltar_sem_trava(self, avisar=False):
        """Modo FPS On desligou (ou o Th Boost abriu depois de fechar com ele ligado)."""
        bk = CONFIG.get("grafico_bk") or {}
        jogos = sorted({v.get("jogo") for v in bk.values() if isinstance(v, dict) and v.get("jogo") in GR_JOGOS})
        for j, acao in list(self.gr["espera"].items()):
            if acao == "aplicar":
                self.gr["espera"].pop(j, None)
        feitos, esperam = [], []
        for jogo in jogos:
            if _gr_rodando(GR_JOGOS[jogo]["procs"]):
                self.gr["espera"][jogo] = "voltar"
                esperam.append(GR_JOGOS[jogo]["nome"])
            else:
                self._gr_voltar_jogo(jogo)
                self.gr["espera"].pop(jogo, None)
                feitos.append(GR_JOGOS[jogo]["nome"])
        partes = []
        if feitos:
            partes.append("O gráfico de " + ", ".join(feitos) + " voltou ao que você usava.")
        if esperam:
            partes.append(", ".join(esperam) + (" está aberto" if len(esperam) == 1 else " estão abertos") +
                          ": o seu gráfico volta assim que fechar.")
        self.gr["texto"] = " ".join(partes) if esperam else ""
        texto = " ".join(partes)
        if avisar and texto:
            self.msg(texto)
        return texto

    def _gr_conferir_sem_trava(self):
        """Chamado o tempo todo: faz o que ficou esperando o jogo fechar (no máximo a cada 3 s)."""
        if not self.gr["espera"]:
            return
        agora = time.time()
        if agora - self.gr["ultimo"] < 3:
            return
        self.gr["ultimo"] = agora
        for jogo, acao in list(self.gr["espera"].items()):
            if _gr_rodando(GR_JOGOS[jogo]["procs"]):
                self.gr["fechou_em"].pop(jogo, None)
                continue
            if agora - self.gr["fechou_em"].setdefault(jogo, agora) < GR_ESPERA:
                continue  # acabou de fechar: o jogo ainda pode estar gravando o arquivo
            self.gr["fechou_em"].pop(jogo, None)
            self.gr["espera"].pop(jogo, None)
            nome = GR_JOGOS[jogo]["nome"]
            if acao == "aplicar" and getattr(self, "modo_fps", False) and self.gr_ligado():
                if self._gr_aplicar_jogo(jogo, gr_arquivos().get(jogo) or []):
                    self.msg(f"{nome} fechou: o gráfico leve já está pronto para a próxima vez que abrir.")
            elif acao == "voltar":
                self._gr_voltar_jogo(jogo)
                self.msg(f"{nome} fechou: o gráfico voltou ao que você usava.")
        if not self.gr["espera"]:
            self.gr["texto"] = ""

    def _gr_fechar_sem_trava(self):
        """O Th Boost vai fechar: devolve o que der agora; o que estiver aberto volta na próxima vez que ele abrir."""
        try:
            bk = CONFIG.get("grafico_bk") or {}
            for jogo in sorted({v.get("jogo") for v in bk.values() if isinstance(v, dict) and v.get("jogo") in GR_JOGOS}):
                if not _gr_rodando(GR_JOGOS[jogo]["procs"]):
                    self._gr_voltar_jogo(jogo)
        except Exception:
            pass
