# ---------------- jogos de TODAS as lojas e launchers (não só Steam e Epic) ----------------
#
# A lista junta, nesta ordem de prioridade (o primeiro que aparecer ganha, sem repetir):
#  1. Steam e Epic (leem os arquivos que a própria loja guarda);
#  2. launchers com formato próprio: Riot (VALORANT, League of Legends), Roblox, FiveM e RAGE MP (GTA RP),
#     Rockstar (GTA V), Ubisoft, EA, GOG, Xbox / Microsoft Store e Minecraft;
#  3. programas instalados (registro do Windows) de empresas de jogos, de jogos conhecidos ou em pastas "Games";
#  4. jogos que o próprio Windows (Game Bar) já reconheceu neste PC;
#  5. os que a pessoa adicionou escolhendo o .exe.
# Aqui só se LÊ o computador: nada é alterado. Quem manda no que aparece é a pessoa:
# dá para adicionar um jogo que faltou e tirar da lista o que não é jogo (e trazer de volta depois).

_EDITORAS_JOGOS = re.compile(
    r"riot games|blizzard|electronic arts|\bea games\b|ubisoft|activision|bethesda|rockstar|take-two|2k games|2k sports|"
    r"cd projekt|square enix|bandai namco|capcom|\bsega\b|konami|mihoyo|cognosphere|hoyoverse|mojang|innersloth|gaijin|"
    r"wargaming|netease|tencent|krafton|pubg|nexon|garena|moonton|proxima beta|level infinite|paradox interactive|"
    r"focus entertainment|embracer|warner bros\.? games|\bthq\b|devolver|team17|obsidian entertainment|larian|"
    r"gearbox|respawn|id software|kuro games|hypergryph|com2us|smilegate|pearl abyss|studio wildcard", re.IGNORECASE)
_NOMES_JOGOS = re.compile(
    r"valorant|league of legends|roblox|fivem|minecraft|fortnite|counter-strike|dota ?2|apex legends|call of duty|warzone|"
    r"overwatch|diablo|world of warcraft|hearthstone|genshin|honkai|zenless|wuthering|lost ark|path of exile|"
    r"escape from tarkov|\brust\b|pubg|battlegrounds|rainbow six|far cry|assassin'?s creed|grand theft auto|\bgta\b|"
    r"red dead|cyberpunk|witcher|elden ring|forza|the sims|\bfifa\b|ea sports|rocket league|among us|fall guys|free fire|"
    r"ragnarok|\btibia\b|black desert|albion online|\bosu!|terraria|stardew|warframe|teamfight|legends of runeterra|"
    r"lunar client|badlion|rage ?mp|alt:?v|garry'?s mod|left 4 dead|team fortress|half-life|portal|the finals|helldivers|"
    r"palworld|valheim|sea of thieves|dead by daylight|rocketleague|brawlhalla|krunker|slither|league client", re.IGNORECASE)
# launchers, antitrapaça e utilitários: nunca entram como "jogo", mesmo quando a empresa é de jogos
_NAO_E_JOGO = re.compile(
    r"^(steam|steam client|epic games launcher|epic online services|battle\.net|ea app|ea desktop|origin|ubisoft connect|"
    r"uplay|gog galaxy|riot client|riot vanguard|xbox|xbox app|gaming services|discord|overwolf|playnite|"
    r"easy anti-?cheat|battleye|faceit|geforce|nvidia|amd software|radeon|directx|vulkan|microsoft visual c\+\+|"
    r"rockstar games launcher|rockstar games social club|bethesda\.net launcher|minecraft launcher updater)\b|"
    r"redistributable|redist\b|runtime|sdk\b|update for|hotfix|uninstall|desinstal|wallpaper|server\b|dedicated server|"
    r"benchmark|mod ?manager|crash ?report|\bdlc\b|soundtrack|trilha sonora", re.IGNORECASE)
# programas que o Windows às vezes marca como jogo mas não são
_EXE_NAO_JOGO = re.compile(
    r"^(chrome|msedge|firefox|brave|opera|iexplore|explorer|notepad|code|devenv|discord|teams|ms-teams|slack|zoom|skype|"
    r"spotify|steam|steamwebhelper|epicgameslauncher|battle\.net|obs64|obs32|obs|vlc|winword|excel|powerpnt|outlook|"
    r"onedrive|python|pythonw|node|java|javaw|cmd|powershell|conhost|setup|installer|unins\d*|uninstall)\.exe$", re.IGNORECASE)
_PRIORIDADE_ORIGEM = ("Steam", "Epic")
MAX_JOGOS_MANUAIS = 60
MAX_JOGOS_LISTA = 300


def _env(nome, padrao=""):
    return os.environ.get(nome) or padrao


def _chave_jogo(nome):
    """Nome sem acento, símbolos e espaços: serve para não repetir o mesmo jogo vindo de duas lojas."""
    return re.sub(r"[^a-z0-9]+", "", str(nome).lower())


def _discos():
    """Raízes das unidades do PC (C:\\, D:\\...), sem CD e sem unidades de rede."""
    saida = []
    try:
        for p in psutil.disk_partitions(all=False):
            opts = (p.opts or "").lower()
            if "cdrom" in opts or "remote" in opts or not p.mountpoint:
                continue
            saida.append(p.mountpoint)
    except Exception:
        pass
    if IS_WIN and not saida:
        saida = [f"{l}:\\" for l in "CDEFGH" if os.path.isdir(f"{l}:\\")]
    return saida


def _reg_valores(raiz, caminho):
    """Valores de uma chave do registro, com os nomes em minúsculas. Vazio se não existe."""
    if REG is None:
        return {}
    try:
        return {str(n).lower(): v for n, v in REG.valores(raiz, caminho)}
    except Exception:
        return {}


def _reg_sub(raiz, caminho):
    if REG is None:
        return []
    try:
        return list(REG.subchaves(raiz, caminho))
    except Exception:
        return []


def _pasta_texto(valor):
    """Caminho vindo do registro ou de arquivo: tira aspas, barra no fim e converte / em \\. '' se não for pasta."""
    if not isinstance(valor, str):
        return ""
    v = valor.strip().strip('"').strip()
    if not v or len(v) > 300 or re.search(r"[<>|*?\"]", v):
        return ""
    v = os.path.normpath(v)
    return v if os.path.isabs(v) and os.path.isdir(v) else ""


def _exe_texto(valor):
    """Caminho de um .exe vindo do registro (aceita aspas e ',0' do ícone). '' se não existir."""
    if not isinstance(valor, str):
        return ""
    v = valor.strip()
    m = re.match(r'^"([^"]+)"', v)
    v = m.group(1) if m else re.sub(r",\s*-?\d+\s*$", "", v).strip()
    v = v.strip().strip('"')
    if not v.lower().endswith(".exe") or len(v) > 300 or re.search(r"[<>|*?\"]", v):
        return ""
    v = os.path.normpath(v)
    return v if os.path.isabs(v) and os.path.isfile(v) else ""


def _exe_principal(pasta):
    achados = exes_do_jogo(pasta, 1) if pasta else []
    return achados[0] if achados else ""


def _pasta_estreita(pasta, exe):
    """Pasta ampla demais (C:\\ ou C:\\Games) vira só a pasta do .exe, para não confundir jogos vizinhos."""
    n = _norm(pasta).rstrip("\\/") if pasta else ""
    partes = [x for x in re.split(r"[\\/]+", n) if x]
    if pasta and len(partes) >= 3:
        return pasta
    return os.path.dirname(exe) if exe else ""


def _jogo(nome, origem, pasta="", abrir=None, exe="", extras=None):
    nome = re.sub(r"\s+", " ", str(nome)).strip()
    if not nome or not abrir:
        return None
    j = {"nome": nome[:80], "origem": origem, "pasta": pasta or "", "abrir": abrir}
    if exe:
        j["exe"] = exe
    if extras:
        j["exes"] = [e for e in extras if e]
    return j


def _limpar_nome_pasta(nome):
    nome = re.sub(r"[_]+", " ", str(nome))
    return re.sub(r"\s+", " ", nome).strip()


def _nome_do_exe(exe):
    """Nome de um jogo a partir do arquivo (hollow_knight.exe -> Hollow Knight)."""
    nome = _limpar_nome_pasta(os.path.splitext(os.path.basename(exe))[0])
    return nome.title() if nome.islower() else nome


# ---------- Riot: VALORANT, League of Legends e os outros ----------

_RIOT_NOMES = {"valorant": "VALORANT", "league_of_legends": "League of Legends", "bacon": "Legends of Runeterra",
               "lion": "2XKO"}


def _cliente_riot():
    base = os.path.join(_env("ProgramData", r"C:\ProgramData"), "Riot Games", "RiotClientInstalls.json")
    try:
        with open(base, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            for k in ("rc_default", "rc_live", "rc_beta"):
                c = d.get(k)
                if isinstance(c, str) and os.path.isfile(c):
                    return os.path.normpath(c)
    except (OSError, ValueError):
        pass
    for raiz in _discos():
        c = os.path.join(raiz, "Riot Games", "Riot Client", "RiotClientServices.exe")
        if os.path.isfile(c):
            return c
    return ""


def _jogos_riot():
    cliente = _cliente_riot()
    jogos, vistos = [], set()
    base = os.path.join(_env("ProgramData", r"C:\ProgramData"), "Riot Games", "Metadata")
    for arq in glob.glob(os.path.join(base, "*", "*.product_settings.yaml")):
        produto, _, patch = os.path.basename(os.path.dirname(arq)).partition(".")
        if not produto or produto == "riot_client" or produto in vistos:
            continue
        try:
            with open(arq, encoding="utf-8", errors="replace") as f:
                texto = f.read()
        except OSError:
            continue
        m = re.search(r'^\s*product_install_full_path:\s*"?([^"\r\n]+?)"?\s*$', texto, re.M)
        pasta = _pasta_texto(m.group(1)) if m else ""
        if not pasta:
            continue
        vistos.add(produto)
        nome = _RIOT_NOMES.get(produto) or _limpar_nome_pasta(produto).title()
        exe = _exe_principal(pasta)
        if cliente:
            abrir = [cliente, f"--launch-product={produto}", f"--launch-patchline={patch or 'live'}"]
        else:
            abrir = [exe] if exe else None
        j = _jogo(nome, "Riot", pasta, abrir, exe)
        if j:
            jogos.append(j)
    if "valorant" not in vistos and cliente:  # sem os arquivos de controle, mas com a pasta padrão
        for raiz in _discos():
            pasta = os.path.join(raiz, "Riot Games", "VALORANT")
            if os.path.isdir(pasta):
                j = _jogo("VALORANT", "Riot", pasta, [cliente, "--launch-product=valorant", "--launch-patchline=live"], _exe_principal(pasta))
                if j:
                    jogos.append(j)
                break
    return jogos


# ---------- Roblox ----------

def _jogos_roblox():
    la = _env("LOCALAPPDATA")
    if not la:
        return []
    jogos = []
    for pasta_base, launcher in ((os.path.join(la, "Roblox"), ""), (os.path.join(la, "Bloxstrap"), os.path.join(la, "Bloxstrap", "Bloxstrap.exe")),
                                 (os.path.join(la, "Fishstrap"), os.path.join(la, "Fishstrap", "Fishstrap.exe"))):
        player = sorted(glob.glob(os.path.join(pasta_base, "Versions", "*", "RobloxPlayerBeta.exe")), key=lambda p: os.path.getmtime(p), reverse=True)
        if not player:
            continue
        # o Roblox abre pelo site: a pessoa clica em Jogar lá e o Th Boost já vigia o programa do jogo
        abrir = [launcher] if launcher and os.path.isfile(launcher) else "https://www.roblox.com/games"
        j = _jogo("Roblox", "Roblox", pasta_base, abrir, player[0])
        if j:
            jogos.append(j)
            break
    if not jogos:
        loja = os.path.join(la, "Packages", "ROBLOXCORPORATION.ROBLOX_55nm5eh3cm0pr")
        if os.path.isdir(loja):  # versão da Microsoft Store: a pasta do programa fica protegida, então só abre
            j = _jogo("Roblox", "Roblox", "", r"shell:AppsFolder\ROBLOXCORPORATION.ROBLOX_55nm5eh3cm0pr!App")
            if j:
                jogos.append(j)
    return jogos


# ---------- GTA RP: FiveM e RAGE MP ----------

def _jogos_gta_rp():
    jogos = []
    la = _env("LOCALAPPDATA")
    if la:
        exe = os.path.join(la, "FiveM", "FiveM.exe")
        if os.path.isfile(exe):
            j = _jogo("GTA RP (FiveM)", "FiveM", os.path.dirname(exe), [exe], exe)
            if j:
                jogos.append(j)
    for raiz in _discos():
        for sub in ("RAGEMP", "RAGE MP", "ragemp"):
            pasta = os.path.join(raiz, sub)
            for nome_exe in ("updater.exe", "ragemp_v.exe"):
                exe = os.path.join(pasta, nome_exe)
                if os.path.isfile(exe):
                    j = _jogo("GTA RP (RAGE MP)", "RAGE MP", pasta, [exe], exe)
                    if j:
                        jogos.append(j)
                    break
            else:
                continue
            break
        if any(x["origem"] == "RAGE MP" for x in jogos):
            break
    return jogos


# ---------- Rockstar (GTA V, Red Dead) ----------

_ROCKSTAR_NOMES = {"gtav": "Grand Theft Auto V", "grand theft auto v": "Grand Theft Auto V", "gta v": "Grand Theft Auto V",
                   "rdr2": "Red Dead Redemption 2", "red dead redemption 2": "Red Dead Redemption 2",
                   "gta iv": "Grand Theft Auto IV", "gta san andreas": "GTA San Andreas"}


def _jogos_rockstar():
    jogos = []
    for chave in (r"SOFTWARE\WOW6432Node\Rockstar Games", r"SOFTWARE\Rockstar Games"):
        for sub in _reg_sub("HKLM", chave):
            if re.search(r"launcher|social ?club|installer", sub, re.IGNORECASE):
                continue
            v = _reg_valores("HKLM", chave + "\\" + sub)
            pasta = _pasta_texto(v.get("installfolder") or v.get("install dir") or "")
            if not pasta:
                continue
            play = sorted(glob.glob(os.path.join(pasta, "Play*.exe")))
            exe = play[0] if play else _exe_principal(pasta)
            j = _jogo(_ROCKSTAR_NOMES.get(sub.lower()) or sub, "Rockstar", pasta, [exe] if exe else None, exe)
            if j:
                jogos.append(j)
    return jogos


# ---------- Ubisoft, EA e GOG ----------

def _jogos_ubisoft():
    jogos = []
    for chave in (r"SOFTWARE\WOW6432Node\Ubisoft\Launcher\Installs", r"SOFTWARE\Ubisoft\Launcher\Installs"):
        for ident in _reg_sub("HKLM", chave):
            v = _reg_valores("HKLM", chave + "\\" + ident)
            pasta = _pasta_texto(v.get("installdir") or "")
            if not pasta:
                continue
            exe = _exe_principal(pasta)
            abrir = f"uplay://launch/{ident}/0" if ident.isdigit() else ([exe] if exe else None)
            j = _jogo(os.path.basename(pasta), "Ubisoft", pasta, abrir, exe)
            if j:
                jogos.append(j)
    return jogos


def _jogos_ea():
    jogos = []
    for chave in (r"SOFTWARE\WOW6432Node\EA Games", r"SOFTWARE\EA Games", r"SOFTWARE\WOW6432Node\Electronic Arts"):
        for sub in _reg_sub("HKLM", chave):
            v = _reg_valores("HKLM", chave + "\\" + sub)
            pasta = _pasta_texto(v.get("install dir") or v.get("installdir") or "")
            if not pasta:
                continue
            exe = _exe_principal(pasta)
            j = _jogo(sub, "EA", pasta, [exe] if exe else None, exe)
            if j:
                jogos.append(j)
    return jogos


def _jogos_gog():
    jogos = []
    chave = r"SOFTWARE\WOW6432Node\GOG.com\Games"
    for ident in _reg_sub("HKLM", chave):
        v = _reg_valores("HKLM", chave + "\\" + ident)
        pasta = _pasta_texto(v.get("path") or "")
        exe = _exe_texto(v.get("exe") or "") or _exe_principal(pasta)
        j = _jogo(v.get("gamename") or os.path.basename(pasta or ""), "GOG", pasta, [exe] if exe else None, exe)
        if j and pasta:
            jogos.append(j)
    return jogos


# ---------- Xbox / Microsoft Store ----------

_B32 = "0123456789abcdefghjkmnpqrstvwxyz"


def _hash_editora(editora):
    """O trecho final do nome de família de um app da Microsoft Store (ex.: 8wekyb3d8bbwe), a partir do Publisher."""
    h = hashlib.sha256(editora.encode("utf-16-le")).digest()[:8]
    bits = int.from_bytes(h, "big") << 1
    return "".join(_B32[(bits >> (60 - 5 * i)) & 31] for i in range(13))


def _app_do_manifesto(pasta_conteudo):
    """'shell:AppsFolder\\Nome_hash!Id' de um jogo da Xbox, lendo o appxmanifest.xml. '' se não der."""
    arq = os.path.join(pasta_conteudo, "appxmanifest.xml")
    try:
        if os.path.getsize(arq) > 2_000_000:
            return ""
        import xml.etree.ElementTree as ET
        raiz = ET.parse(arq).getroot()
    except Exception:
        return ""
    ident = app = None
    for el in raiz.iter():
        marca = el.tag.rsplit("}", 1)[-1]
        if marca == "Identity" and ident is None:
            ident = el.attrib
        elif marca == "Application" and app is None:
            app = el.attrib.get("Id")
    if not ident or not app or not ident.get("Name") or not ident.get("Publisher"):
        return ""
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", ident["Name"]) or not re.fullmatch(r"[A-Za-z0-9.\-]+", app):
        return ""
    return "shell:AppsFolder\\%s_%s!%s" % (ident["Name"], _hash_editora(ident["Publisher"]), app)


def _jogos_xbox():
    jogos = []
    for raiz in _discos():
        base = os.path.join(raiz, "XboxGames")
        if not os.path.isdir(base):
            continue
        try:
            pastas = sorted(os.scandir(base), key=lambda e: e.name.lower())
        except OSError:
            continue
        for e in pastas[:80]:
            try:
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            conteudo = os.path.join(e.path, "Content")
            if not os.path.isdir(conteudo):
                continue
            exe = _exe_principal(conteudo)
            abrir = _app_do_manifesto(conteudo) or ([exe] if exe else None)
            j = _jogo(_limpar_nome_pasta(e.name), "Xbox", e.path, abrir, exe)
            if j:
                jogos.append(j)
    return jogos


# ---------- Minecraft ----------

def _jogos_minecraft():
    la, ap = _env("LOCALAPPDATA"), _env("APPDATA")
    pf = _env("ProgramFiles(x86)", r"C:\Program Files (x86)")
    launcher = os.path.join(pf, "Minecraft Launcher", "MinecraftLauncher.exe")
    loja_java = os.path.join(la, "Packages", "Microsoft.4297127D64EC6_8wekyb3d8bbwe") if la else ""
    jogos = []
    # o programa que de fato roda o jogo (Java) fica na pasta "runtime" do launcher
    java = ""
    for base in (os.path.join(loja_java, "LocalCache", "Local", "runtime") if loja_java else "", os.path.join(ap, ".minecraft", "runtime") if ap else ""):
        if base and os.path.isdir(base):
            for raiz, subs, arqs in os.walk(base):
                if raiz[len(base):].count(os.sep) >= 6:
                    subs[:] = []
                if "javaw.exe" in arqs:
                    java = os.path.join(raiz, "javaw.exe")
                    break
            if java:
                break
    # sobe até a pasta "runtime" para cobrir qualquer versão de Java que o launcher baixar
    pasta = ""
    if java:
        corte = java.lower().rfind(os.sep + "runtime" + os.sep)
        pasta = java[:corte + len("runtime") + 1] if corte > 0 else os.path.dirname(java)
    if os.path.isfile(launcher):
        j = _jogo("Minecraft", "Minecraft", pasta or os.path.dirname(launcher), [launcher], launcher, [java])
    elif loja_java and os.path.isdir(loja_java):
        j = _jogo("Minecraft", "Minecraft", pasta, r"shell:AppsFolder\Microsoft.4297127D64EC6_8wekyb3d8bbwe!Minecraft", "", [java])
    else:
        j = None
    if j:
        jogos.append(j)
    if la and os.path.isdir(os.path.join(la, "Packages", "Microsoft.MinecraftUWP_8wekyb3d8bbwe")):
        j = _jogo("Minecraft Bedrock", "Minecraft", "", r"shell:AppsFolder\Microsoft.MinecraftUWP_8wekyb3d8bbwe!App")
        if j:
            jogos.append(j)
    return jogos


# ---------- programas instalados (registro do Windows) ----------

_CHAVES_UNINSTALL = (("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                     ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                     ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"))


def _e_pasta_de_jogos(pasta):
    return bool(re.search(r"[\\/](games|jogos)[\\/]", pasta + os.sep, re.IGNORECASE))


def _origem_pela_editora(editora):
    e = editora.lower()
    if "blizzard" in e:
        return "Battle.net"
    if "electronic arts" in e or e.strip() in ("ea", "ea games"):
        return "EA"
    if "ubisoft" in e:
        return "Ubisoft"
    if "riot" in e:
        return "Riot"
    if "rockstar" in e:
        return "Rockstar"
    if "mihoyo" in e or "cognosphere" in e or "hoyoverse" in e:
        return "HoYoverse"
    return "Instalado"


def _jogos_instalados():
    jogos, vistos = [], set()
    for raiz, caminho in _CHAVES_UNINSTALL:
        for sub in _reg_sub(raiz, caminho):
            if len(jogos) >= 120:
                return jogos
            v = _reg_valores(raiz, caminho + "\\" + sub)
            nome = str(v.get("displayname") or "").strip()
            if not nome or v.get("systemcomponent") == 1 or v.get("parentkeyname") or v.get("releasetype"):
                continue
            if _NAO_E_JOGO.search(nome):
                continue
            editora = str(v.get("publisher") or "")
            pasta = _pasta_texto(v.get("installlocation") or "")
            exe_icone = _exe_texto(v.get("displayicon") or "")
            if not pasta and exe_icone:
                pasta = os.path.dirname(exe_icone)
            if not pasta or not os.path.isdir(pasta):
                continue
            e_jogo = bool(_EDITORAS_JOGOS.search(editora) or _NOMES_JOGOS.search(nome) or _e_pasta_de_jogos(pasta))
            if not e_jogo:
                continue
            chave = _chave_jogo(nome)
            if chave in vistos:
                continue
            vistos.add(chave)
            exe = _exe_principal(pasta) or (exe_icone if not _EXE_NAO_JOGO.search(os.path.basename(exe_icone or "")) else "")
            if not exe:
                continue
            j = _jogo(nome, _origem_pela_editora(editora), _pasta_estreita(pasta, exe), [exe], exe)
            if j:
                jogos.append(j)
    return jogos


# ---------- jogos que o Windows (Game Bar) já reconheceu ----------

def _jogos_windows():
    jogos = []
    base = r"System\GameConfigStore\Children"
    for sub in _reg_sub("HKCU", base)[:200]:
        v = _reg_valores("HKCU", base + "\\" + sub)
        exe = _exe_texto(v.get("matchedexefullpath") or "")
        if not exe or _EXE_NAO_JOGO.search(os.path.basename(exe)) or _IGNORAR_EXE.search(os.path.basename(exe)):
            continue
        if re.search(r"[\\/](windows|system32|syswow64)[\\/]", exe, re.IGNORECASE):
            continue
        pasta = os.path.dirname(exe)
        nome = _limpar_nome_pasta(os.path.basename(pasta)) if len(re.split(r"[\\/]+", pasta)) > 3 else ""
        if not nome or re.fullmatch(r"(bin|binaries|win64|x64|x86|game|release|retail)", nome, re.IGNORECASE):
            nome = _nome_do_exe(exe)
        if _NAO_E_JOGO.search(nome):
            continue
        j = _jogo(nome, "Windows", pasta, [exe], exe)
        if j:
            jogos.append(j)
    return jogos


# ---------- jogos adicionados pela pessoa ----------

def _exe_manual_valido(exe):
    return (isinstance(exe, str) and 8 < len(exe) < 300 and os.path.isabs(exe) and exe.lower().endswith(".exe")
            and not re.search(r"[;\"<>|*?]", exe) and os.path.isfile(exe)
            and not re.search(r"[\\/](windows|system32|syswow64)[\\/]", exe, re.IGNORECASE))


def _jogos_manuais():
    jogos = []
    for item in (CONFIG.get("jogos_manuais") or [])[:MAX_JOGOS_MANUAIS]:
        if not isinstance(item, dict) or not _exe_manual_valido(item.get("exe")):
            continue
        exe = os.path.normpath(item["exe"])
        j = _jogo(item.get("nome") or _nome_do_exe(exe), "Adicionado", os.path.dirname(exe), [exe], exe)
        if j:
            j["manual"] = True
            jogos.append(j)
    return jogos


def jogo_manual_adicionar(exe, nome=""):
    """Guarda um jogo escolhido pela pessoa. Devolve (ok, texto)."""
    if not _exe_manual_valido(exe):
        return False, "Escolha o programa do jogo (um arquivo .exe que exista)."
    exe = os.path.normpath(exe)
    lista = [i for i in (CONFIG.get("jogos_manuais") or []) if isinstance(i, dict)]
    if any(_norm(i.get("exe", "")) == _norm(exe) for i in lista):
        return False, "Esse jogo já está na lista."
    if len(lista) >= MAX_JOGOS_MANUAIS:
        return False, "A lista de jogos adicionados está cheia."
    nome = re.sub(r"[\x00-\x1f<>]", "", str(nome or "")).strip()[:60] or _nome_do_exe(exe)
    lista.append({"nome": nome, "exe": exe})
    CONFIG["jogos_manuais"] = lista
    ocultos = [c for c in (CONFIG.get("jogos_ocultos") or []) if c != _chave_jogo(nome)]
    CONFIG["jogos_ocultos"] = ocultos
    salvar_config()
    return True, nome


def jogo_tirar_da_lista(jogo):
    """Tira um jogo da lista: o que foi adicionado à mão é apagado; o detectado fica escondido (dá para trazer de volta)."""
    if jogo.get("manual"):
        CONFIG["jogos_manuais"] = [i for i in (CONFIG.get("jogos_manuais") or [])
                                   if not (isinstance(i, dict) and _norm(i.get("exe", "")) == _norm(jogo.get("exe", "")))]
    else:
        ocultos = [c for c in (CONFIG.get("jogos_ocultos") or []) if isinstance(c, str)]
        chave = _chave_jogo(jogo["nome"])
        if chave not in ocultos:
            ocultos.append(chave)
        CONFIG["jogos_ocultos"] = ocultos[:300]
    salvar_config()


def escolher_exe_do_jogo():
    """Abre a janela do Windows para escolher o .exe do jogo. '' se a pessoa cancelar."""
    if not IS_WIN:
        return ""
    script = ("Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
              "$f=New-Object System.Windows.Forms.Form; $f.TopMost=$true; $f.ShowInTaskbar=$false; $f.StartPosition='CenterScreen'; "
              "$f.Size=New-Object System.Drawing.Size(1,1); $f.Opacity=0; $f.Show(); "
              "$d=New-Object System.Windows.Forms.OpenFileDialog; $d.Title='Escolha o programa do jogo (.exe)'; "
              "$d.Filter='Programas (*.exe)|*.exe'; $d.CheckFileExists=$true; "
              "if($d.ShowDialog($f) -eq 'OK'){[Console]::OutputEncoding=[Text.Encoding]::UTF8; Write-Output $d.FileName}; $f.Close()")
    cod, saida = executar(["powershell", "-STA", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=600)
    if cod != 0:
        return ""
    linhas = [x.strip() for x in saida.splitlines() if x.strip()]
    return linhas[-1] if linhas else ""


# ---------- junta tudo ----------

def _fontes_de_jogos():
    return [_jogos_steam, _jogos_epic, _jogos_riot, _jogos_roblox, _jogos_gta_rp, _jogos_rockstar, _jogos_ubisoft,
            _jogos_ea, _jogos_gog, _jogos_xbox, _jogos_minecraft, _jogos_instalados, _jogos_windows, _jogos_manuais]


def _mesma_pasta(a, b):
    return a == b or a.startswith(b + os.sep) or b.startswith(a + os.sep)


def jogos_detectar_tudo():
    """Lista única de jogos, sem repetir, sem launchers e sem os que a pessoa tirou da lista."""
    ocultos = {c for c in (CONFIG.get("jogos_ocultos") or []) if isinstance(c, str)}
    nomes, pastas, exes, lista = set(), [], set(), []
    for fonte in _fontes_de_jogos():
        try:
            achados = fonte() or []
        except Exception:
            achados = []
        for j in achados:
            chave = _chave_jogo(j["nome"])
            if not chave or chave in nomes:
                continue
            if not j.get("manual") and (chave in ocultos or any(t in j["nome"].lower() for t in EXCLUIR_JOGOS)
                                         or _NAO_E_JOGO.search(j["nome"])):
                continue
            pasta_n = _norm(j["pasta"]) if j.get("pasta") else ""
            exe_n = _norm(j["exe"]) if j.get("exe") else ""
            if not j.get("manual"):
                if exe_n and exe_n in exes:
                    continue
                if pasta_n and any(_mesma_pasta(pasta_n, p) for p in pastas):
                    continue
            nomes.add(chave)
            if pasta_n:
                pastas.append(pasta_n)
            if exe_n:
                exes.add(exe_n)
            j["chave"] = chave
            lista.append(j)
            if len(lista) >= MAX_JOGOS_LISTA:
                return sorted(lista, key=lambda g: g["nome"].lower())
    return sorted(lista, key=lambda g: g["nome"].lower())


def exes_da_entrada(jogo):
    """Os programas de um jogo que o Th Boost ajusta: os extras conhecidos e os maiores da pasta."""
    achados = [e for e in (jogo.get("exes") or []) if _exe_valido(e) and os.path.isfile(e)]
    achados += exes_do_jogo(jogo.get("pasta"))
    return list(dict.fromkeys(achados))


def icone_do_jogo(jogo):
    """Imagem (ícone do programa) de um jogo fora da Steam. None se não der. Fica guardada na pasta de capas."""
    exe = jogo.get("exe") or ""
    if not IS_WIN or not exe or not os.path.isfile(exe):
        return None
    destino = os.path.join(pasta_capas(), "ic_" + hashlib.md5(_norm(exe).encode("utf-8", "replace")).hexdigest()[:12] + ".png")
    if os.path.isfile(destino) and os.path.getsize(destino) > 100:
        return destino
    b64 = lambda s: base64.b64encode(s.encode("utf-8")).decode("ascii")
    script = ("Add-Type -AssemblyName System.Drawing; "
              f"$e=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64(exe)}')); "
              f"$o=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64(destino)}')); "
              "$i=[System.Drawing.Icon]::ExtractAssociatedIcon($e); "
              "if($i){$i.ToBitmap().Save($o,[System.Drawing.Imaging.ImageFormat]::Png)}")
    executar(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=30)
    return destino if os.path.isfile(destino) and os.path.getsize(destino) > 100 else None
