# ---------------- v9.0: aviso de versão nova (o dono publicou no GitHub) e atualização com um clique ----------------
# O programa lê de tempos em tempos um arquivo pequeno do repositório do dono (versao.json). Se a versão de lá for mais
# nova, aparece o aviso "O dono atualizou o Th Boost". Ao clicar em Atualizar:
#   1) baixa o ZIP SÓ do repositório do dono no GitHub (qualquer outro endereço é recusado, até nos redirecionamentos);
#   2) confere a "impressão digital" do ZIP (SHA-256 publicada no versao.json) e o que tem dentro (só os arquivos do
#      Th Boost, e o th_boost.py precisa ser Python válido e dizer a mesma versão);
#   3) guarda os arquivos atuais em "versao_anterior" e troca pelos novos;
#   4) abre o Th Boost novo e fecha o antigo; a janela se recarrega sozinha.
# Nada do computador é enviado: é só um download, como abrir uma página.

ATU_REPO = "thiagotriolux22026-sudo/th-boost"
ATU_URL = f"https://raw.githubusercontent.com/{ATU_REPO}/main/versao.json"
ATU_PAGINA = f"https://github.com/{ATU_REPO}"
ATU_PREFIXOS = (f"https://github.com/{ATU_REPO}/", f"https://raw.githubusercontent.com/{ATU_REPO}/")
ATU_HOSTS = ("github.com", "raw.githubusercontent.com", "objects.githubusercontent.com")
ATU_ARQUIVOS = ("th_boost.py", "Th Boost.ico", "LEIAME.txt", "Abrir Th Boost.bat",
                "Criar atalho na area de trabalho.bat", "Encerrar Th Boost.bat", "Gerar executavel.bat")
ATU_MAX_ZIP = 40 * 1024 * 1024
ATU_MAX_ARQ = 25 * 1024 * 1024
ATU_INTERVALO = 6 * 3600  # procura de novo a cada 6 horas enquanto o programa estiver aberto
_RE_SHA = re.compile(r"[0-9a-f]{64}")


def _atu_teste():
    """Só para os testes automáticos: um "GitHub de mentira" no próprio computador (127.0.0.1). Fora disso, nada muda."""
    u = os.environ.get("THBOOST_ATU_URL", "")
    return u if re.fullmatch(r"http://127\.0\.0\.1:\d{2,5}/[\w./-]*", u) else ""


def atu_url_info():
    return _atu_teste() or ATU_URL


def atu_link_ok(url):
    """O ZIP só pode vir do repositório do dono (ou do GitHub de mentira dos testes)."""
    if not isinstance(url, str) or len(url) > 400 or any(c in url for c in "\\\r\n\t \"'<>"):
        return False
    t = _atu_teste()
    if t and url.startswith(t.split("/", 3)[0] + "//" + t.split("/", 3)[2] + "/"):
        return True
    return url.startswith(ATU_PREFIXOS) and ".." not in url


def versao_tupla(v):
    """'v9.0' -> (9, 0, 0); 'v8.10' é mais nova que 'v8.9'. None se não for uma versão."""
    m = re.fullmatch(r"v?(\d{1,3})(?:\.(\d{1,3}))?(?:\.(\d{1,3}))?", str(v or "").strip())
    return tuple(int(x or 0) for x in m.groups()) if m else None


def atu_mais_nova(remota, local):
    a, b = versao_tupla(remota), versao_tupla(local)
    return bool(a and b and a > b)


def atu_valida_info(d):
    """Confere o versao.json publicado. Devolve uma cópia limpa ou levanta ValueError."""
    if not isinstance(d, dict):
        raise ValueError("versao.json inválido")
    v = d.get("versao")
    if not isinstance(v, str) or not versao_tupla(v):
        raise ValueError("versão inválida no versao.json")
    z, sha = d.get("zip"), str(d.get("sha256") or "").lower()
    if not atu_link_ok(z):
        raise ValueError("o endereço do ZIP não é do repositório do Th Boost")
    if not _RE_SHA.fullmatch(sha):
        raise ValueError("falta a impressão digital (SHA-256) do ZIP")
    tam = d.get("tamanho")
    if tam is not None and (not isinstance(tam, int) or isinstance(tam, bool) or not 0 < tam <= ATU_MAX_ZIP):
        raise ValueError("tamanho inválido no versao.json")
    nov = d.get("novidades") if isinstance(d.get("novidades"), list) else []
    nov = [re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", "", x)).strip()[:160] for x in nov if isinstance(x, str)][:8]
    v = v.strip()
    return {"versao": v if v.startswith("v") else "v" + v, "zip": z, "sha256": sha, "tamanho": tam, "novidades": [x for x in nov if x],
            "data": str(d.get("data") or "")[:20]}


class _AtuRedireciona(urllib.request.HTTPRedirectHandler):
    """Segue o redirecionamento do GitHub (github.com -> raw.githubusercontent.com) e nenhum outro."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        t = _atu_teste()
        teste_ok = t and newurl.startswith(t.split("/", 3)[0] + "//" + t.split("/", 3)[2] + "/")
        if not teste_ok and (p.scheme != "https" or p.hostname not in ATU_HOSTS):
            raise urllib.error.HTTPError(newurl, code, "redirecionamento recusado", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def atu_baixar(url, limite, progresso=None, timeout=30):
    """Baixa até 'limite' bytes (mais que isso é recusado). Usa o proxy do Windows, se houver."""
    if not atu_link_ok(url) and url != atu_url_info():
        raise ValueError("endereço recusado")
    abridor = urllib.request.build_opener(_AtuRedireciona)
    req = urllib.request.Request(url, headers={"User-Agent": f"ThBoost/{VERSAO}", "Cache-Control": "no-cache"})
    partes, total = [], 0
    with abridor.open(req, timeout=timeout) as r:
        esperado = int(r.headers.get("Content-Length") or 0)
        if esperado > limite:
            raise ValueError("arquivo grande demais")
        while True:
            bloco = r.read(65536)
            if not bloco:
                break
            total += len(bloco)
            if total > limite:
                raise ValueError("arquivo grande demais")
            partes.append(bloco)
            if progresso and esperado:
                progresso(min(99, int(total * 100 / esperado)))
    return b"".join(partes)


def atu_buscar_info():
    dados = atu_baixar(atu_url_info(), 65536, timeout=15)
    return atu_valida_info(json.loads(dados.decode("utf-8-sig")))


def atu_conferir_zip(dados, info):
    """Confere o ZIP baixado. Devolve {nome: conteúdo} dos arquivos do Th Boost, ou levanta ValueError."""
    if hashlib.sha256(dados).hexdigest() != info["sha256"]:
        raise ValueError("a impressão digital do ZIP não confere (download incompleto ou arquivo trocado)")
    try:
        zf = zipfile.ZipFile(io.BytesIO(dados))
    except zipfile.BadZipFile:
        raise ValueError("o ZIP baixado está estragado")
    nomes = [i for i in zf.infolist() if not i.is_dir()]
    if not nomes or len(nomes) > 40:
        raise ValueError("o ZIP não parece do Th Boost")
    topo = {i.filename.split("/")[0] for i in nomes}
    pref = (next(iter(topo)) + "/") if len(topo) == 1 and all("/" in i.filename for i in nomes) else ""
    saida = {}
    for i in nomes:
        n = i.filename[len(pref):]
        if n not in ATU_ARQUIVOS:
            continue  # arquivos extras do ZIP são ignorados; só os do Th Boost são trocados
        if i.file_size > ATU_MAX_ARQ:
            raise ValueError("arquivo grande demais dentro do ZIP")
        with zf.open(i) as f:
            conteudo = f.read(ATU_MAX_ARQ + 1)
        if len(conteudo) > ATU_MAX_ARQ:
            raise ValueError("arquivo grande demais dentro do ZIP")
        saida[n] = conteudo
    if "th_boost.py" not in saida:
        raise ValueError("o ZIP não tem o th_boost.py")
    try:
        texto = saida["th_boost.py"].decode("utf-8")
        compile(texto, "th_boost.py", "exec")
    except (UnicodeDecodeError, SyntaxError, ValueError):
        raise ValueError("o th_boost.py novo está com defeito; nada foi trocado")
    m = re.search(r'^VERSAO = "(v[\d.]+)"', texto, re.M)
    if not m or versao_tupla(m.group(1)) != versao_tupla(info["versao"]):
        raise ValueError("a versão dentro do ZIP não é a anunciada; nada foi trocado")
    return saida


def atu_trocar_arquivos(arquivos, pasta):
    """Guarda os arquivos atuais em 'versao_anterior' e troca pelos novos.
    O th_boost.py é o que importa: se ele não puder ser trocado, nada muda. Os outros (ícone, LEIAME, .bat) podem estar
    em uso pelo Windows (o ícone da bandeja, por exemplo); esses ficam como estão e o resto segue."""
    principal = "th_boost.py"
    if principal not in arquivos:
        raise ValueError("falta o th_boost.py")
    copia = os.path.join(pasta, "versao_anterior")
    os.makedirs(copia, exist_ok=True)
    for n in arquivos:
        atual = os.path.join(pasta, n)
        if os.path.isfile(atual):
            try:
                shutil.copy2(atual, os.path.join(copia, n))
            except OSError:
                if n == principal:
                    raise  # sem a cópia do programa atual, não troca nada
    def troca(n):
        tmp = os.path.join(pasta, n + ".novo")
        try:
            with open(tmp, "wb") as f:
                f.write(arquivos[n])
            os.replace(tmp, os.path.join(pasta, n))
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
    troca(principal)
    trocados = [principal]
    for n in arquivos:
        if n != principal:
            try:
                troca(n)
                trocados.append(n)
            except OSError:
                pass  # arquivo em uso: fica o antigo
    return trocados


# v9.1: vigia da atualização. Roda separado (o Th Boost antigo já fechou). Se a versão nova não avisar que abriu em até
# 2 minutos, devolve o th_boost.py guardado em "versao_anterior" e abre a versão de antes.
ATU_VIGIA = r"""
import os, sys, time, shutil, subprocess
pasta, exe, nova, pid = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
espera = float(sys.argv[5]) if len(sys.argv) > 5 else 120.0
ok = os.path.join(pasta, "versao_anterior", "atu_ok")
ini = time.time()
h = None
if os.name == "nt":  # segura o processo pelo "identificador": assim o número dele não é reaproveitado por outro programa
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    k32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    h = k32.OpenProcess(0x00100000 | 0x0001, False, pid)  # SYNCHRONIZE | PROCESS_TERMINATE
while time.time() - ini < espera:
    try:
        if os.path.getmtime(ok) >= ini - 5:
            sys.exit(0)
    except OSError:
        pass
    time.sleep(1)
try:
    if os.name == "nt":
        if h and k32.WaitForSingleObject(h, 0) == 0x102:  # ainda rodando (travado): fecha só ele
            k32.TerminateProcess(h, 1)
            k32.WaitForSingleObject(h, 5000)
    else:
        os.kill(pid, 9)
except Exception:
    pass
copia = os.path.join(pasta, "versao_anterior", "th_boost.py")
alvo = os.path.join(pasta, "th_boost.py")
try:
    shutil.copyfile(copia, alvo + ".volta")
    os.replace(alvo + ".volta", alvo)
except OSError:
    sys.exit(1)
fl = (0x00000008 | 0x00000200 | 0x08000000) if os.name == "nt" else 0
kw = {"creationflags": fl} if os.name == "nt" else {"start_new_session": True}
subprocess.Popen([exe, alvo, "--reinicio", "--falhou", nova], cwd=pasta, close_fds=True, stdin=subprocess.DEVNULL,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
"""


def _atu_popen(args):
    opc = {"cwd": pasta_do_programa(), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
           "stderr": subprocess.DEVNULL, "close_fds": True}
    if IS_WIN:
        opc["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
    else:
        opc["start_new_session"] = True
    return subprocess.Popen(args, **opc)


def atu_reabrir(versao_antiga, versao_nova=""):
    """Abre o Th Boost novo (que espera este aqui fechar) e o vigia da atualização. Devolve True se conseguiu."""
    script = os.path.join(pasta_do_programa(), "th_boost.py")
    exe = sys.executable
    if IS_WIN and os.path.basename(exe).lower() == "python.exe":
        w = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(w):
            exe = w
    try:
        novo = _atu_popen([exe, script, "--reinicio", "--de", versao_antiga])
    except OSError:
        return False
    if versao_nova and os.path.isfile(os.path.join(pasta_do_programa(), "versao_anterior", "th_boost.py")):
        try:
            _atu_popen([exe, "-I", "-c", ATU_VIGIA, pasta_do_programa(), exe, versao_nova, str(novo.pid),
                        os.environ.get("THBOOST_ATU_VIGIA", "120")])
        except OSError:
            pass  # sem o vigia a atualização segue igual (só não volta sozinha se a nova falhar)
    return True


def atu_avisar_que_abriu():
    """Chamado pela versão nova logo que abre: o vigia vê este arquivo e não desfaz nada."""
    try:
        caminho = os.path.join(pasta_do_programa(), "versao_anterior", "atu_ok")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(VERSAO)
    except OSError:
        pass


def atu_falhou_argv():
    """Versão que não conseguiu abrir ('--falhou v9.2'), quando o vigia voltou para esta."""
    a = sys.argv[1:]
    if "--falhou" in a:
        i = a.index("--falhou")
        if i + 1 < len(a) and versao_tupla(a[i + 1]):
            return a[i + 1][:12]
    return ""


def atu_de_argv():
    """Versão anterior quando o programa foi reaberto por uma atualização ('--de v8.9')."""
    a = sys.argv[1:]
    if "--de" in a:
        i = a.index("--de")
        if i + 1 < len(a) and versao_tupla(a[i + 1]):
            return a[i + 1][:12]
    return ""


class AtualizaMixin:
    """Estado do aviso de versão nova (vai para a tela) e as ações Procurar / Atualizar."""

    def atu_iniciar_estado(self):
        congelado = bool(getattr(sys, "frozen", False))  # rodando como .exe: troca de arquivo não serve, abre o link
        self.atu = {"estado": "parado", "atual": VERSAO, "nova": "", "novidades": [], "pct": 0, "erro": "",
                    "quando": 0, "de": atu_de_argv(), "modo": "link" if congelado else "auto", "falhou": atu_falhou_argv()}
        self.atu_info = None
        self._atu_trava = threading.Lock()
        if self.atu["falhou"]:
            CONFIG["atu_pular"] = self.atu["falhou"]  # não fica oferecendo sozinho a versão que não abriu aqui
            salvar_config()
            self.msg(f"A versão {self.atu['falhou']} não abriu neste computador, então voltei para a {VERSAO}. "
                     "Nada foi perdido. Avise o dono do Th Boost.")
        if not os.environ.get("THBOOST_SEM_ATU"):
            threading.Thread(target=self._atu_vigiar, daemon=True).start()

    def atu_snapshot(self):
        return dict(self.atu, novidades=list(self.atu["novidades"]), avisar=CONFIG.get("avisar_atualizacao", True) is not False)

    def _atu_vigiar(self):
        time.sleep(float(os.environ.get("THBOOST_ATU_ESPERA", "20")))  # deixa o programa abrir primeiro
        while not self.fechando:
            if CONFIG.get("avisar_atualizacao", True) is not False and self.atu["estado"] in ("parado", "em_dia", "disponivel", "falhou"):
                self.atu_procurar(manual=False)
            time.sleep(ATU_INTERVALO)

    def atu_procurar(self, manual=True):
        if not self._atu_trava.acquire(blocking=False):
            return
        try:
            if self.atu["estado"] in ("baixando", "instalando", "reiniciando"):
                return
            antes = self.atu["estado"]
            self.atu.update(estado="procurando", erro="")
            try:
                info = atu_buscar_info()
            except Exception as e:
                # procura automática sem internet: fica quieto; a pedido, conta o que houve
                self.atu.update(estado="falhou" if manual else (antes if antes != "procurando" else "parado"),
                                erro="Não deu para procurar agora (sem internet?)." if manual else "")
                return
            self.atu["quando"] = time.time()
            if not manual and info["versao"] == CONFIG.get("atu_pular"):
                self.atu_info = None
                self.atu.update(estado="em_dia", nova="", novidades=[])
                return
            if atu_mais_nova(info["versao"], VERSAO):
                self.atu_info = info
                self.atu.update(estado="disponivel", nova=info["versao"], novidades=info["novidades"])
                if antes != "disponivel":
                    self.msg(f"Versão nova do Th Boost: {info['versao']}. Clique em Atualizar no aviso.")
            else:
                self.atu_info = None
                self.atu.update(estado="em_dia", nova="", novidades=[])
        finally:
            self._atu_trava.release()

    def atu_instalar(self):
        info = self.atu_info
        if not info or self.atu["estado"] != "disponivel":
            raise ValueError("não há versão nova para instalar")
        if self.atu["modo"] == "link":  # .exe: abre a página para baixar
            abrir_link(ATU_PAGINA)
            self.msg("Abri a página do Th Boost para baixar a versão nova.")
            return
        self.atu.update(estado="baixando", pct=0, erro="")

        def tarefa():
            info2 = info
            try:
                try:  # lê o versao.json de novo: se o dono publicou outra versão (ou corrigiu o ZIP), já pega a certa
                    novo = atu_buscar_info()
                    if atu_mais_nova(novo["versao"], VERSAO):
                        info2 = self.atu_info = novo
                        self.atu.update(nova=novo["versao"], novidades=novo["novidades"])
                except Exception:
                    pass
                dados = atu_baixar(info2["zip"], ATU_MAX_ZIP, progresso=lambda p: self.atu.update(pct=p), timeout=60)
                self.atu.update(estado="instalando", pct=100)
                arquivos = atu_conferir_zip(dados, info2)
                atu_trocar_arquivos(arquivos, pasta_do_programa())
            except Exception as e:
                motivo = str(e) if isinstance(e, ValueError) else "não consegui baixar ou gravar os arquivos (internet ou pasta sem permissão)"
                self.atu.update(estado="disponivel", erro=f"A atualização não deu certo: {motivo}. O Th Boost continua na {VERSAO}.")
                return
            self.atu.update(estado="reiniciando")
            if not atu_reabrir(VERSAO, info2["versao"]):
                self.atu.update(estado="disponivel", erro="Os arquivos novos foram instalados, mas não consegui abrir o Th Boost de novo. Feche e abra pelo atalho.")
                return
            time.sleep(1.2)  # dá tempo da tela receber o "reiniciando"
            self.encerrar()

        threading.Thread(target=tarefa, daemon=True).start()
