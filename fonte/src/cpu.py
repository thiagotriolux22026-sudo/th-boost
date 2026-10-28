# ---------------- limite de CPU dos programas em segundo plano ----------------
#
# Como funciona: o Windows tem "objetos de trabalho" (Job Objects) com um TETO de CPU de verdade ("hard cap"):
# todos os programas colocados no mesmo objeto, JUNTOS, nunca passam de X% da CPU do PC. O limite é do Windows,
# não é enfeite: ele vale mesmo se o programa quiser usar mais.
#
# Regras de segurança:
#  - só entram programas do PRÓPRIO usuário e só de tipos que costumam rodar em segundo plano: navegador, nuvem,
#    atualizador, launcher, ajudante dispensável e programas comuns. Windows, antivírus, drivers, chat/reunião,
#    o próprio Th Boost e qualquer jogo (da lista do Th Boost ou instalado nas pastas comuns de jogos) ficam de fora;
#  - o programa que está na frente (o que você está usando) nunca fica limitado: enquanto ele está em primeiro plano o
#    teto sobe para 100% sozinho e volta quando você troca de janela;
#  - dá para desligar a qualquer hora, e ao fechar o Th Boost o teto é solto (também na próxima abertura, se o
#    programa tiver sido fechado à força);
#  - o que o Windows não deixa limitar (como abas protegidas do navegador) ganha só prioridade baixa, que é devolvida
#    ao normal quando o limite é desligado.

CPU_MIN, CPU_MAX, CPU_PADRAO = 10, 90, 40
CPU_JOB_NOME = "Local\\ThBoost_LimiteCPU"
_CPU_CATS = frozenset({"navegador", "nuvem", "atualizador", "launcher", "dispensavel", "outro"})
_PASTAS_JOGO = ("\\steamapps\\common\\", "\\epic games\\", "\\gog games\\", "\\riot games\\", "\\xboxgames\\",
                "\\ea games\\", "\\origin games\\", "\\ubisoft game launcher\\games\\", "\\games\\")


class _CpuRate(ctypes.Structure):
    _fields_ = [("ControlFlags", ctypes.c_uint32), ("CpuRate", ctypes.c_uint32)]


class ApiJob:
    """Chamadas do Windows (kernel32) usadas pelo limite de CPU. Nos testes entra uma versão falsa."""

    _k = None

    def disponivel(self):
        """O teto de CPU por objeto de trabalho existe do Windows 8 (compilação 9200) em diante."""
        if not IS_WIN:
            return False
        try:
            return sys.getwindowsversion().build >= 9200
        except Exception:
            return False

    def _k32(self):
        if ApiJob._k is None:
            from ctypes import wintypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.CreateJobObjectW.restype = wintypes.HANDLE
            k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            k.OpenJobObjectW.restype = wintypes.HANDLE
            k.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            k.SetInformationJobObject.restype = wintypes.BOOL
            k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            k.AssignProcessToJobObject.restype = wintypes.BOOL
            k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            k.OpenProcess.restype = wintypes.HANDLE
            k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k.CloseHandle.restype = wintypes.BOOL
            k.CloseHandle.argtypes = [wintypes.HANDLE]
            ApiJob._k = k
        return ApiJob._k

    def abrir(self, nome, criar):
        """Abre (ou cria) o objeto de trabalho do Th Boost. Devolve o handle ou None."""
        try:
            k = self._k32()
            h = k.CreateJobObjectW(None, nome) if criar else k.OpenJobObjectW(0x0002 | 0x0004, False, nome)
            return h or None
        except Exception:
            return None

    def teto(self, h, pct):
        """Define o teto de CPU do objeto: pct de 1 a 100 (100 = sem limite). Devolve True se o Windows aceitou."""
        try:
            info = _CpuRate(0x1 | 0x4, int(max(1, min(100, pct))) * 100)  # ENABLE | HARD_CAP, em centésimos de %
            return bool(self._k32().SetInformationJobObject(h, 15, ctypes.byref(info), ctypes.sizeof(info)))
        except Exception:
            return False

    def adicionar(self, h, pid):
        """Coloca o processo no objeto de trabalho. False se o Windows não deixou (processo protegido)."""
        try:
            k = self._k32()
            ph = k.OpenProcess(0x0100 | 0x0001, False, int(pid))  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
            if not ph:
                return False
            try:
                return bool(k.AssignProcessToJobObject(h, ph))
            finally:
                k.CloseHandle(ph)
        except Exception:
            return False

    def fechar(self, h):
        try:
            self._k32().CloseHandle(h)
        except Exception:
            pass


def _prio_baixa(pid, ct):
    """Prioridade baixa para o que o Windows não deixou limitar. True se mexeu."""
    if not IS_WIN:
        return False
    try:
        p = psutil.Process(pid)
        if abs(p.create_time() - ct) > 1.0:
            return False
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        return True
    except (psutil.Error, OSError, AttributeError):
        return False


def _prio_normal(pid, ct):
    if not IS_WIN:
        return False
    try:
        p = psutil.Process(pid)
        if abs(p.create_time() - ct) > 1.0:
            return False
        p.nice(psutil.NORMAL_PRIORITY_CLASS)
        return True
    except (psutil.Error, OSError, AttributeError):
        return False


def _cpu_limpar_pct(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = CPU_PADRAO
    return max(CPU_MIN, min(CPU_MAX, v))


def exe_de_jogo(exe):
    """True se o programa está numa pasta comum de jogos (Steam, Epic, GOG, Riot, Xbox...)."""
    e = (exe or "").lower().replace("/", "\\")
    return any(p in e for p in _PASTAS_JOGO)


def escolher_para_limitar(grupos, exe_por_pid, pids_jogos, ja):
    """Quais processos entram no limite. Devolve lista de (pid, create_time, rótulo)."""
    escolhidos = []
    for g in grupos:
        if g["cat"] not in _CPU_CATS:
            continue
        for pid, ct in g["pids"]:
            if pid in ja or pid in pids_jogos or exe_de_jogo(exe_por_pid.get(pid)):
                continue
            escolhidos.append((pid, ct, g["rotulo"]))
    return escolhidos


class CpuMixin:
    """Teto de CPU para os programas em segundo plano (a barrinha da página Processos)."""

    def cpu_iniciar_estado(self):
        self.cpu_api = ApiJob()
        self._cpu_trava = threading.Lock()
        self._cpu = {"h": None, "pids": {}, "rot": {}, "procs": {}, "falhas": {}, "prio": {}, "teto": None,
                     "t_varrer": 0.0, "uso": None, "liberado": False, "erro": ""}
        try:
            if self.cpu_api.disponivel():  # sobra de uma abertura anterior que fechou sem soltar o teto
                h = self.cpu_api.abrir(CPU_JOB_NOME, False)
                if h:
                    self.cpu_api.teto(h, 100)
                    self.cpu_api.fechar(h)
        except Exception:
            pass

    @staticmethod
    def _cpu_cfg():
        c = CONFIG.get("cpu_limite") if isinstance(CONFIG.get("cpu_limite"), dict) else {}
        return bool(c.get("ligado")), _cpu_limpar_pct(c.get("pct"))

    def cpu_estado(self):
        ligado, pct = self._cpu_cfg()
        c = self._cpu
        nomes = {}
        for r in c["rot"].values():
            nomes[r] = nomes.get(r, 0) + 1
        top = sorted(nomes.items(), key=lambda x: -x[1])[:5]
        return {"disponivel": bool(self.cpu_api.disponivel()), "ligado": ligado, "pct": pct, "min": CPU_MIN, "max": CPU_MAX,
                "n": len(c["pids"]), "falhas": len(c["falhas"]), "uso": c["uso"], "liberado": c["liberado"],
                "nomes": [{"nome": n, "qtd": q} for n, q in top], "erro": c["erro"]}

    # ----- ligar / desligar / mudar o teto -----

    def t_cpu_definir(self, ligar, pct):
        if not self.cpu_api.disponivel():
            return "O limite de CPU precisa do Windows 8 ou mais novo."
        pct = _cpu_limpar_pct(pct)
        ja_estava = self._cpu_cfg()[0]
        CONFIG["cpu_limite"] = {"ligado": bool(ligar), "pct": pct}
        salvar_config()
        if not ligar:
            n = self.cpu_soltar()
            return f"Limite de CPU desligado. {n} programa(s) voltaram a poder usar toda a CPU." if n else "Limite de CPU desligado."
        self._cpu_passo(forcar=True)
        c = self._cpu
        if c["erro"]:
            return c["erro"]
        quem = ", ".join(f"{x['nome']}" for x in self.cpu_estado()["nomes"][:3])
        if not c["pids"]:
            return f"Limite de {pct}% ligado. Nenhum programa em segundo plano para limitar agora; os que abrirem depois entram sozinhos."
        return (f"Limite de {pct}% ligado para {len(c['pids'])} processo(s) em segundo plano"
                + (f" ({quem})" if quem else "") + (". O programa que você está usando fica sem limite." if not ja_estava else "."))

    def cpu_definir(self, ligar, pct):
        if not isinstance(ligar, bool) or isinstance(pct, bool) or not isinstance(pct, int):
            raise ValueError("opções inválidas")
        self.em_fundo(lambda: self.t_cpu_definir(ligar, pct))

    def cpu_soltar(self):
        """Tira o teto e devolve as prioridades. Devolve quantos processos estavam no limite."""
        with self._cpu_trava:
            c = self._cpu
            n = len(c["pids"])
            if c["h"] is not None:
                self.cpu_api.teto(c["h"], 100)
            for pid, ct in list(c["prio"].items()):
                _prio_normal(pid, ct)
            c.update(pids={}, rot={}, procs={}, falhas={}, prio={}, teto=100 if c["h"] is not None else None,
                     uso=None, liberado=False, erro="")
            return n

    def cpu_fechar(self):
        """Ao encerrar o Th Boost: solta o teto e fecha o objeto."""
        try:
            self.cpu_soltar()
            with self._cpu_trava:
                if self._cpu["h"] is not None:
                    self.cpu_api.fechar(self._cpu["h"])
                    self._cpu["h"] = None
        except Exception:
            pass

    # ----- o passo que roda a cada 2 segundos -----

    def _cpu_pids_jogos(self):
        """Processos dos jogos da lista do Th Boost (nunca limitados)."""
        pids = set()
        pastas = [_norm(j["pasta"]).rstrip("\\/") + os.sep for j in list(getattr(self, "jogos", []) or []) if j.get("pasta")]
        if not pastas:
            return pids
        for p in psutil.process_iter(["pid", "exe"]):
            try:
                exe = p.info.get("exe")
                if exe and any(_norm(exe).startswith(b) for b in pastas):
                    pids.add(p.info["pid"])
            except (psutil.Error, OSError):
                continue
        return pids

    def _cpu_varrer(self):
        c = self._cpu
        procs = _ler_processos()
        d = escanear_processos(procs)
        exes = {p["pid"]: p["exe"] for p in procs}
        # tira quem fechou (ou cujo número foi reaproveitado por outro programa)
        vivos = {p["pid"]: p["ct"] for p in procs}
        for pid in list(c["pids"]):
            if abs(vivos.get(pid, -1.0) - c["pids"][pid]) > 1.0:
                for k in ("pids", "rot", "procs", "falhas", "prio"):
                    c[k].pop(pid, None)
        for pid in list(c["falhas"]):
            if abs(vivos.get(pid, -1.0) - c["falhas"][pid]) > 1.0:
                c["falhas"].pop(pid, None)
                c["prio"].pop(pid, None)
        ja = set(c["pids"]) | set(c["falhas"])
        for pid, ct, rot in escolher_para_limitar(d["grupos"], exes, self._cpu_pids_jogos(), ja):
            if self.cpu_api.adicionar(c["h"], pid):
                c["pids"][pid] = ct
                c["rot"][pid] = rot
                try:
                    c["procs"][pid] = psutil.Process(pid)
                except (psutil.Error, OSError):
                    pass
            else:
                c["falhas"][pid] = ct
                if _prio_baixa(pid, ct):
                    c["prio"][pid] = ct

    def _cpu_passo(self, forcar=False):
        ligado, pct = self._cpu_cfg()
        if not ligado or not self.cpu_api.disponivel():
            if self._cpu["pids"] or self._cpu["prio"]:
                self.cpu_soltar()
            return
        with self._cpu_trava:
            c = self._cpu
            if c["h"] is None:
                c["h"] = self.cpu_api.abrir(CPU_JOB_NOME, True)
                if c["h"] is None:
                    c["erro"] = "O Windows não deixou criar o limite de CPU agora."
                    return
                c["teto"] = None
            c["erro"] = ""
            agora = time.time()
            if forcar or agora - c["t_varrer"] > 10:
                self._cpu_varrer()
                c["t_varrer"] = agora
            frente = pid_em_primeiro_plano()
            libera = frente in c["pids"]  # o programa em uso nunca fica limitado
            alvo = 100 if libera else pct
            if alvo != c["teto"]:
                if self.cpu_api.teto(c["h"], alvo):
                    c["teto"] = alvo
                else:
                    c["erro"] = "O Windows não aceitou o limite de CPU."
            c["liberado"] = libera
            total = 0.0
            for pid, p in list(c["procs"].items()):
                try:
                    total += p.cpu_percent(None)
                except (psutil.Error, OSError):
                    c["procs"].pop(pid, None)
            c["uso"] = round(total / max(1, psutil.cpu_count() or 1), 1)

    def _vigiar_cpu(self):
        while not self.fechando:
            time.sleep(2)
            try:
                self._cpu_passo()
            except Exception:
                continue
