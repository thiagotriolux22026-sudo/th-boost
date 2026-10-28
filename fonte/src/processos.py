# ---------------- processos: ver o que está rodando e reduzir ----------------
#
# Regras de segurança:
#  - só se fecha processo do PRÓPRIO usuário, de programa que fica fora da pasta do Windows;
#  - Windows, antivírus, drivers/hardware, navegadores e o próprio Th Boost nunca são fechados daqui;
#  - a tela manda só um nome; o programa confere de novo na lista atual antes de fechar, e cada processo
#    é conferido pela hora em que foi criado (para nunca fechar outro que herdou o mesmo número);
#  - serviços de programas instalados só são mexidos se estiverem na lista atual e fora das exclusões
#    (antivírus, drivers, VPN, antitrapaça, certificado digital...), e o início anterior fica guardado para desfazer.

_P_WINDOWS = frozenset({
    "system", "system idle process", "registry", "memory compression", "secure system", "vmmem", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe", "winlogon.exe", "fontdrvhost.exe",
    "dwm.exe", "explorer.exe", "sihost.exe", "taskhostw.exe", "ctfmon.exe", "runtimebroker.exe", "searchhost.exe",
    "searchindexer.exe", "searchapp.exe", "searchprotocolhost.exe", "searchfilterhost.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "textinputhost.exe", "applicationframehost.exe", "conhost.exe", "dllhost.exe",
    "audiodg.exe", "spoolsv.exe", "wmiprvse.exe", "taskmgr.exe", "wudfhost.exe", "dashost.exe", "backgroundtaskhost.exe",
    "smartscreen.exe", "useroobebroker.exe", "systemsettings.exe", "msiexec.exe", "unsecapp.exe", "wlanext.exe",
    "sgrmbroker.exe", "lockapp.exe", "logonui.exe", "csrss", "ntoskrnl.exe", "securityhealthsystray.exe",
    "securityhealthservice.exe", "sppsvc.exe", "trustedinstaller.exe", "tiworker.exe", "wermgr.exe", "werfault.exe",
    "msdtc.exe", "lsm.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "wscript.exe",
    "mmc.exe", "regedit.exe", "winlogon", "gamebar.exe",
})
_P_SEGURANCA = re.compile(
    r"^(msmpeng|nissrv|mpcmdrun|mpdefendercoreservice|avp|avpui|kavtray|avgui|avgsvc|avgnt|avastsvc|avastui|afwserv|bdagent|"
    r"bdservicehost|vsserv|bdredline|updatesrv|mbamservice|mbamtray|mbam|mcshield|mfemms|mfevtps|mcuicnt|nortonsecurity|"
    r"nsservice|nswscsvc|ekrn|egui|wrsa|sophos\w*|savservice|cylance\w*|csfalconservice|csfalconcontainer|"
    r"sentinel\w*|mcafee\w*|trendmicro\w*|tmbmsrv|ntrtscan|pccntmon|zonealarm\w*|fsav\w*|fshoster\w*|dwengine|dwservice|"
    r"spideragent|panda\w*|cmdagent|windowsdefender\w*)\.exe$", re.IGNORECASE)
_P_HARDWARE = re.compile(
    r"^(nvcontainer|nvdisplay\.container|nvtelemetrycontainer|nvidia[\w .-]*|nvspcaps\w*|nvsphelper\w*|nvbackend|"
    r"radeonsoftware|amddvr|amdow|atieclxx|atiesrxx|amdrssrcext|cncmd|igfx\w*|intelcphdcpsvc|intelgraphics\w*|"
    r"rtkauduservice\w*|ravbg\w*|ravcpl\w*|rthdvcpl|realtek\w*|waveshaper\w*|nahimicservice|nahimic\w*|sonic\w*|"
    r"syntp\w*|synaptics\w*|apoint|elantech\w*|etdctrl|hidmonitor\w*|lghub\w*|logi\w*|lcore|razer\w*|rzsynapse\w*|"
    r"icue|corsair\w*|steelseries\w*|armourycrate\w*|armoury\w*|asus\w*|msiafterburner|rtss|msicenter\w*|dragoncenter\w*|"
    r"gigabyte\w*|aorus\w*|rgb\w*|openrgb|signalrgb|cam_helper|nzxt\w*|wacom\w*|tobii\w*|vgtray|vgc|"
    r"easyanticheat\w*|beservice|beclient|battleye\w*|faceit\w*|eosoverlayrenderer\w*|punkbuster\w*|xigncode\w*)\.exe$",
    re.IGNORECASE)
_P_NAVEGADOR = re.compile(
    r"^(chrome|msedge|msedgewebview2|firefox|brave|opera|opera_gx\w*|vivaldi|iexplore|chromium|waterfox|librewolf|"
    r"yandex|arc)\.exe$", re.IGNORECASE)

# rótulo amigável, tipo e se é fechado de uma vez pelo botão "Reduzir processos" (só ajudantes que ninguém usa direto)
CONHECIDOS = [
    (r"^(googleupdate|googlecrashhandler\w*|googleupdaterwakesvc)\.exe$", "Atualizador do Google", "atualizador", True),
    (r"^microsoftedgeupdate\.exe$", "Atualizador do Edge", "atualizador", True),
    (r"^(jusched|jucheck|javaupdsvc)\.exe$", "Atualizador do Java", "atualizador", True),
    (r"^(adobearm|adobegcclient|agsservice|agmservice|adobeipcbroker|adobenotificationclient|ccxprocess|cclibrary|"
     r"adobecollabsync|armsvc|acrotray|adobeupdateservice|adobe desktop service|coresync|adobe crash processor)\.exe$",
     "Adobe (segundo plano)", "atualizador", True),
    (r"^(supportassist\w*|sauser\w*|dellsupportassist\w*|hpsupportassistant\w*|hpcommsrecovery|hp\.myhp\w*)\.exe$",
     "Suporte do fabricante", "atualizador", True),
    (r"^(ituneshelper|ipodservice|applemobiledevice\w*|appleosx\w*)\.exe$", "iTunes (ajudante)", "atualizador", True),
    (r"^(ccleaner\w*|ccleanerbrowser\w*)\.exe$", "CCleaner", "atualizador", True),
    (r"^(creative cloud|creativecloud|adobe creative cloud)\.exe$", "Adobe Creative Cloud", "launcher", False),
    (r"^(steam|steamwebhelper|steamservice)\.exe$", "Steam", "launcher", False),
    (r"^(epicgameslauncher|epicwebhelper|unrealcefsubprocess)\.exe$", "Epic Games", "launcher", False),
    (r"^(battle\.net|blizzard\w*)\.exe$", "Battle.net", "launcher", False),
    (r"^(origin|originwebhelperservice|eadesktop|eabackgroundservice|eaconnect_microsoft|ealink\w*|eaanticheat\w*)\.exe$",
     "EA / Origin", "launcher", False),
    (r"^(upc|ubisoftconnect|uplaywebcore|ubisoftgamelauncher\w*)\.exe$", "Ubisoft Connect", "launcher", False),
    (r"^(galaxyclient|galaxyclientservice|galaxycommunication|gogalaxy\w*)\.exe$", "GOG Galaxy", "launcher", False),
    (r"^(riotclientservices|riotclientux|riotclientuxrender|riotclientcrashhandler)\.exe$", "Riot Client", "launcher", False),
    (r"^(xboxpcapp|xboxapp|gamingservices\w*|xboxappservices\w*)\.exe$", "Xbox", "launcher", False),
    (r"^discord(?:ptb|canary|development)?\.exe$|^update\.exe$", "Discord / atualizador", "chat", False),
    (r"^(spotify|spotifylauncher|spotifywebhelper)\.exe$", "Spotify", "chat", False),
    (r"^(teams|ms-teams|msteams|msteamsupdate|teamsupdate)\.exe$", "Microsoft Teams", "chat", False),
    (r"^(slack|telegram|whatsapp|whatsapp\.root|signal|zoom|zoomit|skype|skypehost|skypeapp|skypebackgroundhost)\.exe$",
     "Chat / reunião", "chat", False),
    (r"^(onedrive|onedrivestandalone\w*|filecoauth|dropbox|dropboxupdate|googledrivefs|googledrivesync|megasync|"
     r"icloud\w*|icloudservices|mega)\.exe$", "Sincronização na nuvem", "nuvem", False),
    (r"^(utorrent|bittorrent|qbittorrent|deluge\w*|transmission\w*)\.exe$", "Torrent", "outro", False),
]
# o que as opções “launchers e nuvem” e “chats e músicas” do Reduzir processos fecham (nunca o que está na frente nem o que sustenta um jogo)
TIPOS_OPCIONAIS = {"launchers": ("launcher", "nuvem"), "chats": ("chat",)}
# nomes de ajudantes de um programa (não contam como "outro programa aberto por ele")
_AJUDANTE_RE = re.compile(r"crash|report|helper|webhelper|cef|update|overlay|broker|watchdog|elevat|install", re.IGNORECASE)
_CONHECIDOS_RE = [(re.compile(r, re.IGNORECASE), rot, tipo, auto) for r, rot, tipo, auto in CONHECIDOS]
_ROTULOS_WINDOWS = {
    "svchost.exe": "Serviços do Windows", "system": "Núcleo do Windows", "explorer.exe": "Explorer (barra de tarefas)",
    "dwm.exe": "Gerenciador de janelas", "searchindexer.exe": "Indexação da busca", "msmpeng.exe": "Windows Defender",
    "runtimebroker.exe": "Permissões de apps", "taskhostw.exe": "Tarefas do Windows", "sihost.exe": "Interface do Windows",
    "audiodg.exe": "Áudio do Windows", "spoolsv.exe": "Impressão", "wmiprvse.exe": "Diagnóstico do Windows",
    "conhost.exe": "Janelas de console", "dllhost.exe": "Componentes do Windows", "registry": "Registro do Windows",
    "memory compression": "Compressão de memória", "csrss.exe": "Núcleo do Windows", "lsass.exe": "Segurança do Windows",
    "winlogon.exe": "Entrada no Windows", "services.exe": "Controle de serviços", "ctfmon.exe": "Teclado e escrita",
    "fontdrvhost.exe": "Fontes do Windows", "searchhost.exe": "Busca do Iniciar", "shellexperiencehost.exe": "Interface do Windows",
    "startmenuexperiencehost.exe": "Menu Iniciar", "textinputhost.exe": "Teclado de toque", "applicationframehost.exe": "Janelas de apps",
}
# ajudantes do Windows que quase ninguém usa (a mesma lista da Otimização Extrema)
_DISP_WIN = {k.lower(): v for k, v in PROCESSOS_DISPENSAVEIS.items()}
SVC_CHAVE = r"SYSTEM\CurrentControlSet\Services\%s"


def _rotulo_exe(nome):
    base = nome[:-4] if nome.lower().endswith(".exe") else nome
    return base[:1].upper() + base[1:]


def _raiz_windows():
    return (_env("SYSTEMROOT") or _env("WINDIR") or "").lower().rstrip("\\/")


def _dono_e_o_usuario(username):
    if not username:
        return False
    return username.replace("/", "\\").split("\\")[-1].upper() == USUARIO.upper()


def _ler_processos():
    """Lê os processos do sistema. Cada item: dict com pid, ppid (quem abriu), name, exe, username, rss, ct (hora de criação)."""
    res = []
    for p in psutil.process_iter(["pid", "ppid", "name", "exe", "username", "memory_info", "create_time"]):
        i = p.info
        try:
            mi = i.get("memory_info")
            res.append({"pid": i["pid"], "ppid": i.get("ppid") or 0, "name": i.get("name") or "", "exe": i.get("exe") or "",
                        "username": i.get("username") or "", "rss": getattr(mi, "rss", 0) or 0,
                        "ct": i.get("create_time") or 0.0})
        except (psutil.Error, OSError, KeyError):
            continue
    return res


def _pids_proprios():
    """O próprio Th Boost e tudo que ele abriu (como a janela do aplicativo)."""
    ids = {os.getpid()}
    try:
        eu = psutil.Process()
        ids.update(c.pid for c in eu.children(recursive=True))
        ids.update(p.pid for p in eu.parents()[:3])
    except (psutil.Error, OSError):
        pass
    return ids


def classificar(proc, proprios, raiz):
    """Devolve (categoria, rótulo, auto, fechável) para um processo."""
    nome = proc["name"].lower()
    exe = (proc["exe"] or "").lower()
    meu = _dono_e_o_usuario(proc["username"])
    if proc["pid"] in proprios:
        return "eu", "Th Boost", False, False
    if nome in _DISP_WIN and meu:
        return "dispensavel", _DISP_WIN[nome].capitalize(), True, True
    if (nome in _P_WINDOWS or not exe or not meu or (raiz and exe.startswith(raiz + "\\"))):
        return "windows", _ROTULOS_WINDOWS.get(nome) or _rotulo_exe(proc["name"]), False, False
    if _P_SEGURANCA.match(nome):
        return "seguranca", "Proteção do PC", False, False
    if _P_HARDWARE.match(nome):
        return "hardware", _rotulo_exe(proc["name"]), False, False
    if _P_NAVEGADOR.match(nome):
        return "navegador", _rotulo_exe(proc["name"]), False, False
    for rx, rot, tipo, auto in _CONHECIDOS_RE:
        if rx.match(nome):
            return tipo, rot, auto, True
    return "outro", _rotulo_exe(proc["name"]), False, True


def escanear_processos(fonte=None, proprios=None, raiz=None):
    """Agrupa os processos por nome. 'fonte', 'proprios' e 'raiz' existem para os testes."""
    procs = fonte if fonte is not None else _ler_processos()
    proprios = _pids_proprios() if proprios is None else proprios
    raiz = _raiz_windows() if raiz is None else raiz
    grupos, classe = {}, {}
    for p in procs:
        chave = p["name"].lower()
        if not chave or chave == "system idle process" or p["pid"] == 0:
            continue  # o "ocioso" não é um processo de verdade; o Gerenciador de Tarefas também não conta
        cat, rot, auto, fech = classificar(p, proprios, raiz)
        classe[p["pid"]] = (chave, cat, rot, p["ct"])
        g = grupos.get(chave)
        if g is None:
            g = grupos[chave] = {"nome": chave, "exe": p["name"], "rotulo": rot, "cat": cat, "auto": auto, "qtd": 0,
                                 "mb": 0.0, "fechavel": False, "pids": [], "pids_fechaveis": [], "ocupado": []}
        g["qtd"] += 1
        g["mb"] += p["rss"] / 1048576
        g["pids"].append((p["pid"], p["ct"]))
        if fech:
            g["pids_fechaveis"].append((p["pid"], p["ct"], p["rss"]))
        if cat == "eu":  # se qualquer instância é do próprio programa, o grupo todo fica protegido
            g.update(cat="eu", rotulo="Th Boost", auto=False)
    # quem abriu outro programa de verdade (um jogo aberto pelo launcher) está sendo usado: não é fechado por opção nenhuma
    for p in procs:
        pai = classe.get(p.get("ppid") or 0)
        filho = classe.get(p["pid"])
        if not pai or not filho or filho[3] + 1.0 < pai[3]:
            continue  # sem pai conhecido, ou o número do pai foi reaproveitado
        if filho[1] != "outro" or filho[2] == pai[2] or _AJUDANTE_RE.search(p["name"]):
            continue
        ocupado = grupos[pai[0]]["ocupado"]
        if filho[2] not in ocupado and len(ocupado) < 3:
            ocupado.append(filho[2])
    for g in grupos.values():
        g["fechavel"] = bool(g["pids_fechaveis"]) and g["cat"] not in ("eu", "windows", "seguranca", "hardware", "navegador") \
            and not any(pid in proprios for pid, _ in g["pids"])
        g["mb"] = round(g["mb"], 1)
    lista = sorted(grupos.values(), key=lambda g: -g["mb"])
    dispens = [g for g in lista if g["auto"] and g["fechavel"]]
    por_cat = {}
    for g in lista:
        c = por_cat.setdefault(g["cat"], {"qtd": 0, "mb": 0.0})
        c["qtd"] += g["qtd"]
        c["mb"] = round(c["mb"] + g["mb"], 1)
    opcionais = {}
    for chave, tipos in TIPOS_OPCIONAIS.items():
        alvo = [g for g in lista if g["fechavel"] and g["cat"] in tipos]
        opcionais[chave] = {"qtd": sum(len(g["pids_fechaveis"]) for g in alvo), "mb": round(sum(g["mb"] for g in alvo), 1)}
    sv = grupos.get("svchost.exe")
    return {"total": sum(g["qtd"] for g in lista), "mb_total": round(sum(g["mb"] for g in lista), 1), "grupos": lista,
            "mapa": grupos, "por_cat": por_cat, "svchost": sv["qtd"] if sv else 0, "opcionais": opcionais,
            "dispensaveis": {"qtd": sum(len(g["pids_fechaveis"]) for g in dispens), "mb": round(sum(g["mb"] for g in dispens), 1)}}


def escolher_opcionais(d, tipos, frente=None, jogando=False):
    """Quais programas abertos o Reduzir processos fecha por opção (launchers, nuvem, chats). Função pura.
    Fica de fora, com o motivo: o programa da janela da frente, quem está sustentando outro programa (um jogo aberto pelo
    launcher) e qualquer launcher enquanto há um jogo da lista rodando. Devolve (grupos_a_fechar, [(rótulo, motivo)])."""
    cand = [g for g in d["grupos"] if g["fechavel"] and g["cat"] in tipos]
    bloqueio = {}
    for g in cand:  # o bloqueio vale para o programa inteiro (Steam = steam.exe + steamwebhelper.exe...), em qualquer ordem
        if g["rotulo"] in bloqueio:
            continue
        if frente is not None and any(pid == frente for pid, _ in g["pids"]):
            bloqueio[g["rotulo"]] = "você está usando agora"
        elif g["ocupado"]:
            bloqueio[g["rotulo"]] = "está sustentando " + ", ".join(g["ocupado"][:2])
        elif jogando and g["cat"] == "launcher":
            bloqueio[g["rotulo"]] = "tem um jogo aberto"
    fechar = [g for g in cand if g["rotulo"] not in bloqueio]
    poupados = sorted(bloqueio.items())
    return fechar, poupados


def fechar_pids(pids):
    """Fecha os processos (primeiro com educação, depois à força). Devolve (quantos fechou, MB liberados)."""
    alvos, mb = [], 0.0
    for pid, ct, rss in pids:
        try:
            p = psutil.Process(pid)
            if abs(p.create_time() - ct) > 1.0:
                continue  # o número foi reaproveitado por outro processo: não mexe
            p.terminate()
            alvos.append((p, rss))
        except (psutil.Error, OSError):
            continue
    if not alvos:
        return 0, 0.0
    _, vivos = psutil.wait_procs([p for p, _ in alvos], timeout=2.5)
    vivos_ids = {p.pid for p in vivos}
    for p in vivos:
        try:
            p.kill()
        except (psutil.Error, OSError):
            pass
    if vivos:
        _, ainda = psutil.wait_procs(vivos, timeout=1.5)
        vivos_ids = {p.pid for p in ainda}
    fechados = [(p, r) for p, r in alvos if p.pid not in vivos_ids]
    return len(fechados), round(sum(r for _, r in fechados) / 1048576, 1)


def contar_servicos():
    """(rodando, total) de serviços do Windows. (None, None) se não deu para ler."""
    if not IS_WIN:
        return None, None
    try:
        todos = list(psutil.win_service_iter())
        rod = 0
        for s in todos:
            try:
                if s.status() == "running":
                    rod += 1
            except (psutil.Error, OSError):
                continue
        return rod, len(todos)
    except Exception:
        return None, None


def mb_texto(mb):
    return f"{mb / 1024:.1f} GB".replace(".", ",") if mb >= 1024 else f"{mb:.0f} MB"


# ---------- serviços de programas instalados ----------

_SVC3_FORA = re.compile(
    r"(defender|antivir|security|malware|norton|mcafee|kaspersky|avast|avg\b|bitdefender|eset|sophos|webroot|trend ?micro|"
    r"nvidia|nvcontainer|\bamd\b|radeon|intel|realtek|rtk|synaptics|elan\b|logitech|lghub|razer|corsair|steelseries|asus|"
    r"armoury|\bmsi\b|gigabyte|aorus|\brgb|cooler|thermal|bluetooth|wacom|tobii|"
    r"vpn|openvpn|wireguard|nord|expressvpn|cisco|forti|vmware|virtualbox|vbox|hyper-?v|docker|wsl|sql|mysql|maria|postgres|"
    r"apache|nginx|node|tomcat|redis|mongo|anydesk|teamviewer|rustdesk|parsec|sunshine|moonlight|tailscale|zerotier|hamachi|"
    r"logmein|easyanticheat|battleye|vanguard|vgc|faceit|punkbuster|xigncode|nprotect|gameguard|"
    r"safenet|safesign|gemalto|watchdata|vaultpass|bit4id|certific|token|smart ?card|"
    r"onedrive|dropbox|google ?drive|backup|veeam|acronis|macrium|"
    r"printer|print|spool|scan|epson|canon|brother|hp ?smart|lexmark|ricoh|xerox|kyocera)", re.IGNORECASE)
_SVC3_EXE = re.compile(r'^\s*"?([^"]*?\.exe)', re.IGNORECASE)


def _exe_do_servico(binpath):
    m = _SVC3_EXE.match(binpath or "")
    return m.group(1).strip() if m else ""


def listar_servicos_terceiros(fonte=None, raiz=None):
    """Serviços de programas instalados que iniciam sozinhos com o Windows e podem virar 'manual' sem risco real."""
    raiz = _raiz_windows() if raiz is None else raiz
    if fonte is None:
        if not IS_WIN or REG is None:
            return []
        try:
            fonte = []
            for s in psutil.win_service_iter():
                try:
                    fonte.append(s.as_dict())
                except (psutil.Error, OSError):
                    continue
        except Exception:
            return []
    memoria = {}
    try:
        memoria = {p["pid"]: p["rss"] for p in _ler_processos()} if fonte else {}
    except Exception:
        pass
    itens = []
    for d in fonte:
        nome = d.get("name") or ""
        if not nome or d.get("start_type") != "automatic":
            continue
        exe = _exe_do_servico(d.get("binpath"))
        baixo = exe.lower()
        if not exe or (raiz and baixo.startswith(raiz + "\\")) or "\\microsoft\\" in baixo or "\\windowsapps\\" in baixo \
                or "\\windows defender" in baixo or "\\windows kits\\" in baixo:
            continue
        if _SVC3_FORA.search(nome) or _SVC3_FORA.search(d.get("display_name") or "") or _SVC3_FORA.search(baixo):
            continue
        pid = d.get("pid")
        itens.append({"nome": nome, "exibicao": (d.get("display_name") or nome)[:70], "estado": d.get("status") or "",
                      "mb": round(memoria.get(pid, 0) / 1048576, 1) if pid else 0.0,
                      "programa": os.path.basename(exe)})
    return sorted(itens, key=lambda i: (i["estado"] != "running", -i["mb"], i["exibicao"].lower()))[:40]


def _win_build():
    """Número da compilação do Windows (None fora do Windows). O Windows 10 1703 (15063) é o primeiro que separa serviços."""
    if not IS_WIN:
        return None
    try:
        return int(sys.getwindowsversion().build)
    except Exception:
        return None


def contar_estavel(max_voltas=7, espera=1.0, ler=None, minimo=1):
    """Conta os processos esperando o Windows terminar de fechar serviços (parar um serviço leva alguns segundos).
    Para quando o número se repete duas vezes seguidas (depois de pelo menos 'minimo' esperas). Devolve o último escaneamento."""
    ler = ler or escanear_processos
    d = ler()
    for i in range(max_voltas):
        time.sleep(espera)
        n = ler()
        if n["total"] == d["total"] and i + 1 >= minimo:
            return n
        d = n
    return d


class ProcessosMixin:
    """Lista de processos, 'Reduzir processos' (tarefa com passos) e serviços de terceiros."""

    @staticmethod
    def _proc_base():
        """Quantos processos havia na primeira vez que o Reduzir foi usado (guardado para comparar depois de reiniciar)."""
        b = CONFIG.get("proc_base")
        if not isinstance(b, dict) or not b.get("n"):
            return None
        reiniciou = bool(b.get("boot")) and psutil.boot_time() > float(b["boot"]) + 5
        return {"n": int(b["n"]), "quando": float(b.get("t") or 0), "reiniciou": reiniciou}

    def proc_iniciar_estado(self):
        self._proc_cache = {"t": 0.0, "dados": None}
        self._svc3_cache = {"t": 0.0, "itens": None}
        self._serv_cont = {"t": 0.0, "rod": None, "total": None}

    # ----- leitura (a tela lê com a página aberta) -----

    def proc_dados(self, forcar=False):
        c = self._proc_cache
        if forcar or c["dados"] is None or time.time() - c["t"] > 2.5:
            c["dados"] = escanear_processos()
            c["t"] = time.time()
        return c["dados"]

    def proc_lista(self):
        d = self.proc_dados()
        sc = self._serv_cont
        if time.time() - sc["t"] > 25:
            sc["rod"], sc["total"] = contar_servicos()
            sc["t"] = time.time()
        grupos = []
        for g in d["grupos"][:70]:
            grupos.append({k: g[k] for k in ("nome", "exe", "rotulo", "cat", "auto", "qtd", "mb", "fechavel")})
        feitos = [{"nome": n, "exibicao": v.get("exibicao", n)} for n, v in (_backup().get("_svc3") or {}).items()]
        return {"total": d["total"], "mb": d["mb_total"], "grupos": grupos, "por_cat": d["por_cat"],
                "svchost": d["svchost"], "svchost_junto": self._svchost_junto(), "ram_gb": round(psutil.virtual_memory().total / 1024 ** 3, 1),
                "dispensaveis": d["dispensaveis"], "opcionais": d["opcionais"], "servicos_rodando": sc["rod"], "servicos_total": sc["total"],
                "ids_ligados": [i for i in (CONFIG.get("proc_ids") or []) if isinstance(i, str)],
                "svc3_feitos": feitos, "cpu": self.cpu_estado(), "base": self._proc_base(), "win_build": _win_build()}

    @staticmethod
    def _svchost_junto():
        """True se o ajuste que junta os Host de Serviço já está ligado (None se não dá para saber)."""
        a = POR_ID.get("svc_juntar")
        try:
            return None if a is None or not a.disponivel() else a.estado() is True
        except OSError:
            return None

    def svc3_lista(self):
        c = self._svc3_cache
        if c["itens"] is None or time.time() - c["t"] > 20:
            c["itens"] = listar_servicos_terceiros()
            c["t"] = time.time()
        feitos = _backup().get("_svc3") or {}
        return {"itens": [i for i in c["itens"] if i["nome"] not in feitos],
                "feitos": [{"nome": n, "exibicao": v.get("exibicao", n)} for n, v in feitos.items()]}

    # ----- fechar um programa -----

    def t_proc_fechar(self, nome):
        g = escanear_processos()["mapa"].get(nome.lower())
        if not g or not g["fechavel"]:
            return "Esse programa não pode ser fechado por aqui (é do Windows, da proteção do PC ou do próprio Th Boost)."
        n, mb = fechar_pids(g["pids_fechaveis"])
        self._proc_cache["t"] = 0.0
        if not n:
            return f"{g['rotulo']}: não consegui fechar. Ele pode estar protegido ou já ter fechado."
        self.stats["procs"] = self.stats.get("procs", 0) + n
        self._estat_gravar()
        return f"{g['rotulo']} fechado: {n} processo(s), cerca de {mb_texto(mb)} de memória liberada."

    def proc_fechar(self, nome):
        if not isinstance(nome, str) or not nome or len(nome) > 120:
            raise ValueError("nome inválido")
        self.em_fundo(lambda: self.t_proc_fechar(nome))

    # ----- reduzir tudo de uma vez -----

    def proc_reduzir_iniciar(self, opcoes):
        if self._pesado_ocupado() or self.trab["processos"]["ativo"]:
            return self.msg("Espere a tarefa em andamento terminar.")
        opc = {"raros": False, "svchost": False, "launchers": False, "chats": False}
        opc.update({k: v for k, v in (opcoes or {}).items() if k in opc})
        # ordem pensada para o número cair de verdade: o ponto de restauração vem ANTES da contagem (ele abre processos do
        # Windows que ficam um tempo), primeiro se desliga o que reabre as coisas e só no fim se fecha o que está aberto
        passos = [("ponto", "Criando ponto de restauração", self._px_ponto, True),
                  ("antes", "Contando os processos", self._px_antes, False),
                  ("apps", "Parando apps em segundo plano", self._px_apps, False),
                  ("servicos", "Desligando serviços que pesam", self._px_servicos, True)]
        if opc["raros"]:
            passos.append(("raros", "Desligando serviços raros", self._px_raros, True))
        if opc["svchost"]:
            passos.append(("svchost", "Juntando os serviços do Windows", self._px_svchost, True))
        passos.append(("fechar", "Fechando ajudantes e atualizadores", self._px_fechar, False))
        tipos = tuple(t for k, ts in TIPOS_OPCIONAIS.items() if opc[k] for t in ts)
        if tipos:
            passos.append(("programas", "Fechando programas abertos sem uso", self._px_programas, False))
        passos.append(("depois", "Conferindo o resultado", self._px_depois, False))
        if self.trab_iniciar("processos", "reduzir", "Reduzir processos", passos,
                             {"opc": opc, "tipos": tipos, "ligados": [], "rot_fechados": set(), "poupados": []}):
            self.msg("Reduzindo os processos...")

    def _px_antes(self, ctx):
        # se o ponto de restauração acabou de rodar, espera os processos que ele abriu (PowerShell, VSS...) assentarem:
        # assim o "antes" e o "depois" são contados nas mesmas condições
        d = contar_estavel(max_voltas=8, espera=0.8, minimo=2) if ctx.get("ponto_rodou") else escanear_processos()
        ctx["antes"] = (d["total"], d["mb_total"])
        ctx["antes_nomes"] = {g["nome"]: (g["qtd"], g["rotulo"]) for g in d["grupos"]}
        ctx["resumo"] = {"antes_n": d["total"], "antes_mb": d["mb_total"]}
        if not CONFIG.get("proc_base"):  # a primeira contagem fica guardada: depois de reiniciar dá para ver o quanto caiu de vez
            CONFIG["proc_base"] = {"n": d["total"], "t": time.time(), "boot": psutil.boot_time()}
            salvar_config()
        return f"{d['total']} processos rodando, usando {mb_texto(d['mb_total'])}.", "ok"

    def _px_ponto(self, ctx):
        ctx["ponto_rodou"] = True
        ok = ponto_restauracao()
        return ("Ponto de restauração criado.", "ok") if ok else ("Já existia um ponto recente ou o Windows não criou. Segui mesmo assim.", "pulado")

    def _px_fechar(self, ctx):
        d = escanear_processos()
        n, mb, nomes = 0, 0.0, {}
        for g in d["grupos"]:
            if ctx["parar"]():
                break
            if g["auto"] and g["fechavel"]:
                q, m = fechar_pids(g["pids_fechaveis"])
                if q:
                    n, mb = n + q, mb + m
                    nomes[g["rotulo"]] = nomes.get(g["rotulo"], 0) + q
                    ctx["rot_fechados"].add(g["rotulo"])
        ctx["fechados"], ctx["mb_fechados"] = n, mb
        ctx["nomes_fechados"] = dict(nomes)
        if not n:
            return "Nenhum ajudante ou atualizador estava aberto.", "ok"
        return f"{n} processo(s) fechados ({mb_texto(mb)}): {', '.join(sorted(nomes)[:5])}.", "ok"

    def _jogo_rodando(self):
        """True se algum jogo da lista do Th Boost está aberto agora."""
        try:
            return bool(self._cpu_pids_jogos())
        except Exception:
            return False

    @staticmethod
    def _pid_da_frente():
        try:
            pid = pid_em_primeiro_plano()
        except Exception:
            return None
        return pid if pid and pid > 0 else None

    def _fechar_opcionais(self, ctx, d, so=None):
        """Fecha launchers, nuvem e/ou chats abertos (conforme as opções), poupando o que está em uso. 'so' limita a esses rótulos
        (usado na conferência final: só fecha de novo o que ele mesmo já tinha fechado). Devolve (n, mb, {rótulo: qtd})."""
        fechar, poupados = escolher_opcionais(d, ctx["tipos"], self._pid_da_frente(), self._jogo_rodando())
        if so is not None:
            fechar = [g for g in fechar if g["rotulo"] in so]
            poupados = [(r, m) for r, m in poupados if r in so]
        for rot, motivo in poupados:
            if not any(r == rot for r, _ in ctx["poupados"]):
                ctx["poupados"].append((rot, motivo))
        n, mb, nomes = 0, 0.0, {}
        for g in fechar:
            if ctx["parar"]():
                break
            q, m = fechar_pids(g["pids_fechaveis"])
            if q:
                n, mb = n + q, mb + m
                nomes[g["rotulo"]] = nomes.get(g["rotulo"], 0) + q
                ctx["rot_fechados"].add(g["rotulo"])
        return n, mb, nomes

    def _px_programas(self, ctx):
        n, mb, nomes = self._fechar_opcionais(ctx, escanear_processos())
        ctx["fechados"] = ctx.get("fechados", 0) + n
        ctx["mb_fechados"] = ctx.get("mb_fechados", 0.0) + mb
        for r, q in nomes.items():
            ctx.setdefault("nomes_fechados", {})[r] = ctx.get("nomes_fechados", {}).get(r, 0) + q
        txt = ""
        if ctx["poupados"]:
            txt = " Deixei abertos: " + "; ".join(f"{r} ({m})" for r, m in ctx["poupados"][:4]) + "."
        if not n:
            return "Nenhum launcher, nuvem ou chat estava aberto para fechar." + txt, "ok"
        lista = ", ".join(f"{r} ({q})" for r, q in sorted(nomes.items(), key=lambda x: -x[1])[:6])
        return f"{n} processo(s) fechados ({mb_texto(mb)}): {lista}." + txt, "ok"

    def _ligar_ajustes(self, ctx, ids):
        feitos, ja, falhas = [], 0, 0
        for i in ids:
            a = POR_ID.get(i)
            if a is None or not a.disponivel():
                continue
            if a.estado() is True:
                ja += 1
                if isinstance(a, AjusteServico) and e_admin():  # já estava desligado, mas pode seguir rodando até o PC reiniciar
                    ctx["parados"] = ctx.get("parados", 0) + a.parar_agora()
                continue
            if a.precisa_admin and not e_admin():
                falhas += 1
                continue
            try:
                a.ligar()
                feitos.append(a.id)
            except OSError:
                falhas += 1
        self.atualizar_aj()
        if feitos:
            guardados = [i for i in (CONFIG.get("proc_ids") or []) if isinstance(i, str)]
            CONFIG["proc_ids"] = guardados + [i for i in feitos if i not in guardados]
            salvar_config()
            ctx["ligados"].extend(feitos)
        return len(feitos), ja, falhas

    def _px_apps(self, ctx):
        n, ja, falhas = self._ligar_ajustes(ctx, ["fundo_apps", "widgets"])
        if n:
            return f"{n} ajuste(s) ligados: apps da Loja e Widgets não ficam mais rodando escondidos.", "ok"
        return ("Já estava assim.", "ok") if ja else ("Não consegui mudar agora.", "erro" if falhas else "pulado")

    def _px_servicos(self, ctx):
        ids = [a.id for a in CATALOGO if a.grupo == "servicos" and a.risco != "medio" and (a.rec or a.ext) and not a.sup]
        n, ja, falhas = self._ligar_ajustes(ctx, ids)
        if not n and not ja and falhas:
            return "Precisa de Administrador. Feche e abra o Th Boost pelo atalho.", "pulado"
        txt = f"{n} serviço(s) desligados agora" + (f", {ja} já estavam desligados" if ja else "") + "."
        if ctx.get("parados"):
            txt += f" Parei {ctx['parados']} que ainda estavam rodando."
        if falhas:
            txt += f" {falhas} não puderam ser alterados."
        return txt, "ok"

    def _px_raros(self, ctx):
        ids = [a.id for a in CATALOGO if a.grupo == "servicos" and a.risco != "medio" and a.sup]
        n, ja, falhas = self._ligar_ajustes(ctx, ids)
        if n:
            ctx["reiniciar"] = True
        return (f"{n} grupo(s) de serviços raros desligados. A parte por usuário só some depois de reiniciar." if n
                else ("Já estavam desligados." if ja else "Não consegui alterar.")), ("ok" if (n or ja) else "pulado")

    def _px_svchost(self, ctx):
        n, ja, falhas = self._ligar_ajustes(ctx, ["svc_juntar"])
        if n:
            ctx["reiniciar"] = ctx["juntou"] = True
            return "Pronto. Os serviços passam a dividir menos processos depois de reiniciar o PC.", "ok"
        return ("Já estava ligado.", "ok") if ja else ("Não consegui alterar.", "pulado")

    def _px_depois(self, ctx):
        # o que foi fechado pode ter reaberto sozinho: fecha de novo, uma vez só (e só o que ele mesmo fechou)
        voltaram = {}
        if ctx.get("rot_fechados"):
            time.sleep(1.5)
            d0 = escanear_processos()
            for g in d0["grupos"]:
                if g["auto"] and g["fechavel"] and g["rotulo"] in ctx["rot_fechados"]:
                    q, _ = fechar_pids(g["pids_fechaveis"])
                    if q:
                        voltaram[g["rotulo"]] = voltaram.get(g["rotulo"], 0) + q
            if ctx.get("tipos"):
                _, _, nomes = self._fechar_opcionais(ctx, d0, so=ctx["rot_fechados"])
                for r, q in nomes.items():
                    voltaram[r] = voltaram.get(r, 0) + q
        d = contar_estavel(max_voltas=10, espera=0.8, minimo=3)
        self._proc_cache["t"] = 0.0
        a_n, a_mb = ctx.get("antes", (d["total"], d["mb_total"]))
        res = ctx.setdefault("resumo", {})
        res.update(depois_n=d["total"], depois_mb=d["mb_total"], fechados=ctx.get("fechados", 0),
                   ligados=len(ctx.get("ligados", [])), reiniciar=bool(ctx.get("reiniciar")),
                   fechou=[f"{r} ({q})" for r, q in sorted((ctx.get("nomes_fechados") or {}).items(), key=lambda x: -x[1]) if q][:8],
                   poupados=[f"{r}: {m}" for r, m in ctx.get("poupados", [])][:6],
                   ponto=bool(ctx.get("ponto_rodou")))
        build = _win_build()
        if ctx.get("juntou") and (build is None or build >= 15063):  # estimativa: com os serviços juntos sobram uns 14 Host de Serviço
            res["depois_reiniciar"] = max(1, d["total"] - max(0, d["svchost"] - 14))
        # por que o número não caiu mais (dito com todas as letras, para ninguém achar que o botão não fez nada)
        motivos = []
        if not e_admin():
            motivos.append("O Th Boost está sem Administrador: não consegue desligar serviços do Windows nem juntar os Host de Serviço (svchost). "
                           "Feche e abra pelo atalho da área de trabalho.")
        elif ctx.get("juntou"):
            motivos.append("Juntar os Host de Serviço (svchost) só vale depois de REINICIAR o PC: é uma regra do Windows. "
                           "O número que você vê agora ainda é o de antes disso.")
        if build is not None and build < 15063 and d["svchost"]:
            motivos.append("Seu Windows é anterior ao Windows 10 versão 1703: ele já junta os serviços sozinho, então não há o que juntar.")
        if voltaram:
            motivos.append("Reabriram sozinhos e eu fechei de novo: " + ", ".join(f"{r} ({q})" for r, q in sorted(voltaram.items())[:5]) +
                           ". Para não abrirem mais, tire da página Inicialização.")
        # o que apareceu de novo depois da contagem do "antes" (é daí que vinha o "+3, +4")
        antes_nomes = ctx.get("antes_nomes") or {}
        novos = sorted(((g["rotulo"], g["qtd"] - antes_nomes.get(g["nome"], (0, ""))[0]) for g in d["grupos"]
                        if g["qtd"] > antes_nomes.get(g["nome"], (0, ""))[0]), key=lambda x: -x[1])
        if novos and d["total"] >= a_n:
            motivos.append("Abriram processos novos enquanto o Th Boost trabalhava (o Windows e os programas abrem alguns sozinhos): " +
                           ", ".join(f"{r} (+{q})" for r, q in novos[:4]) + ".")
        # programas do próprio usuário que o botão não fecha sozinho (podem ter algo não salvo)
        sobras = [g for g in d["grupos"] if g["fechavel"] and g["cat"] == "outro" and g["qtd"] >= 3]
        sobras.sort(key=lambda g: -g["qtd"])
        if sobras:
            motivos.append("Seus programas que ainda têm vários processos abertos: " + ", ".join(f"{g['rotulo']} ({g['qtd']})" for g in sobras[:4]) +
                           ". O botão não fecha esses sozinho porque pode haver algo seu sem salvar; fechando aqui na lista, o número cai.")
        if d["total"] >= a_n and not ctx.get("fechados") and not ctx.get("ligados") and not ctx.get("parados"):
            motivos.append("Não havia ajudantes dispensáveis abertos nem serviços de baixo risco ligados: o que sobra é do Windows e dos seus programas.")
        res["motivos"] = motivos
        self.stats["procs"] = self.stats.get("procs", 0) + ctx.get("fechados", 0)
        self._estat_gravar()
        if d["total"] < a_n:
            return f"De {a_n} para {d['total']} processos (−{a_n - d['total']}) e de {mb_texto(a_mb)} para {mb_texto(d['mb_total'])} de memória.", "ok"
        if d["total"] > a_n:
            return f"Subiu de {a_n} para {d['total']}: abriram processos novos durante a tarefa (veja abaixo). O que o botão fechou não voltou.", "ok"
        return (f"{d['total']} processos. O número só cai de vez depois de reiniciar o PC." if ctx.get("reiniciar")
                else f"{d['total']} processos: não havia mais nada seguro para fechar."), "ok"

    # ----- desfazer -----

    def t_proc_desfazer(self):
        ids = [i for i in (CONFIG.get("proc_ids") or []) if isinstance(i, str) and i in POR_ID]
        if not ids:
            return "Não há nada do Reduzir processos para desfazer."
        if REG is None:
            return "Só funciona no Windows."
        if not e_admin() and any(POR_ID[i].precisa_admin for i in ids):
            return "Desfazer precisa de Administrador. Abra o Th Boost pelo atalho."
        feitos = 0
        for i in ids:
            a = POR_ID[i]
            try:
                if a.estado() is True:
                    a.desligar()
                    feitos += 1
            except OSError:
                pass
        CONFIG["proc_ids"] = []
        CONFIG.pop("proc_base", None)
        salvar_config()
        self.atualizar_aj()
        self._proc_cache["t"] = 0.0
        return f"{feitos} ajuste(s) devolvidos ao padrão do Windows. Serviços voltam a iniciar com o Windows."

    # ----- serviços de programas instalados -----

    def t_svc3_definir(self, nome, manual):
        if REG is None:
            return "Só funciona no Windows."
        if not e_admin():
            return "Isso precisa de Administrador. Abra o Th Boost pelo atalho."
        chave = SVC_CHAVE % nome
        if manual:
            alvo = next((i for i in self.svc3_lista()["itens"] if i["nome"] == nome), None)
            if alvo is None:
                return "Esse serviço não está mais na lista."
            with TRAVA_AJ:
                _backup().setdefault("_svc3", {})[nome] = {
                    "inicio": REG.ler("HKLM", chave, "Start"), "atrasado": REG.ler("HKLM", chave, "DelayedAutostart"),
                    "exibicao": alvo["exibicao"]}
                _guardar_backup()
            executar(["sc", "config", nome, "start=", "demand"])
            executar(["sc", "stop", nome])
            self._svc3_cache["t"] = 0.0
            self._proc_cache["t"] = 0.0
            return f"{alvo['exibicao']}: agora só inicia quando algum programa pedir. Dá para desfazer aqui."
        with TRAVA_AJ:
            antigo = (_backup().get("_svc3") or {}).get(nome)
        if not antigo:
            return "Não tenho o registro desse serviço para desfazer."
        ini = antigo.get("inicio")
        modo = "delayed-auto" if (ini == 2 and antigo.get("atrasado") == 1) else \
               ("auto" if ini in (2, None) else ("disabled" if ini == 4 else "demand"))
        executar(["sc", "config", nome, "start=", modo])
        if modo in ("auto", "delayed-auto"):
            executar(["sc", "start", nome])
        with TRAVA_AJ:
            bk = _backup()
            (bk.get("_svc3") or {}).pop(nome, None)
            if not bk.get("_svc3"):
                bk.pop("_svc3", None)
            _guardar_backup()
        self._svc3_cache["t"] = 0.0
        return f"{antigo.get('exibicao', nome)}: voltou a iniciar com o Windows."

    def svc3_definir(self, nome, manual):
        if not isinstance(nome, str) or not nome or len(nome) > 100 or not isinstance(manual, bool):
            raise ValueError("pedido inválido")
        self.em_fundo(lambda: self.t_svc3_definir(nome, manual))

