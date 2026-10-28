APP_NAME = "Th Boost"
IS_WIN = os.name == "nt"
USUARIO = os.environ.get("USERNAME", "").upper()
PRESENTMON_ARGS = ["--output_stdout", "--stop_existing_session"]
PLANO_ALTO_DESEMPENHO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
SERVIDOR_PING = "8.8.8.8"
FONTE = "Segoe UI"


# Processos do sistema que nunca têm a prioridade alterada
PROTEGIDOS = {
    "explorer.exe", "ctfmon.exe", "sihost.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "searchhost.exe",
}


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


def liberar_ram():
    """Libera o máximo de memória: processos, páginas alteradas, cache de arquivos e standby.
    Devolve (bytes_liberados, mensagem)."""
    if not IS_WIN:
        return 0, "Disponível só no Windows."
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
    antes = psutil.virtual_memory().available
    for p in psutil.process_iter(["pid"]):  # esvazia a memória de cada processo
        h = k32.OpenProcess(0x0100 | 0x0400, False, p.info["pid"])  # SET_QUOTA | QUERY_INFORMATION
        if h:
            psapi.EmptyWorkingSet(h)
            k32.CloseHandle(h)
    admin = e_admin()
    if admin:
        _ativar_privilegio("SeProfileSingleProcessPrivilege")
        _ativar_privilegio("SeIncreaseQuotaPrivilege")
        for cmd in (3, 4, 5):  # gravar páginas alteradas e limpar o standby (normal e baixa prioridade)
            _comando_memoria(cmd)
        _limpar_cache_arquivos()
    liberado = max(0, psutil.virtual_memory().available - antes)
    mb = liberado / 1048576
    if admin:
        return liberado, f"RAM liberada: ~{mb:.0f} MB (processos, cache de arquivos e standby)."
    return liberado, (f"RAM liberada: ~{mb:.0f} MB dos processos. "
                      "Abra como Administrador para liberar também o cache do sistema.")


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
    """Procura PresentMon.exe na pasta do programa, na pasta atual e no PATH."""
    for pasta in (pasta_do_programa(), os.getcwd()):
        caminho = os.path.join(pasta, "PresentMon.exe")
        if os.path.isfile(caminho):
            return caminho
    return shutil.which("PresentMon.exe")


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


def _pastas_steam():
    base = None
    for raiz in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files")):
        if os.path.isdir(os.path.join(raiz, "Steam")):
            base = os.path.join(raiz, "Steam")
            break
    if base is None:
        return []
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
    raizes = []
    for raiz in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files")):
        if os.path.isdir(os.path.join(raiz, "Steam")):
            raizes.append(os.path.join(raiz, "Steam"))
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
        self.dados = {"gpu": None, "gpu_lida": False, "fps": None, "app": "", "fps_erro": "",
                      "down": 0.0, "up": 0.0}
        self.modo_leve = False
        self.forcar = False
        self.fps_ligado = False
        self.proc_fps = None
        self.alterados = set()  # PIDs cuja prioridade foi mexida
        self.fixos = set()  # PIDs cuja prioridade é cuidada pela sessão de jogo (o Modo Leve não mexe)
        self.ocioso = False  # sem janela aberta (modo segundo plano): só mantém as prioridades
        self.trava = threading.Lock()
        self.quadros = collections.deque()

    def run(self):
        ultimo_gpu = ultimo_prio = 0.0
        ultimo_rede = time.time()
        rede_antes = psutil.net_io_counters()
        while True:
            agora = time.time()
            if self.ocioso:  # ninguém olhando os números: não gasta CPU lendo GPU e rede
                rede_antes, ultimo_rede = psutil.net_io_counters(), agora
            if not self.ocioso and agora - ultimo_gpu > 1.5:
                self.dados["gpu"] = ler_gpu()
                self.dados["gpu_lida"] = True
                ultimo_gpu = agora
            if not self.ocioso and agora - ultimo_rede >= 1:
                rede_agora = psutil.net_io_counters()
                dt = agora - ultimo_rede
                self.dados["down"] = (rede_agora.bytes_recv - rede_antes.bytes_recv) / dt
                self.dados["up"] = (rede_agora.bytes_sent - rede_antes.bytes_sent) / dt
                rede_antes, ultimo_rede = rede_agora, agora
            if (self.modo_leve or self.alterados) and (self.forcar or agora - ultimo_prio > 4):
                self.forcar = False
                ultimo_prio = agora
                self.aplicar_prioridades(self.modo_leve)
            time.sleep(1.0 if self.ocioso else 0.4)

    def ligar_fps(self, ligar):
        self.dados["fps_erro"] = ""
        self.fps_ligado = ligar
        if ligar and self.proc_fps is None:
            threading.Thread(target=self._ler_presentmon, daemon=True).start()
        elif not ligar and self.proc_fps is not None:
            self.proc_fps.terminate()

    def _ler_presentmon(self):
        caminho = caminho_presentmon()
        if caminho is None:
            self.dados["fps_erro"] = ("PresentMon.exe não encontrado. Coloque o arquivo "
                                      "dentro da pasta do Th Boost e tente de novo.")
            self.fps_ligado = False
            return
        flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
        try:
            proc = subprocess.Popen([caminho] + PRESENTMON_ARGS, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, creationflags=flags)
        except OSError:
            self.dados["fps_erro"] = "Não foi possível iniciar o PresentMon."
            self.fps_ligado = False
            return
        self.proc_fps = proc
        colunas, recebeu = None, False
        for linha in proc.stdout:
            if not self.fps_ligado:
                break
            partes = linha.strip().split(",")
            if colunas is None:
                if "Application" in partes and "TimeInSeconds" in partes:
                    colunas = (partes.index("Application"), partes.index("TimeInSeconds"))
                continue
            try:
                app, t = partes[colunas[0]], float(partes[colunas[1]])
            except (IndexError, ValueError):
                continue
            recebeu = True
            self.quadros.append((t, app))
            while self.quadros and t - self.quadros[0][0] > 2:
                self.quadros.popleft()
            # FPS = quadros do último app nos últimos 1 segundo
            self.dados["fps"] = sum(1 for ti, a in self.quadros if a == app and t - ti < 1)
            self.dados["app"] = app.replace(".exe", "")
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except (OSError, subprocess.SubprocessError):
            pass
        if self.fps_ligado:  # parou sozinho, sem o usuário desligar
            self.dados["fps_erro"] = ("PresentMon parou. Abra o Th Boost como Administrador."
                                      if recebeu else
                                      "PresentMon não iniciou. Abra o Th Boost como Administrador.")
        self.fps_ligado = False
        self.proc_fps = None
        self.dados["fps"] = None
        self.quadros.clear()

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
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    nome = (p.info["name"] or "").lower()
                    if p.pid in (0, 4, os.getpid()) or nome in PROTEGIDOS or p.pid in self.fixos:
                        continue
                    if p.username().split("\\")[-1].upper() != USUARIO:
                        continue  # só mexe nos programas do seu usuário
                    p.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS if p.pid == frente
                           else psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    self.alterados.add(p.pid)
                except (psutil.Error, OSError):
                    continue
