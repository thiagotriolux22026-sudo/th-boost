# ---------------- jogos: perfil por jogo, "Otimizar antes de jogar" e vigia automático ----------------
#
# O que realmente aumenta o FPS (e o que o Th Boost faz aqui):
#  - tirar peso de segundo plano (programas, serviços do Windows Update, indexação) enquanto o jogo roda;
#  - plano de energia de desempenho e RAM livre;
#  - dizer ao Windows para usar a placa de vídeo de ALTO desempenho no jogo (decisivo em notebook com 2 placas);
#  - prioridade alta ao processo do jogo;
#  - ajustes de Windows que tiram trabalho do jogo (Game DVR, Game Bar, MMCSS, mouse).
# Nada aqui inventa FPS: o ganho depende do PC. Tudo que muda é desfeito ao terminar a sessão ou pelo botão da tela.

_GPU_CHAVE = r"Software\Microsoft\DirectX\UserGpuPreferences"
_FSO_CHAVE = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
_FSO_FLAG = "DISABLEDXMAXIMIZEDWINDOWEDMODE"
_IGNORAR_EXE = re.compile(
    r"(unins|crash|report|redist|vcredist|vc_redist|dxsetup|dotnet|install|setup|easyanticheat|eac_|beservice|battleye|"
    r"patcher|helper|cefsubprocess|ue4prereq|prereq|updater|webhelper|errorreporter|benchmark|configtool|"
    r"launcher_|notification_helper|vulkan|zip|7z)", re.IGNORECASE)

# pacote de ajustes de FPS (ids do catálogo) que o "Otimizar antes de jogar" liga, se ainda estiverem desligados
FPS_PACOTE = ["modo_jogo", "game_dvr", "fps_dvr_politica", "fps_gamebar", "prioridade_jogos", "mouse_acel",
              "rede_throttle", "rede_nagle"]
# lista completa mostrada na página Jogos (inclui os de risco médio, que só ligam por escolha da pessoa)
FPS_LISTA = FPS_PACOTE + ["fps_energia_throttle", "hags", "fps_vbs"]
# serviços que podem ser parados só enquanto o jogo roda (voltam sozinhos ao terminar a sessão)
SERVICOS_PAUSA = [("wuauserv", "Windows Update"), ("BITS", "Transferência em segundo plano"),
                  ("DoSvc", "Entrega de atualizações"), ("WSearch", "Indexação de arquivos")]
PRE_PADRAO = {"fechar": True, "ram": True, "energia": True, "ajustes": True, "gpu": True, "pausar": True,
              "leve": True, "prioridade": True, "fso": False, "abrir": True}
PLANO_BOM = re.compile(r"alto desempenho|high performance|desempenho m[aá]ximo|ultimate|th boost", re.IGNORECASE)
MAX_EXES = 6


# ---------- executáveis do jogo ----------

def _exe_valido(exe):
    return (isinstance(exe, str) and 8 < len(exe) < 300 and os.path.isabs(exe) and exe.lower().endswith(".exe")
            and not re.search(r"[;\"<>|*?]", exe))


def exes_do_jogo(pasta, limite=MAX_EXES):
    """Os programas principais (.exe) de um jogo: os maiores da pasta, sem instaladores nem ajudantes."""
    if not pasta or not os.path.isabs(pasta) or not os.path.isdir(pasta) or _e_ligacao(pasta):
        return []
    achados = []
    base_n = _norm(pasta)
    pilha = [(pasta, 0)]
    visitadas = 0
    while pilha and visitadas < 500:
        atual, nivel = pilha.pop()
        visitadas += 1
        try:
            entradas = list(os.scandir(atual))
        except OSError:
            continue
        for e in entradas:
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    if nivel < 4 and not _atributo_ligacao(e.stat(follow_symlinks=False)):
                        pilha.append((e.path, nivel + 1))
                elif e.name.lower().endswith(".exe") and not _IGNORAR_EXE.search(e.name):
                    tam = e.stat(follow_symlinks=False).st_size
                    if tam >= 1_000_000 and _norm(e.path).startswith(base_n):
                        achados.append((tam, e.path))
            except OSError:
                continue
    achados.sort(reverse=True)
    return [c for _, c in achados[:limite]]


# ---------- placa de vídeo de alto desempenho e tela cheia, por jogo (desfazíveis) ----------

def gpu_alto_aplicar(exes):
    """Diz ao Windows para usar a GPU de alto desempenho nestes jogos. Devolve os que mudaram."""
    if REG is None:
        return []
    feitos = []
    with TRAVA_AJ:
        bk = _backup().setdefault("_gpu_pref", {})
        for exe in exes:
            if not _exe_valido(exe):
                continue
            atual = REG.ler("HKCU", _GPU_CHAVE, exe)
            if isinstance(atual, str) and "GpuPreference=2" in atual:
                continue
            bk.setdefault(exe, atual)  # None = não existia
            REG.escrever("HKCU", _GPU_CHAVE, exe, "GpuPreference=2;", "sz")
            feitos.append(exe)
        if not bk:
            _backup().pop("_gpu_pref", None)
        _guardar_backup()
    return feitos


def gpu_alto_remover(exes=None):
    """Devolve a preferência de GPU de antes. exes=None desfaz todas as que o Th Boost mexeu. Devolve a quantidade."""
    if REG is None:
        return 0
    with TRAVA_AJ:
        bk = _backup().get("_gpu_pref") or {}
        alvo = list(bk) if exes is None else [e for e in exes if e in bk]
        for exe in alvo:
            antes = bk.pop(exe)
            if antes is None:
                REG.apagar("HKCU", _GPU_CHAVE, exe)
            else:
                REG.escrever("HKCU", _GPU_CHAVE, exe, antes, "sz")
        if not bk:
            _backup().pop("_gpu_pref", None)
        _guardar_backup()
    return len(alvo)


def fso_desligar(exes):
    """Desliga as 'otimizações de tela cheia' do Windows para estes jogos (ajuda alguns jogos a parar de engasgar)."""
    if REG is None:
        return []
    feitos = []
    with TRAVA_AJ:
        bk = _backup().setdefault("_fso", {})
        for exe in exes:
            if not _exe_valido(exe):
                continue
            atual = REG.ler("HKCU", _FSO_CHAVE, exe)
            partes = str(atual).split() if atual else []
            if _FSO_FLAG in partes:
                continue
            bk.setdefault(exe, atual)
            novo = " ".join((["~"] if "~" not in partes else []) + partes + [_FSO_FLAG])
            REG.escrever("HKCU", _FSO_CHAVE, exe, novo, "sz")
            feitos.append(exe)
        if not bk:
            _backup().pop("_fso", None)
        _guardar_backup()
    return feitos


def fso_restaurar(exes=None):
    if REG is None:
        return 0
    with TRAVA_AJ:
        bk = _backup().get("_fso") or {}
        alvo = list(bk) if exes is None else [e for e in exes if e in bk]
        for exe in alvo:
            antes = bk.pop(exe)
            if antes is None:
                REG.apagar("HKCU", _FSO_CHAVE, exe)
            else:
                REG.escrever("HKCU", _FSO_CHAVE, exe, antes, "sz")
        if not bk:
            _backup().pop("_fso", None)
        _guardar_backup()
    return len(alvo)


# ---------- taxa de atualização e placas de vídeo ----------

def info_monitor():
    """Resolução, taxa de atualização atual e máxima do monitor, e as placas de vídeo (lido pelo Windows)."""
    cod, saida = powershell("Get-CimInstance Win32_VideoController | Select-Object Name,CurrentRefreshRate,MaxRefreshRate,"
                            "CurrentHorizontalResolution,CurrentVerticalResolution | ConvertTo-Json -Compress", tempo=30)
    if cod != 0 or not saida.strip():
        return None
    try:
        dados = json.loads(saida)
    except ValueError:
        return None
    if isinstance(dados, dict):
        dados = [dados]
    placas, hz, hz_max, res = [], 0, 0, ""
    for d in dados if isinstance(dados, list) else []:
        if not isinstance(d, dict):
            continue
        nome = str(d.get("Name") or "").strip()
        if nome:
            placas.append(nome)
        atual = int(d.get("CurrentRefreshRate") or 0)
        if atual and not hz:
            hz, res = atual, f"{d.get('CurrentHorizontalResolution') or '?'}x{d.get('CurrentVerticalResolution') or '?'}"
        hz_max = max(hz_max, int(d.get("MaxRefreshRate") or 0), atual)
    if not hz:
        return None
    return {"hz": hz, "hz_max": hz_max, "res": res, "placas": placas[:4]}


# ---------- a sessão de jogo ----------

class JogosMixin:
    """Parte do Nucleo que cuida do 'Otimizar antes de jogar'. Roda os passos numa thread; a tela acompanha pelo estado."""

    def jogos_iniciar_estado(self):
        self.pre = {"ativo": False, "fracao": 0.0, "passo": "", "jogo": "", "passos": [], "resumo": None, "fim": 0,
                    "opcoes": dict(PRE_PADRAO)}
        self.sessao = None
        self.monitor = {"estado": "nenhum", "dados": None}
        self._pre_pular = False
        salvo = CONFIG.get("pre_opcoes")
        if isinstance(salvo, dict):
            for k in PRE_PADRAO:
                if isinstance(salvo.get(k), bool):
                    self.pre["opcoes"][k] = salvo[k]

    def pre_snapshot(self):
        p = dict(self.pre)
        p["passos"] = [dict(x) for x in self.pre["passos"]]
        p["opcoes"] = dict(self.pre["opcoes"])
        return p

    def sessao_snapshot(self):
        s = self.sessao
        if not s:
            return None
        return {"jogo": s["jogo"], "desde": int(time.time() - s["inicio"]), "pid": bool(s.get("pid")),
                "parados": [n for _, n in s.get("servicos_nomes", [])], "plano": bool(s.get("plano_anterior")),
                "aguardando": bool(s.get("aguardando")), "auto": bool(s.get("auto"))}

    # ----- leitura do monitor (só quando a página Jogos é aberta) -----

    def monitor_ler(self):
        if self.monitor["estado"] == "lendo":
            return
        self.monitor["estado"] = "lendo"

        def tarefa():
            try:
                self.monitor["dados"] = info_monitor()
                self.monitor["estado"] = "pronto"
            except Exception:
                self.monitor["estado"] = "erro"
        threading.Thread(target=tarefa, daemon=True).start()

    # ----- opções -----

    def pre_definir_opcoes(self, novas):
        for k, v in novas.items():
            if k in PRE_PADRAO and isinstance(v, bool):
                self.pre["opcoes"][k] = v
        CONFIG["pre_opcoes"] = dict(self.pre["opcoes"])
        salvar_config()

    # ----- plano dos passos -----

    def _pre_plano(self, j, op):
        P = []
        if op["fechar"]:
            P.append(("processos", "Fechando o que pesa em segundo plano", self._p_processos))
        if op["ram"]:
            P.append(("ram", "Liberando a RAM", self._p_ram))
        if op["energia"]:
            P.append(("energia", "Plano de energia de desempenho", self._p_energia))
        if op["ajustes"]:
            P.append(("ajustes", "Ajustes de FPS do Windows", self._p_ajustes))
        if op["gpu"] and j and j.get("pasta"):
            P.append(("gpu", "Placa de vídeo de alto desempenho no jogo", self._p_gpu))
        if op["pausar"]:
            P.append(("pausar", "Pausando o Windows Update e a indexação", self._p_pausar))
        if op["leve"]:
            P.append(("leve", "Dando prioridade ao jogo", self._p_leve))
        return P

    def pre_iniciar(self, i=None, opcoes=None, auto=False, pid=None):
        """Roda a otimização antes de jogar. i = índice do jogo (ou None para só otimizar o PC)."""
        if self.pre["ativo"] or self.ext["ativo"] or self.otim["ativo"]:
            return self.msg("Já estou otimizando, aguarde.")
        if self.sessao:  # uma sessão nova por cima perderia o que a anterior precisa devolver (serviços, plano de energia)
            return self.msg("Já existe uma sessão de jogo ativa. Toque em “Terminar sessão” para devolver tudo ao normal antes de começar outra.")
        j = self.jogo(i) if i is not None else None
        if i is not None and not j:
            return
        op = dict(self.pre["opcoes"])
        op.update({k: v for k, v in (opcoes or {}).items() if k in PRE_PADRAO and isinstance(v, bool)})
        passos = self._pre_plano(j, op)
        nome = j["nome"] if j else ""
        self.pre.update({"ativo": True, "fracao": 0.02, "passo": "Preparando...", "jogo": nome, "resumo": None})
        self.pre["passos"] = [{"id": p[0], "nome": p[1], "estado": "pendente", "texto": "", "mb": 0.0} for p in passos]
        self._pre_pular = False
        self.msg(f"Otimizando para jogar{(' ' + nome) if nome else ''}...")
        threading.Thread(target=self._pre_rodar, args=(j, op, passos, auto, pid), daemon=True).start()

    def _pre_rodar(self, j, op, passos, auto, pid):
        E = self.pre
        adm = e_admin()
        ctx = {"jogo": j, "op": op, "ajustes": 0, "plano_anterior": None, "servicos": [], "gpu": 0, "fechados": [],
               "ram_mb": 0.0, "leve_antes": self.mon.modo_leve, "adm": adm}
        sessao_ok = False
        try:
            antes = self._medidas()
            n = max(1, len(passos))
            for k, (pid_, nome, func) in enumerate(passos):
                P = E["passos"][k]
                E["passo"] = nome + "..."
                E["fracao"] = max(0.02, k / n)
                P["estado"] = "rodando"
                inicio = time.time()
                try:
                    texto, estado = func(ctx)
                except Exception as erro:
                    texto, estado = f"Erro: {erro}", "erro"
                time.sleep(max(0.0, 0.45 - (time.time() - inicio)))
                P.update(estado=estado, texto=texto)
                E["fracao"] = (k + 1) / n
            depois = self._medidas()
            ram = max(0.0, (depois.get("ram_livre") or 0) - (antes.get("ram_livre") or 0))
            E["resumo"] = {"ajustes": ctx["ajustes"], "fechados": ctx["fechados"], "plano": bool(ctx["plano_anterior"]),
                           "pausados": [n_ for _, n_ in ctx["servicos"]], "gpu": ctx["gpu"], "ram_gb": round(ram, 2),
                           "ram_livre": depois.get("ram_livre"), "processos": [antes.get("processos"), depois.get("processos")],
                           "jogo": E["jogo"], "leve": bool(op["leve"])}
            sessao_ok = True
        except Exception as erro:
            self.msg(f"A otimização para jogar parou por um erro: {erro}")
        finally:
            E["passo"] = "Pronto"
            E["fracao"] = 1.0
            E["ativo"] = False
            E["fim"] += 1
        if not sessao_ok:
            self._sessao_restaurar_parcial(ctx)
            return
        self._sessao_abrir(ctx, j, op, auto, pid)

    # ----- passos -----

    def _p_processos(self, ctx):
        nomes = fechar_dispensaveis()
        ctx["fechados"] = nomes
        return (("Fechei: " + ", ".join(nomes) + ".") if nomes else "Nada pesado rodando escondido."), "ok"

    def _p_ram(self, ctx):
        b, texto = liberar_ram()
        ctx["ram_mb"] = b / 1048576
        return texto, "ok"

    def _p_energia(self, ctx):
        if REG is None:
            return "Só funciona no Windows.", "pulado"
        planos = listar_planos()
        ativo = next((p for p in planos if p["ativo"]), None)
        if ativo and PLANO_BOM.search(ativo["nome"]):
            return f"O plano “{ativo['nome']}” já é de desempenho.", "ok"
        txt = ativar_plano("alto")
        if "ativado" in txt:
            ctx["plano_anterior"] = ativo["guid"] if ativo else PLANOS_CONHECIDOS["equilibrado"][0]
            return txt + " Volta ao normal quando a sessão terminar.", "ok"
        return txt, "erro"

    def _p_ajustes(self, ctx):
        if REG is None:
            return "Só funciona no Windows.", "pulado"
        feitos = ja = sem_adm = 0
        for ident in FPS_PACOTE:
            a = POR_ID.get(ident)
            if a is None or not a.disponivel():
                continue
            try:
                est = a.estado()
            except Exception:
                est = None
            if est is None:
                continue
            if est is True:
                ja += 1
                continue
            if a.precisa_admin and not ctx["adm"]:
                sem_adm += 1
                continue
            try:
                a.ligar()
                if a.estado() is True:
                    feitos += 1
            except OSError:
                pass
        ctx["ajustes"] = feitos
        self.atualizar_aj()
        partes = [f"{feitos} ligado(s)", f"{ja} já estava(m) ligado(s)"]
        if sem_adm:
            partes.append(f"{sem_adm} precisa(m) de Administrador")
        return ", ".join(partes) + ". Ficam ligados; dá para desligar na lista de ajustes de FPS.", "ok"

    def _p_gpu(self, ctx):
        j = ctx["jogo"]
        exes = exes_da_entrada(j)
        if not exes:
            return "Não achei o programa do jogo na pasta dele.", "pulado"
        feitos = gpu_alto_aplicar(exes)
        ctx["gpu"] = len(exes)
        txt = f"{len(exes)} programa(s) do jogo usam a placa de vídeo de alto desempenho."
        if ctx["op"]["fso"]:
            f = fso_desligar(exes)
            txt += f" Otimização de tela cheia desligada em {len(f)}." if f else " Otimização de tela cheia já estava desligada."
        return txt, "ok"

    def _p_pausar(self, ctx):
        if not ctx["adm"]:
            return "Precisa de Administrador.", "pulado"
        parados = []
        for svc, nome in SERVICOS_PAUSA:
            cod, saida = executar(["sc", "query", svc])
            if cod == 0 and re.search(r"RUNNING|EM EXECU", saida or "", re.IGNORECASE):
                executar(["sc", "stop", svc], timeout=30)
                parados.append((svc, nome))
        ctx["servicos"] = parados
        return (("Pausei: " + ", ".join(n for _, n in parados) + ". Voltam quando a sessão terminar.") if parados
                else "Nada disso estava rodando."), "ok"

    def _p_leve(self, ctx):
        if not self.mon.modo_leve:
            self.mon.modo_leve = True
            self.mon.forcar = True
        return "Os outros programas ficam com prioridade menor e o jogo em foco com prioridade alta.", "ok"

    # ----- sessão: dura enquanto o jogo roda e devolve tudo ao terminar -----

    def _sessao_abrir(self, ctx, j, op, auto, pid):
        s = {"jogo": ctx["jogo"]["nome"] if ctx["jogo"] else "", "inicio": time.time(), "pid": pid, "auto": auto,
             "pasta": (ctx["jogo"] or {}).get("pasta") or "", "plano_anterior": ctx["plano_anterior"],
             "servicos_nomes": ctx["servicos"], "leve_antes": ctx["leve_antes"], "leve": bool(op["leve"]),
             "aguardando": False}
        tem_algo = s["plano_anterior"] or s["servicos_nomes"] or (op["leve"] and not s["leve_antes"])
        if not tem_algo and not j:
            self.msg("Pronto para jogar! Nada precisou voltar ao normal depois.")
            return
        self.sessao = s
        if j and op["abrir"] and not pid:
            s["aguardando"] = True
            self.msg(f"Abrindo {j['nome']}..." if lancar_jogo(j["abrir"]) else f"Não consegui abrir {j['nome']}.")
        else:
            self.msg("Pronto para jogar! Quando terminar, o Th Boost devolve tudo ao normal.")
        threading.Thread(target=self._sessao_vigiar, args=(s,), daemon=True).start()

    def _pids_do_jogo(self, pasta):
        if not pasta:
            return []
        base = _norm(pasta).rstrip("\\/") + os.sep
        achados = []
        for p in psutil.process_iter(["pid", "exe"]):
            try:
                exe = p.info.get("exe")
                if exe and _norm(exe).startswith(base):
                    achados.append(p)
            except (psutil.Error, OSError):
                continue
        return achados

    def _sessao_vigiar(self, s):
        """Espera o jogo abrir, dá prioridade alta a ele e, quando fechar, devolve tudo ao normal."""
        espera = time.time()
        visto, ausentes = False, 0
        while not self.fechando and self.sessao is s:
            procs = self._pids_do_jogo(s["pasta"]) if s["pasta"] else []
            if procs:
                visto, ausentes = True, 0
                s["aguardando"] = False
                if s.get("prioridade_ok") != len(procs):
                    for p in procs:
                        try:
                            p.nice(psutil.HIGH_PRIORITY_CLASS)
                            self.mon.fixos.add(p.pid)
                        except (psutil.Error, OSError):
                            pass
                    s["prioridade_ok"] = len(procs)
            elif visto:
                ausentes += 1
                if ausentes >= 2:
                    break
            elif s["pasta"] and time.time() - espera > 240:
                self.msg(f"Não vi {s['jogo'] or 'o jogo'} abrir. Encerrei a sessão e devolvi tudo ao normal.")
                break
            elif not s["pasta"] and not s.get("pid"):
                return  # sessão manual (sem jogo): fica até a pessoa terminar pelo botão
            time.sleep(3)
        if self.sessao is s:
            self.sessao_fim("O jogo fechou")

    def sessao_fim(self, motivo="Sessão terminada"):
        s = self.sessao
        if not s:
            return
        self.sessao = None
        self.mon.fixos.clear()
        feitos = []
        if s.get("servicos_nomes") and e_admin():
            for svc, nome in s["servicos_nomes"]:
                executar(["sc", "start", svc], timeout=30)
            feitos.append("serviços de volta")
        if s.get("plano_anterior"):
            planos = {p["guid"] for p in listar_planos()}
            alvo = s["plano_anterior"] if s["plano_anterior"] in planos else PLANOS_CONHECIDOS["equilibrado"][0]
            executar(["powercfg", "/setactive", alvo])
            feitos.append("plano de energia de antes")
        if s.get("leve") and not s.get("leve_antes"):
            self.mon.modo_leve = False
            self.mon.forcar = True
            feitos.append("prioridades normais")
        self.msg(f"{motivo}. " + (("De volta ao normal: " + ", ".join(feitos) + ".") if feitos else "Nada precisou voltar."))

    def _sessao_restaurar_parcial(self, ctx):
        """A otimização parou no meio por erro: devolve o que já tinha sido mexido."""
        if ctx["servicos"] and e_admin():
            for svc, _ in ctx["servicos"]:
                executar(["sc", "start", svc], timeout=30)
        if ctx["plano_anterior"]:
            executar(["powercfg", "/setactive", ctx["plano_anterior"]])

    # ----- desfazer os perfis por jogo -----

    def jogos_perfis(self):
        """Quantos programas de jogo têm preferência de placa de vídeo / tela cheia mexidas pelo Th Boost."""
        with TRAVA_AJ:
            bk = _backup()
            return {"gpu": len(bk.get("_gpu_pref") or {}), "fso": len(bk.get("_fso") or {})}

    def jogos_desfazer_perfis(self):
        a = gpu_alto_remover()
        b = fso_restaurar()
        return f"Perfis de jogo desfeitos: {a} de placa de vídeo e {b} de tela cheia voltaram ao que eram."

    # ----- vigia: otimiza sozinho quando um jogo abre -----

    def _jogo_aberto(self):
        """Percorre os programas abertos uma vez só e devolve (posição do jogo, programa) do primeiro jogo da lista que está rodando."""
        bases = []
        for idx, j in enumerate(list(self.jogos)):
            pasta = j.get("pasta")
            if pasta:
                bases.append((_norm(pasta).rstrip("\\/") + os.sep, idx))
        if not bases:
            return None
        for p in psutil.process_iter(["pid", "exe"]):
            try:
                exe = p.info.get("exe")
                if not exe:
                    continue
                n = _norm(exe)
                for base, idx in bases:
                    if n.startswith(base):
                        return idx, p
            except (psutil.Error, OSError):
                continue
        return None

    def _vigiar_jogos(self):
        ultimo = {"pid": None, "t": 0}
        while not self.fechando:
            time.sleep(5)
            try:
                if (not CONFIG.get("auto_jogo") or self.sessao or self.pre["ativo"] or self.ext["ativo"]
                        or self.otim["ativo"] or not self.jogos):
                    continue
                achou = self._jogo_aberto()
                if achou:
                    idx, proc = achou
                    if ultimo["pid"] != proc.pid:
                        ultimo.update(pid=proc.pid, t=time.time())
                        self.msg(f"Vi {self.jogos[idx]['nome']} abrindo: otimizando sozinho...")
                        self.pre_iniciar(idx, {"abrir": False}, auto=True, pid=proc.pid)
            except Exception:
                continue
