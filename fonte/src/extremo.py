# ---------------- limpeza profunda e Otimização Extrema ----------------
#
# Regras que valem para tudo daqui:
#  - só se apaga o CONTEÚDO de pastas de cache e de lixo conhecidas (nunca a pasta em si, nunca documentos);
#  - atalhos e junções do Windows nunca são seguidos (assim nada fora da pasta é tocado);
#  - cookies, senhas, históricos e downloads dos navegadores não são mexidos: só o cache;
#  - cada ajuste guarda o valor original (ajustes_backup.json) e o que a Otimização Extrema fez fica em
#    extremo_estado.json, para o botão "Desfazer tudo".

ARQ_EXTREMO = os.path.join(pasta_do_programa(), "extremo_estado.json")
NOME_PLANO_EXT = "Th Boost Extremo"
NOME_PLANO_SUP = "Th Boost Suprema"
TRAVA_EXT = threading.RLock()
_EXT_MEM = {}


def tam_texto(b):
    mb = b / 1048576
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB".replace(".", ",")
    if mb >= 1:
        return f"{mb:.0f} MB"
    return f"{b / 1024:.0f} KB" if b >= 1024 else "0 MB"


# ---------- caminhos e apagador seguro ----------

_VARS_PROIBIDAS = ("USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "SYSTEMROOT", "WINDIR", "PROGRAMFILES",
                   "PROGRAMFILES(X86)", "SYSTEMDRIVE", "HOMEDRIVE", "PUBLIC", "ALLUSERSPROFILE", "HOME")
_NOMES_PROIBIDOS = {"users", "windows", "program files", "program files (x86)", "programdata", "system32", "usr", "etc",
                    "bin", "home", "var", "root"}


def _env(nome):
    v = os.environ.get(nome, "").strip()
    return v if v and os.path.isabs(v) else ""


def _junta(base, *partes):
    return os.path.join(base, *partes) if base else ""


def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def _caminho_seguro(p):
    """Recusa raízes de unidade e pastas inteiras do sistema ou do usuário: só pastas específicas."""
    if not p or not os.path.isabs(p):
        return False
    n = _norm(p)
    partes = [x for x in re.split(r"[\\/]+", n) if x]
    if len(partes) < 2 or (len(partes) == 2 and partes[1] in _NOMES_PROIBIDOS):
        return False
    for v in _VARS_PROIBIDAS:
        x = os.environ.get(v)
        if x and _norm(x) == n:
            return False
    return True


def _atributo_ligacao(st):
    """Junção ou atalho simbólico do Windows (FILE_ATTRIBUTE_REPARSE_POINT)."""
    return bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _e_ligacao(caminho):
    try:
        return os.path.islink(caminho) or _atributo_ligacao(os.lstat(caminho))
    except OSError:
        return True  # na dúvida, não mexe


def _remover_arquivo(caminho):
    try:
        os.remove(caminho)
        return True
    except PermissionError:
        try:
            os.chmod(caminho, 0o666)  # arquivo marcado como somente leitura
            os.remove(caminho)
            return True
        except OSError:
            return False
    except OSError:
        return False


def _percorrer(pasta, apagar, ext=None, dias=None, idade_min=0, parar=None, _nivel=0):
    """Soma (e, se pedido, apaga) os arquivos de uma pasta. Pula o que está em uso. Devolve bytes."""
    total = 0
    if _nivel > 40:
        return 0
    try:
        entradas = list(os.scandir(pasta))
    except OSError:
        return 0
    agora = time.time()
    for e in entradas:
        if parar and parar():
            break
        try:
            st = e.stat(follow_symlinks=False)
            if e.is_symlink() or _atributo_ligacao(st):
                continue  # nunca segue atalhos nem junções
            if e.is_dir(follow_symlinks=False):
                total += _percorrer(e.path, apagar, ext, dias, idade_min, parar, _nivel + 1)
                # pasta vazia só some se for antiga: um programa pode ter acabado de criá-la para usar daqui a pouco
                if apagar and agora - st.st_mtime >= max(idade_min, (dias or 0) * 86400):
                    try:
                        os.rmdir(e.path)
                    except OSError:
                        pass
                continue
            if ext and not e.name.lower().endswith(ext):
                continue
            idade = agora - st.st_mtime
            if (dias and idade < dias * 86400) or (idade_min and idade < idade_min):
                continue
            if apagar:
                if _remover_arquivo(e.path):
                    total += st.st_size
            else:
                total += st.st_size
        except OSError:
            continue
    return total


def _casa(parte, nome):
    if parte == "*":
        return True
    if parte.endswith("*"):
        return nome.lower().startswith(parte[:-1].lower())
    return nome.lower() == parte.lower()


def _resolver(spec):
    """spec = (pasta_base, parte, parte...). Uma parte pode ser '*' ou 'prefixo*'. Devolve pastas reais e seguras."""
    base, partes = spec[0], spec[1:]
    if not base or not os.path.isabs(base):
        return []
    atuais = [base]
    for parte in partes:
        novos = []
        for b in atuais:
            if "*" in parte:
                try:
                    with os.scandir(b) as it:
                        for e in it:
                            if e.is_dir(follow_symlinks=False) and _casa(parte, e.name):
                                novos.append(e.path)
                except OSError:
                    pass
            else:
                novos.append(os.path.join(b, parte))
        atuais = novos
    achadas = []
    for p in atuais:
        try:
            if os.path.isdir(p) and not _e_ligacao(p) and _caminho_seguro(p):
                achadas.append(p)
        except OSError:
            pass
    return achadas


# ---------- o que pode ser limpo ----------

def _cat(id, nome, grupo, pastas, admin=False, arquivos=(), **filtros):
    return {"id": id, "nome": nome, "grupo": grupo, "pastas": [p for p in pastas if p and p[0]],
            "admin": admin, "arquivos": [a for a in arquivos if a], **filtros}


def _pastas_cache(base, *nomes):
    return [(base,) + tuple(n) for n in nomes] if base else []


def categorias():
    """Lista de categorias de limpeza. Tudo aqui é cache ou lixo que o próprio programa recria sozinho."""
    L, A, D = _env("LOCALAPPDATA"), _env("APPDATA"), _env("PROGRAMDATA")
    R = _env("SYSTEMROOT") or _env("WINDIR")
    U = tempfile.gettempdir()
    j = _junta
    c = []
    # --- arquivos temporários ---
    c.append(_cat("temp_usuario", "Temporários do usuário", "temp", [(U,), (j(L, "Temp"),)], idade_min=600))
    c.append(_cat("temp_windows", "Temporários do Windows", "temp", [(j(R, "Temp"),)], admin=True, idade_min=600))
    c.append(_cat("inet_cache", "Cache de internet do Windows", "temp",
                  [(j(L, "Microsoft", "Windows", "INetCache"),)]))
    c.append(_cat("pacotes_temp", "Temporários de apps da Loja", "temp", [(j(L, "Packages"), "*", "TempState")]))
    # --- navegadores: só o cache (cookies, senhas e histórico não são tocados) ---
    cr = ("Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache")
    for ident, nome, base in (
            ("chrome", "Google Chrome", j(L, "Google", "Chrome", "User Data")),
            ("edge", "Microsoft Edge", j(L, "Microsoft", "Edge", "User Data")),
            ("brave", "Brave", j(L, "BraveSoftware", "Brave-Browser", "User Data")),
            ("vivaldi", "Vivaldi", j(L, "Vivaldi", "User Data"))):
        pastas = _pastas_cache(base, *[("*", n) for n in cr], ("GrShaderCache",), ("ShaderCache",))
        c.append(_cat(ident, nome, "nav", pastas))
    for ident, nome, pasta in (("opera", "Opera", "Opera Stable"), ("opera_gx", "Opera GX", "Opera GX Stable")):
        pastas = []
        for raiz in (A, L):
            pastas += _pastas_cache(j(raiz, "Opera Software", pasta), ("Cache",), ("Code Cache",), ("GPUCache",))
        c.append(_cat(ident, nome, "nav", pastas))
    c.append(_cat("firefox", "Mozilla Firefox", "nav",
                  _pastas_cache(j(L, "Mozilla", "Firefox", "Profiles"), ("*", "cache2"), ("*", "startupCache"))))
    # --- caches de programas ---
    el = ("Cache", "Code Cache", "GPUCache")
    pastas = []
    for nome in ("discord", "discordptb", "discordcanary"):
        pastas += _pastas_cache(j(A, nome), *[(n,) for n in el])
    c.append(_cat("discord", "Discord", "apps", pastas))
    c.append(_cat("teams", "Microsoft Teams", "apps",
                  _pastas_cache(j(A, "Microsoft", "Teams"), *[(n,) for n in el + ("tmp", "blob_storage")])))
    c.append(_cat("slack", "Slack", "apps", _pastas_cache(j(A, "Slack"), *[(n,) for n in el])))
    c.append(_cat("whatsapp", "WhatsApp Desktop", "apps", _pastas_cache(j(A, "WhatsApp"), *[(n,) for n in el])))
    c.append(_cat("vscode", "Visual Studio Code", "apps",
                  _pastas_cache(j(A, "Code"), *[(n,) for n in el + ("CachedData", "logs")])))
    c.append(_cat("steam_web", "Steam (navegador interno)", "apps", [(j(L, "Steam", "htmlcache"),)]))
    c.append(_cat("epic", "Epic Games Launcher", "apps",
                  _pastas_cache(j(L, "EpicGamesLauncher", "Saved"), ("webcache*",), ("Logs",))))
    c.append(_cat("nvidia_instalador", "Restos do instalador da NVIDIA", "apps",
                  [(j(D, "NVIDIA Corporation", "Downloader"),)], admin=True))
    # --- Windows ---
    c.append(_cat("wu_download", "Atualizações já baixadas do Windows", "win",
                  [(j(R, "SoftwareDistribution", "Download"),)], admin=True, pular_se="reinicio"))
    c.append(_cat("entrega_otimizada", "Cache da Entrega Otimizada", "win",
                  [(j(R, "ServiceProfiles", "NetworkService", "AppData", "Local", "Microsoft", "Windows",
                      "DeliveryOptimization", "Cache"),)], admin=True))
    c.append(_cat("relatorios_usuario", "Relatórios de erros (usuário)", "win",
                  [(j(L, "Microsoft", "Windows", "WER"),), (j(L, "CrashDumps"),)]))
    c.append(_cat("relatorios_sistema", "Relatórios de erros do Windows", "win",
                  [(j(D, "Microsoft", "Windows", "WER", "ReportArchive"),),
                   (j(D, "Microsoft", "Windows", "WER", "ReportQueue"),),
                   (j(D, "Microsoft", "Windows", "WER", "Temp"),)], admin=True))
    c.append(_cat("dumps_sistema", "Despejos de memória de falhas", "win",
                  [(j(R, "Minidump"),), (j(R, "LiveKernelReports"),)], admin=True, arquivos=[j(R, "MEMORY.DMP")]))
    c.append(_cat("logs_cbs", "Registros antigos de instalação", "win", [(j(R, "Logs", "CBS"),)],
                  admin=True, ext=(".log", ".cab"), dias=7))
    # --- só na Otimização Suprema (sup=True) ---
    SD = (os.environ.get("SystemDrive") or "C:") + os.sep
    c.append(_cat("logs_windows_antigos", "Registros do Windows com mais de 30 dias", "win",
                  [(j(R, "Logs", "WindowsUpdate"),), (j(R, "Logs", "DISM"),), (j(R, "Panther"),)],
                  admin=True, ext=(".log", ".etl"), dias=30, sup=True))
    c.append(_cat("instaladores_driver", "Pacotes de driver já instalados (NVIDIA e AMD)", "apps",
                  [(j(SD, "NVIDIA", "DisplayDriver"),), (j(SD, "AMD"),)], admin=True, sup=True))
    c.append(_cat("cache_loja", "Cache da Microsoft Store", "apps",
                  [(j(L, "Packages", "Microsoft.WindowsStore_8wekyb3d8bbwe", "LocalCache"),)], sup=True))
    c.append(_cat("cache_adobe", "Cache de mídia da Adobe", "apps",
                  [(j(A, "Adobe", "Common", "Media Cache Files"),), (j(A, "Adobe", "Common", "Media Cache"),)], sup=True))
    c.append(_cat("logs_onedrive", "Registros do OneDrive", "apps", [(j(L, "Microsoft", "OneDrive", "logs"),)], sup=True))
    return c


ROTULOS_GRUPO = {"temp": "Temporários", "nav": "Navegadores", "apps": "Caches de programas", "win": "Limpeza do Windows"}
NOMES_PASSO_LIMPEZA = {"temp": "Limpeza: arquivos temporários", "nav": "Limpeza: navegadores",
                       "apps": "Limpeza: caches de programas", "win": "Limpeza: lixo do Windows"}


def reinicio_pendente():
    if REG is None:
        return False
    return any(REG.existe("HKLM", c) for c in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"))


def limpar_grupo(grupo, apenas_medir=False, parar=None, sup=False):
    """Limpa (ou só mede) um grupo de categorias. Devolve {'bytes', 'itens', 'pulados'}.
    sup=True inclui as categorias extras da Otimização Suprema."""
    itens, pulados, total = [], [], 0
    vistos = set()
    adm = e_admin()
    for cat in categorias():
        if cat["grupo"] != grupo or (cat.get("sup") and not sup):
            continue
        if parar and parar():
            break
        if cat["admin"] and not adm:
            pulados.append({"nome": cat["nome"], "motivo": "admin"})
            continue
        if cat.get("pular_se") == "reinicio" and reinicio_pendente():
            pulados.append({"nome": cat["nome"], "motivo": "reinicio"})
            continue
        b = 0
        for spec in cat["pastas"]:
            for pasta in _resolver(spec):
                if _norm(pasta) in vistos:
                    continue
                vistos.add(_norm(pasta))
                b += _percorrer(pasta, not apenas_medir, cat.get("ext"), cat.get("dias"),
                                cat.get("idade_min", 0), parar)
        for arq in cat["arquivos"]:
            try:
                if os.path.isfile(arq) and not _e_ligacao(arq) and _caminho_seguro(arq):
                    tam = os.path.getsize(arq)
                    if apenas_medir or _remover_arquivo(arq):
                        b += tam
            except OSError:
                pass
        total += b
        if b:
            itens.append({"id": cat["id"], "nome": cat["nome"], "bytes": b})
    return {"bytes": total, "itens": itens, "pulados": pulados}


# ---------- programas e processos que pesam ----------

PROCESSOS_DISPENSAVEIS = {
    "compattelrunner.exe": "análise de telemetria", "gamebarpresencewriter.exe": "Game Bar",
    "yourphone.exe": "Vincular ao Celular", "phoneexperiencehost.exe": "Vincular ao Celular",
    "widgets.exe": "Widgets", "widgetservice.exe": "Widgets", "hxtsr.exe": "Email e Calendário",
    "cortana.exe": "Cortana", "skypebackgroundhost.exe": "Skype", "skypeapp.exe": "Skype",
}


def fechar_dispensaveis():
    """Fecha processos de segundo plano que o Windows abre sozinho e quase ninguém usa. Devolve os nomes."""
    alvos, nomes = [], set()
    for p in psutil.process_iter(["name"]):
        nome = (p.info.get("name") or "").lower()
        if nome in PROCESSOS_DISPENSAVEIS:
            try:
                p.terminate()
                alvos.append(p)
                nomes.add(PROCESSOS_DISPENSAVEIS[nome])
            except (psutil.Error, OSError):
                pass
    if alvos:
        _, vivos = psutil.wait_procs(alvos, timeout=2)
        for p in vivos:
            try:
                p.kill()
            except (psutil.Error, OSError):
                pass
    return sorted(nomes)


# Programas que abrem sozinhos com o Windows mas não fazem falta: launchers, atualizadores e chats.
# Antivírus, drivers de áudio/vídeo/touchpad e o OneDrive ficam de fora de propósito.
INICIO_DISPENSAVEL = re.compile(
    r"^(spotify|discord|steam|epicgameslauncher|epic games launcher|battle\.net|battlenet|origin|eadm|ea desktop|"
    r"eabackgroundservice|ubisoft connect|uplay|skype|teams|microsoftteams|com\.squirrel\.teams[\w.]*|zoom|zoomit|"
    r"adobegcinvoker[\w-]*|adobe creative cloud|ccxprocess|adobeaamupdater[\w-]*|acrobat[\w ]*|itunes ?helper|"
    r"ipodservice|googlechromeautolaunch[\w-]*|microsoftedgeautolaunch[\w-]*|ccleaner[\w ]*|utorrent|bittorrent|"
    r"qbittorrent|sunjavaupdatesched|cortana|yourphone)\b", re.IGNORECASE)


# Só na Suprema: atualizadores e programas de fabricante que não fazem falta ao jogar (continuam instalados)
INICIO_SUPREMO = re.compile(
    r"^(googleupdate[\w .-]*|microsoftedgeupdate[\w .-]*|jusched|java update scheduler|cyberlink[\w .-]*|"
    r"hp ?support[\w .-]*|supportassist[\w .-]*|dell ?update[\w .-]*|lenovo ?(vantage|welcome)[\w .-]*|"
    r"msiafterburner ?updater|nvidia geforce experience|geforce experience)\b", re.IGNORECASE)


def itens_inicio_dispensaveis(sup=False):
    return [i for i in listar_inicio() if i["ligado"] and (INICIO_DISPENSAVEL.match(i["nome"])
                                                           or (sup and INICIO_SUPREMO.match(i["nome"])))]


# ---------- disco, plano de energia e comandos longos ----------

def disco_e_ssd():
    """True (SSD), False (HD) ou None (não deu para saber) para a unidade do Windows."""
    letra = (os.environ.get("SystemDrive") or "C:")[:1]
    if not letra.isalpha():
        return None
    cod, saida = powershell("$d=(Get-Partition -DriveLetter %s).DiskNumber; (Get-PhysicalDisk | Where-Object "
                            "{ [int]$_.DeviceId -eq $d }).MediaType" % letra.upper(), tempo=40)
    if cod != 0:
        return None
    s = saida.strip().upper()
    return True if "SSD" in s else (False if "HDD" in s else None)


def tem_bateria():
    try:
        return psutil.sensors_battery() is not None
    except (AttributeError, OSError):
        return False


def _executar_longo(cmd, limite, parar=None):
    """Roda um comando demorado e deixa interromper (botão Parar/Pular). Devolve (código, saída); código -1 = interrompido."""
    flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                             creationflags=flags)
    except OSError as erro:
        return 1, str(erro)
    inicio = time.time()
    while True:
        try:
            saida, _ = p.communicate(timeout=0.5)
            return p.returncode, (saida or "").strip()
        except subprocess.TimeoutExpired:
            if (parar and parar()) or time.time() - inicio > limite:
                p.kill()
                try:
                    p.communicate(timeout=5)
                except (subprocess.SubprocessError, OSError):
                    pass
                return -1, "interrompido"


# valores do plano de energia: (grupo, configuração, valor) aplicados só na tomada (na bateria nada muda)
AJUSTES_PLANO_EXT = [
    ("54533251-82be-4824-96c1-47b60b740d00", "893dee8e-2bef-41e0-89c6-b55d0929964c", 100),  # processador: mínimo 100%
    ("54533251-82be-4824-96c1-47b60b740d00", "bc5038f7-23e0-4960-96da-33abaf5935ec", 100),  # processador: máximo 100%
    ("54533251-82be-4824-96c1-47b60b740d00", "0cc5b647-c1df-4637-891a-dec35c318583", 100),  # núcleos sempre acordados
    ("54533251-82be-4824-96c1-47b60b740d00", "be337238-0d82-4146-a960-4f3749d470c7", 2),    # turbo agressivo
    ("54533251-82be-4824-96c1-47b60b740d00", "94d3a615-a899-4ac5-ae2b-e4d8f634367f", 1),    # ventoinha ativa
    ("501a4d13-42af-4429-9fd1-a8218c268e20", "ee12f906-d277-404b-b6da-e5fa1a576df5", 0),    # PCIe sem economia
    ("2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", 0),    # USB sem suspensão
    ("0012ee47-9041-4b5d-9b77-535fba8b1442", "6738e2c4-e8a5-4a42-b16a-e040e769756e", 0),    # disco nunca desliga
    ("19cbb8fa-5279-450e-9fac-8a3d5fedd0c1", "12bbebe6-58d6-4636-95bb-3217ef867c1a", 0),    # Wi-Fi sem economia
]


# a mais, só na Suprema (o Windows ignora o que o computador não tem)
AJUSTES_PLANO_SUP = [
    ("54533251-82be-4824-96c1-47b60b740d00", "45bcc044-d885-43e2-8605-ee0ec6e96b59", 100),  # turbo: política de 100%
    ("54533251-82be-4824-96c1-47b60b740d00", "36687f9e-e3a5-4dbf-b1dc-15eb381c6863", 0),    # preferência: desempenho
    ("54533251-82be-4824-96c1-47b60b740d00", "943c8cb6-6f93-4227-ad87-e9a3ccbf8bc2", 100),  # núcleos: limite máximo 100%
    ("e276e160-7cb0-43c6-b20b-73f5dce39954", "a1662ab2-9d34-4e53-ba8b-2639b9e20857", 3),    # placa de vídeo no máximo
    ("2a737441-1930-4402-8d77-b2bebba308a3", "d4e98f31-5ffe-4ce1-be31-1b38b384c009", 0),    # USB: hub sem suspensão
    ("238c9fa8-0aad-41ed-83f4-97be242c8f20", "29f6c1db-86da-48c5-9fdb-f2b67b1f44da", 0),    # nunca suspender sozinho
]


def criar_plano_extremo(sup=False):
    """Cria (ou reaproveita) o plano 'Th Boost Extremo' (ou 'Suprema') e ativa. Devolve (ok, texto, guid, guid_anterior)."""
    planos = listar_planos()
    ativo = next((p["guid"] for p in planos if p["ativo"]), None)
    nome_novo = NOME_PLANO_SUP if sup else NOME_PLANO_EXT
    nomes_nossos = (NOME_PLANO_SUP.lower(), NOME_PLANO_EXT.lower())
    existente = next((p for p in planos if p["nome"].strip().lower() == nome_novo.lower()), None) \
        or next((p for p in planos if p["nome"].strip().lower() in nomes_nossos), None)
    if existente:
        guid = existente["guid"]
        if existente["nome"].strip().lower() != nome_novo.lower():
            executar(["powercfg", "-changename", guid, nome_novo, "Criado pelo Th Boost"])
    else:
        guid = None
        for origem in (PLANOS_CONHECIDOS["maximo"][0], PLANOS_CONHECIDOS["alto"][0], PLANOS_CONHECIDOS["equilibrado"][0]):
            cod, saida = executar(["powercfg", "-duplicatescheme", origem])
            m = re.search(_GUID, saida or "")
            if cod == 0 and m:
                guid = m.group(0).lower()
                break
        if not guid:
            return False, "Não foi possível criar o plano de energia (o Windows recusou).", None, ativo
        executar(["powercfg", "-changename", guid, nome_novo, "Criado pelo Th Boost (Otimização " + ("Suprema" if sup else "Extrema") + ")"])
    for sub, cfg, valor in AJUSTES_PLANO_EXT + (AJUSTES_PLANO_SUP if sup else []):  # o que o Windows não conhece é ignorado
        executar(["powercfg", "/setacvalueindex", guid, sub, cfg, str(valor)])
    cod, _ = executar(["powercfg", "/setactive", guid])
    if cod != 0:
        return False, "Plano criado, mas o Windows não deixou ativar.", guid, ativo
    return True, f"Plano “{nome_novo}” ativado (processador sempre pronto, sem economia de energia na tomada).", \
        guid, (None if ativo == guid else ativo)


def restaurar_plano(guid_extremo, guid_anterior):
    planos = {p["guid"] for p in listar_planos()}
    alvo = guid_anterior if guid_anterior in planos else PLANOS_CONHECIDOS["equilibrado"][0]
    cod, _ = executar(["powercfg", "/setactive", alvo])
    if guid_extremo and guid_extremo in planos and guid_extremo != alvo:
        executar(["powercfg", "/delete", guid_extremo])
    return cod == 0


def pasta_windows_old():
    p = os.path.join(disco_sistema(), "Windows.old")
    return p if os.path.isdir(p) and not _e_ligacao(p) else None


# ---------- o que a Otimização Extrema fez (para o Desfazer) ----------

def _ext_tem_algo(d):
    return bool(d and (d.get("ajustes") or d.get("inicio") or d.get("plano") or d.get("gpu")))


def _ext_ler():
    with TRAVA_EXT:
        if _EXT_MEM:
            return dict(_EXT_MEM)
        try:
            with open(ARQ_EXTREMO, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}


def _ext_gravar(d):
    with TRAVA_EXT:
        _EXT_MEM.clear()
        _EXT_MEM.update(d)
        try:
            if d:
                with open(ARQ_EXTREMO, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=1)
            elif os.path.exists(ARQ_EXTREMO):
                os.remove(ARQ_EXTREMO)
        except OSError:
            pass  # sem permissão de escrita: o registro fica só na memória desta execução


class ExtremoMixin:
    """Parte do Nucleo responsável pela Otimização Extrema. Os passos rodam em uma thread e a tela acompanha pelo estado."""

    def ext_iniciar_estado(self):
        prev = _ext_ler()
        self.ext = {"ativo": False, "parando": False, "fracao": 0.0, "passo": "", "passos": [], "mb": 0.0,
                    "opcoes": {"dism": True, "apps": False, "busca": False, "winold": False, "nivel": "extrema"},
                    "antes": None, "depois": None, "resumo": None,
                    "fim": 0, "desfazer": _ext_tem_algo(prev),
                    "analise": {"estado": "nenhuma", "total_mb": 0.0, "itens": [], "winold_gb": 0.0, "nivel": "extrema"}}
        self.ext_pular = False
        self.reinicio_ate = 0.0

    def ext_snapshot(self):
        e = self.ext
        d = dict(e)
        d["passos"] = [dict(p) for p in e["passos"]]
        d["opcoes"] = dict(e["opcoes"])
        d["analise"] = dict(e["analise"])
        d["analise"]["itens"] = list(e["analise"]["itens"])
        d["reinicio"] = max(0, int(self.reinicio_ate - time.time())) if self.reinicio_ate else 0
        return d

    # ----- análise (só mede, não apaga nada) -----

    def ext_analisar(self, nivel="extrema"):
        a = self.ext["analise"]
        if a["estado"] == "rodando" or self.ext["ativo"]:
            return
        sup = nivel == "suprema"

        def tarefa():
            a["estado"] = "rodando"
            itens, total = [], 0
            try:
                for g in ("temp", "nav", "apps", "win"):
                    r = limpar_grupo(g, apenas_medir=True, parar=lambda: self.fechando, sup=sup)
                    total += r["bytes"]
                    itens += [{"nome": i["nome"], "mb": round(i["bytes"] / 1048576, 1), "grupo": g} for i in r["itens"]]
                itens.sort(key=lambda i: -i["mb"])
                wo = pasta_windows_old()
                gb = 0.0
                if wo:  # a pasta que sobra de uma atualização do Windows: mede com limite de tempo
                    fim = time.time() + 25
                    gb = round(_percorrer(wo, False, parar=lambda: self.fechando or time.time() > fim) / 1024 ** 3, 1)
                a.update({"itens": itens[:8], "total_mb": round(total / 1048576, 1), "estado": "pronto",
                          "winold_gb": gb, "nivel": nivel})
            except Exception:
                a["estado"] = "erro"

        a["estado"] = "rodando"
        threading.Thread(target=tarefa, daemon=True).start()

    # ----- medidas de antes e depois -----

    def _medidas(self):
        mem = psutil.virtual_memory()
        try:
            livre = psutil.disk_usage(disco_sistema()).free / 1024 ** 3
        except OSError:
            livre = None
        try:
            inicio = len([i for i in listar_inicio() if i["ligado"]])
        except Exception:
            inicio = None
        try:
            processos = len(psutil.pids())
        except Exception:
            processos = None
        try:
            servicos = sum(1 for sv in psutil.win_service_iter() if sv.status() == "running") if IS_WIN else None
        except Exception:
            servicos = None
        return {"ram_livre": round(mem.available / 1024 ** 3, 2), "ram_pct": round(mem.percent, 1),
                "disco_livre": None if livre is None else round(livre, 2), "inicio": inicio,
                "processos": processos, "servicos": servicos}

    # ----- plano dos passos -----

    def _ext_plano(self, opcoes):
        sup = opcoes.get("nivel") == "suprema"
        P = []
        P.append(("restauracao", "Ponto de restauração", self._x_restauracao, True))
        P.append(("processos", "Fechando o que pesa em segundo plano", self._x_processos, False))
        for g in ("temp", "nav", "apps", "win"):
            P.append(("l_" + g, NOMES_PASSO_LIMPEZA[g], (lambda ctx, g=g: self._x_limpar(ctx, g)), False))
        P.append(("lixeira", "Esvaziando a lixeira", self._x_lixeira, False))
        if opcoes.get("winold"):
            P.append(("winold", "Removendo o Windows.old", self._x_winold, True))
        if opcoes.get("dism"):
            P.append(("dism", "Componentes antigos do Windows", self._x_dism, True))
        for g, nome in (("windows", "Ajustes do Windows"), ("mouse", "Mouse e teclado"),
                        ("servicos", "Serviços desnecessários"), ("privacidade", "Privacidade e telemetria"),
                        ("rede", "Rede e latência"), ("jogos", "Ajustes de FPS para jogos")):
            P.append(("aj_" + g, nome, (lambda ctx, g=g: self._x_ajustes(ctx, g)), False))
        P.append(("inicio", "Programas que abrem com o Windows", self._x_inicio, False))
        if sup:
            P.append(("gpu", "Seus jogos usam a placa de vídeo forte", self._x_gpu_jogos, False))
        P.append(("energia", "Plano de energia Suprema" if sup else "Plano de energia Extremo", self._x_energia, True))
        P.append(("disco", "Disco: manutenção do SSD", self._x_disco, True))
        if opcoes.get("apps"):
            P.append(("apps", "Removendo apps inúteis do Windows", self._x_apps, True))
        P.append(("dns", "Rede: limpando o DNS", self._x_dns, False))
        P.append(("ram", "Liberando a RAM", self._x_ram, False))
        return P

    def ext_iniciar(self, opcoes):
        if self.ext["ativo"] or self.otim["ativo"]:
            return self.msg("Já estou otimizando, aguarde.")
        if REG is None:
            return self.msg("A Otimização Extrema só funciona no Windows. Aqui você vê apenas uma prévia.")
        opc = {"dism": bool(opcoes.get("dism", True)), "apps": bool(opcoes.get("apps", False)),
               "busca": bool(opcoes.get("busca", False)), "winold": bool(opcoes.get("winold", False)),
               "nivel": "suprema" if opcoes.get("nivel") == "suprema" else "extrema"}
        passos = self._ext_plano(opc)
        self.ext.update({"ativo": True, "parando": False, "fracao": 0.02, "passo": "Preparando...", "mb": 0.0,
                         "opcoes": opc, "antes": None, "depois": None, "resumo": None})
        self.ext["passos"] = [{"id": p[0], "nome": p[1], "estado": "pendente", "texto": "", "mb": 0.0} for p in passos]
        self.ext_pular = False
        self.msg("Otimização Suprema iniciada..." if opc["nivel"] == "suprema" else "Otimização Extrema iniciada...")
        threading.Thread(target=self._ext_rodar, args=(passos,), daemon=True).start()

    def ext_parar(self):
        if self.ext["ativo"]:
            self.ext["parando"] = True
            self.ext_pular = True
            self.msg("Parando a Otimização Extrema...")

    def _ext_rodar(self, passos):
        E = self.ext
        adm = e_admin()
        opc = E["opcoes"]
        ctx = {"ajustes": [], "inicio": [], "plano": None, "apps": 0, "mb": 0.0, "fechados": [], "ssd": "?",
               "hibernacao": False, "servicos": 0, "ajustes_n": 0, "trim": None, "dism": None, "reinicio": False,
               "sup": opc.get("nivel") == "suprema", "busca": bool(opc.get("busca")), "gpu": [], "winold": None}
        self._xctx = ctx
        try:
            E["antes"] = self._medidas()
            n = len(passos)
            for i, (pid, nome, func, precisa_adm) in enumerate(passos):
                P = E["passos"][i]
                if E["parando"] or self.fechando:
                    for outro in E["passos"][i:]:
                        outro.update(estado="pulado", texto="Interrompido")
                    break
                if precisa_adm and not adm:
                    P.update(estado="pulado", texto="Precisa de Administrador")
                    E["fracao"] = (i + 1) / n
                    continue
                E["passo"] = nome + "..."
                E["fracao"] = max(0.02, i / n)
                P["estado"] = "rodando"
                inicio = time.time()
                try:
                    texto, estado, mb = func(ctx)
                except Exception as erro:
                    texto, estado, mb = f"Erro: {erro}", "erro", 0.0
                time.sleep(max(0.0, 0.6 - (time.time() - inicio)))  # cada passo fica à vista por um instante
                ctx["mb"] += mb
                E["mb"] = round(ctx["mb"], 1)
                P.update(estado=estado, texto=texto, mb=round(mb, 1))
                E["fracao"] = (i + 1) / n
                self._ext_guardar(ctx)
            E["depois"] = self._medidas()
            E["resumo"] = self._ext_resumo(ctx)
        except Exception as erro:
            self.msg(f"A Otimização Extrema parou por um erro: {erro}")
        finally:
            parou = E["parando"]
            E["passo"] = "Pronto"
            E["fracao"] = 1.0
            E["ativo"] = False
            E["parando"] = False
            E["desfazer"] = _ext_tem_algo(_ext_ler())
            self.atualizar_aj()
            E["fim"] += 1
            r = E["resumo"] or {}
            nome_otim = "Otimização Suprema" if ctx["sup"] else "Otimização Extrema"
            self.msg((f"{nome_otim} interrompida. " if parou else f"{nome_otim} concluída: ")
                     + f"{tam_texto(ctx['mb'] * 1048576)} liberados, {r.get('ajustes', 0)} ajuste(s), "
                       f"{r.get('inicio', 0)} programa(s) fora da inicialização.")
            self.estat_otimizacao(ctx["mb"], "suprema" if ctx["sup"] else "extrema", parou)

    def _ext_resumo(self, ctx):
        a, d = self.ext["antes"] or {}, self.ext["depois"] or {}
        ram = max(0.0, (d.get("ram_livre") or 0) - (a.get("ram_livre") or 0))
        return {"nivel": "suprema" if ctx["sup"] else "extrema", "gpu": len(ctx["gpu"]), "winold": ctx["winold"],
                "processos": [a.get("processos"), d.get("processos")], "servicos_rodando": [a.get("servicos"), d.get("servicos")],
                "limpo_mb": round(ctx["mb"], 1), "ram_gb": round(ram, 2), "ajustes": ctx["ajustes_n"],
                "servicos": ctx["servicos"], "inicio": len(ctx["inicio"]), "apps": ctx["apps"],
                "fechados": ctx["fechados"], "plano": bool(ctx["plano"]), "trim": ctx["trim"],
                "dism": ctx["dism"], "hibernacao": ctx["hibernacao"],
                "reiniciar": bool(ctx["ajustes_n"] or ctx["plano"] or ctx["inicio"] or ctx["hibernacao"] or ctx["dism"] or ctx["gpu"])}

    def _ext_guardar(self, ctx):
        """Anota o que foi feito, para o Desfazer, a cada passo (se o programa fechar no meio, nada se perde)."""
        prev = _ext_ler()
        plano = prev.get("plano")
        if ctx["plano"]:
            anterior = (plano or {}).get("anterior") or ctx["plano"].get("anterior")
            plano = {"extremo": ctx["plano"]["extremo"], "anterior": anterior}
        novo = {"quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "ajustes": list(dict.fromkeys(list(prev.get("ajustes", [])) + ctx["ajustes"])),
                "inicio": list(dict.fromkeys(list(prev.get("inicio", [])) + ctx["inicio"])),
                "gpu": list(dict.fromkeys(list(prev.get("gpu", [])) + ctx["gpu"])),
                "plano": plano}
        if _ext_tem_algo(novo):
            _ext_gravar(novo)
            self.ext["desfazer"] = True

    # ----- cada passo devolve (texto, estado, megabytes_liberados) -----

    def _x_restauracao(self, ctx):
        if ponto_restauracao():
            return "Ponto de restauração do Windows criado.", "ok", 0.0
        return ("Sem ponto novo (o Windows só cria um por dia ou a Proteção do Sistema está desligada). "
                "O Desfazer do Th Boost continua valendo."), "pulado", 0.0

    def _x_processos(self, ctx):
        nomes = fechar_dispensaveis()
        ctx["fechados"] = nomes
        return ("Fechei: " + ", ".join(nomes) + ".") if nomes else "Nada pesado rodando escondido.", "ok", 0.0

    def _x_limpar(self, ctx, grupo):
        texto, b = self._limpar_texto(grupo, sup=ctx["sup"])
        return texto, "ok", b / 1048576

    def _x_lixeira(self, ctx):
        ok, texto = esvaziar_lixeira()
        return texto, ("ok" if ok else "erro"), 0.0

    def _x_dism(self, ctx):
        if reinicio_pendente():
            ctx["dism"] = "adiado"
            return "Adiado: há um reinício pendente. Reinicie o PC e rode de novo para esta parte.", "pulado", 0.0
        self.ext_pular = False
        antes = psutil.disk_usage(disco_sistema()).free
        cod, _ = _executar_longo(["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"], 1500,
                                 lambda: self.ext["parando"] or self.ext_pular or self.fechando)
        self.ext_pular = self.ext["parando"]
        if cod == -1:
            ctx["dism"] = "pulado"
            return "Pulado por você. Dá para rodar de novo depois.", "pulado", 0.0
        if cod != 0:
            ctx["dism"] = "adiado"
            return "O Windows adiou esta limpeza (pode haver uma atualização pendente).", "pulado", 0.0
        ctx["dism"] = "ok"
        livre = max(0, psutil.disk_usage(disco_sistema()).free - antes)
        return "Versões antigas de componentes do Windows removidas.", "ok", livre / 1048576

    def _x_winold(self, ctx):
        pasta = pasta_windows_old()
        if not pasta:
            ctx["winold"] = "nenhuma"
            return "Não existe a pasta Windows.old neste PC.", "ok", 0.0
        if reinicio_pendente():
            ctx["winold"] = "adiado"
            return "Adiado: há um reinício pendente. Reinicie o PC e rode de novo para esta parte.", "pulado", 0.0
        antes = psutil.disk_usage(disco_sistema()).free
        parar = lambda: self.ext["parando"] or self.ext_pular or self.fechando
        self.ext_pular = False
        # toma posse da pasta (pelo código do grupo Administradores, que não depende do idioma) e apaga
        _executar_longo(["icacls", pasta, "/setowner", "*S-1-5-32-544", "/T", "/C", "/Q"], 900, parar)
        _executar_longo(["icacls", pasta, "/grant", "*S-1-5-32-544:(OI)(CI)F", "/T", "/C", "/Q"], 900, parar)
        cod, _ = _executar_longo(["cmd", "/c", "rd", "/s", "/q", pasta], 1800, parar)
        self.ext_pular = self.ext["parando"]
        if cod == -1:
            ctx["winold"] = "pulado"
            return "Pulado por você. A pasta ficou como estava (parte pode ter sido apagada).", "pulado", 0.0
        livre = max(0, psutil.disk_usage(disco_sistema()).free - antes)
        if pasta_windows_old() and os.listdir(pasta):
            ctx["winold"] = "parcial"
            return f"Apaguei parte do Windows.old ({tam_texto(livre)}); o resto está em uso. Tente de novo depois de reiniciar.", "ok", livre / 1048576
        ctx["winold"] = "ok"
        return "Windows.old removido. (Não dá mais para voltar à versão anterior do Windows.)", "ok", livre / 1048576

    def _x_ajustes(self, ctx, grupo):
        itens = [a for a in CATALOGO if a.grupo == grupo and (a.rec or a.ext or (ctx["sup"] and a.sup))
                 and a.risco != "medio" and a.disponivel()]
        if ctx["sup"] and tem_bateria():
            itens = [a for a in itens if not a.so_mesa]
        if grupo == "servicos" and ctx["busca"]:  # escolha da pessoa na tela: indexação de arquivos desligada
            ws = POR_ID.get("svc_wsearch")
            if ws and ws.disponivel():
                itens.append(ws)
        if grupo == "servicos":  # o Superfetch só atrapalha em SSD; em HD mecânico ajuda
            ssd = self._ssd(ctx)
            itens = [a for a in itens if a.id != "svc_sysmain"]
            sm = POR_ID.get("svc_sysmain")
            if sm and ssd is True and sm.disponivel():
                itens.append(sm)
        feitos = ja = sem_adm = falhas = 0
        e_adm = e_admin()
        for a in itens:
            try:
                est = a.estado()
            except Exception:
                est = None
            if est is None:
                continue
            if est is True:
                ja += 1
                continue
            if a.precisa_admin and not e_adm:
                sem_adm += 1
                continue
            try:
                a.ligar()
                ok = a.estado() is True
            except OSError:
                ok = False
            if ok:
                feitos += 1
                ctx["ajustes"].append(a.id)
                ctx["ajustes_n"] += 1
                if grupo == "servicos":
                    ctx["servicos"] += 1
            else:
                falhas += 1
        partes = [f"{feitos} aplicado(s)"]
        if ja:
            partes.append(f"{ja} já estava(m) assim")
        if sem_adm:
            partes.append(f"{sem_adm} precisa(m) de Administrador")
        if falhas:
            partes.append(f"{falhas} o Windows não aceitou")
        estado = "ok" if (feitos or ja or not falhas) else "erro"
        if not feitos and not ja and sem_adm and not falhas:
            estado = "pulado"
        return ", ".join(partes) + ".", estado, 0.0

    def _ssd(self, ctx):
        if ctx["ssd"] == "?":
            ctx["ssd"] = disco_e_ssd()
        return ctx["ssd"]

    def _x_gpu_jogos(self, ctx):
        todos = []
        for j in list(self.jogos):
            if j.get("pasta") or j.get("exes"):
                todos += exes_da_entrada(j)
        todos = list(dict.fromkeys(todos))
        if not todos:
            return "Nenhum jogo encontrado neste PC para ajustar.", "ok", 0.0
        feitos = gpu_alto_aplicar(todos)
        ctx["gpu"] = list(dict.fromkeys(ctx["gpu"] + feitos))
        return (f"{len(feitos)} programa(s) de jogos agora usam a placa de vídeo de alto desempenho."
                if feitos else "Seus jogos já usam a placa de vídeo de alto desempenho."), "ok", 0.0

    def _x_inicio(self, ctx):
        alvos = itens_inicio_dispensaveis(ctx["sup"])
        feitos = []
        for i in alvos:
            try:
                definir_inicio(i["id"], False)
                feitos.append(i)
            except OSError:
                pass
        ctx["inicio"] = [i["id"] for i in feitos]
        if not feitos:
            return "Nenhum programa pesado abrindo com o Windows.", "ok", 0.0
        nomes = ", ".join(i["nome"] for i in feitos[:6]) + (f" e mais {len(feitos) - 6}" if len(feitos) > 6 else "")
        return f"Não abrem mais sozinhos: {nomes}.", "ok", 0.0

    def _x_energia(self, ctx):
        ok, texto, guid, anterior = criar_plano_extremo(ctx["sup"])
        if guid and ok:
            ctx["plano"] = {"extremo": guid, "anterior": anterior}
        mb = 0.0
        h = POR_ID.get("hibernacao")
        if h and not tem_bateria() and h.estado() is False:  # em PC de mesa a hibernação só ocupa disco
            try:
                tam = os.path.getsize(os.path.join(disco_sistema(), "hiberfil.sys"))
            except OSError:
                tam = 0
            h.ligar()
            if h.estado() is True:
                ctx["ajustes"].append("hibernacao")
                ctx["ajustes_n"] += 1
                ctx["hibernacao"] = True
                mb = tam / 1048576
                texto += f" Hibernação desligada (liberou {tam_texto(tam)})." if tam else " Hibernação desligada."
        return texto, ("ok" if ok else "erro"), mb

    def _x_disco(self, ctx):
        ssd = self._ssd(ctx)
        if ssd is None:
            return "Não consegui saber se o disco é SSD ou HD, então deixei como está.", "pulado", 0.0
        if ssd is False:
            return "O disco é HD mecânico: desfragmentar leva horas, então fica de fora. Use a Desfragmentação do Windows à noite.", "pulado", 0.0
        letra = (os.environ.get("SystemDrive") or "C:")[:2]
        cod, _ = executar(["defrag", letra, "/L"], timeout=600)
        ctx["trim"] = cod == 0
        return ("TRIM enviado ao SSD (ele reaproveita os espaços livres)." if cod == 0
                else "O Windows não aceitou o TRIM agora."), ("ok" if cod == 0 else "erro"), 0.0

    def _x_apps(self, ctx):
        instalados = [a["nome"] for a in listar_apps() if a["risco"] == "baixo"]
        if not instalados:
            return "Nenhum app inútil instalado.", "ok", 0.0
        feitos = remover_apps(instalados)
        ctx["apps"] = feitos
        return f"{feitos} de {len(instalados)} app(s) removido(s). Voltam pela Microsoft Store.", "ok", 0.0

    def _x_dns(self, ctx):
        return self.t_dns(), "ok", 0.0

    def _x_ram(self, ctx):
        b, texto = liberar_ram()
        return texto, "ok", 0.0

    # ----- desfazer -----

    def ext_desfazer(self):
        if self.ext["ativo"] or self.otim["ativo"]:
            return self.msg("Espere a otimização terminar para desfazer.")
        self.msg("Desfazendo a Otimização Extrema...")
        self.em_fundo(self._ext_desfazer_agora)

    def _ext_desfazer_agora(self):
        est = _ext_ler()
        if not _ext_tem_algo(est):
            _ext_gravar({})
            self.ext["desfazer"] = False
            return "Não há nada da Otimização Extrema para desfazer."
        adm = e_admin()
        devolvidos, restante = 0, []
        for ident in est.get("ajustes", []):
            a = POR_ID.get(ident)
            if a is None:
                continue
            if a.precisa_admin and not adm:
                restante.append(ident)
                continue
            try:
                a.desligar()
                devolvidos += 1
            except OSError:
                restante.append(ident)
        inicio = 0
        for ident in est.get("inicio", []):
            try:
                definir_inicio(ident, True)
                inicio += 1
            except OSError:
                pass
        gpus = gpu_alto_remover(est.get("gpu") or []) if est.get("gpu") else 0
        plano = est.get("plano") or {}
        plano_ok = False
        if plano.get("extremo") and adm:
            plano_ok = restaurar_plano(plano["extremo"], plano.get("anterior"))
        plano_pendente = bool(plano.get("extremo")) and not plano_ok
        resto = {"quando": est.get("quando"), "ajustes": restante, "inicio": [], "gpu": [], "plano": plano if plano_pendente else None}
        _ext_gravar(resto if _ext_tem_algo(resto) else {})
        self.atualizar_aj()
        self.ext["desfazer"] = _ext_tem_algo(_ext_ler())
        self.ext["resumo"] = None
        texto = f"Otimização desfeita: {devolvidos} ajuste(s) e {inicio} programa(s) da inicialização devolvidos"
        if gpus:
            texto += f", {gpus} perfil(is) de placa de vídeo"
        texto += ", plano de energia de antes de volta." if plano_ok else "."
        if restante or plano_pendente:
            texto += " Parte precisa de Administrador: abra o Th Boost pelo atalho e desfaça de novo."
        return texto

    # ----- reiniciar o PC -----

    def reiniciar_pc(self):
        if not IS_WIN:
            return self.msg("Disponível só no Windows.")
        cod, _ = executar(["shutdown", "/r", "/t", "20", "/c", "Th Boost: reiniciando para concluir a otimização."])
        if cod == 0:
            self.reinicio_ate = time.time() + 20
            self.msg("O PC reinicia em 20 segundos. Salve o que estiver aberto.")
        else:
            self.msg("Não consegui agendar o reinício. Reinicie pelo menu Iniciar.")

    def reiniciar_cancelar(self):
        executar(["shutdown", "/a"])
        self.reinicio_ate = 0.0
        self.msg("Reinício cancelado.")
