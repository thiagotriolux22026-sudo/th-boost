# ---------------- v9.2: FPS na tela (overlay de monitoramento) e contador de FPS com um clique ----------------
# O "FPS na tela" é uma janelinha sempre por cima do jogo (num canto), que não pega clique nem foco: o mouse e o teclado
# continuam indo para o jogo. Ela roda num programa separado (o mesmo th_boost.py com --overlay), que só lê os números do
# Th Boost a cada meio segundo. Ctrl+Shift+F esconde e mostra durante o jogo.
# Funciona por cima de jogos em janela ou em "tela cheia sem bordas" (a maioria dos jogos atuais). Em tela cheia exclusiva,
# alguns jogos não deixam nenhuma janela aparecer por cima.

OV_PADRAO = {"on": False, "pos": "se", "tam": 2, "itens": ["fps", "fps1", "ms", "cpu", "tcpu", "gpu", "tgpu", "ram", "lim"]}
OV_ITENS = ("fps", "fps1", "ms", "cpu", "tcpu", "gpu", "tgpu", "ram", "lim")
GARGALO_TXT = {"cpu": ("CPU", "#f87171"), "gpu": ("GPU", "#4ade80"), "folga": ("nenhum", "#e2e8f0")}


def gargalo(amostras):
    """Quem segura o FPS agora, pela média das últimas leituras [(CPU total %, núcleo mais usado %, GPU %)]:
    'gpu' (a placa está no limite: overclock da placa ajuda), 'cpu' (o processador está no limite e a placa sobra)
    ou 'folga' (nenhum dos dois: o FPS está preso por um limite do jogo). None sem leituras suficientes. Função pura."""
    ok = [a for a in amostras if a and a[0] is not None and a[2] is not None]
    if len(ok) < 3:
        return None
    tot = sum(a[0] for a in ok) / len(ok)
    mx = sum((a[1] if a[1] is not None else a[0]) for a in ok) / len(ok)
    gpu = sum(a[2] for a in ok) / len(ok)
    if gpu >= 90:
        return "gpu"
    if tot >= 85 or mx >= 95:
        return "cpu"
    return "folga"
OV_POS = ("se", "sd", "ie", "id")  # superior esquerdo, superior direito, inferior esquerdo, inferior direito
OV_SEM_TK = 3  # código de saída da janelinha quando o Python deste PC não tem o Tk (a parte de janelas)

# PresentMon oficial (Intel, código aberto, github.com/GameTechDev/PresentMon), conferido pela impressão digital
PM_VERSAO = "2.6.0"
PM_NOME = f"PresentMon-{PM_VERSAO}-x64.exe"
PM_URL = f"https://github.com/GameTechDev/PresentMon/releases/download/v{PM_VERSAO}/{PM_NOME}"
PM_SHA256 = "b2a706bc6ad475749e3b7e3409263aa1e6906d45bdcf993f6dbc0f660188f1af"
PM_TAM = 980320
PM_HOSTS = ("github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com")


def ov_valida(d, base=None):
    """Configuração do FPS na tela, só com valores conhecidos. Função pura."""
    o = dict(base or OV_PADRAO)
    o["itens"] = list(o.get("itens") or OV_PADRAO["itens"])
    if not isinstance(d, dict):
        return o
    if isinstance(d.get("on"), bool):
        o["on"] = d["on"]
    if d.get("pos") in OV_POS:
        o["pos"] = d["pos"]
    if isinstance(d.get("tam"), int) and not isinstance(d.get("tam"), bool) and 1 <= d["tam"] <= 3:
        o["tam"] = d["tam"]
    if isinstance(d.get("itens"), list):
        itens = [i for i in OV_ITENS if i in d["itens"]]
        o["itens"] = itens or ["fps"]
    return o


def ov_linhas(itens, v):
    """Linhas do overlay [(rótulo, valor, cor)] a partir dos números de agora. Função pura."""
    def n(x, suf=""):
        return "--" if x is None else f"{x:.0f}{suf}"
    def cor_fps(x):
        return "#9aa4b2" if x is None else "#4ade80" if x >= 60 else "#facc15" if x >= 30 else "#f87171"
    def cor_t(x, quente):
        return "#e2e8f0" if x is None else "#f87171" if x >= quente else "#facc15" if x >= quente - 10 else "#e2e8f0"
    L = []
    for i in itens:
        if i == "fps":
            L.append(("FPS", n(v.get("fps")), cor_fps(v.get("fps"))))
        elif i == "fps1":
            L.append(("1% baixo", n(v.get("fps1")), cor_fps(v.get("fps1"))))
        elif i == "ms":
            ms = v.get("ms")
            L.append(("Quadro", "--" if ms is None else f"{ms:.1f} ms".replace(".", ","), "#e2e8f0"))
        elif i == "cpu":
            L.append(("CPU", n(v.get("cpu"), "%"), "#e2e8f0"))
        elif i == "tcpu":
            if v.get("tcpu") is not None:  # a maioria dos PCs com Windows não informa: aí a linha some
                L.append(("CPU °C", n(v.get("tcpu"), "°"), cor_t(v.get("tcpu"), 90)))
        elif i == "gpu":
            L.append(("GPU", n(v.get("gpu"), "%"), "#e2e8f0"))
        elif i == "tgpu":
            if v.get("tgpu") is not None:
                L.append(("GPU °C", n(v.get("tgpu"), "°"), cor_t(v.get("tgpu"), 83)))
        elif i == "ram":
            L.append(("RAM", n(v.get("ram"), "%"), "#e2e8f0"))
        elif i == "lim" and v.get("lim") in GARGALO_TXT:  # v9.5: quem segura o FPS
            L.append(("Gargalo", *GARGALO_TXT[v["lim"]]))
    return L


# ----- baixar o PresentMon -----

class _PmRedireciona(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        teste = os.environ.get("THBOOST_PM_URL", "")
        if not (teste.startswith("http://127.0.0.1:") and newurl.startswith("http://127.0.0.1:")) and \
                (p.scheme != "https" or p.hostname not in PM_HOSTS):
            raise urllib.error.HTTPError(newurl, code, "redirecionamento recusado", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def pm_url():
    t = os.environ.get("THBOOST_PM_URL", "")
    return t if re.fullmatch(r"http://127\.0\.0\.1:\d{2,5}/[\w./-]+", t) else PM_URL


def pm_baixar(pasta, progresso=None):
    """Baixa o PresentMon oficial e só grava se a impressão digital bater. Devolve o caminho gravado."""
    abridor = urllib.request.build_opener(_PmRedireciona)
    req = urllib.request.Request(pm_url(), headers={"User-Agent": f"ThBoost/{VERSAO}"})
    partes, total = [], 0
    with abridor.open(req, timeout=60) as r:
        while True:
            b = r.read(65536)
            if not b:
                break
            total += len(b)
            if total > PM_TAM * 2:
                raise ValueError("o arquivo veio maior do que o esperado")
            partes.append(b)
            if progresso:
                progresso(min(99, int(total * 100 / PM_TAM)))
    dados = b"".join(partes)
    if hashlib.sha256(dados).hexdigest() != PM_SHA256:
        raise ValueError("a impressão digital do arquivo não confere; nada foi gravado")
    alvo = os.path.join(pasta, PM_NOME)
    tmp = alvo + ".baixando"
    with open(tmp, "wb") as f:
        f.write(dados)
    os.replace(tmp, alvo)
    return alvo


# ----- o processo do overlay (janela por cima do jogo) -----

def overlay_principal(porta, token):
    """Roda a janelinha do FPS na tela. Sai sozinha quando o Th Boost manda desligar ou fecha."""
    try:
        import tkinter as tk
    except ImportError:
        return OV_SEM_TK
    u32 = None
    if IS_WIN:
        try:  # nítido em tela com zoom do Windows
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError, AttributeError):
            pass
        try:
            u32 = ctypes.windll.user32
            u32.GetParent.restype = ctypes.c_void_p
            u32.GetParent.argtypes = [ctypes.c_void_p]
            u32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            u32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
            u32.SetLayeredWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_ubyte, ctypes.c_uint]
            u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        except (OSError, AttributeError):
            u32 = None
    url = f"http://127.0.0.1:{int(porta)}/api/overlay?k={urllib.parse.quote(token)}"
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        root = tk.Tk()
    except tk.TclError:
        return OV_SEM_TK
    root.withdraw()
    root.overrideredirect(True)
    chave = "#010203"  # cor que fica transparente
    root.config(bg=chave)
    try:
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", chave)
        root.attributes("-alpha", 0.93)
    except tk.TclError:
        pass
    caixa = tk.Frame(root, bg="#0b1220", highlightthickness=1, highlightbackground="#1e3a8a")
    caixa.pack(padx=0, pady=0)
    estado = {"falhas": 0, "visivel": True, "alternar": False, "cfg": None, "rotulos": [], "hwnd": None, "mostrou": False,
              "hk": "", "acento": "#8fb3ff", "borda": "#1e3a8a"}

    def prende():  # sem foco, sem clique (o jogo continua recebendo tudo) e fora da barra de tarefas
        if not u32:
            return
        try:
            hwnd = u32.GetParent(root.winfo_id()) or root.winfo_id()
            estado["hwnd"] = hwnd
            ex = u32.GetWindowLongW(hwnd, -20) & 0xFFFFFFFF
            novo = ex | 0x80000 | 0x20 | 0x80 | 0x08000000 | 0x8  # LAYERED, TRANSPARENT (clique passa), TOOLWINDOW, NOACTIVATE, TOPMOST
            u32.SetWindowLongW(hwnd, -20, ctypes.c_long(novo - (1 << 32) if novo >= 1 << 31 else novo).value)
            # cor-chave #010203 vira transparente e o resto fica 93% opaco (feito aqui, para não depender da ordem do Tk)
            u32.SetLayeredWindowAttributes(hwnd, 0x00030201, 237, 0x1 | 0x2)
        except Exception:
            pass

    def no_topo():
        if u32 and estado["hwnd"]:
            try:  # HWND_TOPMOST, sem mover, sem mudar o tamanho, sem pegar o foco
                u32.SetWindowPos(estado["hwnd"], ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            except Exception:
                pass
        root.after(1000, no_topo)

    def monta(cfg, linhas):
        tam = cfg.get("tam", 2)
        f1, f2 = {1: (9, 12), 2: (10, 15), 3: (12, 19)}[tam]
        sig = (tam, tuple(l[0] for l in linhas))
        if estado.get("sig") != sig:
            for w in caixa.winfo_children():
                w.destroy()
            estado["rotulos"] = []
            for r_, (rot, val, cor) in enumerate(linhas):
                a = tk.Label(caixa, text=rot, fg=estado["acento"], bg="#0b1220", font=("Segoe UI", f1, "bold"), anchor="w")
                b = tk.Label(caixa, text=val, fg=cor, bg="#0b1220", font=("Consolas", f2, "bold"), anchor="e")
                a.grid(row=r_, column=0, sticky="w", padx=(10, 12), pady=(4 if r_ == 0 else 0, 4 if r_ == len(linhas) - 1 else 0))
                b.grid(row=r_, column=1, sticky="e", padx=(0, 10))
                estado["rotulos"].append(b)
            estado["sig"] = sig
        for b, (_, val, cor) in zip(estado["rotulos"], linhas):
            if b.cget("text") != val:
                b.config(text=val)
            if b.cget("fg") != cor:
                b.config(fg=cor)
        root.update_idletasks()
        w, h = root.winfo_reqwidth(), root.winfo_reqheight()
        sw, sh, m = root.winfo_screenwidth(), root.winfo_screenheight(), 14
        pos = cfg.get("pos", "se")
        x = m if pos in ("se", "ie") else sw - w - m
        y = m if pos in ("se", "sd") else sh - h - m - 40
        root.geometry(f"+{x}+{y}")

    def atalho():  # Ctrl+Shift+F esconde/mostra (fica numa thread com a fila de mensagens própria do Windows)
        if not IS_WIN:
            return
        try:
            import ctypes.wintypes as _wt
            u = ctypes.windll.user32
            if not u.RegisterHotKey(None, 1, 0x0002 | 0x0004 | 0x4000, 0x46):
                estado["hk"] = "0"  # outro programa já usa Ctrl+Shift+F: o Th Boost avisa na tela
                return
            estado["hk"] = "1"
            msg = _wt.MSG()
            while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    estado["alternar"] = True
        except Exception:
            pass

    def ciclo():
        try:
            with abridor.open(url + (f"&hk={estado['hk']}" if estado["hk"] else ""), timeout=3) as r:
                d = json.loads(r.read() or b"{}")
            estado["falhas"] = 0
        except Exception:
            estado["falhas"] += 1
            if estado["falhas"] >= 10:  # o Th Boost fechou
                root.destroy()
                return
            root.after(500, ciclo)
            return
        if not d.get("on"):
            root.destroy()
            return
        ac, bo = d.get("acento") or "#8fb3ff", d.get("borda") or "#1e3a8a"
        if (ac, bo) != (estado["acento"], estado["borda"]) and re.fullmatch(r"#[0-9a-f]{6}", ac) and re.fullmatch(r"#[0-9a-f]{6}", bo):
            estado["acento"], estado["borda"], estado["sig"] = ac, bo, None  # a cor do painel mudou: remonta
            caixa.config(highlightbackground=bo)
        if estado["alternar"]:
            estado["alternar"] = False
            estado["visivel"] = not estado["visivel"]
        monta(d, [tuple(x) for x in d.get("linhas") or []])
        if estado["visivel"]:
            if not estado["mostrou"] or root.state() == "withdrawn":
                root.deiconify()
                if not estado["mostrou"]:
                    root.update_idletasks()
                    prende()
                    estado["mostrou"] = True
        elif root.state() != "withdrawn":
            root.withdraw()
        root.after(500, ciclo)

    threading.Thread(target=atalho, daemon=True).start()
    root.after(50, ciclo)
    root.after(1500, no_topo)
    root.mainloop()
    return 0


class OverlayMixin:
    """Parte do Nucleo que cuida do FPS na tela e do download do contador de FPS."""

    def ov_iniciar_estado(self):
        self.ov = ov_valida(CONFIG.get("overlay"))
        self.ov["on"] = False  # sempre começa desligado (liga pela tela ou pelo Modo FPS On)
        self.ov_proc = None
        self.ov_trava = threading.Lock()  # nunca duas janelinhas ao mesmo tempo
        self.ov_hk = None  # o atalho Ctrl+Shift+F ficou registrado? (None = ainda não se sabe)
        self.ov_quedas = []  # horários em que a janelinha fechou logo depois de abrir
        self.pm = {"estado": "", "pct": 0, "erro": ""}

    def ov_snapshot(self):
        return {"cfg": dict(self.ov, itens=list(self.ov["itens"])), "rodando": bool(self.ov_proc and self.ov_proc.poll() is None),
                "pm": dict(self.pm), "pm_versao": PM_VERSAO, "atalho": self.ov_hk}

    def ov_dados(self):
        """O que a janelinha mostra (o /api/overlay manda isto a cada meio segundo)."""
        d, g = self.mon.dados, (self.mon.dados.get("gpu") or {})
        try:
            ram = psutil.virtual_memory().percent
        except Exception:
            ram = None
        a = self.amostra or {}
        # CPU %: lida sempre pela mesma linha do programa (o Monitor), senão o número sai errado (0% ou média velha)
        v = {"fps": d.get("fps"), "fps1": d.get("fps1"), "ms": d.get("fps_ms"), "cpu": d.get("cpu_ov"), "ram": ram, "lim": d.get("gargalo"),
             "gpu": g.get("uso"), "tgpu": g.get("temp"), "tcpu": None if self.ocioso else a.get("tcpu")}
        if self.ocioso:  # janela fechada: a amostra para (e fica velha); lê a temperatura daqui (no máximo a cada 5 s)
            agora = time.time()
            if agora - getattr(self, "_ov_tcpu_t", 0) > 5:
                self._ov_tcpu_t = agora
                try:
                    self._ov_tcpu = temp_cpu()
                except Exception:
                    self._ov_tcpu = None
            v["tcpu"] = getattr(self, "_ov_tcpu", None)
        tr = tema_tr()
        return {"on": self.ov["on"], "pos": self.ov["pos"], "tam": self.ov["tam"], "linhas": ov_linhas(self.ov["itens"], v),
                "acento": tom_hex("#8fb3ff", tr), "borda": tom_hex("#1e3a8a", tr)}

    def ov_atalho(self, valor):
        """A janelinha conta se conseguiu o Ctrl+Shift+F (vem junto da leitura dos números)."""
        if valor in ("0", "1"):
            self.ov_hk = valor == "1"

    def ov_definir(self, dados):
        antes = self.ov["on"]
        self.ov = ov_valida(dados, self.ov)
        CONFIG["overlay"] = {k: self.ov[k] for k in ("pos", "tam", "itens")}
        salvar_config()
        if self.ov["on"] and not antes:
            self.ov_quedas = []
            self._ov_abrir(avisar=True)
        elif not self.ov["on"] and antes:
            self.mon.protege = set()
            self.msg("FPS na tela desligado.")
        self.mon.overlay = self.ov["on"]
        self.fps_contador_ajusta()

    def _ov_abrir(self, avisar=False):
        with self.ov_trava:
            self._ov_abrir_travado(avisar)

    def _ov_abrir_travado(self, avisar):
        if not self.ov["on"]:
            return
        if self.ov_proc and self.ov_proc.poll() is None:  # já aberta (por exemplo, desligou e ligou rápido): ela continua
            return
        if getattr(sys, "frozen", False):
            args = [sys.executable, "--overlay", str(PORTA), TOKEN]
        else:
            exe = sys.executable
            if IS_WIN and os.path.basename(exe).lower() == "python.exe":
                w = os.path.join(os.path.dirname(exe), "pythonw.exe")
                if os.path.isfile(w):
                    exe = w
            args = [exe, os.path.abspath(__file__), "--overlay", str(PORTA), TOKEN]
        try:
            self.ov_proc = subprocess.Popen(args, cwd=pasta_do_programa(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if IS_WIN else 0)
            self.ov_aberta_em = time.time()
            self.mon.protege = {self.ov_proc.pid}  # o Modo Leve não baixa a prioridade da janelinha
            if avisar:
                self.msg("FPS na tela ligado. Ctrl+Shift+F esconde e mostra durante o jogo.")
        except OSError:
            self.ov["on"] = False
            self.msg("Não consegui abrir o FPS na tela.")

    def ov_conferir(self):
        """A cada segundo: se a janelinha fechou sozinha, abre de novo; se ela não consegue abrir neste PC, desliga e avisa."""
        if not self.ov["on"]:
            return
        with self.ov_trava:
            p = self.ov_proc
            if not p or p.poll() is None:
                return
            agora, cod = time.time(), p.returncode
            rapida = agora - getattr(self, "ov_aberta_em", 0) < 8  # fechou logo depois de abrir
            if cod != OV_SEM_TK and not rapida and agora - getattr(self, "_ov_reaberto", 0) < 30:
                return  # reabriu há pouco: espera um pouco antes de tentar de novo
            if rapida:
                self.ov_quedas.append(agora)
            self.ov_proc = None
            if cod == OV_SEM_TK or len(self.ov_quedas) >= 2:
                self.ov["on"] = False
                self.mon.overlay = False
                self.mon.protege = set()
                motivo = ("o Python deste computador foi instalado sem a parte de janelas (tcl/tk). Instale o Python de novo pelo "
                          "python.org deixando marcada a opção “tcl/tk and IDLE”, ou use o Th Boost.exe"
                          if cod == OV_SEM_TK else "a janelinha fechou logo depois de abrir")
                self.msg(f"Não deu para mostrar o FPS na tela: {motivo}.")
            else:  # fechou depois de um tempo (por exemplo, o Windows matou): abre de novo
                self._ov_reaberto = agora
                self._ov_abrir_travado(False)
                return
        self.fps_contador_ajusta()

    def ov_fechar(self):
        self.ov["on"] = False
        self.mon.protege = set()
        p = self.ov_proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def fps_contador_ajusta(self):
        """O contador de FPS fica ligado enquanto alguém precisa dele (Modo FPS On, FPS na tela ou o Monitor)."""
        quer = bool(self.modo_fps or self.ov["on"] or getattr(self, "contador_manual", False))
        if quer and not self.mon.fps_ligado and caminho_presentmon():
            self.mon.ligar_fps(True)
        elif not quer and self.mon.fps_ligado:
            self.mon.ligar_fps(False)

    def pm_instalar(self):
        if self.pm["estado"] == "baixando":
            return
        if caminho_presentmon():
            return self.msg("O contador de FPS já está instalado.")
        self.pm = {"estado": "baixando", "pct": 0, "erro": ""}

        def tarefa():
            try:
                pm_baixar(pasta_do_programa(), progresso=lambda p: self.pm.update(pct=p))
            except Exception as e:
                motivo = str(e) if isinstance(e, ValueError) else "não deu para baixar agora (internet ou pasta sem permissão)"
                self.pm = {"estado": "erro", "pct": 0, "erro": f"O contador de FPS não foi instalado: {motivo}."}
                return self.msg(self.pm["erro"])
            self.pm = {"estado": "ok", "pct": 100, "erro": ""}
            self.mon.dados["fps_erro"] = ""
            self.msg("Contador de FPS instalado (PresentMon oficial, conferido). Pronto para usar.")
            self.fps_contador_ajusta()
        threading.Thread(target=tarefa, daemon=True).start()
