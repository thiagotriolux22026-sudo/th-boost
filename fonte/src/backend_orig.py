APP_NAME = "Th Boost"
IS_WIN = os.name == "nt"
USUARIO = os.environ.get("USERNAME", "").upper()
PRESENTMON_ARGS = ["--output_stdout", "--stop_existing_session"]
# v9.1: o PresentMon 2.x usa "--", o 1.x usa "-"; se um jeito não der cabeçalho, tenta o outro
PRESENTMON_VARIANTES = (PRESENTMON_ARGS, ["-output_stdout", "-stop_existing_session"])
PLANO_ALTO_DESEMPENHO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
SERVIDOR_PING = "8.8.8.8"
FONTE = "Segoe UI"


# Processos do sistema que nunca têm a prioridade alterada
PROTEGIDOS = {
    "explorer.exe", "ctfmon.exe", "sihost.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "searchhost.exe",
}
# v9.1: o Modo Leve não baixa a prioridade de quem precisa de tempo certo: voz, áudio, gravação/transmissão, controles e
# sobreposições de FPS. Baixar esses causa voz picotando, áudio estalando, gravação perdendo quadros e controle sem resposta.
PROTEGIDOS_LEVE = frozenset({
    "discord.exe", "discordptb.exe", "discordcanary.exe", "teamspeak.exe", "ts3client_win64.exe", "ts3client_win32.exe",
    "mumble.exe", "voicemod.exe", "voicemeeter.exe", "voicemeeterpro.exe", "voicemeeter8.exe", "voicemeeter8x64.exe",
    "obs64.exe", "obs32.exe", "streamlabs obs.exe", "streamlabs desktop.exe", "xsplit.core.exe", "nvcontainer.exe",
    "nvidia share.exe", "nvidia overlay.exe", "amdrsserv.exe", "radeonsoftware.exe", "rtss.exe", "msiafterburner.exe",
    "steam.exe", "steamwebhelper.exe", "lghub.exe", "lghub_agent.exe", "lghub_system_tray.exe", "razer synapse 3.exe",
    "razercentralservice.exe", "icue.exe", "steelseriesgg.exe", "ds4windows.exe", "x360ce.exe", "wallpaper64.exe",
    "wallpaper32.exe", "spotify.exe", "audiodg.exe", "fxsound.exe", "nahimic.exe", "sonic studio 3.exe"})



# ---------------- funções de sistema ----------------

def executar(cmd, timeout=20):
    """Roda um comando sem abrir janela. Devolve (código, saída)."""
    flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=timeout, creationflags=flags)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as erro:
        return 1, str(erro)


def e_admin():
    if not IS_WIN:
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except OSError:
        return False


def tamanho_pasta(caminho):
    total = 0
    for raiz, _, arquivos in os.walk(caminho):
        for nome in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, nome))
            except OSError:
                pass
    return total


def limpar_temporarios():
    """Apaga temporários do usuário e do Windows. Devolve bytes liberados (aprox.)."""
    pastas = {tempfile.gettempdir()}
    if os.environ.get("LOCALAPPDATA"):
        pastas.add(os.path.join(os.environ["LOCALAPPDATA"], "Temp"))
    if IS_WIN:
        pastas.add(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"))
    liberado = 0
    for base in pastas:
        try:
            nomes = os.listdir(base)
        except OSError:
            continue
        for nome in nomes:
            caminho = os.path.join(base, nome)
            try:
                if os.path.isdir(caminho) and not os.path.islink(caminho):
                    tam = tamanho_pasta(caminho)
                    shutil.rmtree(caminho, ignore_errors=True)
                else:
                    tam = os.path.getsize(caminho)
                    os.remove(caminho)
                liberado += tam
            except OSError:
                pass  # arquivo em uso: pula
    return liberado


def esvaziar_lixeira():
    """Esvazia a lixeira de todas as unidades pela API do Windows. Devolve (ok, mensagem)."""
    if not IS_WIN:
        return False, "Disponível só no Windows."
    SHERB_NOCONFIRMATION, SHERB_NOPROGRESSUI, SHERB_NOSOUND = 0x1, 0x2, 0x4
    shell32 = ctypes.windll.shell32
    shell32.SHEmptyRecycleBinW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong]
    shell32.SHEmptyRecycleBinW.restype = ctypes.c_long
    # HRESULT 0 = sucesso; -2147418113 (0x8000FFFF) = lixeira já vazia
    resultado = shell32.SHEmptyRecycleBinW(None, None,
                                           SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND)
    if resultado in (0, -2147418113):
        return True, "Lixeira esvaziada." if resultado == 0 else "A lixeira já estava vazia."
    return False, f"Não foi possível esvaziar a lixeira (código {resultado & 0xFFFFFFFF:#x})."


def disco_sistema():
    if IS_WIN:
        return os.environ.get("SystemDrive", "C:") + "\\"
    return os.path.abspath(os.sep)


class _Luid(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]


class _LuidAtributos(ctypes.Structure):
    _fields_ = [("Luid", _Luid), ("Attributes", ctypes.c_ulong)]


class _Privilegios(ctypes.Structure):
    _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", _LuidAtributos * 1)]


def _ativar_privilegio(nome):
    """Liga um privilégio do token atual (precisa de Administrador). True se conseguiu."""
    advapi, k32 = ctypes.windll.advapi32, ctypes.windll.kernel32
    token = ctypes.c_void_p()
    if not advapi.OpenProcessToken(k32.GetCurrentProcess(), 0x0020 | 0x0008, ctypes.byref(token)):
        return False  # TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY
    try:
        luid = _Luid()
        if not advapi.LookupPrivilegeValueW(None, nome, ctypes.byref(luid)):
            return False
        novo = _Privilegios(1, (_LuidAtributos * 1)(_LuidAtributos(luid, 0x2)))  # SE_PRIVILEGE_ENABLED
        k32.SetLastError(0)
        advapi.AdjustTokenPrivileges(token, False, ctypes.byref(novo), 0, None, None)
        return k32.GetLastError() == 0
    finally:
        k32.CloseHandle(token)


def _comando_memoria(cmd):
    """Manda um comando ao gerenciador de memória do Windows. True se deu certo.
    3 = gravar páginas alteradas, 4 = limpar standby, 5 = limpar standby de baixa prioridade."""
    valor = ctypes.c_int(cmd)
    return ctypes.windll.ntdll.NtSetSystemInformation(0x50, ctypes.byref(valor), ctypes.sizeof(valor)) == 0


def _limpar_cache_arquivos():
    """Esvazia o cache de arquivos do sistema (precisa de Administrador)."""
    k32 = ctypes.windll.kernel32
    k32.SetSystemFileCacheSize.argtypes = [ctypes.c_size_t, ctypes.c_size_t, ctypes.c_ulong]
    k32.SetSystemFileCacheSize.restype = ctypes.c_bool
    return bool(k32.SetSystemFileCacheSize(ctypes.c_size_t(-1), ctypes.c_size_t(-1), 0))


def liberar_ram(evitar=None):
    """v9.1: libera memória SÓ quando ela está apertada, e sem prejudicar o que está rodando.
    Antes, esvaziava a memória de TODOS os programas (inclusive do jogo e do áudio) e o cache de arquivos: o Windows
    tinha que recarregar tudo do disco depois, o que dava travadinhas. Agora:
      - com memória folgada (mais de 25% livre), não faz nada: memória "parada" no cache deixa o PC mais rápido, não mais lento;
      - apertada: esvazia só programas em segundo plano do seu usuário (nunca o da frente, jogos, voz, áudio, gravação)
        e limpa só a parte de baixa prioridade do cache (standby). O cache de arquivos não é mais jogado fora.
    Devolve (bytes_liberados, mensagem)."""
    if not IS_WIN:
        return 0, "Disponível só no Windows."
    vm = psutil.virtual_memory()
    livre = 100 - vm.percent
    if livre >= 25:
        return 0, (f"A memória está folgada ({livre:.0f}% livre). Limpar agora não deixaria nada mais rápido: "
                   "o Windows usa a memória sobrando como cache, e isso ajuda.")
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
    antes = vm.available
    poupar = set(evitar or ())
    frente = pid_em_primeiro_plano()
    if frente:
        poupar.add(frente)
    for p in psutil.process_iter(["pid", "name", "username"]):
        try:
            nome = (p.info["name"] or "").lower()
            if (p.pid in poupar or p.pid in (0, 4, os.getpid()) or nome in PROTEGIDOS or nome in PROTEGIDOS_LEVE
                    or (p.info["username"] or "").split("\\")[-1].upper() != USUARIO):
                continue
            h = k32.OpenProcess(0x0100 | 0x0400, False, p.pid)  # SET_QUOTA | QUERY_INFORMATION
            if h:
                psapi.EmptyWorkingSet(h)
                k32.CloseHandle(h)
        except (psutil.Error, OSError):
            continue
    admin = e_admin()
    if admin:
        _ativar_privilegio("SeProfileSingleProcessPrivilege")
        _ativar_privilegio("SeIncreaseQuotaPrivilege")
        for cmd in (3, 5):  # grava as páginas alteradas e limpa só o standby de BAIXA prioridade
            _comando_memoria(cmd)
    liberado = max(0, psutil.virtual_memory().available - antes)
    mb = liberado / 1048576
    return liberado, (f"Memória estava apertada ({livre:.0f}% livre): ~{mb:.0f} MB liberados de programas em segundo plano. "
                      "O programa que você está usando e o jogo não foram mexidos.")


def abrir_link(url):
    """v9.1: abre um site no navegador da pessoa. Com o Th Boost como Administrador, abrir direto deixaria o navegador
    também como Administrador (inseguro e sem as contas da pessoa); pelo explorer.exe ele abre normal."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("link inválido")
    if IS_WIN and e_admin():
        try:
            subprocess.Popen(["explorer.exe", url])
            return True
        except OSError:
            pass
    return webbrowser.open(url)


def plano_alto_desempenho():
    cod, _ = executar(["powercfg", "/setactive", PLANO_ALTO_DESEMPENHO])
    return cod == 0


def renovar_ip():
    executar(["ipconfig", "/release"], timeout=30)
    cod, _ = executar(["ipconfig", "/renew"], timeout=60)
    return cod == 0


def medir_ping(host=SERVIDOR_PING):
    """Latência em ms até o servidor, ou None se não respondeu."""
    if not IS_WIN:
        return None
    _, saida = executar(["ping", "-n", "1", "-w", "1500", host], timeout=5)
    m = re.search(r"(?:tempo|time)\s*[=<]\s*(\d+)\s*ms", saida, re.IGNORECASE)
    return int(m.group(1)) if m else None


def ler_gpu():
    """Dados da GPU NVIDIA pelo nvidia-smi. Devolve None se não houver."""
    campos = ("name,temperature.gpu,utilization.gpu,memory.used,memory.total,"
              "power.limit,power.default_limit,power.min_limit,power.max_limit")
    cod, saida = executar(["nvidia-smi", f"--query-gpu={campos}", "--format=csv,noheader,nounits"], timeout=8)
    if cod != 0 or not saida:
        return None
    v = [x.strip() for x in saida.splitlines()[0].split(",")]
    if len(v) != 9:
        return None

    def num(x):
        try:
            return float(x)
        except ValueError:
            return None

    chaves = ["temp", "uso", "vram_usada", "vram_total", "limite", "padrao", "min", "max"]
    g = {"nome": v[0]}
    for chave, valor in zip(chaves, v[1:]):
        g[chave] = num(valor)
    return g


def aplicar_limite_gpu(watts):
    cod, _ = executar(["nvidia-smi", "-pl", str(watts)])
    return cod == 0


def temp_cpu():
    """Temperatura da CPU. No Windows a psutil não expõe isso, então devolve None."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    for lista in temps.values():
        if lista:
            return lista[0].current
    return None


def pid_em_primeiro_plano():
    if not IS_WIN:
        return -1
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    pid = ctypes.c_ulong(0)
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def pasta_do_programa():
    """Pasta onde está o .py (ou o .exe gerado), independente de onde o atalho foi aberto."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def caminho_presentmon():
    """Procura o PresentMon na pasta do programa, na pasta atual e no PATH. v9.1: aceita o nome do download
    (PresentMon-2.3.0-x64.exe) além de PresentMon.exe."""
    for pasta in (pasta_do_programa(), os.getcwd()):
        caminho = os.path.join(pasta, "PresentMon.exe")
        if os.path.isfile(caminho):
            return caminho
        try:
            achados = [a for a in sorted(glob.glob(os.path.join(pasta, "PresentMon*.exe")), reverse=True)
                       if not re.search(r"service|setup|install", os.path.basename(a), re.I)]
        except OSError:
            achados = []
        if achados:
            return achados[0]
    return shutil.which("PresentMon.exe")


def presentmon_colunas(partes):
    """Cabeçalho do CSV do PresentMon -> (coluna do app, do PID ou None, do tempo do quadro em ms) ou None.
    1.x: MsBetweenPresents; 2.x: FrameTime (os dois em milissegundos). Função pura."""
    if "Application" not in partes:
        return None
    for nome in ("MsBetweenPresents", "FrameTime", "MsBetweenDisplayChange", "DisplayedTime"):
        if nome in partes:
            return partes.index("Application"), (partes.index("ProcessID") if "ProcessID" in partes else None), partes.index(nome)
    return None


def fps_estat(quadros, agora, pid_frente=None):
    """v9.2: (fps do último segundo, app, "1% mais baixo" dos últimos 10 s, tempo médio do quadro em ms). Função pura.
    O 1% mais baixo é o FPS dos piores quadros (as travadinhas): quanto mais perto do FPS normal, mais liso o jogo."""
    fps, app = fps_da_janela(quadros, agora, pid_frente)
    if fps is None:
        return None, "", None, None
    ms = [q[3] for q in quadros if q[1] == app and agora - q[0] <= 10 and q[3] > 0]
    ms_rec = [q[3] for q in quadros if q[1] == app and agora - q[0] <= 1.0 and q[3] > 0]
    medio = sum(ms_rec) / len(ms_rec) if ms_rec else None
    baixo = None
    if len(ms) >= 30:
        ms.sort()
        p99 = ms[min(len(ms) - 1, int(len(ms) * 0.99))]
        baixo = round(1000.0 / p99) if p99 > 0 else None
    return fps, app, baixo, (round(medio, 1) if medio else None)


def fps_da_janela(quadros, agora, pid_frente=None, janela=1.0):
    """quadros: deque de (hora, app, pid, ms). Devolve (fps, app) do jogo na frente; se ele não desenhou nada, o app com
    mais quadros (sem o dwm, que é a própria área de trabalho). Função pura."""
    por = {}
    for t, app, pid, ms in quadros:
        if agora - t <= janela and ms > 0:
            por.setdefault((app, pid), []).append(ms)
    if not por:
        return None, ""
    candidatos = [k for k in por if pid_frente is not None and k[1] == pid_frente]
    if not candidatos:
        candidatos = sorted((k for k in por if k[0].lower() != "dwm.exe"), key=lambda k: -len(por[k])) or list(por)
    k = candidatos[0]
    media = sum(por[k]) / len(por[k])
    return (round(1000.0 / media) if media > 0 else None), k[0]


def formatar_velocidade(bps):
    unidades = ["B/s", "KB/s", "MB/s", "GB/s"]
    i = 0
    while bps >= 1024 and i < len(unidades) - 1:
        bps /= 1024
        i += 1
    return f"{bps:.1f} {unidades[i]}"


# ---------------- jogos instalados (Steam, Epic e as outras lojas: veja jogos_lojas) ----------------

EXCLUIR_JOGOS = ("redistributable", "redist", "steamworks", "proton", "linux runtime",
                 "directx", "vc_redist", "dotnet", "easyanticheat", "battleye")


def _steam_registro():
    """v9.1: pasta da Steam pelo registro (Steam instalada em D:\\Steam, por exemplo)."""
    if not IS_WIN:
        return []
    achados = []
    try:
        import winreg as _w
        for raiz, caminho, nome in ((_w.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                    (_w.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                                    (_w.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
            try:
                with _w.OpenKey(raiz, caminho) as k:
                    v = str(_w.QueryValueEx(k, nome)[0]).replace("/", "\\")
                if v and os.path.isdir(v) and v.lower() not in [a.lower() for a in achados]:
                    achados.append(v)
            except OSError:
                continue
    except ImportError:
        pass
    return achados


def _pastas_steam():
    raizes = _raizes_steam()
    if not raizes:
        return []
    base = raizes[0]
    pastas = [os.path.join(base, "steamapps")]
    try:  # bibliotecas extras (ex.: outro HD)
        with open(os.path.join(base, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as f:
            for caminho in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                pastas.append(os.path.join(caminho.replace("\\\\", "\\"), "steamapps"))
    except OSError:
        pass
    return [p for p in dict.fromkeys(pastas) if os.path.isdir(p)]


def _valor_acf(texto, chave):
    m = re.search(r'"%s"\s+"([^"]*)"' % chave, texto)
    return m.group(1) if m else ""


def _jogos_steam():
    jogos = []
    for pasta in _pastas_steam():
        for arq in glob.glob(os.path.join(pasta, "appmanifest_*.acf")):
            try:
                with open(arq, encoding="utf-8", errors="replace") as f:
                    texto = f.read()
            except OSError:
                continue
            nome, appid, instalado = _valor_acf(texto, "name"), _valor_acf(texto, "appid"), _valor_acf(texto, "installdir")
            if nome and appid:
                jogo_pasta = os.path.join(pasta, "common", instalado) if instalado and not re.search(r"[\\/]|\.\.", instalado) else ""
                jogos.append({"nome": nome, "origem": "Steam", "appid": appid, "pasta": jogo_pasta,
                              "abrir": f"steam://rungameid/{appid}"})
    return jogos


def _jogos_epic():
    pasta = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                         "Epic", "EpicGamesLauncher", "Data", "Manifests")
    jogos = []
    for arq in glob.glob(os.path.join(pasta, "*.item")):
        try:
            with open(arq, encoding="utf-8", errors="replace") as f:
                dados = json.load(f)
        except (OSError, ValueError):
            continue
        nome, app = dados.get("DisplayName"), dados.get("AppName")
        if nome and app and dados.get("bIsApplication", True):
            jogos.append({"nome": nome, "origem": "Epic", "pasta": str(dados.get("InstallLocation") or ""),
                          "abrir": f"com.epicgames.launcher://apps/{app}?action=launch&silent=true"})
    return jogos


def detectar_jogos():
    """Lista os jogos instalados (Steam, Epic, Riot, Roblox, FiveM, Xbox, EA, Ubisoft, GOG...), sem programas auxiliares."""
    if not IS_WIN:
        return []
    return jogos_detectar_tudo()


def lancar_jogo(abrir):
    """Abre o jogo: por um endereço do launcher (steam://, uplay://...), pelo .exe, ou pelo launcher com argumentos. True se conseguiu."""
    if not IS_WIN:
        return False
    try:
        if isinstance(abrir, (list, tuple)):
            exe = abrir[0] if abrir else ""
            if not isinstance(exe, str) or not exe.lower().endswith(".exe") or not os.path.isfile(exe):
                return False
            subprocess.Popen([str(x) for x in abrir], cwd=os.path.dirname(exe), close_fds=True,
                             creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            return True
        os.startfile(abrir)
        return True
    except (OSError, ValueError):
        return False


# ---------------- capas dos jogos ----------------

def _raizes_steam():
    raizes = list(_steam_registro())  # v9.1: primeiro onde a Steam diz que está (pode ser D:\\Steam)
    for raiz in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files")):
        c = os.path.join(raiz, "Steam")
        if os.path.isdir(c) and c.lower() not in [r.lower() for r in raizes]:
            raizes.append(c)
    return raizes


def pasta_capas():
    caminho = os.path.join(pasta_do_programa(), "capas")
    try:
        os.makedirs(caminho, exist_ok=True)
        return caminho
    except OSError:
        return tempfile.gettempdir()


def _capa_no_computador(appid):
    """Procura a capa que a própria Steam já guardou no PC."""
    for raiz in _raizes_steam():
        cache = os.path.join(raiz, "appcache", "librarycache")
        candidatos = [os.path.join(cache, f"{appid}_header.jpg"),
                      os.path.join(cache, f"{appid}_library_600x900.jpg"),
                      os.path.join(cache, str(appid), "header.jpg"),
                      os.path.join(cache, str(appid), "library_600x900.jpg")]
        for caminho in candidatos:
            if os.path.isfile(caminho):
                return caminho
    return None


def capa_do_jogo(jogo):
    """Caminho da imagem do jogo: usa a do PC, senão baixa da Steam. None se não houver."""
    appid = jogo.get("appid")
    if not appid:
        return icone_do_jogo(jogo)  # fora da Steam: usa o ícone do programa do jogo
    local = _capa_no_computador(appid)
    if local:
        return local
    destino = os.path.join(pasta_capas(), f"{appid}.jpg")
    if os.path.isfile(destino):
        return destino
    url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
    try:
        with urllib.request.urlopen(url, timeout=10) as resposta, open(destino, "wb") as arq:
            shutil.copyfileobj(resposta, arq)
        return destino if os.path.getsize(destino) > 1000 else None
    except Exception:
        try:
            os.remove(destino)
        except OSError:
            pass
        return None



# ---------------- coleta em segundo plano ----------------

class Monitor(threading.Thread):
    """Coleta GPU, rede, FPS e prioridades em segundo plano, para a janela não travar."""

    def __init__(self):
        super().__init__(daemon=True)
        self.dados = {"gpu": None, "gpu_lida": False, "fps": None, "app": "", "fps_erro": "", "fps1": None, "fps_ms": None,
                      "down": 0.0, "up": 0.0}
        self.overlay = False  # v9.2: FPS na tela ligado (lê a placa de vídeo mesmo com a janela do Th Boost fechada)
        self.modo_leve = False
        self.forcar = False
        self.fps_ligado = False
        self.proc_fps = None
        self.alterados = set()  # PIDs cuja prioridade foi mexida
        self.fixos = set()  # PIDs cuja prioridade é cuidada pela sessão de jogo (o Modo Leve não mexe)
        self.ocioso = False  # sem janela aberta (modo segundo plano): só mantém as prioridades
        self.trava = threading.Lock()
        self.quadros = collections.deque()
        self.jogando = False  # v9.1: durante uma sessão de jogo o Th Boost lê menos coisas (sobra mais CPU para o jogo)
        self._dono = {}  # pid -> (hora de criação, é do seu usuário?) para não perguntar ao Windows a cada 4 s
        self.protege = set()  # v9.2: a janelinha do FPS na tela (o Modo Leve não baixa a prioridade dela)
        self._religar_fps = False

    def run(self):
        ultimo_gpu = ultimo_prio = ultimo_cpu_ov = 0.0
        ultimo_rede = time.time()
        rede_antes = psutil.net_io_counters()
        while True:
            agora = time.time()
            if self.ocioso:  # ninguém olhando os números: não gasta CPU lendo GPU e rede
                rede_antes, ultimo_rede = psutil.net_io_counters(), agora
            if (not self.ocioso or self.overlay) and agora - ultimo_gpu > (2.0 if self.overlay else 5.0 if self.jogando else 1.5):
                self.dados["gpu"] = ler_gpu()
                self.dados["gpu_lida"] = True
                ultimo_gpu = agora
            if self.overlay and agora - ultimo_cpu_ov >= 0.9:  # v9.2: CPU % do FPS na tela, lida sempre por esta mesma linha
                ultimo_cpu_ov = agora
                try:
                    self.dados["cpu_ov"] = psutil.cpu_percent(interval=None)
                except Exception:
                    self.dados["cpu_ov"] = None
            if not self.ocioso and agora - ultimo_rede >= 1:
                rede_agora = psutil.net_io_counters()
                dt = agora - ultimo_rede
                self.dados["down"] = (rede_agora.bytes_recv - rede_antes.bytes_recv) / dt
                self.dados["up"] = (rede_agora.bytes_sent - rede_antes.bytes_sent) / dt
                rede_antes, ultimo_rede = rede_agora, agora
            if (self.modo_leve or self.alterados) and (self.forcar or agora - ultimo_prio > (6 if self.jogando else 4)):
                self.forcar = False
                ultimo_prio = agora
                self.aplicar_prioridades(self.modo_leve)
            time.sleep(1.0 if self.ocioso else 0.4)

    def ligar_fps(self, ligar):
        self.dados["fps_erro"] = ""
        self.fps_ligado = ligar
        if ligar and self.proc_fps is None:
            self._religar_fps = False
            threading.Thread(target=self._ler_presentmon, daemon=True).start()
        elif ligar:
            self._religar_fps = True  # o leitor antigo ainda está fechando: abre outro assim que ele terminar
        elif self.proc_fps is not None:
            self._religar_fps = False
            try:
                self.proc_fps.terminate()
            except OSError:
                pass

    def _ler_presentmon(self):
        """v9.1: funciona com o PresentMon 1.x e 2.x, mostra o FPS do jogo que está na frente e nunca fica preso."""
        caminho = caminho_presentmon()
        if caminho is None:
            self.dados["fps_erro"] = ("PresentMon não encontrado. Baixe em github.com/GameTechDev/PresentMon e coloque o "
                                      ".exe dentro da pasta do Th Boost.")
            self.fps_ligado = False
            return
        flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
        recebeu = False
        try:
            for args in PRESENTMON_VARIANTES:
                if not self.fps_ligado:
                    break
                try:
                    proc = subprocess.Popen([caminho] + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                            text=True, encoding="utf-8", errors="replace", creationflags=flags)
                except OSError:
                    self.dados["fps_erro"] = "Não foi possível iniciar o PresentMon."
                    break
                self.proc_fps = proc
                colunas, ultimo = None, 0.0
                for linha in proc.stdout:
                    if not self.fps_ligado:
                        break
                    partes = linha.strip().split(",")
                    if colunas is None:
                        colunas = presentmon_colunas(partes)
                        continue
                    try:
                        app = partes[colunas[0]]
                        pid = int(partes[colunas[1]]) if colunas[1] is not None else None
                        ms = float(partes[colunas[2]])
                    except (IndexError, ValueError):
                        continue
                    recebeu = True
                    agora = time.time()
                    self.quadros.append((agora, app, pid, ms))
                    while self.quadros and agora - self.quadros[0][0] > 10:
                        self.quadros.popleft()
                    if agora - ultimo >= 0.5:  # atualiza a tela 2x por segundo
                        ultimo = agora
                        fps, nome, baixo, ms_q = fps_estat(self.quadros, agora, pid_em_primeiro_plano())
                        self.dados["fps"] = fps
                        self.dados["app"] = nome.replace(".exe", "")
                        self.dados["fps1"] = baixo
                        self.dados["fps_ms"] = ms_q
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except (OSError, subprocess.SubprocessError):
                    pass
                if colunas is not None or not self.fps_ligado:
                    break  # este jeito funcionou (ou a pessoa desligou): não tenta o outro
            if self.fps_ligado:  # parou sozinho, sem o usuário desligar
                self.dados["fps_erro"] = (("PresentMon parou. " if recebeu else "PresentMon não iniciou. ")
                                          + ("Abra o Th Boost como Administrador." if not e_admin()
                                             else "Feche outros contadores de FPS (Afterburner/RTSS) e tente de novo."))
        except Exception:
            self.dados["fps_erro"] = "O contador de FPS falhou. Desligue e ligue de novo."
        finally:
            self.proc_fps = None
            self.dados["fps"] = None
            self.dados["fps1"] = self.dados["fps_ms"] = None
            self.quadros.clear()
            if self._religar_fps:  # desligou e ligou de novo rápido
                self._religar_fps = False
                self.fps_ligado = True
                self.dados["fps_erro"] = ""
                threading.Thread(target=self._ler_presentmon, daemon=True).start()
            else:
                self.fps_ligado = False

    def aplicar_prioridades(self, leve):
        """Modo leve: app em foco com prioridade alta; o resto do seu usuário com prioridade baixa."""
        if not IS_WIN or not USUARIO:
            return
        with self.trava:
            if not leve:
                for pid in self.alterados:
                    try:
                        psutil.Process(pid).nice(psutil.NORMAL_PRIORITY_CLASS)
                    except (psutil.Error, OSError):
                        pass
                self.alterados.clear()
                return
            frente = pid_em_primeiro_plano()
            vistos = set()
            for p in psutil.process_iter(["pid", "name", "create_time"]):
                try:
                    nome = (p.info["name"] or "").lower()
                    vistos.add(p.pid)
                    if p.pid in (0, 4, os.getpid()) or nome in PROTEGIDOS or nome in PROTEGIDOS_LEVE or p.pid in self.fixos \
                            or p.pid in self.protege or nome.startswith("presentmon"):  # v9.2: o contador e o FPS na tela
                        continue
                    criado = p.info.get("create_time")
                    dono = self._dono.get(p.pid)
                    if dono is None or dono[0] != criado:
                        dono = (criado, p.username().split("\\")[-1].upper() == USUARIO)
                        self._dono[p.pid] = dono
                    if not dono[1]:
                        continue  # só mexe nos programas do seu usuário
                    alvo = psutil.ABOVE_NORMAL_PRIORITY_CLASS if p.pid == frente else psutil.BELOW_NORMAL_PRIORITY_CLASS
                    atual = p.nice()
                    if p.pid not in self.alterados and atual != psutil.NORMAL_PRIORITY_CLASS:
                        continue  # v9.1: quem já tinha outra prioridade (escolhida por você ou pelo programa) fica como está
                    if atual != alvo:
                        p.nice(alvo)
                    self.alterados.add(p.pid)
                except (psutil.Error, OSError):
                    continue
            for pid in [x for x in self._dono if x not in vistos]:  # programas que fecharam
                self._dono.pop(pid, None)
            self.alterados &= vistos
