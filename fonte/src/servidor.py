

# ---------------- estado compartilhado, histórico e tarefas ----------------

# ---------------- modo segundo plano (a janela fecha, o programa continua) ----------------

ARQ_CONFIG = os.environ.get("TOTIMIZE_CONFIG") or os.path.join(pasta_do_programa(), "th_boost_config.json")
CONFIG = {"segundo_plano": False}


def _nome_limpo(valor):
    """Nome que aparece em 'Olá, ...': sem caracteres de controle nem < >, até 24 letras. '' se vier vazio."""
    if not isinstance(valor, str):
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f<>]", "", valor)).strip()[:24]


def nome_da_pessoa():
    """O nome escolhido pela pessoa; se ainda não escolheu, o nome do usuário do Windows deste computador."""
    return _nome_limpo(CONFIG.get("nome")) or _nome_limpo(USUARIO.title()) or "Jogador"


def carregar_config():
    try:
        with open(ARQ_CONFIG, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(dados, dict):
        return
    CONFIG["segundo_plano"] = dados.get("segundo_plano") is True
    for k in ("stats", "backup", "pre_opcoes"):
        if isinstance(dados.get(k), dict):
            CONFIG[k] = dados[k]
    if isinstance(dados.get("auto_jogo"), bool):
        CONFIG["auto_jogo"] = dados["auto_jogo"]
    nome = _nome_limpo(dados.get("nome"))
    if nome:
        CONFIG["nome"] = nome
    manuais = []
    for i in (dados.get("jogos_manuais") or [])[:60] if isinstance(dados.get("jogos_manuais"), list) else []:
        if isinstance(i, dict) and isinstance(i.get("exe"), str) and isinstance(i.get("nome"), str):
            manuais.append({"nome": i["nome"][:60], "exe": i["exe"][:300]})
    if manuais:
        CONFIG["jogos_manuais"] = manuais
    if isinstance(dados.get("jogos_ocultos"), list):
        CONFIG["jogos_ocultos"] = [c for c in dados["jogos_ocultos"] if isinstance(c, str) and len(c) < 120][:300]
    if isinstance(dados.get("proc_ids"), list):
        CONFIG["proc_ids"] = [i for i in dados["proc_ids"] if isinstance(i, str)][:60]
    cl = dados.get("cpu_limite")
    if isinstance(cl, dict):
        CONFIG["cpu_limite"] = {"ligado": cl.get("ligado") is True, "pct": _cpu_limpar_pct(cl.get("pct"))}
    if dados.get("oc_ativo") is True:
        CONFIG["oc_ativo"] = True
    cpp = dados.get("cpu_perfil")
    if (isinstance(cpp, dict) and cpp.get("nivel") in PERFIS_CPU and isinstance(cpp.get("plano"), str)
            and re.fullmatch(_GUID, cpp["plano"]) and isinstance(cpp.get("antes"), dict)):
        CONFIG["cpu_perfil"] = {"nivel": cpp["nivel"], "plano": cpp["plano"].lower(),
                                "antes": {k: v for k, v in cpp["antes"].items()
                                          if k in _CFG_CPU and isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 100}}
    pb = dados.get("proc_base")
    if isinstance(pb, dict) and isinstance(pb.get("n"), int) and not isinstance(pb.get("n"), bool) and 0 < pb["n"] < 100000:
        CONFIG["proc_base"] = {"n": pb["n"], "t": float(pb.get("t") or 0), "boot": float(pb.get("boot") or 0)}


def salvar_config():
    try:
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=1)
    except OSError:
        pass  # sem permissão de escrita na pasta: vale só até fechar o programa


def _pasta_dados():
    base = (os.environ.get("LOCALAPPDATA") if IS_WIN else None) or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "ThBoost")


# Quem abre o Th Boost de novo lê este arquivo para falar com o que já está rodando, em vez de abrir outro.
ARQ_INSTANCIA = os.environ.get("TOTIMIZE_INSTANCIA") or os.path.join(_pasta_dados(), "instancia.json")
USAR_INSTANCIA = (not os.environ.get("TOTIMIZE_SEM_JANELA")) or bool(os.environ.get("TOTIMIZE_INSTANCIA"))


def _chamar(inst, caminho, corpo=None):
    """Fala com um Th Boost já aberto (sem passar por proxy). Devolve o JSON da resposta ou None."""
    url = f"http://127.0.0.1:{int(inst['porta'])}{caminho}?k={urllib.parse.quote(str(inst['token']))}"
    req = urllib.request.Request(url, data=corpo, method="POST" if corpo is not None else "GET",
                                 headers={"Content-Type": "application/json"} if corpo is not None else {})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=3) as r:
            return json.loads(r.read() or b"{}")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def instancia_ativa():
    try:
        with open(ARQ_INSTANCIA, encoding="utf-8") as f:
            inst = json.load(f)
        resp = _chamar(inst, "/api/ping")
    except (OSError, ValueError, TypeError):
        return None
    return inst if resp and resp.get("ok") and resp.get("pid") == inst.get("pid") else None


def pedir_instancia(inst, acao):
    return _chamar(inst, "/api/acao", json.dumps({"acao": acao}).encode("utf-8")) is not None


def gravar_instancia():
    try:
        os.makedirs(os.path.dirname(ARQ_INSTANCIA), exist_ok=True)
        with open(ARQ_INSTANCIA, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "porta": PORTA, "token": TOKEN}, f)
        if not IS_WIN:
            os.chmod(ARQ_INSTANCIA, 0o600)
    except OSError:
        pass


def apagar_instancia():
    try:
        with open(ARQ_INSTANCIA, encoding="utf-8") as f:
            if json.load(f).get("pid") != os.getpid():
                return
        os.remove(ARQ_INSTANCIA)
    except (OSError, ValueError, AttributeError):
        pass


# Ícone perto do relógio. Roda num PowerShell à parte: se falhar, o Th Boost segue normal (dá para abrir pelo atalho).
PS_BANDEJA = r"""
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  function Enviar([string]$acao) {
    try {
      $c = New-Object System.Net.WebClient
      $c.Proxy = $null
      $c.Headers.Add('Content-Type', 'application/json')
      [void]$c.UploadString($env:T_URL, 'POST', ('{"acao":"' + $acao + '"}'))
    } catch { }
  }
  $ni = New-Object System.Windows.Forms.NotifyIcon
  $ni.Icon = New-Object System.Drawing.Icon($env:T_ICONE)
  $ni.Text = 'Th Boost - em segundo plano'
  $menu = New-Object System.Windows.Forms.ContextMenuStrip
  $mAbrir = $menu.Items.Add('Abrir o Th Boost')
  $mSair = $menu.Items.Add('Encerrar o Th Boost')
  $mAbrir.add_Click({ Enviar 'abrir_janela' })
  $mSair.add_Click({ Enviar 'encerrar_tudo'; $ni.Visible = $false; [System.Windows.Forms.Application]::Exit() })
  $ni.add_DoubleClick({ Enviar 'abrir_janela' })
  $ni.ContextMenuStrip = $menu
  $ni.Visible = $true
  $estado = @{ janela = $true; falhas = 0 }
  $relogio = New-Object System.Windows.Forms.Timer
  $relogio.Interval = 2000
  $relogio.add_Tick({
    try {
      $c = New-Object System.Net.WebClient
      $c.Proxy = $null
      $j = $c.DownloadString($env:T_PING) | ConvertFrom-Json
      $estado.falhas = 0
      if (-not $j.bg) { $ni.Visible = $false; [System.Windows.Forms.Application]::Exit(); return }
      if ($estado.janela -and -not $j.janela) {
        $ni.ShowBalloonTip(4000, 'Th Boost', 'Continua rodando em segundo plano. Clique duas vezes no ícone para abrir.', [System.Windows.Forms.ToolTipIcon]::Info)
      }
      $estado.janela = [bool]$j.janela
    } catch {
      $estado.falhas = $estado.falhas + 1
      if ($estado.falhas -ge 3) { $ni.Visible = $false; [System.Windows.Forms.Application]::Exit() }
    }
  })
  $relogio.Start()
  [System.Windows.Forms.Application]::Run()
  $ni.Visible = $false
  $ni.Dispose()
} catch { }
Remove-Item -LiteralPath $env:T_ARQ -ErrorAction SilentlyContinue
"""

# Traz a janela do Th Boost para a frente (quando a pessoa abre o programa de novo e a janela já existe).
PS_FOCO = r"""
$ErrorActionPreference = 'Stop'
$tipo = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ThBoostFoco {
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
  public static void Focar(string titulo) {
    IntPtr achado = IntPtr.Zero;
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (!IsWindowVisible(h)) return true;
      StringBuilder t = new StringBuilder(256);
      GetWindowText(h, t, 256);
      if (!t.ToString().StartsWith(titulo)) return true;
      StringBuilder c = new StringBuilder(256);
      GetClassName(h, c, 256);
      if (c.ToString() != "Chrome_WidgetWin_1") return true;
      achado = h;
      return false;
    }, IntPtr.Zero);
    if (achado != IntPtr.Zero) { ShowWindow(achado, 9); SetForegroundWindow(achado); }
  }
}
'@
try { Add-Type -TypeDefinition $tipo; [ThBoostFoco]::Focar('Th Boost') } catch { }
Remove-Item -LiteralPath $env:T_ARQ -ErrorAction SilentlyContinue
"""


def _rodar_ps(roteiro, prefixo, extra_env, oculto=True):
    """Grava o roteiro numa pasta temporária e roda num PowerShell escondido. Devolve o processo (ou None)."""
    if not IS_WIN:
        return None
    arq = os.path.join(tempfile.gettempdir(), f"thboost_{prefixo}_{os.getpid()}.ps1")
    try:
        with open(arq, "w", encoding="utf-8-sig") as f:
            f.write(roteiro)
        ambiente = dict(os.environ, T_ARQ=arq, **extra_env)
        return subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-STA", "-WindowStyle", "Hidden",
                                 "-ExecutionPolicy", "Bypass", "-File", arq], env=ambiente,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None


VERSAO = "v8.6"
PORTA = 0
TOKEN = secrets.token_urlsafe(24)
TRAVA = threading.Lock()


def _contar_processos():
    try:
        return len(psutil.pids())
    except Exception:
        return None


class Nucleo(ExtremoMixin, JogosMixin, ManutencaoMixin, ProcessosMixin, FerramentasMixin, MemoriaMixin, CpuMixin,
             OverclockMixin, CpuPerfilMixin):
    """Guarda tudo o que a interface mostra e executa as ações pedidas por ela."""

    def __init__(self):
        self.mon = Monitor()
        self.mon.start()
        self.historico = collections.deque(maxlen=40)
        self.contador_msg = 0
        self.serie = {k: collections.deque(maxlen=120) for k in ("cpu", "ram", "gpu", "down", "up")}
        self.amostra = {}
        self.ping_ms = None
        self.otim = {"ativo": False, "fracao": 0.0, "passo": "", "titulo": "", "passos": [], "fim": 0, "mb": 0.0}
        self.ext_iniciar_estado()
        self.jogos_iniciar_estado()
        self.trab_iniciar_estado()
        self.proc_iniciar_estado()
        self.memoria_iniciar_estado()
        self.cpu_iniciar_estado()
        self.cpu_perfil_iniciar_estado()
        self.jogos = []
        self.procurando = False
        self.capas = {}
        self.fechando = False
        self.aj = {}
        self.mouse_vel = None
        self.ocioso = False          # janela fechada com o segundo plano ligado
        self.saindo = False          # encerrando de vez (avisa a bandeja para sumir)
        self.bandeja = None          # processo do ícone perto do relógio
        self.aberturas = 0           # quantas vezes a janela foi reaberta por pedido
        self._ultima_abertura = 0.0
        self.atualizar_aj()
        threading.Thread(target=self._vigiar_aj, daemon=True).start()
        psutil.cpu_percent(interval=None)  # primeira leitura serve só de base
        threading.Thread(target=self._amostrar, daemon=True).start()
        self.procurar_jogos()
        threading.Thread(target=self._vigiar_jogos, daemon=True).start()
        threading.Thread(target=self._vigiar_cpu, daemon=True).start()
        self.oc_iniciar_estado()

    # ----- mensagens (viram avisos e histórico na tela) -----

    def msg(self, texto):
        if not texto:
            return
        with TRAVA:
            self.contador_msg += 1
            self.historico.appendleft({"id": self.contador_msg, "h": datetime.now().strftime("%H:%M"),
                                       "t": str(texto)})

    # ----- coleta de números a cada segundo -----

    def _amostrar(self):
        while not self.fechando:
            if self.ocioso:  # sem janela ninguém vê os números
                time.sleep(3.0)
                continue
            try:
                self._coletar()
            except Exception as erro:  # a coleta nunca pode derrubar o programa
                self.amostra["erro"] = str(erro)
            time.sleep(1.0)

    def _coletar(self):
        d = self.mon.dados
        g = d["gpu"] or {}
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        vram = None
        if g.get("vram_total") and g.get("vram_usada") is not None:
            vram = g["vram_usada"] / g["vram_total"] * 100
        try:
            du = psutil.disk_usage(disco_sistema())
            disco = {"pct": du.percent, "livre": du.free / 1024 ** 3, "total": du.total / 1024 ** 3}
        except OSError:
            disco = None
        a = {
            "cpu": cpu, "nucleos": psutil.cpu_count() or 0,
            "ram": mem.percent, "ram_usada": mem.used / 1024 ** 3, "ram_total": mem.total / 1024 ** 3,
            "ram_livre": mem.available / 1024 ** 3,
            "gpu": d["gpu"], "gpu_lida": d["gpu_lida"], "gpu_uso": g.get("uso"), "vram": vram,
            "tcpu": temp_cpu(), "tgpu": g.get("temp"), "disco": disco,
            "down": d["down"], "up": d["up"], "nproc": _contar_processos(),
        }
        self.amostra = a
        self.serie["cpu"].append(round(cpu, 1))
        self.serie["ram"].append(round(mem.percent, 1))
        self.serie["gpu"].append(round(g.get("uso") or 0, 1))
        self.serie["down"].append(round(d["down"] / 1024, 1))
        self.serie["up"].append(round(d["up"] / 1024, 1))

    # ----- ajustes do Windows -----

    def atualizar_aj(self):
        try:
            self.aj = estados_ajustes()
            self.mouse_vel = velocidade_mouse()
        except Exception:
            pass

    def _vigiar_aj(self):
        while not self.fechando:
            time.sleep(4)
            if not self.ocioso:
                self.atualizar_aj()

    def t_aj(self, a, ligar):
        if a.precisa_admin and not e_admin():
            return "Este ajuste precisa de Administrador. Abra o Th Boost pelo atalho."
        try:
            a.ligar() if ligar else a.desligar()
        except OSError as erro:
            return f"Não foi possível alterar: {erro}"
        self.atualizar_aj()
        if a.estado() == bool(ligar):
            extra = f" {a.nota}" if (ligar and a.nota) else ""
            return f"{a.titulo}: {'ligado' if ligar else 'desfeito'}.{extra}"
        return f"{a.titulo}: comando enviado, mas o Windows ainda não confirmou. Confira em alguns segundos."

    def t_preset(self, grupo, modo):
        itens = [a for a in CATALOGO if a.grupo == grupo and a.disponivel()]
        if modo == "rec":
            alvo, ligar = [a for a in itens if a.rec and a.estado() is False], True
            if alvo:
                ponto_restauracao()
        else:
            alvo, ligar = [a for a in itens if a.estado() is True], False
        if not e_admin():
            pulados = [a for a in alvo if a.precisa_admin]
            alvo = [a for a in alvo if not a.precisa_admin]
        else:
            pulados = []
        feitos = 0
        for a in alvo:
            try:
                a.ligar() if ligar else a.desligar()
                feitos += 1
            except OSError:
                pulados.append(a)
        self.atualizar_aj()
        verbo = "aplicado(s)" if ligar else "restaurado(s) ao padrão"
        texto = f"{feitos} ajuste(s) {verbo}." if feitos else ("Tudo já estava assim." if not pulados else "Nada foi alterado.")
        if pulados:
            texto += f" {len(pulados)} precisa(m) de Administrador."
        return texto

    def t_debloat(self, pacotes):
        if not e_admin():
            return "Remover apps precisa de Administrador. Abra o Th Boost pelo atalho."
        ponto_restauracao()
        feitos = remover_apps(pacotes)
        return f"{feitos} de {len(pacotes)} app(s) removido(s). Dá para reinstalar pela Microsoft Store."

    def lista(self, nome):
        if nome == "energia":
            planos = listar_planos()
            conhecidos = []
            for k, v in PLANOS_CONHECIDOS.items():
                p = plano_existente(k, planos)
                conhecidos.append({"chave": k, "nome": v[1], "existe": p is not None, "ativo": bool(p and p["ativo"])})
            ativo = next((p["nome"] for p in planos if p["ativo"]), "")
            return {"planos": planos, "conhecidos": conhecidos, "ativo": ativo}
        if nome == "dns":
            return dns_atual()
        if nome == "inicio":
            return {"itens": listar_inicio()}
        if nome == "apps":
            return {"apps": listar_apps()}
        if nome == "dashboard":
            return self.dashboard()
        if nome == "processos":
            return self.proc_lista()
        if nome == "svc3":
            return self.svc3_lista()
        if nome == "correcoes":
            return {"itens": correcoes_publico(), "links": links_publico(), "admin": e_admin()}
        if nome == "backup":
            return self.backup_lista()
        if nome == "programas":
            return self.programas_lista()
        if nome == "espaco":
            return self.espaco_publico()
        if nome == "atalhos":
            return {"itens": atalhos_publico()}
        if nome == "monitor":
            if self.monitor["estado"] in ("nenhum", "erro"):
                self.monitor_ler()
            return {"estado": self.monitor["estado"], "dados": self.monitor["dados"]}
        if nome == "perfis":
            return self.jogos_perfis()
        if nome == "memoria":
            return self.memoria_lista()
        if nome == "cpu_perfil":
            return self.cpu_perfil_lista()
        raise ValueError("lista desconhecida")

    def catalogo(self):
        return {"ajustes": catalogo_publico(), "windows": REG is not None}

    def estado(self):
        d = self.mon.dados
        a = dict(self.amostra)
        with TRAVA:
            hist = list(self.historico)
        a.update({
            "versao": VERSAO, "admin": e_admin(), "win": IS_WIN, "usuario": USUARIO.title(),
            "nome": nome_da_pessoa(), "nome_fixo": bool(_nome_limpo(CONFIG.get("nome"))),
            "pasta": pasta_do_programa(), "presentmon": bool(caminho_presentmon()),
            "modo_leve": self.mon.modo_leve, "fps_ligado": self.mon.fps_ligado,
            "fps": d["fps"], "fps_app": d["app"], "fps_erro": d["fps_erro"],
            "ping": self.ping_ms, "otim": self.otim, "ext": self.ext_snapshot(),
            "oc": self.oc_estado(),
            "jogos": {"procurando": self.procurando, "ocultos": len(CONFIG.get("jogos_ocultos") or []),
                      "lista": [{"i": i, "nome": j["nome"], "origem": j["origem"],
                                 "steam": bool(j.get("appid")), "pasta": bool(j.get("pasta")),
                                 "icone": bool(j.get("exe") and not j.get("appid")), "manual": bool(j.get("manual"))}
                                for i, j in enumerate(self.jogos)]},
            "pre": self.pre_snapshot(), "sessao": self.sessao_snapshot(), "trab": self.trab_snapshot(),
            "stats": dict(self.stats), "auto_jogo": bool(CONFIG.get("auto_jogo")),
            "hist": hist, "serie": {k: list(v) for k, v in self.serie.items()},
            "aj": self.aj, "mouse_vel": self.mouse_vel,
            "segundo_plano": CONFIG["segundo_plano"],
        })
        return a

    # ----- tarefas em segundo plano -----

    def em_fundo(self, alvo, depois=None):
        def tarefa():
            try:
                resultado = alvo()
            except Exception as erro:
                resultado = f"Erro: {erro}"
            (depois or self.msg)(resultado)
        threading.Thread(target=tarefa, daemon=True).start()

    def _limpar_texto(self, grupo, sup=False):
        """Limpa um grupo (temp, nav, apps ou win). Devolve (texto, bytes liberados)."""
        r = limpar_grupo(grupo, parar=lambda: self.fechando, sup=sup)
        texto = f"{ROTULOS_GRUPO[grupo]}: ~{tam_texto(r['bytes'])} liberados."
        adm = sum(1 for p in r["pulados"] if p["motivo"] == "admin")
        if adm:
            texto += f" {adm} parte(s) precisam de Administrador."
        if any(p["motivo"] == "reinicio" for p in r["pulados"]):
            texto += " Atualizações do Windows mantidas: há um reinício pendente."
        return texto, r["bytes"]

    def t_temp(self):
        texto, b = self._limpar_texto("temp")
        self.estat_limpeza(b)
        return texto

    def t_limpar(self, grupo):
        texto, b = self._limpar_texto(grupo)
        self.estat_limpeza(b)
        return texto

    def t_limpar_tudo(self):
        total, partes = 0, []
        for g in ("temp", "nav", "apps", "win"):
            texto, b = self._limpar_texto(g)
            total += b
        self.estat_limpeza(total)
        ok, _ = esvaziar_lixeira()
        return f"Limpeza completa: ~{tam_texto(total)} liberados" + (" e a lixeira foi esvaziada." if ok else ".")

    def t_ram(self):
        return liberar_ram()[1]

    def t_plano(self):
        return ("Plano Alto desempenho ativado." if plano_alto_desempenho()
                else "Plano indisponível (abra como Administrador).")

    def t_dns(self):
        cod, _ = executar(["ipconfig", "/flushdns"])
        return "Cache DNS limpo." if cod == 0 else "Não foi possível limpar o cache DNS."

    def t_lixeira(self):
        return esvaziar_lixeira()[1]

    def t_renovar_ip(self):
        if not IS_WIN:
            return "Disponível só no Windows."
        return "IP renovado." if renovar_ip() else "Não foi possível renovar o IP (abra como Administrador)."

    def t_ping(self):
        ms = medir_ping()
        if isinstance(ms, int):
            self.ping_ms = ms
            return f"Ping: {ms} ms"
        self.ping_ms = None
        return "Sem resposta ao testar o ping."

    # ----- otimização com passos -----

    def otimizar(self, titulo_fim="Otimização concluída"):
        if self.otim["ativo"] or self.ext["ativo"]:
            return self.msg("Já estou otimizando, aguarde.")
        passos = [("Limpando temporários", lambda: self._limpar_texto("temp")),
                  ("Limpando os navegadores", lambda: self._limpar_texto("nav")),
                  ("Limpando caches de programas", lambda: self._limpar_texto("apps")),
                  ("Limpeza do Windows", lambda: self._limpar_texto("win")),
                  ("Esvaziando a lixeira", self.t_lixeira),
                  ("Liberando a RAM", self.t_ram),
                  ("Plano de energia", self.t_plano),
                  ("Limpando o DNS", self.t_dns)]
        self.otim = {"ativo": True, "fracao": 0.04, "passo": "Começando...", "titulo": titulo_fim,
                     "passos": [{"nome": n, "estado": "pendente", "texto": "", "mb": 0.0} for n, _ in passos],
                     "fim": self.otim.get("fim", 0), "mb": 0.0}
        self.msg("Otimizando...")

        def tarefa():
            saidas, total = [], 0
            for i, (nome, funcao) in enumerate(passos):
                self.otim["passo"] = nome + "..."
                self.otim["fracao"] = max(0.04, i / len(passos))
                self.otim["passos"][i]["estado"] = "rodando"
                inicio = time.time()
                b = 0
                try:
                    r = funcao()
                    texto, b = r if isinstance(r, tuple) else (r, 0)
                    estado = "ok"
                except Exception as erro:
                    texto, estado = f"Erro: {erro}", "erro"
                # cada passo fica à vista por um instante, para dar para acompanhar na tela
                time.sleep(max(0.0, 0.6 - (time.time() - inicio)))
                saidas.append(texto)
                total += b
                self.otim["passos"][i].update({"estado": estado, "texto": texto, "mb": round(b / 1048576, 1)})
                self.otim["mb"] = round(total / 1048576, 1)
                self.otim["fracao"] = (i + 1) / len(passos)
            self.otim["passo"] = "Pronto para otimizar"
            self.otim["ativo"] = False
            self.otim["fim"] = self.otim.get("fim", 0) + 1
            self.estat_otimizacao(total / 1048576, "normal")
            self.msg(f"{titulo_fim}: ~{tam_texto(total)} de lixo apagados · " + " · ".join(saidas[-3:]))

        threading.Thread(target=tarefa, daemon=True).start()

    # ----- jogos -----

    def procurar_jogos(self):
        if self.procurando:
            return
        self.procurando = True

        def tarefa():
            try:
                lista = detectar_jogos()
            except Exception:
                lista = []
            self.capas = {}
            self.jogos = lista
            self.procurando = False

        threading.Thread(target=tarefa, daemon=True).start()

    def nome_definir(self, nome):
        """Troca o nome que aparece embaixo da logo. Vazio volta ao nome do usuário do Windows."""
        if nome is not None and not isinstance(nome, str):
            raise ValueError("nome inválido")
        limpo = _nome_limpo(nome)
        if limpo:
            CONFIG["nome"] = limpo
        else:
            CONFIG.pop("nome", None)
        salvar_config()
        self.msg(f"Pronto, agora é {nome_da_pessoa()}.")

    def t_jogo_adicionar(self):
        """Abre a janela do Windows para escolher o .exe de um jogo e põe na lista."""
        if getattr(self, "_escolhendo_jogo", False):
            return ""
        self._escolhendo_jogo = True
        try:
            self.msg("Escolha o programa do jogo (.exe) na janela que abriu.")
            exe = escolher_exe_do_jogo()
        finally:
            self._escolhendo_jogo = False
        if not exe:
            self.msg("Nenhum jogo escolhido.")
            return ""
        ok, texto = jogo_manual_adicionar(exe)
        self.msg(f"{texto} entrou na lista." if ok else texto)
        if ok:
            self.procurar_jogos()
        return ""

    def capa(self, i):
        """Caminho da imagem do jogo i (usa a da Steam no PC ou baixa uma vez). None se não houver."""
        if not (0 <= i < len(self.jogos)):
            return None
        if i not in self.capas:
            try:
                self.capas[i] = capa_do_jogo(self.jogos[i])
            except Exception:
                self.capas[i] = None
        return self.capas[i]

    def jogo(self, i):
        return self.jogos[i] if isinstance(i, int) and 0 <= i < len(self.jogos) else None

    # ----- ações vindas da interface -----

    def acao(self, dados):
        nome = dados.get("acao")
        if nome == "otimizar_tudo":
            self.otimizar()
        elif nome == "ram":
            self.msg("Liberando a RAM...")
            self.em_fundo(self.t_ram)
        elif nome == "plano":
            self.em_fundo(self.t_plano)
        elif nome == "dns":
            self.em_fundo(self.t_dns)
        elif nome == "temp":
            self.msg("Limpando temporários...")
            self.em_fundo(self.t_temp)
        elif nome == "lixeira":
            self.msg("Esvaziando a lixeira...")
            self.em_fundo(self.t_lixeira)
        elif nome == "renovar_ip":
            self.msg("Renovando IP...")
            self.em_fundo(self.t_renovar_ip)
        elif nome == "ping":
            self.em_fundo(self.t_ping)
        elif nome in ("limpar_nav", "limpar_apps", "limpar_win"):
            g = {"limpar_nav": "nav", "limpar_apps": "apps", "limpar_win": "win"}[nome]
            self.msg(f"Limpando: {ROTULOS_GRUPO[g].lower()}...")
            self.em_fundo(lambda: self.t_limpar(g))
        elif nome == "limpar_tudo":
            self.msg("Limpeza completa em andamento...")
            self.em_fundo(self.t_limpar_tudo)
        elif nome == "extremo":
            opc = dados.get("opcoes", {})
            if not isinstance(opc, dict) or any(
                    (v not in ("extrema", "suprema")) if k == "nivel" else (k not in ("dism", "apps", "busca", "winold") or not isinstance(v, bool))
                    for k, v in opc.items()):
                raise ValueError("opções inválidas")
            self.ext_iniciar(opc)
        elif nome == "extremo_parar":
            self.ext_parar()
        elif nome == "extremo_pular":
            self.ext_pular = True
        elif nome == "extremo_analisar":
            nivel = dados.get("nivel", "extrema")
            if nivel not in ("extrema", "suprema"):
                raise ValueError("nível inválido")
            self.ext_analisar(nivel)
        elif nome == "extremo_desfazer":
            self.ext_desfazer()
        elif nome == "reiniciar_pc":
            self.em_fundo(lambda: self.reiniciar_pc() or "")
        elif nome == "reiniciar_cancelar":
            self.em_fundo(lambda: self.reiniciar_cancelar() or "")
        elif nome == "limpeza_windows":
            if not IS_WIN:
                return self.msg("Disponível só no Windows.")
            try:
                subprocess.Popen(["cleanmgr.exe"])
                self.msg("Limpeza de disco do Windows aberta.")
            except OSError:
                self.msg("Não foi possível abrir a Limpeza de disco.")
        elif nome == "leve":
            self.mon.modo_leve = not self.mon.modo_leve
            self.mon.forcar = True
            self.msg("Modo Leve ligado." if self.mon.modo_leve else "Modo Leve desligado.")
        elif nome == "fps":
            ligar = not self.mon.fps_ligado
            self.mon.modo_leve = ligar
            self.mon.forcar = True
            self.mon.ligar_fps(ligar)
            if ligar:
                self.msg("Modo FPS On ligado.")
                self.em_fundo(self.t_plano)
            else:
                self.msg("Modo FPS On desligado.")
        elif nome == "oc_nivel":
            self.oc_definir(dados.get("nivel"))
        elif nome == "oc_zerar":
            self.oc_definir(0)
        elif nome == "cpu_perfil":
            self.cpu_perfil_definir(dados.get("perfil"))
        elif nome in ("aj", "aj_preset", "energia", "dns_trocar", "rede_reset", "inicio", "debloat", "mouse_vel"):
            self.acao_ajuste(nome, dados)
        elif nome == "segundo_plano":
            ligar = dados.get("ligar")
            if not isinstance(ligar, bool):
                raise ValueError("pedido inválido")
            CONFIG["segundo_plano"] = ligar
            salvar_config()
            if ligar:
                self.iniciar_bandeja()
                self.msg("Segundo plano ligado: ao fechar a janela, o Th Boost continua rodando escondido.")
            else:
                self.msg("Segundo plano desligado: ao fechar a janela, o Th Boost encerra.")
        elif nome == "abrir_janela":
            self.reabrir_janela()
        elif nome == "encerrar_tudo":
            self.msg("Encerrando o Th Boost...")
            self.saindo = True  # a bandeja percebe e some sozinha antes de o programa fechar
            threading.Timer(2.5, self.encerrar).start()
        elif nome == "jogos_procurar":
            self.procurar_jogos()
        elif nome == "jogo_otimizar":
            i = dados.get("i")
            if i is not None and (not isinstance(i, int) or isinstance(i, bool)):
                raise ValueError("jogo inválido")
            opc = dados.get("opcoes") or {}
            if not isinstance(opc, dict) or any(k not in PRE_PADRAO or not isinstance(v, bool) for k, v in opc.items()):
                raise ValueError("opções inválidas")
            self.pre_iniciar(i, opc)
        elif nome == "pre_opcoes":
            opc = dados.get("opcoes")
            if not isinstance(opc, dict) or any(k not in PRE_PADRAO or not isinstance(v, bool) for k, v in opc.items()):
                raise ValueError("opções inválidas")
            self.pre_definir_opcoes(opc)
        elif nome == "sessao_fim":
            self.em_fundo(lambda: self.sessao_fim("Sessão encerrada por você") or "")
        elif nome == "auto_jogo":
            ligar = dados.get("ligar")
            if not isinstance(ligar, bool):
                raise ValueError("pedido inválido")
            CONFIG["auto_jogo"] = ligar
            salvar_config()
            self.msg("Modo automático ligado: quando um jogo da lista abrir, o Th Boost otimiza sozinho e devolve tudo ao fechar."
                     if ligar else "Modo automático desligado.")
        elif nome == "jogos_desfazer_perfis":
            self.em_fundo(self.jogos_desfazer_perfis)
        elif nome == "monitor_ler":
            self.monitor_ler()
        elif nome == "memoria_ler":
            self.memoria_ler(True)
        elif nome == "memoria_bios":
            self.memoria_bios()
        elif nome == "memoria_bios_cancelar":
            self.memoria_bios_cancelar()
        elif nome == "trab_parar":
            chave = dados.get("chave")
            if not isinstance(chave, str) or chave not in self.trab:
                raise ValueError("pedido inválido")
            self.trab_parar(chave)
        elif nome == "correcao":
            ident = dados.get("id")
            if not isinstance(ident, str) or ident not in CORRECOES_POR_ID:
                raise ValueError("correção inválida")
            self.correcao_iniciar(ident)
        elif nome == "link":
            self.link_oficial(dados.get("id"))
        elif nome == "bk_config":
            self.bk_definir(dados.get("destino") if isinstance(dados.get("destino"), str) else "", dados.get("pastas"))
        elif nome == "bk_arquivos":
            self.backup_arquivos_iniciar()
        elif nome == "bk_restaurar":
            self.backup_restaurar_iniciar()
        elif nome == "bk_ponto":
            self.backup_ponto_iniciar()
        elif nome == "bk_protecao":
            self.backup_protecao_iniciar()
        elif nome == "bk_drivers":
            self.backup_drivers_iniciar()
        elif nome == "bk_ajustes":
            self.backup_ajustes_iniciar()
        elif nome == "bk_importar":
            self.backup_ajustes_importar(dados.get("nome"))
        elif nome == "bk_abrir":
            self.backup_abrir_pasta()
        elif nome == "proc_fechar":
            self.proc_fechar(dados.get("nome"))
        elif nome == "proc_reduzir":
            opc = dados.get("opcoes") or {}
            if not isinstance(opc, dict) or any(k not in ("raros", "svchost", "launchers", "chats") or not isinstance(v, bool) for k, v in opc.items()):
                raise ValueError("opções inválidas")
            self.proc_reduzir_iniciar(opc)
        elif nome == "proc_desfazer":
            self.em_fundo(self.t_proc_desfazer)
        elif nome == "cpu_limite":
            self.cpu_definir(dados.get("ligar"), dados.get("pct"))
        elif nome == "svc3":
            self.svc3_definir(dados.get("nome"), dados.get("manual"))
        elif nome == "programa_desinstalar":
            self.programa_desinstalar(dados.get("id"))
        elif nome == "atalho":
            self.atalho_abrir(dados.get("id"))
        elif nome == "espaco_iniciar":
            self.espaco_iniciar(dados.get("alvo"))
        elif nome == "espaco_mostrar":
            self.espaco_mostrar(dados.get("i"))
        elif nome == "nome_definir":
            self.nome_definir(dados.get("nome"))
        elif nome == "jogo_adicionar":
            self.em_fundo(self.t_jogo_adicionar)
        elif nome == "jogo_tirar":
            j = self.jogo(dados.get("i"))
            if not j:
                return
            jogo_tirar_da_lista(j)
            self.msg(f"{j['nome']} saiu da lista. Para trazer de volta, use \"Mostrar os que tirei\".")
            self.procurar_jogos()
        elif nome == "jogos_mostrar_ocultos":
            CONFIG["jogos_ocultos"] = []
            salvar_config()
            self.msg("Os jogos que você tirou voltaram para a lista.")
            self.procurar_jogos()
        elif nome == "jogo_abrir":
            j = self.jogo(dados.get("i"))
            if not j:
                return
            self.msg(f"Abrindo {j['nome']}..." if lancar_jogo(j["abrir"])
                     else f"Não foi possível abrir {j['nome']}.")
        else:
            raise ValueError("ação desconhecida")

    def acao_ajuste(self, nome, dados):
        """Ações das páginas de ajustes. Tudo que vem da tela é conferido aqui antes de mexer no Windows."""
        if REG is None:
            return self.msg("Os ajustes do Windows só funcionam no Windows.")
        if nome == "aj":
            a = POR_ID.get(dados.get("id"))
            ligar = dados.get("ligar")
            if a is None or not isinstance(ligar, bool):
                raise ValueError("ajuste inválido")
            self.em_fundo(lambda: self.t_aj(a, ligar))
        elif nome == "aj_preset":
            grupo, modo = dados.get("grupo"), dados.get("modo")
            if grupo not in {a.grupo for a in CATALOGO} or modo not in ("rec", "padrao"):
                raise ValueError("pedido inválido")
            self.msg("Aplicando os ajustes recomendados..." if modo == "rec" else "Restaurando o padrão do Windows...")
            self.em_fundo(lambda: self.t_preset(grupo, modo))
        elif nome == "energia":
            chave = dados.get("plano")
            if chave not in PLANOS_CONHECIDOS:
                raise ValueError("plano inválido")
            self.em_fundo(lambda: ativar_plano(chave))
        elif nome == "dns_trocar":
            modo = dados.get("modo")
            if modo not in ("auto", "google", "cloudflare"):
                raise ValueError("DNS inválido")
            self.msg("Trocando o DNS...")
            self.em_fundo(lambda: dns_trocar(modo))
        elif nome == "rede_reset":
            self.msg("Resetando a rede...")
            self.em_fundo(resetar_rede)
        elif nome == "inicio":
            ident, ligar = dados.get("id"), dados.get("ligar")
            if not isinstance(ident, str) or not isinstance(ligar, bool):
                raise ValueError("pedido inválido")
            self.em_fundo(lambda: definir_inicio(ident, ligar))
        elif nome == "debloat":
            pacotes = dados.get("pacotes")
            if (not isinstance(pacotes, list) or not pacotes or len(pacotes) > 40
                    or any(not isinstance(p, str) or p not in APPS_POR_NOME for p in pacotes)):
                raise ValueError("lista de apps inválida")
            self.msg(f"Removendo {len(pacotes)} app(s)... pode levar um tempo.")
            self.em_fundo(lambda: self.t_debloat(pacotes))
        elif nome == "mouse_vel":
            v = dados.get("valor")
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError("valor inválido")
            v = definir_velocidade_mouse(v)
            self.atualizar_aj()
            self.msg(f"Velocidade do ponteiro: {v}/20" + (" (padrão do Windows)." if v == 10 else "."))

    def ping(self):
        """Resposta curta para a bandeja e para quem abre o programa de novo."""
        return {"ok": True, "pid": os.getpid(), "bg": CONFIG["segundo_plano"] and not self.saindo,
                "janela": CLIENTES["abertos"] > 0, "aberturas": self.aberturas, "ocioso": self.ocioso,
                "bandeja": bool(self.bandeja and self.bandeja.poll() is None)}

    def reabrir_janela(self):
        """Pedido de quem abriu o Th Boost de novo (ou do ícone da bandeja)."""
        if CLIENTES["abertos"] > 0:  # já tem janela: só traz para a frente
            _rodar_ps(PS_FOCO, "foco", {})
            return
        if time.time() - self._ultima_abertura < 5:  # evita abrir duas por clique duplo
            return
        self._ultima_abertura = time.time()
        self.aberturas += 1
        if not os.environ.get("TOTIMIZE_SEM_JANELA"):
            abrir_janela(f"http://127.0.0.1:{PORTA}/")
            ajustar_icone_barra()

    def iniciar_bandeja(self):
        if not IS_WIN or (self.bandeja is not None and self.bandeja.poll() is None):
            return
        icone = os.path.join(pasta_do_programa(), "Th Boost.ico")
        if not os.path.isfile(icone):
            return
        base = f"http://127.0.0.1:{PORTA}"
        self.bandeja = _rodar_ps(PS_BANDEJA, "bandeja", {"T_ICONE": icone, "T_URL": f"{base}/api/acao?k={TOKEN}",
                                                         "T_PING": f"{base}/api/ping?k={TOKEN}"})

    def encerrar(self):
        """Devolve as prioridades ao normal, para o FPS e sai."""
        if self.fechando:
            return
        self.fechando = True
        apagar_instancia()
        try:
            self.sessao_fim("O Th Boost fechou")  # devolve plano de energia e serviços pausados durante um jogo
        except Exception:
            pass
        self.cpu_fechar()  # solta o teto de CPU dos programas em segundo plano
        self.oc_fechar()  # devolve a placa de vídeo ao padrão, se o overclock estava ligado
        try:
            self.mon.ligar_fps(False)
            self.mon.aplicar_prioridades(False)
        except Exception:
            pass
        os._exit(0)


NUCLEO = None
HTML_PRONTO = ""
CLIENTES = {"abertos": 0, "ja_teve": False, "ultimo": time.time()}


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _host_ok(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORTA}", f"localhost:{PORTA}")

    def _token_ok(self, consulta):
        return secrets.compare_digest(consulta.get("k", [""])[0], TOKEN)

    def _responder(self, codigo, corpo, tipo="application/json", extra=None):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False)
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if not self._host_ok():
            return self._responder(403, {"erro": "host"})
        url = urllib.parse.urlparse(self.path)
        consulta = urllib.parse.parse_qs(url.query)
        if url.path == "/":
            return self._responder(200, HTML_PRONTO, "text/html; charset=utf-8", {
                "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                           "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})
        if url.path == "/favicon.ico":
            return self._responder(204, b"", "image/x-icon")
        if not self._token_ok(consulta):
            return self._responder(403, {"erro": "token"})
        if url.path == "/api/estado":
            return self._responder(200, NUCLEO.estado())
        if url.path == "/api/fluxo":
            return self._fluxo()
        if url.path == "/api/ping":
            return self._responder(200, NUCLEO.ping())
        if url.path == "/api/catalogo":
            return self._responder(200, NUCLEO.catalogo())
        if url.path == "/api/lista":
            try:
                return self._responder(200, NUCLEO.lista(consulta.get("nome", [""])[0]))
            except ValueError:
                return self._responder(404, {"erro": "lista desconhecida"})
        m = re.fullmatch(r"/capa/(\d+)", url.path)
        if m:
            caminho = NUCLEO.capa(int(m.group(1)))
            if not caminho or not os.path.isfile(caminho):
                return self._responder(404, b"", "image/jpeg")
            tipo = "image/png" if caminho.lower().endswith(".png") else "image/jpeg"
            with open(caminho, "rb") as f:
                return self._responder(200, f.read(), tipo, {"Cache-Control": "max-age=3600"})
        return self._responder(404, {"erro": "não encontrado"})

    def _fluxo(self):
        """Envia o estado a cada segundo. Enquanto a janela estiver aberta, esta conexão fica viva."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        CLIENTES["abertos"] += 1
        CLIENTES["ja_teve"] = True
        try:
            while not NUCLEO.fechando:
                CLIENTES["ultimo"] = time.time()
                self.wfile.write(("data: " + json.dumps(NUCLEO.estado(), ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
        except (OSError, ValueError):
            pass
        finally:
            CLIENTES["abertos"] -= 1
            CLIENTES["ultimo"] = time.time()
            self.close_connection = True

    def do_POST(self):
        if not self._host_ok():
            return self._responder(403, {"erro": "host"})
        url = urllib.parse.urlparse(self.path)
        consulta = urllib.parse.parse_qs(url.query)
        origem = self.headers.get("Origin")
        if origem and origem not in (f"http://127.0.0.1:{PORTA}", f"http://localhost:{PORTA}"):
            return self._responder(403, {"erro": "origem"})
        if not self._token_ok(consulta) or url.path != "/api/acao":
            return self._responder(403, {"erro": "token"})
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._responder(415, {"erro": "tipo"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 4096:
                return self._responder(413, {"erro": "grande"})
            dados = json.loads(self.rfile.read(n) or b"{}")
            NUCLEO.acao(dados if isinstance(dados, dict) else {})
        except (ValueError, KeyError, TypeError):
            return self._responder(400, {"erro": "pedido inválido"})
        except Exception:
            return self._responder(500, {"erro": "falhou"})
        return self._responder(200, {"ok": True, "estado": NUCLEO.estado()})


PORTA_PREFERIDA = 47813  # porta fixa: o navegador só lembra as preferências (efeitos, página) se a porta for sempre a mesma


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = not IS_WIN  # no Windows isso deixaria dois programas usarem a mesma porta


# ---------------- janela do programa ----------------

def _navegadores():
    """Caminhos do Edge e do Chrome (o Edge já vem no Windows 10 e 11)."""
    pastas = [os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
              os.environ.get("ProgramFiles", r"C:\Program Files"),
              os.environ.get("LOCALAPPDATA", "")]
    relativos = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
    achados = []
    for rel in relativos:
        for pasta in pastas:
            if pasta and os.path.isfile(os.path.join(pasta, rel)):
                achados.append(os.path.join(pasta, rel))
    for nome in ("msedge", "chrome", "google-chrome", "chromium"):
        caminho = shutil.which(nome)
        if caminho:
            achados.append(caminho)
    return achados


def abrir_janela(url):
    """Abre o painel como um aplicativo (janela própria, sem barra de endereço)."""
    perfil = os.path.join(pasta_do_programa(), "ui_perfil")
    for exe in _navegadores():
        try:
            subprocess.Popen([exe, f"--app={url}", f"--user-data-dir={perfil}", "--window-size=1280,800",
                              "--no-first-run", "--no-default-browser-check", "--disable-sync",
                              "--disable-features=Translate,msEdgeSidebar"],
                             creationflags=subprocess.CREATE_NO_WINDOW if IS_WIN else 0)
            return True
        except OSError:
            continue
    return webbrowser.open(url)


# ---------------- ícone do botão na barra de tarefas (Windows) ----------------

# Roda num PowerShell à parte: se algo falhar, o Th Boost segue normal (só fica o ícone do Edge).
PS_ICONE = r"""
$ErrorActionPreference = 'Stop'
$icone = $env:T_ICONE
$cmd = $env:T_CMD
$tipo = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ThBoostIcone {
  [StructLayout(LayoutKind.Sequential, Pack = 4)]
  public struct PROPERTYKEY { public Guid fmtid; public uint pid; }
  [StructLayout(LayoutKind.Explicit)]
  public struct PROPVARIANT {
    [FieldOffset(0)] public ushort vt;
    [FieldOffset(8)] public IntPtr p;
    [FieldOffset(12)] public int pad;
  }
  [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IPropertyStore {
    [PreserveSig] int GetCount(out uint c);
    [PreserveSig] int GetAt(uint i, out PROPERTYKEY k);
    [PreserveSig] int GetValue(ref PROPERTYKEY k, out PROPVARIANT v);
    [PreserveSig] int SetValue(ref PROPERTYKEY k, ref PROPVARIANT v);
    [PreserveSig] int Commit();
  }
  [DllImport("shell32.dll")]
  static extern int SHGetPropertyStoreForWindow(IntPtr hwnd, ref Guid riid, [MarshalAs(UnmanagedType.Interface)] out IPropertyStore ps);
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);

  public static IntPtr Achar(string titulo) {
    IntPtr achado = IntPtr.Zero;
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (!IsWindowVisible(h)) return true;
      StringBuilder t = new StringBuilder(256);
      GetWindowText(h, t, 256);
      if (!t.ToString().StartsWith(titulo)) return true;
      StringBuilder c = new StringBuilder(256);
      GetClassName(h, c, 256);
      if (c.ToString() != "Chrome_WidgetWin_1") return true;
      achado = h;
      return false;
    }, IntPtr.Zero);
    return achado;
  }

  static void Texto(IPropertyStore ps, uint pid, string valor) {
    PROPERTYKEY k = new PROPERTYKEY();
    k.fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
    k.pid = pid;
    PROPVARIANT v = new PROPVARIANT();
    v.vt = 31;
    v.p = Marshal.StringToCoTaskMemUni(valor);
    int r = ps.SetValue(ref k, ref v);
    Marshal.FreeCoTaskMem(v.p);
    if (r != 0) throw new Exception("SetValue " + r.ToString("X"));
  }

  public static void Aplicar(IntPtr hwnd, string id, string icone, string comando, string nome) {
    Guid iid = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
    IPropertyStore ps;
    int r = SHGetPropertyStoreForWindow(hwnd, ref iid, out ps);
    if (r != 0) throw new Exception("store " + r.ToString("X"));
    Texto(ps, 2, comando);
    Texto(ps, 3, icone + ",0");
    Texto(ps, 4, nome);
    Texto(ps, 5, id);
    ps.Commit();
  }
}
'@
try {
  Add-Type -TypeDefinition $tipo
  for ($i = 0; $i -lt 45; $i++) {
    $h = [ThBoostIcone]::Achar('Th Boost')
    if ($h -ne [IntPtr]::Zero) {
      [ThBoostIcone]::Aplicar($h, 'ThBoost.Painel', $icone, $cmd, 'Th Boost')
      break
    }
    Start-Sleep -Milliseconds 700
  }
} catch { }
"""


def ajustar_icone_barra():
    """Faz o botão da barra de tarefas mostrar o ícone do Th Boost (e não o do Edge)."""
    if not IS_WIN:
        return
    pasta = pasta_do_programa()
    icone = os.path.join(pasta, "Th Boost.ico")
    if not os.path.isfile(icone):
        return
    bat = os.path.join(pasta, "Abrir Th Boost.bat")
    if os.path.isfile(bat):
        comando = f'"{bat}"'
    elif getattr(sys, "frozen", False):
        comando = f'"{sys.executable}"'
    else:
        comando = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

    def tarefa():
        arq = os.path.join(tempfile.gettempdir(), f"thboost_icone_{os.getpid()}.ps1")
        try:
            with open(arq, "w", encoding="utf-8-sig") as f:
                f.write(PS_ICONE)
            ambiente = dict(os.environ, T_ICONE=icone, T_CMD=comando)
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", arq],
                           env=ambiente, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        finally:
            try:
                os.remove(arq)
            except OSError:
                pass

    threading.Thread(target=tarefa, daemon=True).start()


def esconder_console():
    """Se o programa foi aberto com uma janela preta própria (clique direto no .py), esconde essa janela.
    Quando foi aberto de dentro de um terminal que já existia, não mexe nele."""
    if not IS_WIN:
        return
    try:
        k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
        k32.GetConsoleWindow.restype = ctypes.c_void_p
        u32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        janela = k32.GetConsoleWindow()
        if not janela:
            return
        lista = (ctypes.c_uint * 8)()
        if k32.GetConsoleProcessList(lista, 8) <= 1:  # só este programa usa a janela preta
            u32.ShowWindow(janela, 0)
    except Exception:
        pass


def vigiar():
    """Fecha o programa quando a janela é fechada, a menos que o segundo plano esteja ligado."""
    inicio = time.time()
    while True:
        time.sleep(1.0)
        agora = time.time()
        if CLIENTES["abertos"] > 0:
            NUCLEO.ocioso = NUCLEO.mon.ocioso = False
            continue
        sem_janela = CLIENTES["ja_teve"] and agora - CLIENTES["ultimo"] > 3
        if CONFIG["segundo_plano"]:
            # fica rodando escondido: mantém o Modo Leve e as prioridades, sem gastar com números que ninguém vê
            NUCLEO.ocioso = NUCLEO.mon.ocioso = bool(sem_janela)
            continue
        if CLIENTES["ja_teve"] and agora - CLIENTES["ultimo"] > 6:
            NUCLEO.encerrar()
        if not CLIENTES["ja_teve"] and agora - inicio > 60:  # a janela nem chegou a abrir
            NUCLEO.encerrar()


def principal():
    global NUCLEO, PORTA, HTML_PRONTO
    if "--encerrar" in sys.argv[1:]:  # usado pelo "Encerrar Th Boost.bat": fecha o que está rodando em segundo plano
        inst = instancia_ativa() if USAR_INSTANCIA else None
        if inst:
            pedir_instancia(inst, "encerrar_tudo")
        return
    if USAR_INSTANCIA:  # já existe um Th Boost aberto (por exemplo em segundo plano): só abre a janela dele
        inst = instancia_ativa()
        if inst and pedir_instancia(inst, "abrir_janela"):
            return
    if IS_WIN:
        try:  # evita que o Windows borre o texto em telas de alta resolução
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError, AttributeError):
            pass
    esconder_console()
    porta_fixa = int(os.environ.get("TOTIMIZE_PORTA", "0") or 0)
    try:
        servidor = Servidor(("127.0.0.1", porta_fixa or PORTA_PREFERIDA), Manipulador)
    except OSError:  # porta ocupada (por exemplo, outro Th Boost aberto): usa qualquer outra livre
        servidor = Servidor(("127.0.0.1", 0), Manipulador)
    PORTA = servidor.server_address[1]
    HTML_PRONTO = HTML.replace("__TOKEN__", TOKEN)
    carregar_config()
    NUCLEO = Nucleo()
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    if USAR_INSTANCIA:
        gravar_instancia()
    if CONFIG["segundo_plano"]:
        NUCLEO.iniciar_bandeja()
    url = f"http://127.0.0.1:{PORTA}/"
    if not os.environ.get("TOTIMIZE_SEM_JANELA"):
        abrir_janela(url)
        ajustar_icone_barra()
    else:
        print("Th Boost em", url, "token", TOKEN, flush=True)
    try:
        vigiar()
    except KeyboardInterrupt:
        NUCLEO.encerrar()
