# ---------------- v9.1: Autoteste — confere, no computador da pessoa, se cada parte do Th Boost funciona ----------------
# Só lê (não muda nada no Windows). O resultado vira um relatório que a pessoa pode copiar e mandar para o suporte.
# O relatório não leva o nome do usuário nem o nome do computador.

AT_OK, AT_AVISO, AT_ERRO, AT_PULADO = "ok", "aviso", "erro", "pulado"


def _at_anon(texto):
    t = str(texto)
    casa = os.path.expanduser("~")
    if casa and len(casa) > 3:
        t = t.replace(casa, "%USERPROFILE%")
    for nome in {os.environ.get("USERNAME", ""), os.environ.get("COMPUTERNAME", "")}:
        if len(nome) >= 3:
            t = re.sub(re.escape(nome), "<oculto>", t, flags=re.I)
    return t[:300]


def _n(x, casas=1):
    """Número no jeito brasileiro (vírgula decimal)."""
    return f"{x:.{casas}f}".replace(".", ",")


def _at_ps(comando, timeout=25):
    return executar(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", comando], timeout=timeout)


def _at_reg(raiz, caminho, nome):
    """Lê um valor do registro (ou None). Usa winreg direto: o autoteste não pode depender do que ele testa."""
    try:
        import winreg as _w
        r = {"HKLM": _w.HKEY_LOCAL_MACHINE, "HKCU": _w.HKEY_CURRENT_USER}[raiz]
        with _w.OpenKey(r, caminho) as k:
            return _w.QueryValueEx(k, nome)[0]
    except (OSError, ImportError, KeyError):
        return None


def at_sistema():
    if not IS_WIN:
        return AT_PULADO, f"não é Windows ({sys.platform})"
    v = sys.getwindowsversion()
    nome = "Windows 11" if v.build >= 22000 else "Windows 10" if v.major == 10 else f"Windows {v.major}.{v.minor}"
    ed = _at_reg("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "DisplayVersion") or ""
    return AT_OK, f"{nome} {ed} (build {v.build})".replace("  ", " ")


def at_python():
    bits = "64 bits" if sys.maxsize > 2 ** 32 else "32 bits"
    modo = ".exe" if getattr(sys, "frozen", False) else "th_boost.py"
    st = AT_OK if sys.version_info >= (3, 9) else AT_AVISO
    return st, f"Python {sys.version.split()[0]} ({bits}), psutil {getattr(psutil, '__version__', '?')}, rodando como {modo}"


def at_admin():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    return (AT_OK, "sim") if e_admin() else (AT_ERRO, "NÃO — abra pelo atalho e clique em Sim quando o Windows pedir. Sem isso, plano de energia, serviços, RAM, overclock e FPS não funcionam.")


def at_pasta():
    pasta = pasta_do_programa()
    teste = os.path.join(pasta, f"th_boost_autoteste_{os.getpid()}.tmp")
    try:
        with open(teste, "w") as f:
            f.write("ok")
        os.remove(teste)
        return AT_OK, f"dá para gravar em {_at_anon(pasta)}"
    except OSError:
        return AT_ERRO, f"não dá para gravar em {_at_anon(pasta)}: configurações, backup e atualização não vão funcionar. Tire o Th Boost de dentro do ZIP ou de Arquivos de Programas."


def at_ram():
    m = psutil.virtual_memory()
    tot, livre = m.total / 2 ** 30, m.available / 2 ** 30
    txt = f"{_n(tot)} GB no total, {_n(livre)} GB livres agora ({100 - m.percent:.0f}%)"
    if tot < 7.5:
        return AT_AVISO, txt + ". Menos de 8 GB: jogos atuais vão travar por falta de memória (nenhum programa resolve isso; só mais RAM)."
    if m.percent > 85:
        return AT_AVISO, txt + ". Memória quase cheia: feche programas antes de jogar."
    return AT_OK, txt


def at_disco():
    raiz = (os.environ.get("SystemDrive", "C:") + "\\") if IS_WIN else "/"
    try:
        u = psutil.disk_usage(raiz)
    except OSError as e:
        return AT_ERRO, f"não consegui ler o disco {raiz}: {e}"
    livre_gb, pct = u.free / 2 ** 30, 100 * u.free / max(1, u.total)
    txt = f"{raiz} com {livre_gb:.0f} GB livres de {u.total / 2 ** 30:.0f} GB ({pct:.0f}%)"
    if livre_gb < 15 or pct < 10:
        return AT_AVISO, txt + ". Pouco espaço deixa o Windows e os jogos lentos: use a Limpeza ou apague jogos que não usa."
    return AT_OK, txt


def at_cpu():
    nome = (_at_reg("HKLM", r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString") or "").strip() if IS_WIN else ""
    f = None
    try:
        f = psutil.cpu_freq()
    except Exception:
        pass
    txt = f"{nome or 'processador'}: {psutil.cpu_count(logical=False) or '?'} núcleos / {psutil.cpu_count() or '?'} threads"
    if f and f.max:
        txt += f", {_n(f.current / 1000, 2)} GHz agora (máx. {_n(f.max / 1000, 2)} GHz)"
    return AT_OK, re.sub(r"\s+", " ", txt)


def at_energia():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    cod, saida = executar(["powercfg", "/getactivescheme"], timeout=15)
    if cod != 0:
        return AT_ERRO, "o comando powercfg não respondeu: os planos de energia e o Resfriamento não vão funcionar."
    m = re.search(r"\(([^)]+)\)", saida)
    txt = f"powercfg funciona; plano ativo: {m.group(1) if m else 'desconhecido'}"
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if b is not None and not b.power_plugged:
        return AT_AVISO, txt + f". Notebook NA BATERIA ({b.percent:.0f}%): na bateria o Windows segura o desempenho; para jogar, ligue na tomada."
    if b is not None:
        txt += f". Notebook na tomada ({b.percent:.0f}%)"
    return AT_OK, txt


def at_powershell():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    cod, saida = _at_ps("$PSVersionTable.PSVersion.ToString()", timeout=30)
    v = saida.strip().splitlines()[-1] if saida.strip() else ""
    if cod == 0 and re.match(r"\d+\.\d+", v):
        return AT_OK, f"PowerShell {v}"
    return AT_ERRO, "o PowerShell não respondeu (antivírus ou política da empresa?): muitas funções usam ele."


def at_registro():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    if REG is None:
        return AT_ERRO, "não consegui abrir o registro do Windows"
    gm = _at_reg("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled")
    dvr = _at_reg("HKCU", r"System\GameConfigStore", "GameDVR_Enabled")
    hags = _at_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode")
    partes = [f"Modo de Jogo {'ligado' if gm in (None, 1) else 'desligado'}",
              f"gravação em segundo plano (Game DVR) {'desligada' if dvr == 0 else 'ligada'}",
              f"agendamento de GPU por hardware {'ligado' if hags == 2 else 'desligado' if hags == 1 else 'padrão'}"]
    st = AT_OK if gm in (None, 1) and dvr == 0 else AT_AVISO
    return st, "registro lido; " + ", ".join(partes)


def at_servicos():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    cod, saida = executar(["sc", "query", "wuauserv"], timeout=15)
    if cod == 0 and "STATE" in saida.upper():
        return AT_OK, "dá para consultar os serviços do Windows"
    return AT_ERRO, "não consegui consultar os serviços (sc query): as páginas Serviços e Jogos podem falhar."


def at_gpu():
    if not IS_WIN:
        g = ler_gpu()
        return (AT_OK, f"NVIDIA {g['nome']}") if g else (AT_PULADO, "só no Windows")
    cod, saida = _at_ps("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,@{n='Data';e={$_.DriverDate.ToString('yyyy-MM-dd')}} | ConvertTo-Json -Compress", timeout=40)
    try:
        dados = json.loads(saida[saida.index("["):] if saida.lstrip().startswith("[") else saida[saida.index("{"):]) if cod == 0 else None
    except ValueError:
        dados = None
    if not dados:
        return AT_AVISO, "não consegui ler a placa de vídeo pelo Windows"
    if isinstance(dados, dict):
        dados = [dados]
    partes, velho = [], False
    for d in dados[:3]:
        nome = str(d.get("Name") or "?")
        data = str(d.get("Data") or "")
        partes.append(f"{nome} (driver {d.get('DriverVersion') or '?'}{', de ' + data if data else ''})")
        if re.match(r"\d{4}-\d{2}", data) and not re.search(r"basic|remote|virtual|parsec|meta", nome, re.I):
            idade = (datetime.now() - datetime.strptime(data[:7], "%Y-%m")).days
            velho = velho or idade > 365
    g = ler_gpu()
    txt = "; ".join(partes) + ("; nvidia-smi funciona" if g else "")
    if velho:
        return AT_AVISO, txt + ". Driver de vídeo com mais de 1 ano: atualizar pelo site da NVIDIA/AMD/Intel costuma melhorar jogos novos."
    return AT_OK, txt


def at_paginacao():
    """Arquivo de paginação desligado é uma causa comum de jogos fechando sozinhos e de travadas."""
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    cod, saida = _at_ps("$c=(Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile; "
                        "$n=@(Get-CimInstance Win32_PageFileUsage).Count; \"$c|$n\"", timeout=30)
    m = re.search(r"(True|False)\|(\d+)", saida or "", re.I) if cod == 0 else None
    if not m:
        return AT_AVISO, "não consegui ler o arquivo de paginação"
    auto, qtd = m.group(1).lower() == "true", int(m.group(2))
    if auto:
        return AT_OK, "arquivo de paginação no automático (o Windows cuida do tamanho)"
    if qtd == 0:
        return AT_ERRO, ("arquivo de paginação DESLIGADO: jogos podem fechar sozinhos e travar quando a memória enche. "
                         "Toque em Corrigir para voltar ao automático (vale depois de reiniciar)."), "pagefile_auto"
    return AT_OK, "arquivo de paginação com tamanho escolhido à mão (funciona; o automático costuma ser melhor)"


def at_tela():
    if not IS_WIN:
        return AT_PULADO, "só no Windows"
    m = info_monitor()
    if not m:
        return AT_AVISO, "não consegui ler o monitor"
    txt = f"{m['res']} a {m['hz']} Hz"
    if m["hz"] <= 60 and m["hz_max"] >= 100:
        return AT_AVISO, (txt + f". O Windows diz que a tela aceita até {m['hz_max']} Hz: confira em Configurações > Sistema > "
                          "Tela > Tela avançada > Taxa de atualização (e se o cabo é HDMI 2.0/DisplayPort).")
    return AT_OK, txt


def at_fps():
    if caminho_presentmon():
        return AT_OK, "PresentMon.exe encontrado: o contador de FPS funciona"
    return AT_AVISO, "PresentMon.exe não está na pasta do Th Boost: o contador de FPS fica desligado (o resto funciona)."


def at_temperatura():
    if not IS_WIN:
        t = temp_cpu()
        return (AT_OK, f"{t:.0f} °C") if t else (AT_PULADO, "só no Windows")
    cod, saida = _at_ps("Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop | Select-Object -ExpandProperty CurrentTemperature", timeout=30)
    nums = [int(x) for x in re.findall(r"^\s*(\d{3,5})\s*$", saida, re.M)] if cod == 0 else []
    temps = [round(n / 10 - 273.15) for n in nums if 2731 < n < 3982]
    if not temps:
        return AT_AVISO, "este computador não informa a temperatura para o Windows (comum). A temperatura da CPU só aparece com programas do fabricante."
    t = max(temps)
    st = AT_AVISO if t >= 90 else AT_OK
    return st, f"sensor de temperatura do Windows: {t} °C" + (" — quente: limpe as saídas de ar e use o Resfriamento." if t >= 90 else "")


def at_internet():
    p = medir_ping()
    try:
        import socket
        socket.getaddrinfo("github.com", 443)
        dns = True
    except OSError:
        dns = False
    if p is None and not dns:
        return AT_ERRO, "sem internet (o ping e o DNS falharam)"
    txt = f"ping {p:.0f} ms" if p is not None else "ping bloqueado (DNS funciona)"
    if p is not None and p > 120:
        return AT_AVISO, txt + ": alto para jogos online (Wi-Fi fraco? prefira cabo)"
    return AT_OK, txt + ("" if dns else "; DNS falhou")


def at_atualizacao():
    try:
        info = atu_buscar_info()
    except Exception:
        return AT_AVISO, "não consegui ler o aviso de versão nova no GitHub (internet ou bloqueio)"
    if atu_mais_nova(info["versao"], VERSAO):
        return AT_AVISO, f"tem versão nova: {info['versao']} (você está na {VERSAO})"
    return AT_OK, f"em dia ({VERSAO})"


AT_LISTA = [
    ("sistema", "Sistema", "Windows", at_sistema),
    ("python", "Sistema", "Python e psutil", at_python),
    ("admin", "Sistema", "Administrador", at_admin),
    ("pasta", "Sistema", "Pasta do programa", at_pasta),
    ("cpu", "Peças", "Processador", at_cpu),
    ("ram", "Peças", "Memória RAM", at_ram),
    ("disco", "Peças", "Espaço no disco", at_disco),
    ("gpu", "Peças", "Placa de vídeo e driver", at_gpu),
    ("temp", "Peças", "Temperatura", at_temperatura),
    ("tela", "Peças", "Monitor", at_tela),
    ("paginacao", "Funções", "Arquivo de paginação", at_paginacao),
    ("energia", "Funções", "Energia / Resfriamento (powercfg)", at_energia),
    ("ps", "Funções", "PowerShell", at_powershell),
    ("reg", "Funções", "Registro (ajustes do Windows)", at_registro),
    ("svc", "Funções", "Serviços do Windows", at_servicos),
    ("fps", "Funções", "Contador de FPS", at_fps),
    ("net", "Internet", "Internet e ping", at_internet),
    ("atu", "Internet", "Aviso de versão nova", at_atualizacao),
]


AT_ACOES = {"pagefile_auto": "Corrigir"}


def pagefile_automatico():
    """Volta o arquivo de paginação para o automático do Windows (vale depois de reiniciar)."""
    if not IS_WIN:
        return "Só funciona no Windows."
    if not e_admin():
        return "Precisa de Administrador. Feche e abra o Th Boost pelo atalho."
    cod, _ = _at_ps("$c=Get-CimInstance Win32_ComputerSystem; Set-CimInstance -InputObject $c -Property @{AutomaticManagedPagefile=$true}",
                    timeout=60)
    return ("Arquivo de paginação no automático. Reinicie o PC para valer." if cod == 0
            else "O Windows não aceitou mudar o arquivo de paginação.")


class AutotesteMixin:
    def at_iniciar_estado(self):
        self.at = {"estado": "nunca", "itens": [], "inicio": 0, "fim": 0, "texto": ""}

    def at_snapshot(self):
        return {"estado": self.at["estado"], "itens": [dict(i) for i in self.at["itens"]], "fim": self.at["fim"]}

    def at_texto(self):
        return self.at["texto"]

    def at_rodar(self):
        if self.at["estado"] == "rodando":
            return
        itens = [{"id": i, "grupo": g, "rotulo": r, "st": "esperando", "txt": "", "acao": ""} for i, g, r, _ in AT_LISTA]
        self.at.update(estado="rodando", itens=itens, inicio=time.time(), fim=0, texto="")

        def tarefa():
            for item, (_, _, _, fn) in zip(itens, AT_LISTA):
                item["st"] = "testando"
                acao = ""
                try:
                    r = fn()
                    st, txt = r[0], r[1]
                    acao = r[2] if len(r) > 2 and r[2] in AT_ACOES else ""
                except Exception as e:  # um teste quebrado não derruba os outros
                    st, txt = AT_ERRO, f"o teste falhou: {type(e).__name__}"
                item.update(st=st, txt=_at_anon(txt), acao=acao)
            jogos = {}
            for j in getattr(self, "jogos", []):
                jogos[j.get("origem", "?")] = jogos.get(j.get("origem", "?"), 0) + 1
            marca = {AT_OK: "OK   ", AT_AVISO: "AVISO", AT_ERRO: "ERRO ", AT_PULADO: "--   "}
            linhas = [f"Th Boost {VERSAO} - Autoteste - {datetime.now():%d/%m/%Y %H:%M}", ""]
            grupo = None
            for i in itens:
                if i["grupo"] != grupo:
                    grupo = i["grupo"]
                    linhas.append(f"[{grupo}]")
                linhas.append(f"{marca.get(i['st'], i['st'])} {i['rotulo']}: {i['txt']}")
            linhas += ["", f"Jogos encontrados: {sum(jogos.values())}" + (" (" + ", ".join(f"{k}: {v}" for k, v in sorted(jogos.items())) + ")" if jogos else ""),
                       f"Segundo plano: {'ligado' if CONFIG.get('segundo_plano') else 'desligado'}",
                       f"Resumo: {sum(1 for i in itens if i['st'] == AT_OK)} ok, {sum(1 for i in itens if i['st'] == AT_AVISO)} aviso(s), {sum(1 for i in itens if i['st'] == AT_ERRO)} erro(s)"]
            self.at.update(estado="pronto", fim=time.time(), texto="\n".join(linhas))
            erros = sum(1 for i in itens if i["st"] == AT_ERRO)
            self.msg("Autoteste pronto: " + ("tudo certo." if not erros else f"{erros} problema(s) encontrado(s). Veja em Configurações › Autoteste."))

        threading.Thread(target=tarefa, daemon=True).start()
