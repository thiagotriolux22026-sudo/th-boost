

# ---------------- ajustes do Windows (reversíveis, com backup do valor original) ----------------

try:
    import winreg
except ImportError:  # fora do Windows
    winreg = None


class Registro:
    """Camada fina sobre o registro do Windows (nos testes é trocada por uma versão falsa)."""

    def _raiz(self, nome):
        return winreg.HKEY_CURRENT_USER if nome == "HKCU" else winreg.HKEY_LOCAL_MACHINE

    def _abrir(self, raiz, caminho, acesso):
        return winreg.OpenKey(self._raiz(raiz), caminho, 0, acesso | winreg.KEY_WOW64_64KEY)

    def ler(self, raiz, caminho, nome):
        try:
            with self._abrir(raiz, caminho, winreg.KEY_READ) as chave:
                return winreg.QueryValueEx(chave, nome)[0]
        except OSError:
            return None

    def escrever(self, raiz, caminho, nome, valor, tipo):
        tipos = {"dword": winreg.REG_DWORD, "sz": winreg.REG_SZ, "bin": winreg.REG_BINARY}
        with winreg.CreateKeyEx(self._raiz(raiz), caminho, 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as chave:
            winreg.SetValueEx(chave, nome, 0, tipos[tipo], valor)

    def apagar(self, raiz, caminho, nome):
        try:
            with self._abrir(raiz, caminho, winreg.KEY_SET_VALUE) as chave:
                winreg.DeleteValue(chave, nome)
        except OSError:
            pass

    def valores(self, raiz, caminho):
        """Lista de (nome, valor) de uma chave. Vazia se a chave não existe."""
        itens = []
        try:
            with self._abrir(raiz, caminho, winreg.KEY_READ) as chave:
                i = 0
                while True:
                    try:
                        nome, valor, _ = winreg.EnumValue(chave, i)
                    except OSError:
                        break
                    itens.append((nome, valor))
                    i += 1
        except OSError:
            pass
        return itens

    def subchaves(self, raiz, caminho):
        nomes = []
        try:
            with self._abrir(raiz, caminho, winreg.KEY_READ) as chave:
                i = 0
                while True:
                    try:
                        nomes.append(winreg.EnumKey(chave, i))
                    except OSError:
                        break
                    i += 1
        except OSError:
            pass
        return nomes

    def existe(self, raiz, caminho):
        try:
            with self._abrir(raiz, caminho, winreg.KEY_READ):
                return True
        except OSError:
            return False


REG = Registro() if winreg else None
ARQ_BACKUP = os.path.join(pasta_do_programa(), "ajustes_backup.json")
TRAVA_AJ = threading.RLock()
_BACKUP = None


def _backup():
    global _BACKUP
    if _BACKUP is None:
        try:
            with open(ARQ_BACKUP, encoding="utf-8") as f:
                _BACKUP = json.load(f)
        except (OSError, ValueError):
            _BACKUP = {}
    return _BACKUP


def _guardar_backup():
    try:
        with open(ARQ_BACKUP, "w", encoding="utf-8") as f:
            json.dump(_BACKUP or {}, f, ensure_ascii=False, indent=1)
    except OSError:
        pass  # sem permissão de escrita: o backup fica só na memória desta execução


def _para_json(valor):
    return {"hex": valor.hex()} if isinstance(valor, (bytes, bytearray)) else valor


def _de_json(valor):
    return bytes.fromhex(valor["hex"]) if isinstance(valor, dict) and "hex" in valor else valor


def powershell(script, tempo=60):
    return executar(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-Command", script], timeout=tempo)


class Ajuste:
    """Base: um ajuste que se liga e se desfaz. estado(): True ligado, False desligado, None indisponível."""
    precisa_admin = True

    def __init__(self, id, grupo, titulo, desc, risco="baixo", rec=False, nota="", ext=False, sup=False, so_mesa=False, fps=False):
        self.id, self.grupo, self.titulo, self.desc = id, grupo, titulo, desc
        self.risco, self.rec, self.nota = risco, rec, nota
        self.ext = ext  # entra na Otimização Extrema (além dos recomendados)
        self.sup = sup  # entra só na Otimização Suprema (acima da Extrema)
        self.so_mesa = so_mesa  # não é aplicado sozinho em notebook (gasta bateria)
        self.fps = fps  # aparece na lista "Ajustes de FPS" da página Jogos

    def estado(self):
        return None

    def ligar(self):
        raise NotImplementedError

    def desligar(self):
        raise NotImplementedError

    def disponivel(self):
        return REG is not None

    def info(self):
        return {"id": self.id, "grupo": self.grupo, "titulo": self.titulo, "desc": self.desc,
                "risco": self.risco, "rec": self.rec, "ext": self.ext, "sup": self.sup, "fps": self.fps, "nota": self.nota,
                "admin": self.precisa_admin}


class AjusteReg(Ajuste):
    """Valores do registro. Cada item: (raiz, caminho, nome, tipo, valor_ligado, valor_padrao_do_windows)."""

    def __init__(self, id, grupo, titulo, desc, itens, depois=None, **kw):
        super().__init__(id, grupo, titulo, desc, **kw)
        self.itens = itens
        self.depois = depois
        self.precisa_admin = any(i[0] == "HKLM" for i in itens)

    def estado(self):
        if REG is None:
            return None
        for raiz, caminho, nome, tipo, ligado, _ in self.itens:
            atual = REG.ler(raiz, caminho, nome)
            if atual is None or str(atual) != str(ligado):
                return False
        return True

    def ligar(self):
        with TRAVA_AJ:
            bk = _backup()
            if self.id not in bk and not self.estado():  # guarda como estava antes de mexer
                bk[self.id] = [[r, c, n, t, _para_json(REG.ler(r, c, n))] for r, c, n, t, _, _ in self.itens]
                _guardar_backup()
            for raiz, caminho, nome, tipo, ligado, _ in self.itens:
                REG.escrever(raiz, caminho, nome, ligado, tipo)
        if self.depois:
            self.depois(True)

    def desligar(self):
        with TRAVA_AJ:
            bk = _backup()
            antigos = {(r, c, n): _de_json(v) for r, c, n, t, v in bk.get(self.id, [])}
            tem_backup = self.id in bk
            for raiz, caminho, nome, tipo, _, padrao in self.itens:
                valor = antigos.get((raiz, caminho, nome)) if tem_backup else padrao
                if valor is None:
                    REG.apagar(raiz, caminho, nome)
                else:
                    REG.escrever(raiz, caminho, nome, valor, tipo)
            if tem_backup:
                del bk[self.id]
                _guardar_backup()
        if self.depois:
            self.depois(False)


class AjusteServico(Ajuste):
    """Desliga serviços do Windows (início 'desativado'). Desfazer devolve o tipo de início de antes."""
    CHAVE = r"SYSTEM\CurrentControlSet\Services\%s"

    def __init__(self, id, grupo, titulo, desc, servicos, padroes=None, **kw):
        super().__init__(id, grupo, titulo, desc, **kw)
        self.servicos = servicos if isinstance(servicos, (list, tuple)) else [servicos]
        self.padroes = padroes or {}  # início padrão do Windows por serviço: (tipo, atrasado). Se faltar: manual

    def _existentes(self):
        return [s for s in self.servicos if REG is not None and REG.existe("HKLM", self.CHAVE % s)]

    def disponivel(self):
        return bool(self._existentes())

    def estado(self):
        lista = self._existentes()
        if not lista:
            return None
        return all(REG.ler("HKLM", self.CHAVE % s, "Start") == 4 for s in lista)

    def rodando(self):
        """Serviços deste ajuste que estão rodando agora (desligar o início não para quem já está rodando)."""
        res = []
        for s in self._existentes():
            try:
                if psutil.win_service_get(s).status() == "running":
                    res.append(s)
            except Exception:
                continue
        return res

    def parar_agora(self):
        """Para os serviços que seguem rodando. Devolve quantos o Windows aceitou parar."""
        n = 0
        for s in self.rodando():
            cod, _ = executar(["sc", "stop", s])
            n += 1 if cod == 0 else 0
        return n

    def ligar(self):
        with TRAVA_AJ:
            bk = _backup()
            if self.id not in bk and not self.estado():
                bk[self.id] = {s: [REG.ler("HKLM", self.CHAVE % s, "Start"),
                                   REG.ler("HKLM", self.CHAVE % s, "DelayedAutostart")] for s in self._existentes()}
                _guardar_backup()
        for s in self._existentes():
            executar(["sc", "config", s, "start=", "disabled"])
            executar(["sc", "stop", s])

    def desligar(self):
        with TRAVA_AJ:
            bk = _backup()
            antigos = bk.get(self.id, {})
        for s in self._existentes():
            inicio, atrasado = antigos.get(s) or self.padroes.get(s, (3, None))
            if inicio is None:
                inicio, atrasado = self.padroes.get(s, (3, None))
            if inicio == 2:
                modo = "delayed-auto" if atrasado == 1 else "auto"
            elif inicio == 4:
                modo = "disabled"
            else:
                modo = "demand"
            executar(["sc", "config", s, "start=", modo])
            if inicio == 2:
                executar(["sc", "start", s])
        with TRAVA_AJ:
            if self.id in _backup():
                del _backup()[self.id]
                _guardar_backup()


class AjusteHibernacao(Ajuste):
    def estado(self):
        if REG is None:
            return None
        atual = REG.ler("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "HibernateEnabled")
        return None if atual is None else atual == 0

    def ligar(self):
        executar(["powercfg", "/hibernate", "off"])

    def desligar(self):
        executar(["powercfg", "/hibernate", "on"])


class AjusteNagle(Ajuste):
    """Desliga o algoritmo de Nagle nas placas de rede que estão em uso (menos latência em jogos online)."""
    BASE = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"

    def _em_uso(self):
        usadas = []
        for guid in REG.subchaves("HKLM", self.BASE):
            caminho = self.BASE + "\\" + guid
            for campo in ("DhcpIPAddress", "IPAddress"):
                v = REG.ler("HKLM", caminho, campo)
                lista = v if isinstance(v, (list, tuple)) else [v]
                if any(isinstance(x, str) and x.strip() and not x.startswith("0.0.0.0") for x in lista):
                    usadas.append(caminho)
                    break
        return usadas

    def estado(self):
        if REG is None:
            return None
        placas = self._em_uso()
        if not placas:
            return None
        return all(REG.ler("HKLM", c, "TcpAckFrequency") == 1 and REG.ler("HKLM", c, "TCPNoDelay") == 1
                   for c in placas)

    def ligar(self):
        for c in self._em_uso():
            REG.escrever("HKLM", c, "TcpAckFrequency", 1, "dword")
            REG.escrever("HKLM", c, "TCPNoDelay", 1, "dword")

    def desligar(self):
        for guid in REG.subchaves("HKLM", self.BASE):
            for nome in ("TcpAckFrequency", "TCPNoDelay"):
                REG.apagar("HKLM", self.BASE + "\\" + guid, nome)


class AjusteTarefas(Ajuste):
    """Desliga tarefas agendadas de telemetria, que acordam o disco e o processador em segundo plano.
    Perguntar o estado de cada tarefa ao Windows é lento, então o Th Boost lembra quais ele mesmo desligou."""

    def __init__(self, id, grupo, titulo, desc, tarefas, **kw):
        super().__init__(id, grupo, titulo, desc, **kw)
        self.tarefas = tarefas

    def estado(self):
        if REG is None:
            return None
        return bool(_backup().get(self.id))

    def ligar(self):
        feitas = []
        for t in self.tarefas:
            cod, _ = executar(["schtasks", "/Change", "/TN", t, "/Disable"])
            if cod == 0:
                feitas.append(t)
        if feitas:
            with TRAVA_AJ:
                _backup()[self.id] = feitas
                _guardar_backup()

    def desligar(self):
        with TRAVA_AJ:
            feitas = list(_backup().get(self.id) or [])
        for t in feitas:
            executar(["schtasks", "/Change", "/TN", t, "/Enable"])
        with TRAVA_AJ:
            _backup().pop(self.id, None)
            _guardar_backup()


class AjusteMemoriaComprimida(Ajuste):
    """Desliga a compressão de memória do Windows. Só faz sentido com bastante RAM (16 GB ou mais): o processador
    deixa de gastar tempo comprimindo páginas. Como o estado vem do PowerShell (lento), o Th Boost lembra o que ele mesmo mudou."""

    def disponivel(self):
        return REG is not None and psutil.virtual_memory().total >= 15 * 1024 ** 3

    def estado(self):
        if REG is None:
            return None
        return bool(_backup().get(self.id))

    def ligar(self):
        cod, _ = powershell("Disable-MMAgent -MemoryCompression", tempo=40)
        if cod == 0:
            with TRAVA_AJ:
                _backup()[self.id] = True
                _guardar_backup()

    def desligar(self):
        powershell("Enable-MMAgent -MemoryCompression", tempo=40)
        with TRAVA_AJ:
            _backup().pop(self.id, None)
            _guardar_backup()


# ---- mouse: aplica na hora, sem precisar sair do Windows ----

def _aplicar_aceleracao(desligada):
    if not IS_WIN:
        return
    try:
        valores = (ctypes.c_int * 3)(*((0, 0, 0) if desligada else (6, 10, 1)))
        ctypes.windll.user32.SystemParametersInfoW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        ctypes.windll.user32.SystemParametersInfoW(0x0004, 0, ctypes.byref(valores), 3)  # SPI_SETMOUSE
    except Exception:
        pass


def definir_velocidade_mouse(v):
    """Velocidade do ponteiro de 1 a 20 (10 é o padrão do Windows, o '6/11' do painel)."""
    v = max(1, min(20, int(v)))
    REG.escrever("HKCU", r"Control Panel\Mouse", "MouseSensitivity", str(v), "sz")
    if IS_WIN:
        try:
            ctypes.windll.user32.SystemParametersInfoW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            ctypes.windll.user32.SystemParametersInfoW(0x0071, 0, ctypes.c_void_p(v), 3)  # SPI_SETMOUSESPEED
        except Exception:
            pass
    return v


def velocidade_mouse():
    if REG is None:
        return None
    try:
        return int(REG.ler("HKCU", r"Control Panel\Mouse", "MouseSensitivity") or 10)
    except (TypeError, ValueError):
        return 10


# ---------------- catálogo ----------------

SP = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"


def _montar_catalogo():
    c = []
    R = AjusteReg
    # ----- Windows -----
    c += [
        R("game_dvr", "windows", "Gravação em segundo plano desligada",
          "Para a captura automática de vídeo do Windows (Game DVR), que gasta CPU e GPU enquanto você joga.",
          [("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", "dword", 0, 1),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "dword", 0, 1)], rec=True),
        R("transparencia", "windows", "Transparência desligada",
          "Tira o efeito de vidro do menu e da barra de tarefas. Alivia a placa de vídeo em computadores fracos.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", "dword", 0, 1)], rec=True),
        R("animacoes", "windows", "Animações de janelas e da barra desligadas",
          "Janelas abrem e fecham na hora, sem efeito de movimento.",
          [("HKCU", r"Control Panel\Desktop\WindowMetrics", "MinAnimate", "sz", "0", "1"),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", "dword", 0, 1)],
          rec=True, nota="Vale ao entrar de novo no Windows."),
        R("menus_rapidos", "windows", "Menus instantâneos",
          "Tira o atraso de meio segundo para abrir os menus.",
          [("HKCU", r"Control Panel\Desktop", "MenuShowDelay", "sz", "0", "400")], rec=True),
        R("prioridade_jogos", "windows", "Prioridade máxima para jogos",
          "Diz ao Windows para dar mais tempo de processador aos jogos (ajuste MMCSS).",
          [("HKLM", SP + r"\Tasks\Games", "Priority", "dword", 6, 2),
           ("HKLM", SP + r"\Tasks\Games", "Scheduling Category", "sz", "High", "Medium"),
           ("HKLM", SP + r"\Tasks\Games", "SFIO Priority", "sz", "High", "Normal")], rec=True),
        R("desligar_rapido", "windows", "Desligar o Windows mais rápido",
          "Reduz a espera para fechar programas travados ao desligar ou reiniciar.",
          [("HKCU", r"Control Panel\Desktop", "WaitToKillAppTimeout", "sz", "5000", None),
           ("HKCU", r"Control Panel\Desktop", "HungAppTimeout", "sz", "2000", None)], rec=True),
        R("extensoes", "windows", "Mostrar a extensão dos arquivos",
          "Mostra o .exe, .pdf, .jpg no nome dos arquivos. Ajuda a perceber arquivos disfarçados.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "HideFileExt", "dword", 0, 1)]),
        R("hags", "windows", "Agendamento de GPU por hardware",
          "Deixa a placa de vídeo gerenciar a própria memória. Ajuda em algumas placas e atrapalha em outras.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", "dword", 2, 1)],
          risco="medio", nota="Precisa reiniciar o PC."),
        R("efeitos_visuais", "windows", "Efeitos visuais no mínimo",
          "Arrastar janelas sem sombra, seleção sem transição e sem a prévia ao passar o mouse na barra de tarefas. Menos trabalho para o processador e a placa de vídeo.",
          [("HKCU", r"Control Panel\Desktop", "DragFullWindows", "sz", "0", "1"),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ListviewAlphaSelect", "dword", 0, 1),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ListviewShadow", "dword", 0, 1),
           ("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", "dword", 0, 1)],
          ext=True, nota="Vale ao entrar de novo no Windows."),
        R("fundo_apps", "windows", "Apps da Loja parados em segundo plano",
          "Impede que Email, Clima, Notícias e outros apps da Microsoft Store rodem escondidos. Eles só atualizam quando você abre.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", "dword", 1, 0),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BackgroundAppGlobalToggle", "dword", 0, 1)],
          ext=True, nota="Notificações desses apps só chegam com eles abertos."),
        R("inicio_sem_atraso", "windows", "Programas de início sem espera",
          "O Windows espera alguns segundos antes de abrir os programas da inicialização. Isto tira essa espera.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec", "dword", 0, None)],
          ext=True, nota="Vale ao entrar de novo no Windows."),
        R("desligar_servicos", "windows", "Serviços fecham mais rápido ao desligar",
          "Dá 2 segundos (em vez de 5) para cada serviço terminar quando o PC desliga ou reinicia.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control", "WaitToKillServiceTimeout", "sz", "2000", None)],
          ext=True, nota="Vale no próximo desligamento."),
        R("ntfs_acesso", "windows", "Disco com menos gravações",
          "O Windows anota a hora em que cada arquivo foi aberto, e isso gera gravações extras no disco o tempo todo. Isto desliga essa anotação.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisableLastAccessUpdate", "dword", 1, 2147483650)],
          ext=True, nota="Vale depois de reiniciar."),
        R("modo_jogo", "windows", "Modo de Jogo do Windows ligado",
          "Pede ao Windows para deixar o jogo em primeiro lugar e adiar atualizações e tarefas enquanto você joga.",
          [("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode", "dword", 1, None),
           ("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", "dword", 1, None)], ext=True),
        R("visual_minimo", "windows", "Visual do Windows no modo desempenho",
          "Liga o “Ajustar para obter o melhor desempenho” do Windows: sem fade de menus, sem rolagem suave e sem sombra no ponteiro. O Windows fica mais seco, porém mais ágil, sobretudo em PCs fracos.",
          [("HKCU", r"Control Panel\Desktop", "UserPreferencesMask", "bin", bytes.fromhex("9012038010000000"), bytes.fromhex("9e3e078012000000"))],
          sup=True, nota="Vale ao entrar de novo no Windows."),
        AjusteMemoriaComprimida("mmagent", "windows", "Compressão de memória desligada",
                                "Com 16 GB de RAM ou mais, o Windows não precisa comprimir a memória, e o processador fica livre para o jogo. Só aparece em PCs com bastante memória.",
                                sup=True, nota="Vale depois de reiniciar o PC."),
        R("widgets", "windows", "Widgets e Chat da barra de tarefas desligados",
          "Tira os Widgets (clima e notícias) e o ícone de Chat, que mantêm processos rodando. Só tem efeito no Windows 11.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarDa", "dword", 0, 1),
           ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarMn", "dword", 0, 1)],
          ext=True, nota="Em algumas versões do Windows 11 o próprio Windows bloqueia esta mudança."),
    ]
    # ----- Energia -----
    c += [
        AjusteHibernacao("hibernacao", "energia", "Hibernação desligada",
                         "Apaga o arquivo de hibernação e libera vários GB no disco. A suspensão continua funcionando."),
        R("inicio_rapido", "energia", "Inicialização rápida do Windows desligada",
          "Faz o desligar ser completo. Resolve lentidão e travamentos que só passam ao reiniciar.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", "dword", 0, 1)],
          nota="Vale no próximo desligamento."),
    ]
    # ----- Mouse e teclado -----
    c += [
        R("mouse_acel", "mouse", "Aceleração do ponteiro desligada",
          "Tira o 'Aprimorar precisão do ponteiro'. O mouse anda sempre a mesma distância, ideal para mira em jogos.",
          [("HKCU", r"Control Panel\Mouse", "MouseSpeed", "sz", "0", "1"),
           ("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "sz", "0", "6"),
           ("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "sz", "0", "10")],
          depois=lambda ligado: _aplicar_aceleracao(ligado), rec=True),
        R("teclas_aderencia", "mouse", "Avisos de acessibilidade desligados",
          "Acaba com a janelinha de Teclas de Aderência que aparece ao apertar Shift 5 vezes no meio do jogo.",
          [("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", "sz", "506", "510"),
           ("HKCU", r"Control Panel\Accessibility\Keyboard Response", "Flags", "sz", "122", "126"),
           ("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", "sz", "58", "62")], rec=True),
        R("teclado_rapido", "mouse", "Repetição de teclas mais rápida",
          "O teclado começa a repetir a letra segurada sem esperar.",
          [("HKCU", r"Control Panel\Keyboard", "KeyboardDelay", "sz", "0", "1")],
          ext=True, nota="Vale ao entrar de novo no Windows."),
    ]
    # ----- Serviços -----
    S = AjusteServico
    c += [
        S("svc_diagtrack", "servicos", "Telemetria (DiagTrack)", "Envia dados de uso para a Microsoft o tempo todo.", "DiagTrack", padroes={"DiagTrack": (2, None)}, rec=True),
        S("svc_dmwappush", "servicos", "Mensagens push da telemetria", "Serviço auxiliar da telemetria.", "dmwappushservice", rec=True),
        S("svc_wersvc", "servicos", "Relatório de erros do Windows", "Prepara e envia relatórios quando um programa fecha com erro.", "WerSvc", rec=True),
        S("svc_mapsbroker", "servicos", "Mapas baixados", "Atualiza mapas offline que quase ninguém usa.", "MapsBroker", padroes={"MapsBroker": (2, 1)}, rec=True),
        S("svc_retaildemo", "servicos", "Modo demonstração de loja", "Só serve para computadores de vitrine.", "RetailDemoService", rec=True),
        S("svc_wmpnetwork", "servicos", "Compartilhamento do Media Player", "Compartilha músicas e vídeos pela rede.", "WMPNetworkSvc", rec=True),
        S("svc_fax", "servicos", "Fax", "Serviço de fax, sem uso hoje em dia.", "Fax", rec=True),
        S("svc_sysmain", "servicos", "Superfetch (SysMain)",
          "Pré-carrega programas na memória. Em SSD quase não ajuda e consome disco e RAM. Em HD mecânico, deixe ligado.", "SysMain", padroes={"SysMain": (2, None)}),
        S("svc_dosvc", "servicos", "Entrega de atualizações para outros PCs (DoSvc)",
          "Usa sua internet e seu disco para repassar atualizações do Windows a outros computadores. As suas atualizações continuam chegando normalmente.",
          "DoSvc", padroes={"DoSvc": (2, 1)}, ext=True),
        S("svc_trkwks", "servicos", "Rastreamento de atalhos (TrkWks)",
          "Procura arquivos que mudaram de lugar na rede para consertar atalhos. Quase ninguém usa.", "TrkWks", padroes={"TrkWks": (2, None)}, ext=True),
        S("svc_pcasvc", "servicos", "Assistente de compatibilidade (PcaSvc)",
          "Monitora programas antigos para sugerir ajustes de compatibilidade. Sem ele, o aviso de 'este programa pode não funcionar' deixa de aparecer.",
          "PcaSvc", padroes={"PcaSvc": (2, None)}, ext=True),
        S("svc_diaghub", "servicos", "Coletor de diagnóstico", "Coleta dados técnicos para ferramentas de diagnóstico do Windows.",
          "diagnosticshub.standardcollector.service", ext=True),
        S("svc_raros", "servicos", "Serviços que quase ninguém usa",
          "Telefone, carteira digital, roteador AllJoyn, pagamentos por aproximação, Windows Insider, registro remoto, descoberta de rede (LLTD) e o painel de relatórios de erro. Nenhum deles faz falta num PC de jogo.",
          ["PhoneSvc", "WalletService", "AJRouter", "SEMgrSvc", "wisvc", "RemoteRegistry", "lltdsvc", "wercplsupport"],
          padroes={"RemoteRegistry": (4, None)}, sup=True),
        S("svc_lfsvc", "servicos", "Localização", "Desliga o serviço de localização do Windows.", "lfsvc"),
        S("svc_wsearch", "servicos", "Pesquisa do Windows (indexação)",
          "Para de indexar os arquivos. Alivia o disco, mas a busca do Iniciar fica mais lenta.", "WSearch", padroes={"WSearch": (2, 1)}, risco="medio"),
        S("svc_spooler", "servicos", "Impressão (Spooler)",
          "Só desligue se você não usa impressora. Ligado de novo, volta a imprimir.", "Spooler", padroes={"Spooler": (2, None)}, risco="medio"),
        S("svc_tablet", "servicos", "Teclado de toque e caneta",
          "Desliga o teclado virtual e a caneta. Não use em tablets e notebooks com tela de toque.", "TabletInputService", risco="medio"),
        S("svc_xbox", "servicos", "Serviços do Xbox",
          "Quebra o login do Xbox e do Game Pass e o salvamento na nuvem de alguns jogos. Só desligue se não usa.",
          ["XblAuthManager", "XblGameSave", "XboxNetApiSvc", "XboxGipSvc"], risco="medio"),
        S("svc_usuario", "servicos", "Serviços por usuário (contas, contatos e sincronização)",
          "O Windows cria uma cópia de vários serviços para cada usuário (sincronização de contas, contatos, mensagens e dispositivos conectados), e cada cópia vira um processo. Desligados, o app Email e Calendário do Windows deixa de sincronizar sozinho.",
          ["OneSyncSvc", "CDPUserSvc", "CDPSvc", "UnistoreSvc", "UserDataSvc", "PimIndexMaintenanceSvc", "MessagingService", "BcastDVRUserService"],
          padroes={"OneSyncSvc": (2, None), "CDPUserSvc": (2, None), "CDPSvc": (2, None)}, sup=True,
          nota="Os processos por usuário só somem depois de reiniciar o PC."),
        S("svc_ssdp", "servicos", "Descoberta de aparelhos na rede (SSDP e UPnP)",
          "Faz o PC procurar e anunciar TVs, caixas de som e impressoras na rede. Desligado, a internet funciona igual; só deixa de aparecer para aparelhos que usam DLNA ou UPnP.",
          ["SSDPSRV", "upnphost"], sup=True),
        S("svc_bluetooth", "servicos", "Bluetooth",
          "Só desligue se não usa fone, mouse, teclado ou controle por Bluetooth. Ligado de novo, volta a funcionar.", ["bthserv", "BthAvctpSvc"], risco="medio"),
        S("svc_biometria", "servicos", "Impressão digital e reconhecimento facial (Windows Hello)",
          "Só desligue se não entra no Windows com digital ou rosto.", "WbioSrvc", risco="medio"),
        S("svc_server", "servicos", "Compartilhamento de pastas com a rede (Servidor)",
          "Só desligue se você não compartilha pastas nem impressoras com outros computadores. Os acessos que você faz a outros PCs continuam funcionando.",
          "LanmanServer", padroes={"LanmanServer": (2, None)}, risco="medio"),
        R("svc_juntar", "servicos", "Juntar os serviços do Windows em menos processos",
          "Desde o Windows 10 cada serviço roda em um processo svchost separado quando o PC tem mais de 3,5 GB de memória. Isto volta ao método antigo, com vários serviços por processo: a lista de processos fica bem menor. O ganho de memória é pequeno, e se um serviço travar pode derrubar os que dividem o processo com ele.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control", "SvcHostSplitThresholdInKB", "dword", 268435456, 3670016)],
          risco="medio", nota="Precisa reiniciar o PC. Dá para desfazer aqui."),
    ]
    # ----- Privacidade -----
    DC = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    cdm = [("HKCU", CDM, n, "dword", 0, 1) for n in (
        "SubscribedContent-338388Enabled", "SubscribedContent-338389Enabled", "SubscribedContent-353694Enabled",
        "SubscribedContent-353696Enabled", "SubscribedContent-310093Enabled", "SubscribedContent-338393Enabled",
        "SilentInstalledAppsEnabled", "SystemPaneSuggestionsEnabled", "SoftLandingEnabled")]
    c += [
        R("p_telemetria", "privacidade", "Telemetria no mínimo",
          "Pede ao Windows para enviar o mínimo de dados à Microsoft. No Windows Home o mínimo possível ainda é enviado.",
          [("HKLM", DC, "AllowTelemetry", "dword", 0, None)], rec=True),
        R("p_anuncio_id", "privacidade", "ID de publicidade desligado",
          "Impede que os apps usem um número seu para mostrar anúncios personalizados.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", "dword", 0, 1)], rec=True),
        R("p_historico", "privacidade", "Histórico de atividades desligado",
          "Para de guardar e enviar o histórico do que você abre e faz no computador.",
          [("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed", "dword", 0, None),
           ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", "dword", 0, None),
           ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "UploadUserActivities", "dword", 0, None)], rec=True),
        R("p_sugestoes", "privacidade", "Sugestões e anúncios no Windows desligados",
          "Tira as dicas, os anúncios no menu Iniciar e a instalação silenciosa de apps patrocinados.",
          cdm, rec=True),
        R("p_pesquisa_web", "privacidade", "Pesquisa da web no Iniciar desligada",
          "A busca do Iniciar procura só no seu computador, sem mandar o que você digita para a internet.",
          [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", "dword", 0, 1),
           ("HKCU", r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", "dword", 1, None)], rec=True),
        R("p_erros", "privacidade", "Relatório de erros desligado",
          "Não envia à Microsoft o relatório quando um programa trava.",
          [("HKLM", r"SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", "dword", 1, None)], rec=True),
        R("p_feedback", "privacidade", "Pedidos de feedback desligados",
          "Para de perguntar o que você achou do Windows.",
          [("HKCU", r"Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", "dword", 0, None)], rec=True),
        AjusteTarefas("p_tarefas", "privacidade", "Tarefas de telemetria desligadas",
                      "Desliga as tarefas agendadas que analisam seu PC em segundo plano e enviam dados (como o CompatTelRunner, que costuma pesar no disco e no processador).",
                      [r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
                       r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
                       r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
                       r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
                       r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
                       r"\Microsoft\Windows\Feedback\Siuf\DmClient",
                       r"\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload"], ext=True),
        R("p_localizacao", "privacidade", "Localização do sistema desligada",
          "Nenhum app descobre onde você está. Mapas e clima deixam de se ajustar sozinhos.",
          [("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
            "Value", "sz", "Deny", "Allow")]),
        R("p_copilot", "privacidade", "Copilot desligado",
          "Esconde o assistente Copilot do Windows. Em algumas versões novas pode não ter efeito.",
          [("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", "dword", 1, None)]),
    ]
    # ----- Jogos (FPS) -----
    c += [
        R("fps_dvr_politica", "jogos", "Captura de tela do Windows bloqueada",
          "Além de desligar a gravação em segundo plano, bloqueia por regra do Windows o Game DVR. Nenhum programa liga ele sozinho de novo.",
          [("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", "dword", 0, None)], rec=True, fps=True),
        R("fps_gamebar", "jogos", "Game Bar fora do caminho",
          "Tira o painel de boas-vindas e a integração do controle com a Game Bar do Xbox, que abrem janelas no meio do jogo.",
          [("HKCU", r"Software\Microsoft\GameBar", "UseNexusForGameBarEnabled", "dword", 0, None),
           ("HKCU", r"Software\Microsoft\GameBar", "ShowStartupPanel", "dword", 0, None)], rec=True, fps=True),
        R("fps_energia_throttle", "jogos", "Sem economia de energia nos programas",
          "O Windows reduz a velocidade de programas que ele julga “em segundo plano”. Isto desliga essa freada, o que ajuda quem joga e grava ou transmite ao mesmo tempo.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", "dword", 1, None)],
          sup=True, so_mesa=True, fps=True, nota="Em notebook gasta mais bateria. Vale depois de reiniciar."),
        R("fps_vbs", "jogos", "Isolamento de núcleo (VBS) desligado",
          "O Windows roda uma camada de segurança por virtualização que pode custar de 5% a 10% de FPS em alguns jogos. Desligar devolve esse desempenho, mas reduz a proteção do Windows contra certos ataques.",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity", "Enabled", "dword", 0, None)],
          risco="medio", fps=True, nota="Só use em PC de jogo. Precisa reiniciar. Dá para desfazer aqui."),
    ]
    # ----- Rede -----
    c += [
        R("rede_throttle", "rede", "Sem limite de rede para multimídia",
          "O Windows reserva parte da rede e do processador para áudio e vídeo. Isto libera esse limite.",
          [("HKLM", SP, "NetworkThrottlingIndex", "dword", 0xFFFFFFFF, 10),
           ("HKLM", SP, "SystemResponsiveness", "dword", 0, 20)], rec=True),
        AjusteNagle("rede_nagle", "rede", "Menos atraso nos jogos online",
                    "Desliga o algoritmo de Nagle, que junta pacotes pequenos antes de enviar. Melhora o ping em jogos.", rec=True),
    ]
    return c


CATALOGO = _montar_catalogo()
POR_ID = {a.id: a for a in CATALOGO}


def catalogo_publico():
    """Lista que a tela recebe. Serviços que não existem neste Windows ficam de fora."""
    return [a.info() for a in CATALOGO if a.disponivel() or REG is None]


def estados_ajustes():
    res = {}
    for a in CATALOGO:
        try:
            res[a.id] = a.estado()
        except Exception:
            res[a.id] = None
    return res


_RESTAURACAO = {"feita": False}


def ponto_restauracao():
    """Cria um ponto de restauração do Windows, uma vez por execução. Devolve True se criou."""
    if _RESTAURACAO["feita"] or not IS_WIN:
        return False
    _RESTAURACAO["feita"] = True
    cod, _ = powershell("Checkpoint-Computer -Description 'Th Boost' -RestorePointType MODIFY_SETTINGS", tempo=120)
    return cod == 0


# ---------------- planos de energia ----------------

PLANOS_CONHECIDOS = {
    "equilibrado": ("381b4222-f694-41f0-9685-ff5bb260df2e", "Equilibrado"),
    "alto": ("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "Alto desempenho"),
    "economia": ("a1841308-3541-4fab-bc81-f71556f20b4a", "Economia de energia"),
    "maximo": ("e9a42b02-d5df-448d-aa00-03f14749eb61", "Desempenho máximo"),
}
_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


def listar_planos():
    cod, saida = executar(["powercfg", "/list"])
    planos = []
    if cod == 0:
        for linha in saida.splitlines():
            m = re.search(rf"({_GUID})\s+\(([^)]*)\)\s*(\*)?", linha)
            if m:
                planos.append({"guid": m.group(1).lower(), "nome": m.group(2).strip(), "ativo": bool(m.group(3))})
    return planos


def plano_existente(chave, planos=None):
    """Acha o plano pelo código padrão, pelo código que o Th Boost criou antes ou pelo nome (o Windows copia o nome do modelo)."""
    planos = listar_planos() if planos is None else planos
    guid, nome = PLANOS_CONHECIDOS[chave]
    por_guid = {p["guid"]: p for p in planos}
    criado = (_backup().get("_planos") or {}).get(chave)
    for g in (guid, criado):
        if g and g in por_guid:
            return por_guid[g]
    for p in planos:
        if p["nome"].strip().lower() == nome.lower():
            return p
    return None


def ativar_plano(chave):
    """Ativa um plano pelo nome conhecido. Se o Windows não tiver o plano, cria uma cópia a partir do modelo (uma vez só)."""
    if chave not in PLANOS_CONHECIDOS:
        return "Plano desconhecido."
    guid, nome = PLANOS_CONHECIDOS[chave]
    achado = plano_existente(chave)
    if achado:
        guid = achado["guid"]
    else:
        cod, saida = executar(["powercfg", "-duplicatescheme", guid])
        m = re.search(_GUID, saida or "")
        if cod != 0 or not m:
            return f"Este computador não tem o plano {nome} e não foi possível criá-lo."
        guid = m.group(0).lower()
        with TRAVA_AJ:
            _backup().setdefault("_planos", {})[chave] = guid
            _guardar_backup()
    cod, _ = executar(["powercfg", "/setactive", guid])
    return f"Plano {nome} ativado." if cod == 0 else "Não foi possível trocar o plano (abra como Administrador)."


# ---------------- DNS ----------------

DNS_OPCOES = {"google": ("8.8.8.8", "8.8.4.4"), "cloudflare": ("1.1.1.1", "1.0.0.1")}
_PS_REDE_ATIVA = ("Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and "
                  "$_.NetAdapter.Status -eq 'Up' }")


def dns_atual():
    cod, saida = powershell(_PS_REDE_ATIVA + " | ForEach-Object { ($_.DNSServer | Where-Object { $_.AddressFamily -eq 2 } | "
                            "ForEach-Object { $_.ServerAddresses }) -join ',' }", tempo=30)
    servidores = []
    if cod == 0:
        for parte in re.split(r"[,\s]+", saida):
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", parte):
                servidores.append(parte)
    modo = "outro"
    for nome, par in DNS_OPCOES.items():
        if servidores[:2] == list(par):
            modo = nome
    return {"modo": modo, "servidores": servidores[:2]}


def dns_trocar(modo):
    if modo == "auto":
        acao = "-ResetServerAddresses"
    elif modo in DNS_OPCOES:
        acao = "-ServerAddresses ('%s','%s')" % DNS_OPCOES[modo]
    else:
        return "Opção de DNS desconhecida."
    cod, _ = powershell(_PS_REDE_ATIVA + " | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex "
                        + acao + " }", tempo=40)
    executar(["ipconfig", "/flushdns"])
    nomes = {"auto": "automático", "google": "Google (8.8.8.8)", "cloudflare": "Cloudflare (1.1.1.1)"}
    return f"DNS: {nomes[modo]}." if cod == 0 else "Não foi possível trocar o DNS (abra como Administrador)."


def resetar_rede():
    a, _ = executar(["netsh", "winsock", "reset"], timeout=40)
    b, _ = executar(["netsh", "int", "ip", "reset"], timeout=40)
    return ("Rede reiniciada. Reinicie o computador para terminar." if a == 0 and b == 0
            else "Não foi possível resetar a rede (abra como Administrador).")


# ---------------- programas que abrem com o Windows ----------------

_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APROVADO = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
FONTES_INICIO = [
    ("HKCU", _RUN, "HKCU", _APROVADO + r"\Run", "Usuário"),
    ("HKLM", _RUN, "HKLM", _APROVADO + r"\Run", "Todos os usuários"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM", _APROVADO + r"\Run32", "Todos (32 bits)"),
]


def listar_inicio():
    itens = []
    if REG is None:
        return itens
    for n, (raiz, caminho, raiz_ap, caminho_ap, origem) in enumerate(FONTES_INICIO):
        aprovados = {n_.lower(): v for n_, v in REG.valores(raiz_ap, caminho_ap)}
        for nome, comando in REG.valores(raiz, caminho):
            if not isinstance(comando, str):
                continue
            marca = aprovados.get(nome.lower())
            desligado = bool(marca and isinstance(marca, (bytes, bytearray)) and len(marca) > 0 and marca[0] & 1)
            itens.append({"id": f"{n}|{nome}", "nome": nome, "comando": comando[:160], "origem": origem,
                          "ligado": not desligado})
    return sorted(itens, key=lambda i: i["nome"].lower())


def definir_inicio(id, ligar):
    existentes = {i["id"]: i for i in listar_inicio()}
    if id not in existentes:
        return "Programa não encontrado."
    n, nome = id.split("|", 1)
    raiz, caminho, raiz_ap, caminho_ap, _ = FONTES_INICIO[int(n)]
    if ligar:
        marca = b"\x02" + b"\x00" * 11
    else:
        agora = int((time.time() + 11644473600) * 10_000_000)  # hora atual no formato FILETIME do Windows
        marca = b"\x03\x00\x00\x00" + agora.to_bytes(8, "little")
    REG.escrever(raiz_ap, caminho_ap, nome, marca, "bin")
    return f"{nome}: {'vai abrir' if ligar else 'não abre mais'} com o Windows."


# ---------------- remover apps que vêm com o Windows ----------------

APPS = [
    ("Microsoft.BingNews", "Notícias", "baixo"), ("Microsoft.BingWeather", "Clima", "baixo"),
    ("Microsoft.GetHelp", "Obter Ajuda", "baixo"), ("Microsoft.Getstarted", "Dicas", "baixo"),
    ("Microsoft.MicrosoftOfficeHub", "Atalho do Office", "baixo"),
    ("Microsoft.MicrosoftSolitaireCollection", "Paciência (Solitaire)", "baixo"),
    ("Microsoft.People", "Pessoas", "baixo"), ("Microsoft.WindowsFeedbackHub", "Central de Comentários", "baixo"),
    ("Microsoft.YourPhone", "Vincular ao Celular", "baixo"), ("Microsoft.ZuneVideo", "Filmes e TV", "baixo"),
    ("Microsoft.SkypeApp", "Skype", "baixo"), ("Microsoft.MixedReality.Portal", "Realidade Mista", "baixo"),
    ("Microsoft.Microsoft3DViewer", "Visualizador 3D", "baixo"), ("Microsoft.Print3D", "Imprimir 3D", "baixo"),
    ("Clipchamp.Clipchamp", "Clipchamp", "baixo"), ("Microsoft.Todos", "Microsoft To Do", "baixo"),
    ("Microsoft.PowerAutomateDesktop", "Power Automate", "baixo"), ("MicrosoftTeams", "Teams (versão pessoal)", "baixo"),
    ("Microsoft.549981C3F5F10", "Cortana", "baixo"), ("Microsoft.ZuneMusic", "Media Player / Groove", "medio"),
    ("king.com.CandyCrushSaga", "Candy Crush Saga", "baixo"), ("king.com.CandyCrushSodaSaga", "Candy Crush Soda", "baixo"),
    ("SpotifyAB.SpotifyMusic", "Spotify (pré-instalado)", "baixo"), ("BytedancePte.Ltd.TikTok", "TikTok", "baixo"),
    ("Disney.37853FC22B2CE", "Disney+", "baixo"), ("4DF9E0F8.Netflix", "Netflix", "baixo"),
    ("Facebook.Facebook", "Facebook", "baixo"), ("Facebook.InstagramBeta", "Instagram", "baixo"),
    ("AmazonVideo.PrimeVideo", "Prime Video", "baixo"),
    ("Microsoft.XboxApp", "Xbox (app antigo)", "medio"), ("Microsoft.GamingApp", "Xbox (Game Pass)", "medio"),
    ("Microsoft.XboxGamingOverlay", "Xbox Game Bar", "medio"),
]
APPS_POR_NOME = {a[0]: a for a in APPS}


def listar_apps():
    """Apps da lista segura que estão instalados neste computador."""
    cod, saida = powershell("Get-AppxPackage -AllUsers | Select-Object -ExpandProperty Name", tempo=90)
    if cod != 0:
        return []
    instalados = {linha.strip() for linha in saida.splitlines()}
    return [{"nome": n, "titulo": t, "risco": r} for n, t, r in APPS if n in instalados]


def remover_apps(nomes):
    """Remove só apps da lista segura. Devolve a quantidade removida."""
    feitos = 0
    for nome in nomes:
        if nome not in APPS_POR_NOME:
            continue
        cod, _ = powershell(f"Get-AppxPackage -AllUsers -Name '{nome}' | Remove-AppxPackage -AllUsers", tempo=180)
        feitos += 1 if cod == 0 else 0
    return feitos
