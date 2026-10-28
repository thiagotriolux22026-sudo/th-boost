# ---------------- manutenção: Correções, Backup, diagnóstico e estatísticas do Dashboard ----------------
#
# Regras:
#  - nada daqui apaga arquivos pessoais; o backup só COPIA (nunca apaga nem muda a origem);
#  - cada correção é um comando conhecido do próprio Windows (SFC, DISM, chkdsk...), com confirmação na tela;
#  - tudo o que vem da tela é só um identificador: o programa procura o caminho/comando na própria lista.

# ---------- correções ----------

CORRECOES = [
    # id, nome, descrição, admin, demora, reinicia, confirmação (None = roda direto)
    ("sfc", "Reparar arquivos do Windows", "Verifica os arquivos do sistema e conserta os que estiverem danificados (SFC). Resolve travamentos e erros estranhos.",
     True, "5 a 20 min", False, None),
    ("dism", "Reparar a imagem do Windows", "Baixa do Windows Update as peças originais para consertar o sistema (DISM). Use se o SFC não conseguiu consertar. Precisa de internet.",
     True, "10 a 30 min", True, None),
    ("chkdsk", "Verificar o disco", "Procura erros no sistema de arquivos sem precisar reiniciar. Não apaga nada.",
     True, "2 a 15 min", False, None),
    ("chkdsk_agendar", "Reparar o disco ao reiniciar", "Marca o disco para ser consertado no próximo reinício. O reinício demora mais uma vez só.",
     True, "rápido", True, "Agendar o reparo do disco?|O Windows vai verificar e consertar o disco na próxima vez que o PC ligar, o que pode demorar de alguns minutos a uma hora. Não desligue o PC durante isso."),
    ("wu", "Consertar o Windows Update", "Zera os arquivos temporários do Windows Update quando as atualizações travam, falham ou ficam em 0%.",
     True, "1 min", True, "Consertar o Windows Update?|As atualizações já baixadas serão baixadas de novo. Nada é perdido."),
    ("icones", "Reconstruir ícones e miniaturas", "Corrige ícones em branco, errados ou miniaturas que não aparecem. A barra de tarefas some por alguns segundos.",
     False, "10 s", False, "Reconstruir os ícones?|A barra de tarefas e a área de trabalho vão piscar e voltar em alguns segundos. Salve o que estiver aberto."),
    ("explorer", "Reiniciar o Explorer", "Destrava a barra de tarefas, o menu Iniciar e a área de trabalho quando ficam congelados.",
     False, "5 s", False, "Reiniciar o Explorer?|A barra de tarefas e a área de trabalho somem por alguns segundos e voltam. Seus programas continuam abertos."),
    ("som", "Consertar o áudio", "Reinicia os serviços de som do Windows. Resolve “sem dispositivo de áudio” e som que sumiu.",
     True, "10 s", False, None),
    ("spooler", "Destravar a impressão", "Limpa a fila de impressão presa e reinicia o serviço de impressão.",
     True, "10 s", False, "Destravar a impressão?|Trabalhos de impressão que estiverem na fila serão cancelados."),
    ("hora", "Acertar o relógio", "Sincroniza data e hora com a internet. Resolve sites com erro de certificado por causa da hora errada.",
     True, "5 s", False, None),
    ("loja", "Reparar a Microsoft Store", "Limpa o cache da Loja. Resolve downloads parados e Loja que não abre. A Loja abre sozinha ao terminar.",
     False, "30 s", False, None),
    ("rede", "Consertar a internet", "Limpa o DNS, renova o IP e reinicia a pilha de rede do Windows. Use quando a internet some ou trava.",
     True, "30 s", True, "Consertar a internet?|A conexão cai por alguns segundos e é preciso reiniciar o PC depois. Redes Wi-Fi salvas continuam salvas."),
]
CORRECOES_POR_ID = {c[0]: c for c in CORRECOES}

# sites oficiais (só estes endereços são abertos; a tela manda apenas o identificador)
LINKS_OFICIAIS = {
    "vcredist": ("Visual C++ (faltando DLL, jogo não abre)", "Microsoft", "https://aka.ms/vs/17/release/vc_redist.x64.exe"),
    "directx": ("DirectX (erros d3dx9, xinput)", "Microsoft", "https://www.microsoft.com/download/details.aspx?id=35"),
    "dotnet": (".NET (programas que pedem o .NET)", "Microsoft", "https://dotnet.microsoft.com/download/dotnet"),
    "nvidia": ("Driver da placa NVIDIA", "NVIDIA", "https://www.nvidia.com/Download/index.aspx"),
    "amd": ("Driver da placa AMD", "AMD", "https://www.amd.com/en/support/download/drivers.html"),
    "intel": ("Driver Intel (vídeo e rede)", "Intel", "https://www.intel.com/content/www/us/en/download-center/home.html"),
}


def correcoes_publico():
    out = []
    for ident, nome, desc, adm, demora, reinicia, conf in CORRECOES:
        t, _, p = (conf or "").partition("|")
        out.append({"id": ident, "nome": nome, "desc": desc, "admin": adm, "demora": demora, "reinicia": reinicia,
                    "conf": [t, p] if conf else None})
    return out


def links_publico():
    return [{"id": k, "nome": v[0], "site": v[1]} for k, v in LINKS_OFICIAIS.items()]


# ---------- backup ----------

PASTAS_BACKUP = [("docs", "Documentos", "Personal", "Documents"), ("desktop", "Área de Trabalho", "Desktop", "Desktop"),
                 ("imagens", "Imagens", "My Pictures", "Pictures"), ("videos", "Vídeos", "My Video", "Videos"),
                 ("musicas", "Músicas", "My Music", "Music"),
                 ("downloads", "Downloads", "{374DE290-123F-4565-9164-39C4925E467B}", "Downloads")]
BACKUP_PADRAO = ["docs", "desktop", "imagens"]
PASTA_BACKUP_NOME = "Th Boost Backup"
ARQ_REGISTRO_BACKUP = "th_boost_backup.json"
_SEM_COPIA = re.compile(r"^(~\$.*|thumbs\.db|desktop\.ini|.*\.thboost-tmp)$", re.IGNORECASE)
ATRIB_NUVEM = 0x1000 | 0x40000 | 0x400000  # arquivo só na nuvem (OneDrive): copiar baixaria tudo, então é pulado


def pasta_do_usuario(valor_registro, padrao):
    c = ""
    if REG is not None:
        v = REG.ler("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders", valor_registro)
        if isinstance(v, str) and v.strip():
            c = os.path.expandvars(v)
    if not c or not os.path.isabs(c):
        base = _env("USERPROFILE")
        c = os.path.join(base, padrao) if base else ""
    return c if c and os.path.isabs(c) else ""


def pastas_de_backup():
    res = []
    for ident, nome, reg, padrao in PASTAS_BACKUP:
        c = pasta_do_usuario(reg, padrao)
        res.append({"id": ident, "nome": nome, "caminho": c, "existe": bool(c and os.path.isdir(c))})
    return res


def destinos_de_backup():
    """Unidades onde dá para guardar o backup (não lista CD/DVD nem unidades de rede)."""
    sistema = (os.environ.get("SystemDrive") or "C:").upper()
    res = []
    try:
        particoes = psutil.disk_partitions(all=False)
    except (OSError, RuntimeError):
        particoes = []
    for p in particoes:
        opts = (p.opts or "").lower()
        if "cdrom" in opts or not p.fstype or "remote" in opts:
            continue
        letra = (p.mountpoint or p.device or "")[:2].upper()
        if not re.fullmatch(r"[A-Z]:", letra) and not os.environ.get("TOTIMIZE_BACKUP_TESTE"):
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        res.append({"id": letra, "montagem": p.mountpoint, "livre_gb": round(u.free / 1024 ** 3, 1),
                    "total_gb": round(u.total / 1024 ** 3, 1), "removivel": "removable" in opts,
                    "sistema": letra == sistema})
    return res


def _lp(caminho):
    """Caminhos longos no Windows (mais de 260 caracteres) precisam do prefixo especial."""
    if IS_WIN and len(caminho) > 240 and not caminho.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(caminho)
    return caminho


def _pontos_restauracao():
    """Lista de pontos de restauração do Windows (do mais novo ao mais velho)."""
    cod, saida = powershell("Get-ComputerRestorePoint | Select-Object SequenceNumber,Description,CreationTime | "
                            "ConvertTo-Json -Compress", tempo=40)
    if cod != 0 or not saida.strip():
        return []
    try:
        dados = json.loads(saida)
    except ValueError:
        return []
    if isinstance(dados, dict):
        dados = [dados]
    res = []
    for d in dados if isinstance(dados, list) else []:
        if not isinstance(d, dict):
            continue
        t = str(d.get("CreationTime") or "")
        try:
            quando = datetime.strptime(t[:14], "%Y%m%d%H%M%S")
        except ValueError:
            continue
        res.append({"n": d.get("SequenceNumber"), "nome": str(d.get("Description") or "")[:80],
                    "quando": quando.strftime("%d/%m/%Y %H:%M"), "ts": quando.timestamp()})
    return sorted(res, key=lambda r: -r["ts"])[:12]


def criar_ponto_manual():
    """Cria um ponto de restauração agora. O Windows normalmente só deixa criar um por dia: a trava é levantada só durante a criação."""
    if REG is None:
        return False, "Só funciona no Windows."
    chave = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore"
    antigo = REG.ler("HKLM", chave, "SystemRestorePointCreationFrequency")
    try:
        REG.escrever("HKLM", chave, "SystemRestorePointCreationFrequency", 0, "dword")
    except OSError:
        pass
    try:
        cod, saida = powershell("Checkpoint-Computer -Description 'Th Boost (manual)' -RestorePointType MODIFY_SETTINGS", tempo=240)
    finally:
        try:
            if antigo is None:
                REG.apagar("HKLM", chave, "SystemRestorePointCreationFrequency")
            else:
                REG.escrever("HKLM", chave, "SystemRestorePointCreationFrequency", antigo, "dword")
        except OSError:
            pass
    return cod == 0, saida


# ---------- o que a tela de Dashboard e o diagnóstico leem ----------

def nome_do_processador():
    if REG is None:
        return ""
    v = REG.ler("HKLM", r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""


def _por_pct(valor, pontos):
    """Interpola linearmente: pontos = [(entrada, nota), ...] em ordem crescente de entrada."""
    if valor <= pontos[0][0]:
        return pontos[0][1]
    for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
        if valor <= x1:
            return y0 + (y1 - y0) * (valor - x0) / max(1e-9, x1 - x0)
    return pontos[-1][1]


class ManutencaoMixin:
    """Estatísticas, tarefas com passos (Correções, Backup, Espaço), diagnóstico e pontuação."""

    # ===== estatísticas que o Dashboard mostra =====

    def estat_iniciar_estado(self):
        e = CONFIG.get("stats") if isinstance(CONFIG.get("stats"), dict) else {}
        self.stats = {"mb": float(e.get("mb") or 0), "otimizacoes": int(e.get("otimizacoes") or 0),
                      "extremas": int(e.get("extremas") or 0), "supremas": int(e.get("supremas") or 0),
                      "correcoes": int(e.get("correcoes") or 0), "procs": int(e.get("procs") or 0), "ultima": str(e.get("ultima") or ""),
                      "ultima_tipo": str(e.get("ultima_tipo") or "")}

    def _estat_gravar(self):
        CONFIG["stats"] = dict(self.stats)
        salvar_config()

    def estat_otimizacao(self, mb, tipo, interrompida=False):
        s = self.stats
        s["mb"] += max(0.0, float(mb or 0))
        if not interrompida:
            if tipo == "suprema":
                s["supremas"] += 1
            elif tipo == "extrema":
                s["extremas"] += 1
            else:
                s["otimizacoes"] += 1
            s["ultima"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            s["ultima_tipo"] = tipo
        self._estat_gravar()

    def estat_limpeza(self, b):
        self.stats["mb"] += max(0.0, b / 1048576)
        self._estat_gravar()

    # ===== tarefas com passos =====

    def trab_iniciar_estado(self):
        vazio = lambda: {"ativo": False, "parando": False, "fracao": 0.0, "passo": "", "titulo": "", "id": "",
                         "passos": [], "resumo": None, "fim": 0}
        self.trab = {"correcao": vazio(), "backup": vazio(), "espaco": vazio(), "processos": vazio()}
        self.diag = {"estado": "nenhum", "quando": 0.0, "lento": {}}
        self.pontos = {"estado": "nenhum", "itens": [], "quando": 0.0}
        self.espaco = {"pastas": [], "arquivos": [], "quando": ""}
        self._prog_proc = {}
        self._proc_ofertados = set()
        self.estat_iniciar_estado()

    def trab_snapshot(self):
        res = {}
        for k, t in self.trab.items():
            d = dict(t)
            d["passos"] = [dict(p) for p in t["passos"]]
            res[k] = d
        return res

    def _pesado_ocupado(self):
        return (self.otim["ativo"] or self.ext["ativo"] or self.pre["ativo"] or self.trab["correcao"]["ativo"]
                or self.trab["processos"]["ativo"])

    def trab_iniciar(self, chave, ident, titulo, passos, ctx=None):
        T = self.trab[chave]
        if T["ativo"]:
            self.msg("Já tem uma tarefa desse tipo rodando. Aguarde terminar.")
            return False
        T.update(ativo=True, parando=False, fracao=0.02, passo="Preparando...", titulo=titulo, id=ident, resumo=None)
        T["passos"] = [{"id": p[0], "nome": p[1], "estado": "pendente", "texto": ""} for p in passos]
        threading.Thread(target=self._trab_rodar, args=(chave, passos, ctx or {}), daemon=True).start()
        return True

    def trab_parar(self, chave):
        if chave in self.trab and self.trab[chave]["ativo"]:
            self.trab[chave]["parando"] = True
            self.msg("Parando...")

    def _trab_rodar(self, chave, passos, ctx):
        T = self.trab[chave]
        adm = e_admin()
        ctx["parar"] = lambda: T["parando"] or self.fechando
        n = max(1, len(passos))
        textos, piores = [], "ok"
        try:
            for i, (pid, nome, func, precisa_adm) in enumerate(passos):
                P = T["passos"][i]
                if T["parando"] or self.fechando:
                    for outro in T["passos"][i:]:
                        outro.update(estado="pulado", texto="Interrompido")
                    break
                if precisa_adm and not adm:
                    P.update(estado="pulado", texto="Precisa de Administrador. Feche e abra o Th Boost pelo atalho.")
                    textos.append(P["texto"])
                    piores = "pulado" if piores == "ok" else piores
                    continue
                T["passo"] = nome + "..."
                T["fracao"] = max(0.02, i / n)
                P["estado"] = "rodando"
                ctx["prog"] = (lambda f, i=i: T.__setitem__("fracao", max(0.02, min(0.99, (i + max(0.0, min(1.0, f))) / n))))
                inicio = time.time()
                try:
                    texto, estado = func(ctx)
                except Exception as erro:
                    texto, estado = f"Erro: {erro}", "erro"
                time.sleep(max(0.0, 0.5 - (time.time() - inicio)))
                P.update(estado=estado, texto=texto)
                textos.append(texto)
                if estado == "erro":
                    piores = "erro"
                elif estado == "pulado" and piores == "ok":
                    piores = "pulado"
                T["fracao"] = (i + 1) / n
            T["resumo"] = {"estado": piores, "texto": textos[-1] if textos else "", "textos": textos,
                           "reiniciar": bool(ctx.get("reiniciar")), "interrompido": bool(T["parando"]),
                           "dados": ctx.get("resumo") or {}}
        except Exception as erro:
            T["resumo"] = {"estado": "erro", "texto": f"Parou por um erro: {erro}", "textos": [], "reiniciar": False,
                           "interrompido": False, "dados": {}}
        finally:
            T["passo"] = "Pronto"
            T["fracao"] = 1.0
            T["ativo"] = False
            T["parando"] = False
            T["fim"] += 1
            if chave == "correcao":
                self.stats["correcoes"] += 1
                self._estat_gravar()

    # ===== correções =====

    def correcao_iniciar(self, ident):
        c = CORRECOES_POR_ID.get(ident)
        if c is None:
            raise ValueError("correção desconhecida")
        if REG is None:
            return self.msg("As correções só funcionam no Windows.")
        if self._pesado_ocupado():
            return self.msg("Espere a otimização em andamento terminar.")
        passos = getattr(self, "_c_" + ident)()
        self.trab_iniciar("correcao", ident, c[1], passos, {"ident": ident})
        self.msg(f"{c[1]}: começando...")

    def _c_sfc(self):
        return [("sfc", "Verificando os arquivos do Windows", self._cx_sfc, True)]

    def _cx_sfc(self, ctx):
        cod, saida = _executar_longo(["sfc", "/scannow"], 3600, ctx["parar"])
        if cod == -1:
            return "Interrompido. Dá para rodar de novo quando quiser.", "pulado"
        t = (saida or "").replace("\x00", "").lower()
        if re.search(r"did not find any integrity|n[aã]o encontrou nenhuma viola", t):
            return "Nenhum arquivo do Windows estava danificado.", "ok"
        if re.search(r"unable to fix|n[aã]o p[oô]de reparar|n[aã]o foi poss[ií]vel reparar|n[aã]o conseguiu reparar", t):
            return ("Há arquivos danificados que o SFC não conseguiu consertar. Rode “Reparar a imagem do Windows” e depois "
                    "este de novo."), "erro"
        if re.search(r"successfully repaired|reparou com [eê]xito|reparados com [eê]xito|com [eê]xito", t):
            ctx["reiniciar"] = True
            return "Achei arquivos danificados e consertei. Reinicie o PC para terminar.", "ok"
        if cod == 0:
            return "Verificação concluída.", "ok"
        return "O Windows não conseguiu rodar a verificação agora (pode haver uma atualização pendente). Reinicie e tente de novo.", "erro"

    def _c_dism(self):
        return [("dism", "Reparando a imagem do Windows", self._cx_dism, True)]

    def _cx_dism(self, ctx):
        cod, saida = _executar_longo(["DISM.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"], 3600, ctx["parar"])
        if cod == -1:
            return "Interrompido. Dá para rodar de novo quando quiser.", "pulado"
        if cod == 0:
            ctx["reiniciar"] = True
            return "A imagem do Windows está íntegra. Rode o “Reparar arquivos do Windows” agora e reinicie.", "ok"
        return "Não consegui reparar agora. Confira a internet e se há atualização pendente, e tente de novo.", "erro"

    def _c_chkdsk(self):
        return [("chkdsk", "Verificando o disco", self._cx_chkdsk, True)]

    def _cx_chkdsk(self, ctx):
        letra = (os.environ.get("SystemDrive") or "C:")[:2]
        cod, saida = _executar_longo(["chkdsk", letra, "/scan"], 3600, ctx["parar"])
        if cod == -1:
            return "Interrompido.", "pulado"
        if cod == 0:
            return "O Windows examinou o disco e não achou problemas.", "ok"
        if cod == 1:
            return "O Windows achou e corrigiu pequenos erros no disco.", "ok"
        return ("O disco tem erros que só dá para consertar ao reiniciar. Use “Reparar o disco ao reiniciar”. "
                "Se o aviso voltar, faça cópia dos seus arquivos: o disco pode estar falhando."), "erro"

    def _c_chkdsk_agendar(self):
        return [("agendar", "Marcando o disco para verificação", self._cx_chkdsk_agendar, True)]

    def _cx_chkdsk_agendar(self, ctx):
        letra = (os.environ.get("SystemDrive") or "C:")[:2]
        cod, _ = executar(["fsutil", "dirty", "set", letra], timeout=30)
        if cod != 0:
            return "O Windows não aceitou marcar o disco.", "erro"
        ctx["reiniciar"] = True
        return "Pronto. Na próxima vez que o PC ligar, o Windows verifica e conserta o disco.", "ok"

    def _c_wu(self):
        return [("wu", "Consertando o Windows Update", self._cx_wu, True)]

    def _cx_wu(self, ctx):
        serv = ("wuauserv", "cryptSvc", "bits", "msiserver")
        raiz = _env("SYSTEMROOT") or _env("WINDIR")
        alvos = [os.path.join(raiz, "SoftwareDistribution"), os.path.join(raiz, "System32", "catroot2")] if raiz else []
        renomeadas, falhas = 0, 0
        try:
            for s in serv:
                executar(["net", "stop", s, "/y"], timeout=60)
            sufixo = ".thboost-" + datetime.now().strftime("%Y%m%d%H%M%S")
            for a in alvos:
                if os.path.isdir(a) and not _e_ligacao(a):
                    try:
                        os.rename(a, a + sufixo)
                        renomeadas += 1
                    except OSError:
                        falhas += 1
                    # cópias de segurança de correções anteriores (criadas só por este programa) são apagadas
                    for velho in glob.glob(a + ".thboost-*"):
                        if velho != a + sufixo and os.path.isdir(velho) and not _e_ligacao(velho):
                            shutil.rmtree(velho, ignore_errors=True)
        finally:
            for s in ("cryptSvc", "bits", "wuauserv", "msiserver"):
                executar(["net", "start", s], timeout=60)
        if falhas and not renomeadas:
            return "Não consegui limpar as pastas do Windows Update (algum programa está usando). Reinicie e tente de novo.", "erro"
        ctx["reiniciar"] = True
        return "Windows Update zerado. Reinicie o PC e procure atualizações de novo.", "ok"

    def _c_icones(self):
        return [("icones", "Reconstruindo ícones e miniaturas", self._cx_icones, False)]

    def _cx_icones(self, ctx):
        L = _env("LOCALAPPDATA")
        apagados = 0
        executar(["taskkill", "/F", "/IM", "explorer.exe"], timeout=20)
        try:
            time.sleep(1.0)
            alvos = []
            if L:
                alvos.append(os.path.join(L, "IconCache.db"))
                pasta = os.path.join(L, "Microsoft", "Windows", "Explorer")
                alvos += glob.glob(os.path.join(pasta, "iconcache_*.db")) + glob.glob(os.path.join(pasta, "thumbcache_*.db"))
            for a in alvos:
                if os.path.isfile(a) and not _e_ligacao(a) and _remover_arquivo(a):
                    apagados += 1
        finally:
            self._iniciar_explorer()
        return f"Cache de ícones e miniaturas refeito ({apagados} arquivo(s)). Os ícones voltam em alguns segundos.", "ok"

    def _iniciar_explorer(self):
        try:
            subprocess.Popen(["explorer.exe"])
        except OSError:
            pass

    def _c_explorer(self):
        return [("explorer", "Reiniciando o Explorer", self._cx_explorer, False)]

    def _cx_explorer(self, ctx):
        executar(["taskkill", "/F", "/IM", "explorer.exe"], timeout=20)
        time.sleep(1.0)
        self._iniciar_explorer()
        return "O Explorer foi reiniciado. A barra de tarefas deve voltar em instantes.", "ok"

    def _c_som(self):
        return [("som", "Reiniciando o áudio do Windows", self._cx_som, True)]

    def _cx_som(self, ctx):
        executar(["net", "stop", "audiosrv", "/y"], timeout=40)
        executar(["net", "stop", "AudioEndpointBuilder", "/y"], timeout=40)
        a, _ = executar(["net", "start", "AudioEndpointBuilder"], timeout=40)
        b, _ = executar(["net", "start", "audiosrv"], timeout=40)
        return (("Os serviços de áudio foram reiniciados.", "ok") if a == 0 and b == 0
                else ("Não consegui reiniciar o áudio. Reinicie o PC.", "erro"))

    def _c_spooler(self):
        return [("spooler", "Limpando a fila de impressão", self._cx_spooler, True)]

    def _cx_spooler(self, ctx):
        raiz = _env("SYSTEMROOT") or _env("WINDIR")
        executar(["net", "stop", "spooler", "/y"], timeout=40)
        apagados = 0
        try:
            pasta = os.path.join(raiz, "System32", "spool", "PRINTERS") if raiz else ""
            if pasta and os.path.isdir(pasta) and not _e_ligacao(pasta):
                for e in os.scandir(pasta):
                    if e.is_file(follow_symlinks=False) and _remover_arquivo(e.path):
                        apagados += 1
        finally:
            cod, _ = executar(["net", "start", "spooler"], timeout=40)
        return ((f"Fila limpa ({apagados} arquivo(s)) e impressão reiniciada.", "ok") if cod == 0
                else ("Limpei a fila, mas não consegui reiniciar o serviço de impressão. Reinicie o PC.", "erro"))

    def _c_hora(self):
        return [("hora", "Sincronizando o relógio", self._cx_hora, True)]

    def _cx_hora(self, ctx):
        executar(["net", "start", "w32time"], timeout=30)
        cod, _ = executar(["w32tm", "/resync", "/force"], timeout=40)
        return (("Relógio sincronizado com a internet.", "ok") if cod == 0
                else ("Não consegui sincronizar. Confira a internet e tente de novo.", "erro"))

    def _c_loja(self):
        return [("loja", "Limpando o cache da Microsoft Store", self._cx_loja, False)]

    def _cx_loja(self, ctx):
        cod, _ = executar(["wsreset.exe"], timeout=120)
        return (("Cache da Loja limpo. Ela abre sozinha.", "ok") if cod == 0
                else ("O Windows não deixou limpar o cache da Loja agora.", "erro"))

    def _c_rede(self):
        return [("dns", "Limpando o DNS", self._cx_rede_dns, True), ("ip", "Renovando o IP", self._cx_rede_ip, True),
                ("pilha", "Reiniciando a pilha de rede", self._cx_rede_pilha, True)]

    def _cx_rede_dns(self, ctx):
        cod, _ = executar(["ipconfig", "/flushdns"], timeout=30)
        return ("Cache DNS limpo.", "ok") if cod == 0 else ("Não consegui limpar o DNS.", "erro")

    def _cx_rede_ip(self, ctx):
        return ("IP renovado.", "ok") if renovar_ip() else ("O IP não renovou (pode ser rede sem DHCP).", "pulado")

    def _cx_rede_pilha(self, ctx):
        texto = resetar_rede()
        ok = "reinicie" in texto.lower()
        if ok:
            ctx["reiniciar"] = True
        return texto, ("ok" if ok else "erro")

    # ===== backup =====

    def bk_config(self):
        c = CONFIG.get("backup") if isinstance(CONFIG.get("backup"), dict) else {}
        pastas = [p for p in (c.get("pastas") or BACKUP_PADRAO) if p in {x[0] for x in PASTAS_BACKUP}]
        return {"destino": c.get("destino") if isinstance(c.get("destino"), str) else "", "pastas": pastas,
                "ultimo": c.get("ultimo") if isinstance(c.get("ultimo"), dict) else None}

    def bk_definir(self, destino, pastas):
        validos = {d["id"] for d in destinos_de_backup()}
        if destino and destino not in validos:
            raise ValueError("destino inválido")
        ids = {x[0] for x in PASTAS_BACKUP}
        if not isinstance(pastas, list) or any(p not in ids for p in pastas):
            raise ValueError("pastas inválidas")
        c = self.bk_config()
        CONFIG["backup"] = {"destino": destino, "pastas": list(dict.fromkeys(pastas)), "ultimo": c["ultimo"]}
        salvar_config()

    def _bk_raiz(self, destino=None):
        d = destino or self.bk_config()["destino"]
        for x in destinos_de_backup():
            if x["id"] == d:
                return os.path.join(x["montagem"], PASTA_BACKUP_NOME, USUARIO.title() or "Usuario")
        return ""

    def backup_arquivos_iniciar(self):
        cfg = self.bk_config()
        raiz = self._bk_raiz()
        if not raiz:
            return self.msg("Escolha primeiro onde guardar o backup (um pendrive, HD externo ou outro disco).")
        if not cfg["pastas"]:
            return self.msg("Marque pelo menos uma pasta para o backup.")
        passos = [("contar", "Procurando o que mudou desde o último backup", self._bx_contar, False),
                  ("copiar", "Copiando seus arquivos", self._bx_copiar, False),
                  ("registro", "Anotando o backup", self._bx_registro, False)]
        if self.trab_iniciar("backup", "arquivos", "Backup dos arquivos", passos, {"raiz": raiz, "cfg": cfg}):
            self.msg("Backup dos arquivos começando...")

    def _bx_contar(self, ctx):
        raiz, cfg = ctx["raiz"], ctx["cfg"]
        fontes = [(p["id"], p["nome"], p["caminho"]) for p in pastas_de_backup() if p["id"] in cfg["pastas"] and p["existe"]]
        if not fontes:
            return "As pastas escolhidas não existem neste PC.", "erro"
        lista, total, vistos, pulados_nuvem = [], 0, 0, 0
        for ident, nome, origem in fontes:
            if ctx["parar"]():
                return "Interrompido.", "pulado"
            for dirpath, dirnames, nomes in os.walk(origem, followlinks=False):
                if ctx["parar"]():
                    return "Interrompido.", "pulado"
                dirnames[:] = [d for d in dirnames if not _e_ligacao(os.path.join(dirpath, d))]
                rel = os.path.relpath(dirpath, origem)
                for n in nomes:
                    if _SEM_COPIA.match(n):
                        continue
                    src = os.path.join(dirpath, n)
                    try:
                        st = os.lstat(src)
                    except OSError:
                        continue
                    if _atributo_ligacao(st) or not stat_is_reg(st):
                        continue
                    if getattr(st, "st_file_attributes", 0) & ATRIB_NUVEM:
                        pulados_nuvem += 1
                        continue
                    vistos += 1
                    dst = os.path.join(raiz, nome, "" if rel == "." else rel, n)
                    try:
                        sd = os.stat(_lp(dst))
                        if sd.st_size == st.st_size and sd.st_mtime >= st.st_mtime - 2:
                            continue
                    except OSError:
                        pass
                    lista.append((src, dst, st.st_size))
                    total += st.st_size
        try:
            os.makedirs(_lp(raiz), exist_ok=True)
            livre = psutil.disk_usage(raiz).free
        except OSError as erro:
            return f"Não consegui usar o destino ({erro}).", "erro"
        if total + 256 * 1048576 > livre:
            return (f"Não cabe: preciso de {tam_texto(total)} e o destino tem só {tam_texto(livre)} livres. "
                    "Escolha outro destino ou menos pastas."), "erro"
        ctx["lista"], ctx["total"], ctx["vistos"], ctx["nuvem"] = lista, total, vistos, pulados_nuvem
        if not lista:
            return f"Nada novo para copiar: {vistos} arquivo(s) já estão no backup.", "ok"
        return f"{len(lista)} arquivo(s) novos ou alterados ({tam_texto(total)}) de {vistos}.", "ok"

    def _bx_copiar(self, ctx):
        lista = ctx.get("lista")
        if lista is None:
            return "Nada a copiar.", "pulado"
        if not lista:
            return "Nada novo para copiar.", "ok"
        total, feito, n, falhas = ctx["total"] or 1, 0, 0, 0
        ultimo = 0.0
        for src, dst, tam in lista:
            if ctx["parar"]():
                ctx["parcial"] = True
                break
            tmp = _lp(dst) + ".thboost-tmp"
            try:
                os.makedirs(_lp(os.path.dirname(dst)), exist_ok=True)
                with open(_lp(src), "rb") as a, open(tmp, "wb") as b:
                    while True:
                        bloco = a.read(4 * 1048576)
                        if not bloco:
                            break
                        b.write(bloco)
                        feito += len(bloco)
                        if time.time() - ultimo > 0.4:
                            ultimo = time.time()
                            ctx["prog"](feito / total)
                            self.trab["backup"]["passos"][1]["texto"] = f"{n} de {len(lista)} · {tam_texto(feito)} de {tam_texto(total)}"
                        if ctx["parar"]():
                            raise InterruptedError
                shutil.copystat(_lp(src), tmp)
                os.replace(tmp, _lp(dst))
                n += 1
            except InterruptedError:
                ctx["parcial"] = True
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                break
            except OSError:
                falhas += 1  # arquivo aberto por outro programa, sem permissão etc.
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        ctx["copiados"], ctx["bytes"], ctx["falhas"] = n, feito, falhas
        texto = f"{n} arquivo(s) copiados ({tam_texto(feito)})."
        if falhas:
            texto += f" {falhas} em uso ou sem permissão ficaram de fora."
        if ctx.get("parcial"):
            return "Interrompido. " + texto + " Rode de novo para continuar de onde parou.", "pulado"
        return texto, "ok"

    def _bx_registro(self, ctx):
        if ctx.get("lista") is None:  # a contagem falhou (sem espaço, destino ruim): não anota um backup que não houve
            return "Nada a anotar.", "pulado"
        info = {"quando": datetime.now().strftime("%d/%m/%Y %H:%M"), "arquivos": ctx.get("copiados", 0),
                "mb": round(ctx.get("bytes", 0) / 1048576, 1), "pastas": ctx["cfg"]["pastas"], "destino": ctx["cfg"]["destino"],
                "parcial": bool(ctx.get("parcial"))}
        try:
            with open(os.path.join(ctx["raiz"], ARQ_REGISTRO_BACKUP), "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
        if not ctx.get("parcial"):
            c = self.bk_config()
            CONFIG["backup"] = {"destino": c["destino"], "pastas": c["pastas"], "ultimo": info}
            salvar_config()
        ctx["resumo"] = info
        return "Backup anotado." if not ctx.get("parcial") else "Backup parcial anotado.", "ok"

    def backup_restaurar_iniciar(self):
        raiz = self._bk_raiz()
        if not raiz or not os.path.isdir(raiz):
            return self.msg("Não achei um backup do Th Boost no destino escolhido.")
        if self.trab_iniciar("backup", "restaurar", "Restaurar arquivos do backup",
                             [("restaurar", "Devolvendo o que está faltando", self._bx_restaurar, False)], {"raiz": raiz}):
            self.msg("Restaurando arquivos do backup...")

    def _bx_restaurar(self, ctx):
        raiz = ctx["raiz"]
        n = pulados = 0
        for p in pastas_de_backup():
            origem_bk = os.path.join(raiz, p["nome"])
            if not p["caminho"] or not os.path.isdir(origem_bk):
                continue
            for dirpath, dirnames, nomes in os.walk(origem_bk, followlinks=False):
                if ctx["parar"]():
                    return f"Interrompido. {n} arquivo(s) devolvidos.", "pulado"
                dirnames[:] = [d for d in dirnames if not _e_ligacao(os.path.join(dirpath, d))]
                rel = os.path.relpath(dirpath, origem_bk)
                for nome in nomes:
                    if nome.endswith(".thboost-tmp"):
                        continue
                    src = os.path.join(dirpath, nome)
                    dst = os.path.join(p["caminho"], "" if rel == "." else rel, nome)
                    if os.path.lexists(_lp(dst)):
                        pulados += 1  # nunca sobrescreve o que já existe
                        continue
                    try:
                        os.makedirs(_lp(os.path.dirname(dst)), exist_ok=True)
                        shutil.copy2(_lp(src), _lp(dst))
                        n += 1
                    except OSError:
                        pass
        return f"{n} arquivo(s) devolvidos. {pulados} já existiam e foram deixados como estão.", "ok"

    def backup_ponto_iniciar(self):
        def passo(ctx):
            ok, saida = criar_ponto_manual()
            self.pontos["quando"] = 0.0  # força reler a lista
            if ok:
                return "Ponto de restauração criado.", "ok"
            if re.search(r"disabled|desativ|desligad|protection|prote", saida or "", re.IGNORECASE):
                return "A Proteção do Sistema está desligada neste disco. Ligue em “Ligar a proteção” abaixo e tente de novo.", "erro"
            return "O Windows não criou o ponto agora.", "erro"
        if self.trab_iniciar("backup", "ponto", "Ponto de restauração", [("ponto", "Criando o ponto de restauração", passo, True)]):
            self.msg("Criando um ponto de restauração...")

    def backup_protecao_iniciar(self):
        def passo(ctx):
            letra = (os.environ.get("SystemDrive") or "C:")[:2] + "\\"
            cod, _ = powershell(f"Enable-ComputerRestore -Drive '{letra}'", tempo=60)
            self.pontos["quando"] = 0.0
            return (("Proteção do Sistema ligada.", "ok") if cod == 0 else ("O Windows não deixou ligar a proteção.", "erro"))
        if self.trab_iniciar("backup", "protecao", "Proteção do Sistema", [("protecao", "Ligando a Proteção do Sistema", passo, True)]):
            self.msg("Ligando a Proteção do Sistema...")

    def backup_drivers_iniciar(self):
        raiz = self._bk_raiz()
        if not raiz:
            return self.msg("Escolha primeiro onde guardar o backup.")

        def passo(ctx):
            pasta = os.path.join(raiz, "Drivers")
            try:
                os.makedirs(pasta, exist_ok=True)
            except OSError as erro:
                return f"Não consegui criar a pasta no destino ({erro}).", "erro"
            cod, saida = _executar_longo(["pnputil", "/export-driver", "*", pasta], 1200, ctx["parar"])
            if cod == -1:
                return "Interrompido.", "pulado"
            if cod != 0:
                return "O Windows não exportou os drivers.", "erro"
            try:
                tam = tamanho_pasta(pasta)
                qtd = len([d for d in os.listdir(pasta) if os.path.isdir(os.path.join(pasta, d))])
            except OSError:
                tam, qtd = 0, 0
            return f"{qtd} driver(s) guardados ({tam_texto(tam)}). Para usar depois: Gerenciador de Dispositivos > Atualizar driver > escolher esta pasta.", "ok"
        if self.trab_iniciar("backup", "drivers", "Backup dos drivers", [("drivers", "Exportando os drivers instalados", passo, True)]):
            self.msg("Exportando os drivers...")

    def _pasta_backups_ajustes(self):
        p = os.path.join(pasta_do_programa(), "backups")
        try:
            os.makedirs(p, exist_ok=True)
        except OSError:
            return ""
        return p

    def backup_ajustes_iniciar(self):
        def passo(ctx):
            pasta = self._pasta_backups_ajustes()
            if not pasta:
                return "Não consegui criar a pasta de backups ao lado do programa.", "erro"
            nome = "ThBoost-ajustes-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".zip"
            alvo = os.path.join(pasta, nome)
            n = 0
            with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
                for arq in (ARQ_BACKUP, ARQ_EXTREMO, ARQ_CONFIG):
                    if os.path.isfile(arq):
                        z.write(arq, os.path.basename(arq))
                        n += 1
            if not n:
                os.remove(alvo)
                return "Ainda não há ajustes do Th Boost para guardar.", "pulado"
            extra = ""
            raiz = self._bk_raiz()
            if raiz:
                try:
                    os.makedirs(raiz, exist_ok=True)
                    shutil.copy2(alvo, os.path.join(raiz, nome))
                    extra = " Uma cópia também foi para o destino do backup."
                except OSError:
                    pass
            return f"Configurações do Th Boost guardadas ({n} arquivo(s)).{extra}", "ok"
        if self.trab_iniciar("backup", "ajustes", "Backup dos ajustes", [("ajustes", "Guardando as configurações do Th Boost", passo, False)]):
            self.msg("Guardando as configurações do Th Boost...")

    def backups_ajustes_listar(self):
        pasta = self._pasta_backups_ajustes()
        res = []
        if pasta:
            for nome in sorted(os.listdir(pasta), reverse=True)[:8]:
                if re.fullmatch(r"ThBoost-ajustes-\d{8}-\d{6}\.zip", nome):
                    st = os.stat(os.path.join(pasta, nome))
                    res.append({"nome": nome, "quando": datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M"),
                                "kb": max(1, st.st_size // 1024)})
        return res

    def backup_ajustes_importar(self, nome):
        if not isinstance(nome, str) or not re.fullmatch(r"ThBoost-ajustes-\d{8}-\d{6}\.zip", nome):
            raise ValueError("nome inválido")
        caminho = os.path.join(self._pasta_backups_ajustes(), nome)
        if not os.path.isfile(caminho):
            return self.msg("Não achei esse backup.")

        def passo(ctx):
            esperados = {os.path.basename(ARQ_BACKUP): ARQ_BACKUP, os.path.basename(ARQ_EXTREMO): ARQ_EXTREMO}
            lidos = {}
            with zipfile.ZipFile(caminho) as z:
                for m in z.namelist():
                    if m in esperados:
                        if z.getinfo(m).file_size > 2_000_000:
                            return "O arquivo de backup é grande demais para ser dos ajustes.", "erro"
                        dados = json.loads(z.read(m).decode("utf-8"))
                        if not isinstance(dados, dict):
                            return "O arquivo de backup está com defeito.", "erro"
                        lidos[m] = dados
            if not lidos:
                return "Esse backup não tem os registros dos ajustes.", "erro"
            for m, dados in lidos.items():
                alvo = esperados[m]
                if os.path.isfile(alvo):
                    shutil.copy2(alvo, alvo + ".antes")
                with open(alvo, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False, indent=1)
            global _BACKUP
            with TRAVA_AJ:
                _BACKUP = None
            with TRAVA_EXT:
                _EXT_MEM.clear()
            self.atualizar_aj()
            self.ext["desfazer"] = _ext_tem_algo(_ext_ler())
            return "Registros dos ajustes devolvidos. Os botões de desfazer voltam a funcionar como na data do backup.", "ok"
        if self.trab_iniciar("backup", "importar", "Devolver configurações", [("importar", "Lendo o backup", passo, False)]):
            self.msg("Devolvendo as configurações...")

    def backup_abrir_pasta(self):
        raiz = self._bk_raiz()
        if not raiz or not os.path.isdir(raiz):
            return self.msg("Ainda não existe um backup no destino escolhido.")
        try:
            subprocess.Popen(["explorer.exe", raiz])
        except OSError:
            self.msg("Não consegui abrir a pasta.")

    def backup_lista(self):
        cfg = self.bk_config()
        self.pontos_ler()
        raiz = self._bk_raiz()
        pastas = pastas_de_backup()
        for p in pastas:
            p["marcada"] = p["id"] in cfg["pastas"]
        return {"destinos": destinos_de_backup(), "pastas": pastas, "config": cfg, "admin": e_admin(),
                "tem_backup": bool(raiz and os.path.isdir(raiz)), "pontos": {"estado": self.pontos["estado"], "itens": list(self.pontos["itens"])},
                "ajustes": self.backups_ajustes_listar()}

    # ===== pontos de restauração (leitura em segundo plano) =====

    def pontos_ler(self, forcar=False):
        p = self.pontos
        if p["estado"] == "lendo" or REG is None:
            return
        if not forcar and p["estado"] == "pronto" and time.time() - p["quando"] < 120:
            return
        p["estado"] = "lendo"

        def tarefa():
            try:
                p["itens"] = _pontos_restauracao()
                p["estado"] = "pronto"
            except Exception:
                p["estado"] = "erro"
            p["quando"] = time.time()
        threading.Thread(target=tarefa, daemon=True).start()

    # ===== diagnóstico e pontuação =====

    def diag_atualizar(self):
        """Leituras lentas (disco, pontos de restauração, monitor) em segundo plano, no máximo a cada 3 minutos."""
        d = self.diag
        if d["estado"] == "lendo" or REG is None:
            return
        if d["estado"] == "pronto" and time.time() - d["quando"] < 180:
            return
        d["estado"] = "lendo"

        def tarefa():
            lento = {}
            try:
                cod, saida = powershell("Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus | ConvertTo-Json -Compress", tempo=40)
                if cod == 0 and saida.strip():
                    dados = json.loads(saida)
                    lento["discos"] = [x for x in (dados if isinstance(dados, list) else [dados]) if isinstance(x, dict)]
                self.pontos_ler(True)
                for _ in range(80):
                    if self.pontos["estado"] != "lendo":
                        break
                    time.sleep(0.25)
                lento["pontos"] = list(self.pontos["itens"])
                self.monitor_ler()
                for _ in range(80):
                    if self.monitor["estado"] != "lendo":
                        break
                    time.sleep(0.25)
                lento["monitor"] = self.monitor.get("dados")
                try:
                    lento["memoria"] = self.memoria_agora()
                except Exception:
                    lento["memoria"] = None
                d["estado"] = "pronto"
            except Exception:
                d["estado"] = "erro"
            d["lento"] = lento
            d["quando"] = time.time()
        threading.Thread(target=tarefa, daemon=True).start()

    def dashboard(self):
        """Tudo que a página Dashboard mostra: pontuação por categoria, o que falta fazer e números do sistema."""
        self.diag_atualizar()
        a = self.amostra or {}
        lento = self.diag.get("lento") or {}
        win = REG is not None
        aj = self.aj or {}
        cats, achados = [], []

        def cat(ident, nome, valor, dica, ir):
            cats.append({"id": ident, "nome": nome, "valor": None if valor is None else int(round(max(0, min(100, valor)))),
                         "dica": dica, "ir": ir})

        def achado(ident, nivel, titulo, texto, ir=None, acao=None, rotulo=""):
            achados.append({"id": ident, "nivel": nivel, "titulo": titulo, "texto": texto, "ir": ir, "acao": acao, "rotulo": rotulo})

        # 1) ajustes de desempenho
        cand = [x for x in CATALOGO if (x.rec or x.ext) and x.risco != "medio" and aj.get(x.id) is not None]
        lig = sum(1 for x in cand if aj.get(x.id) is True)
        cat("desempenho", "Ajustes de desempenho", (100 * lig / len(cand)) if cand else None,
            f"{lig} de {len(cand)} ajustes seguros ligados" if cand else "Só no Windows", "extremo")
        if cand and len(cand) - lig >= 3:
            achado("ajustes", "aviso", f"{len(cand) - lig} ajustes de desempenho ainda desligados",
                   "A Otimização Extrema liga todos os que são seguros, com ponto de restauração e botão de desfazer.", "extremo", None, "Abrir a Otimização Extrema")
        # 2) inicialização
        try:
            ini = [i for i in listar_inicio() if i["ligado"]] if win else []
        except Exception:
            ini = []
        pesados = [i for i in ini if INICIO_DISPENSAVEL.match(i["nome"])]
        cat("inicio", "Inicialização do Windows", _por_pct(len(ini), [(0, 100), (6, 100), (12, 55), (25, 20)]) if win else None,
            f"{len(ini)} programas abrem com o Windows" if win else "Só no Windows", "inicializacao")
        if len(pesados) >= 2:
            achado("inicio", "aviso", f"{len(pesados)} programas pesados abrem com o Windows",
                   "Launchers e atualizadores (" + ", ".join(i["nome"] for i in pesados[:3]) + ") atrasam a inicialização e comem memória.", "inicializacao", None, "Ver a inicialização")
        # 3) espaço em disco
        disco = a.get("disco")
        if disco:
            livre_pct = 100 - disco["pct"]
            cat("espaco", "Espaço em disco", _por_pct(livre_pct, [(3, 5), (10, 35), (20, 70), (35, 100)]),
                f"{disco['livre']:.0f} GB livres de {disco['total']:.0f} GB", "disco")
            if livre_pct < 10:
                achado("espaco", "ruim", "O disco está quase cheio", f"Só {livre_pct:.0f}% livre. Abaixo de 10% o Windows e os jogos ficam lentos.", "extremo", None, "Limpar agora")
            elif livre_pct < 20:
                achado("espaco", "aviso", "Pouco espaço livre no disco", f"{livre_pct:.0f}% livre. O ideal é manter pelo menos 20%.", "disco", None, "Limpeza de disco")
        else:
            cat("espaco", "Espaço em disco", None, "Disco indisponível", "disco")
        # 4) memória
        ram_total = a.get("ram_total") or 0
        if ram_total:
            nota = _por_pct(ram_total, [(2, 20), (4, 40), (8, 70), (16, 95), (32, 100)])
            mem = lento.get("memoria") or {}
            extra = (f" · {mem['tipo']} a {mem['vel_atual']} MHz" if mem.get("vel_atual") else "") + (" · canal único" if mem.get("canal") == "unico" else "")
            if mem.get("abaixo"):
                nota = nota * 0.85
            cat("memoria", "Memória RAM", nota, f"{ram_total:.0f} GB instalados · {a.get('ram', 0):.0f}% em uso agora{extra}", "memoria")
            if mem.get("abaixo"):
                achado("mem_mhz", "aviso", f"A memória roda a {mem['vel_atual']} MHz e o kit é de {mem['vel_kit']} MHz",
                       "Ativar o perfil XMP/DOCP/EXPO na BIOS dá mais FPS e menos travadas, de graça. A página Memória RAM mostra o passo a passo.", "memoria", None, "Ver a memória")
            if mem.get("canal") == "unico":
                achado("mem_canal", "aviso", "Só 1 pente de memória (canal único)",
                       "Com 2 pentes iguais a memória fica bem mais rápida em jogos. Veja os detalhes na página Memória RAM.", "memoria", None, "Ver a memória")
            if ram_total <= 8:
                achado("ram", "info", f"Só {ram_total:.0f} GB de memória RAM",
                       "Para jogos atuais o ideal é 16 GB. Mais memória é um dos upgrades que mais ajudam. Enquanto isso, a Otimização Extrema libera o máximo possível.", "extremo", None, "Abrir a Otimização Extrema")
            if a.get("ram", 0) > 88:
                achado("ram_uso", "aviso", "A memória está quase toda em uso agora", "Feche programas que não está usando ou libere a RAM.", None, "ram", "Liberar a RAM")
        else:
            cat("memoria", "Memória RAM", None, "", "monitor")
        # 5) plano de energia
        plano = ""
        if win:
            try:
                plano = next((p["nome"] for p in listar_planos() if p["ativo"]), "")
            except Exception:
                plano = ""
        if plano:
            bom = bool(PLANO_BOM.search(plano))
            econ = bool(re.search(r"economia|saver", plano, re.IGNORECASE))
            cat("energia", "Plano de energia", 100 if bom else (30 if econ else 70), f"Em uso: {plano}", "energia")
            if not bom and not tem_bateria():
                achado("energia", "aviso", "O PC está no plano de energia “" + plano + "”",
                       "Em PC de mesa, o plano de alto desempenho deixa o processador sempre pronto para o jogo.", None, "plano", "Ativar Alto desempenho")
        else:
            cat("energia", "Plano de energia", None, "Só no Windows" if not win else "Não consegui ler", "energia")
        # 5b) processos
        try:
            nproc = max(0, len(psutil.pids()) - 1)  # sem o "ocioso", igual ao Gerenciador de Tarefas
        except Exception:
            nproc = 0
        if nproc:
            cat("processos", "Processos em segundo plano", _por_pct(nproc, [(90, 100), (140, 90), (190, 55), (280, 15)]),
                f"{nproc} processos rodando agora", "processos")
            if nproc > 190:
                achado("processos", "aviso", f"{nproc} processos rodando",
                       "Muitos processos ocupam memória e processador à toa. A coluna Processos fecha o que é dispensável e desliga serviços que pesam.",
                       "processos", None, "Reduzir processos")
        else:
            cat("processos", "Processos em segundo plano", None, "", "processos")
        # 6) jogos (FPS)
        fps_ids = [i for i in FPS_PACOTE if aj.get(i) is not None]
        fps_lig = sum(1 for i in fps_ids if aj.get(i) is True)
        mon = lento.get("monitor")
        nota_j = (100 * fps_lig / len(fps_ids)) if fps_ids else None
        dica_j = f"{fps_lig} de {len(fps_ids)} ajustes de FPS ligados" if fps_ids else "Só no Windows"
        if mon and mon.get("hz_max", 0) > mon.get("hz", 0) + 5:
            nota_j = (nota_j if nota_j is not None else 100) * 0.8
            dica_j += f" · monitor a {mon['hz']} Hz (aceita {mon['hz_max']} Hz)"
            achado("hz", "aviso", f"Seu monitor está a {mon['hz']} Hz e aceita {mon['hz_max']} Hz",
                   "Muita gente joga a 60 Hz sem saber que o monitor aguenta mais. Mais Hz deixa tudo mais fluido, mesmo com o mesmo FPS.", "jogos", None, "Ver em Jogos")
        cat("jogos", "Preparo para jogos", nota_j, dica_j, "jogos")
        if fps_ids and fps_lig < len(fps_ids) - 1:
            achado("fps", "aviso", "Ajustes de FPS desligados", f"{len(fps_ids) - fps_lig} ajustes que tiram trabalho do jogo ainda não estão ligados.", "jogos", None, "Abrir Jogos")
        # 7) segurança dos dados
        pontos = lento.get("pontos")
        ult_bk = (self.bk_config().get("ultimo") or {}).get("quando")
        dias_ponto = None
        if pontos:
            dias_ponto = (time.time() - pontos[0]["ts"]) / 86400
        nota_b = 0 if (win and pontos is not None and not pontos) else (None if pontos is None else _por_pct(dias_ponto, [(0, 100), (14, 85), (45, 40), (120, 10)]))
        if ult_bk:
            nota_b = (nota_b if nota_b is not None else 50) * 0.5 + 50
        cat("dados", "Segurança dos dados", nota_b,
            ("Ponto de restauração há %d dia(s)" % dias_ponto if dias_ponto is not None else "Lendo pontos de restauração...") + (f" · backup em {ult_bk}" if ult_bk else " · sem backup de arquivos"), "backup")
        if win and pontos is not None and (not pontos or dias_ponto > 45):
            achado("restauracao", "aviso", "Sem ponto de restauração recente", "Crie um antes de mudar coisas importantes no Windows.", "backup", None, "Abrir Backup")
        if not ult_bk:
            achado("backup", "info", "Você ainda não fez backup dos seus arquivos", "Documentos, Área de Trabalho e Imagens podem ser copiados para um pendrive ou HD externo em poucos minutos.", "backup", None, "Fazer backup")
        # extras
        try:
            ligado_h = (time.time() - psutil.boot_time()) / 3600
        except Exception:
            ligado_h = None
        if ligado_h and ligado_h > 24 * 7:
            achado("uptime", "aviso", f"O PC está ligado há {ligado_h / 24:.0f} dias", "Reiniciar de vez em quando libera memória e aplica atualizações.", None, None, "")
        if win and reinicio_pendente():
            achado("reinicio", "aviso", "Há um reinício pendente", "O Windows está esperando você reiniciar para terminar uma atualização.", None, None, "")
        for dsk in lento.get("discos") or []:
            if str(dsk.get("HealthStatus") or "").lower() not in ("healthy", "", "0"):
                achado("disco_saude", "ruim", "O disco “%s” reporta problema de saúde" % str(dsk.get("FriendlyName") or "")[:40],
                       "Faça backup dos seus arquivos agora e considere trocar o disco.", "backup", None, "Fazer backup")
        if any("hdd" in str(dsk.get("MediaType") or "").lower() or str(dsk.get("MediaType")) == "3" for dsk in lento.get("discos") or []):
            achado("hdd", "info", "Seu PC usa HD mecânico", "Trocar por um SSD é o upgrade que mais acelera o Windows e o carregamento dos jogos.", None, None, "")
        if a.get("tcpu") and a["tcpu"] > 88:
            achado("temp", "ruim", f"Processador a {a['tcpu']:.0f}°C", "Calor demais reduz o desempenho. Limpe o cooler e confira a ventilação.", None, None, "")
        if win and not e_admin():
            achado("admin", "aviso", "Th Boost aberto sem Administrador", "Vários ajustes e correções não funcionam. Feche e abra pelo atalho da área de trabalho.", None, None, "")
        valores = [c["valor"] for c in cats if c["valor"] is not None]
        pesos = {"desempenho": 1.4, "inicio": 1.0, "espaco": 1.2, "memoria": 0.8, "energia": 0.9, "processos": 1.0, "jogos": 1.1, "dados": 0.8}
        num = sum(c["valor"] * pesos[c["id"]] for c in cats if c["valor"] is not None)
        den = sum(pesos[c["id"]] for c in cats if c["valor"] is not None)
        score = int(round(num / den)) if den else None
        ordem = {"ruim": 0, "aviso": 1, "info": 2}
        achados.sort(key=lambda x: ordem.get(x["nivel"], 3))
        return {"score": score, "categorias": cats, "achados": achados[:9],
                "lendo": self.diag["estado"] == "lendo", "stats": dict(self.stats),
                "sistema": {"cpu": nome_do_processador(), "nucleos": a.get("nucleos"), "ram_gb": round(ram_total) if ram_total else None,
                            "gpu": (a.get("gpu") or {}).get("nome") or ((mon or {}).get("placas") or [""])[0],
                            "ligado_h": round(ligado_h, 1) if ligado_h else None, "plano": plano, "processos": nproc or None,
                            "monitor": ({"hz": mon["hz"], "hz_max": mon["hz_max"], "res": mon["res"]} if mon else None)}}


def stat_is_reg(st):
    import stat as _s
    return _s.S_ISREG(st.st_mode)
