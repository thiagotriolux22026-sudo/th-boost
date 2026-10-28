# ---------------- ferramentas: programas instalados, espaço em disco e atalhos do Windows ----------------
#
# Nada aqui apaga arquivos: desinstalar abre o desinstalador do próprio programa (como o Windows faz),
# e os arquivos grandes só podem ser mostrados no Explorer para você decidir.

_UNINSTALL = [("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
              ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
              ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Uninstall")]

# programas que o Windows ou o hardware precisam: ficam fora da lista de desinstalação
_PROG_PROTEGIDO = re.compile(
    r"(microsoft (visual c\+\+|\.net|windows desktop runtime|edge webview2)|webview2|directx|nvidia (graphics driver|physx|hd audio)|"
    r"amd (software|chipset)|intel\(r\) (chipset|management|graphics|serial|rapid)|realtek|windows (driver|sdk)|"
    r"microsoft update health|vulkan run ?time)", re.IGNORECASE)

ATALHOS = [
    # id, nome, descrição, alvo (arquivo/URI aberto pelo Windows), grupo
    ("tarefas", "Gerenciador de Tarefas", "Veja o que está pesando agora e feche programas travados.", "taskmgr.exe", "Desempenho"),
    ("recursos", "Monitor de Recursos", "Uso detalhado de processador, memória, disco e rede por programa.", "resmon.exe", "Desempenho"),
    ("energia", "Opções de energia", "Escolha o plano de energia (Alto desempenho, Equilibrado...).", "powercfg.cpl", "Desempenho"),
    ("msconfig", "Configuração do sistema", "Inicialização e serviços do Windows, para quem sabe o que está fazendo.", "msconfig.exe", "Desempenho"),
    ("servicos", "Serviços do Windows", "Lista completa de serviços. Cuidado ao mexer.", "services.msc", "Desempenho"),
    ("memdiag", "Diagnóstico de Memória do Windows", "Testa a memória no próximo reinício e procura pentes com defeito. O Windows pergunta antes de reiniciar.", "mdsched.exe", "Desempenho"),
    ("modojogo", "Modo de Jogo", "Ligue ou desligue o Modo de Jogo do Windows.", "ms-settings:gaming-gamemode", "Jogos"),
    ("graficos", "Configurações de gráficos", "Escolha qual placa de vídeo cada jogo usa e ligue o agendamento por hardware.", "ms-settings:display-advancedgraphics", "Jogos"),
    ("tela", "Taxa de atualização do monitor", "Confira se o monitor está na taxa mais alta (Hz) que ele aceita.", "ms-settings:display-advanced", "Jogos"),
    ("dxdiag", "Diagnóstico do DirectX", "Mostra processador, placa de vídeo e versão do DirectX.", "dxdiag.exe", "Jogos"),
    ("som", "Som", "Dispositivos de áudio de entrada e saída.", "mmsys.cpl", "Jogos"),
    ("mouse", "Mouse", "Velocidade e botões do mouse.", "main.cpl", "Jogos"),
    ("limpeza", "Limpeza de disco do Windows", "A ferramenta de limpeza do próprio Windows.", "cleanmgr.exe", "Disco"),
    ("armazenamento", "Armazenamento", "O que ocupa espaço no disco, segundo o Windows.", "ms-settings:storagesense", "Disco"),
    ("otimizar_disco", "Otimizar unidades", "Desfragmenta HD e faz o TRIM do SSD.", "dfrgui.exe", "Disco"),
    ("gerenciador_disco", "Gerenciamento de disco", "Partições e unidades conectadas.", "diskmgmt.msc", "Disco"),
    ("programas", "Programas e recursos", "A lista de programas do Windows para desinstalar.", "appwiz.cpl", "Sistema"),
    ("dispositivos", "Gerenciador de dispositivos", "Drivers e hardware, para ver o que está com defeito.", "devmgmt.msc", "Sistema"),
    ("update", "Windows Update", "Procure atualizações e veja o histórico.", "ms-settings:windowsupdate", "Sistema"),
    ("seguranca", "Segurança do Windows", "Antivírus e proteção do Windows.", "windowsdefender:", "Sistema"),
    ("eventos", "Visualizador de eventos", "Registros de erros do Windows, para achar a causa de travamentos.", "eventvwr.msc", "Sistema"),
    ("sistema", "Informações do sistema", "Resumo técnico completo do PC.", "msinfo32.exe", "Sistema"),
    ("rede", "Conexões de rede", "Adaptadores de rede e Wi-Fi.", "ncpa.cpl", "Rede"),
]
ATALHOS_POR_ID = {a[0]: a for a in ATALHOS}


def atalhos_publico():
    return [{"id": i, "nome": n, "desc": d, "grupo": g} for i, n, d, _, g in ATALHOS]


def _data_instalacao(texto):
    try:
        return datetime.strptime(str(texto)[:8], "%Y%m%d").strftime("%d/%m/%Y")
    except ValueError:
        return ""


def listar_programas():
    """Programas instalados, do mesmo lugar que o painel 'Programas e recursos' do Windows."""
    if REG is None:
        return []
    vistos, itens = set(), []
    for raiz, caminho in _UNINSTALL:
        for sub in REG.subchaves(raiz, caminho):
            c = caminho + "\\" + sub
            nome = REG.ler(raiz, c, "DisplayName")
            if not isinstance(nome, str) or not nome.strip():
                continue
            if REG.ler(raiz, c, "SystemComponent") == 1 or REG.ler(raiz, c, "ParentKeyName") or REG.ler(raiz, c, "ReleaseType") in ("Update", "Hotfix", "Security Update"):
                continue
            desin = REG.ler(raiz, c, "UninstallString")
            if not isinstance(desin, str) or not desin.strip():
                continue
            chave = nome.strip().lower() + "|" + str(REG.ler(raiz, c, "DisplayVersion") or "")
            if chave in vistos:
                continue
            vistos.add(chave)
            kb = REG.ler(raiz, c, "EstimatedSize")
            itens.append({"id": f"{raiz}|{c}", "nome": nome.strip()[:80],
                          "versao": str(REG.ler(raiz, c, "DisplayVersion") or "")[:24],
                          "editora": str(REG.ler(raiz, c, "Publisher") or "")[:50],
                          "mb": round(kb / 1024, 1) if isinstance(kb, int) and kb > 0 else 0.0,
                          "data": _data_instalacao(REG.ler(raiz, c, "InstallDate") or ""),
                          "protegido": bool(_PROG_PROTEGIDO.search(nome)), "_desin": desin.strip()})
    return sorted(itens, key=lambda i: i["nome"].lower())


def programas_publico():
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in listar_programas()]


def espaco_alvos():
    """Pastas que dá para analisar: as do usuário, mais o perfil inteiro."""
    res = [{"id": "usuario", "nome": "Todo o seu perfil", "caminho": _env("USERPROFILE")}]
    res += [{"id": p["id"], "nome": p["nome"], "caminho": p["caminho"]} for p in pastas_de_backup() if p["caminho"]]
    return [a for a in res if a["caminho"] and os.path.isdir(a["caminho"])]


class FerramentasMixin:
    """Programas instalados, análise de espaço e atalhos de ferramentas do Windows."""

    # ----- programas -----

    def programas_lista(self):
        return {"itens": programas_publico()}

    def programa_desinstalar(self, ident):
        if not isinstance(ident, str) or len(ident) > 300:
            raise ValueError("pedido inválido")
        alvo = next((p for p in listar_programas() if p["id"] == ident), None)
        if alvo is None:
            return self.msg("Esse programa não está mais na lista.")
        if alvo["protegido"]:
            return self.msg(f"{alvo['nome']} é um componente que o Windows ou seus jogos usam. Não vou desinstalar por aqui.")
        try:
            subprocess.Popen(alvo["_desin"])  # o desinstalador do próprio programa, como no painel do Windows
            self.msg(f"Abrindo o desinstalador de {alvo['nome']}...")
        except OSError:
            self.msg(f"Não consegui abrir o desinstalador de {alvo['nome']}. Use Programas e recursos do Windows.")

    # ----- atalhos -----

    def atalho_abrir(self, ident):
        a = ATALHOS_POR_ID.get(ident) if isinstance(ident, str) else None
        if a is None:
            raise ValueError("atalho inválido")
        if not IS_WIN:
            return self.msg("Disponível só no Windows.")
        try:
            os.startfile(a[3])
            self.msg(f"{a[1]} aberto.")
        except (OSError, AttributeError):
            self.msg(f"Não consegui abrir {a[1]} neste Windows.")

    # ----- espaço em disco -----

    def espaco_iniciar(self, alvo):
        achado = next((a for a in espaco_alvos() if a["id"] == alvo), None) if isinstance(alvo, str) else None
        if achado is None:
            return self.msg("Escolha uma pasta da lista.")
        if self.trab["espaco"]["ativo"]:
            return self.msg("A análise já está rodando.")
        ctx = {"raiz": achado["caminho"], "id": achado["id"], "nome": achado["nome"]}
        if self.trab_iniciar("espaco", "analisar", f"Espaço: {achado['nome']}",
                             [("ler", "Medindo as pastas", self._ex_medir, False)], ctx):
            self.msg(f"Analisando {achado['nome']}...")

    def _ex_medir(self, ctx):
        raiz = ctx["raiz"]
        pastas, arquivos, total, n = {}, [], 0, 0
        limite = time.time() + 240
        grandes_min = 50 * 1048576
        try:
            filhos = [e for e in os.scandir(raiz)]
        except OSError as erro:
            return f"Não consegui ler a pasta ({erro}).", "erro"
        for k, e in enumerate(filhos):
            if ctx["parar"]() or time.time() > limite:
                ctx["parcial"] = True
                break
            ctx["prog"](k / max(1, len(filhos)))
            try:
                if e.is_symlink() or _e_ligacao(e.path):
                    continue
                if e.is_file(follow_symlinks=False):
                    st = e.stat(follow_symlinks=False)
                    total += st.st_size
                    pastas["(arquivos soltos)"] = pastas.get("(arquivos soltos)", 0) + st.st_size
                    if st.st_size >= grandes_min:
                        arquivos.append((e.path, st.st_size, st.st_mtime))
                    continue
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            soma = 0
            for dirpath, dirnames, nomes in os.walk(e.path, followlinks=False):
                if ctx["parar"]() or time.time() > limite:
                    ctx["parcial"] = True
                    break
                dirnames[:] = [d for d in dirnames if not _e_ligacao(os.path.join(dirpath, d))]
                for nome in nomes:
                    caminho = os.path.join(dirpath, nome)
                    try:
                        st = os.lstat(caminho)
                    except OSError:
                        continue
                    if _atributo_ligacao(st) or not stat_is_reg(st):
                        continue
                    soma += st.st_size
                    n += 1
                    if st.st_size >= grandes_min:
                        arquivos.append((caminho, st.st_size, st.st_mtime))
            pastas[e.name] = pastas.get(e.name, 0) + soma
            total += soma
        arquivos.sort(key=lambda a: -a[1])
        self.espaco = {
            "alvo": ctx["id"], "nome": ctx["nome"], "total": total, "arquivos_lidos": n, "parcial": bool(ctx.get("parcial")),
            "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "pastas": [{"nome": k, "bytes": v} for k, v in sorted(pastas.items(), key=lambda x: -x[1])[:15] if v > 0],
            "arquivos": [{"i": i, "nome": os.path.basename(c), "pasta": os.path.dirname(c)[-60:], "bytes": b,
                          "quando": datetime.fromtimestamp(m).strftime("%d/%m/%Y"), "_caminho": c}
                         for i, (c, b, m) in enumerate(arquivos[:25])]}
        ctx["resumo"] = {"total": total}
        return f"{tam_texto(total)} em {n} arquivos" + (" (análise parcial)" if ctx.get("parcial") else "") + ".", "ok"

    def espaco_publico(self):
        e = dict(self.espaco)
        e["arquivos"] = [{k: v for k, v in a.items() if not k.startswith("_")} for a in e.get("arquivos", [])]
        e["alvos"] = [{"id": a["id"], "nome": a["nome"]} for a in espaco_alvos()]
        return e

    def espaco_mostrar(self, i):
        if not isinstance(i, int) or isinstance(i, bool):
            raise ValueError("pedido inválido")
        a = next((x for x in self.espaco.get("arquivos", []) if x["i"] == i), None)
        if a is None or not os.path.isfile(a["_caminho"]):
            return self.msg("Esse arquivo não está mais lá.")
        try:
            subprocess.Popen(["explorer.exe", "/select,", a["_caminho"]])
        except OSError:
            self.msg("Não consegui abrir o Explorer.")

    # ----- links oficiais (drivers, Visual C++, DirectX) -----

    def link_oficial(self, ident):
        l = LINKS_OFICIAIS.get(ident) if isinstance(ident, str) else None
        if l is None:
            raise ValueError("link inválido")
        try:
            webbrowser.open(l[2])
            self.msg(f"Abrindo o site oficial ({l[1]})...")
        except Exception:
            self.msg("Não consegui abrir o navegador.")
