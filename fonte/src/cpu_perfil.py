# ---------------- perfil de desempenho da CPU (página Processador) ----------------
#
# O clock real do processador (overclock de verdade) só é mudado na BIOS da placa-mãe: nenhum programa do Windows faz isso
# com segurança, igual à memória RAM. O que o Windows deixa ajustar é COMO o processador se comporta: quão rápido sobe de
# velocidade, se o turbo fica liberado e se algum núcleo pode "dormir". É isso que os perfis abaixo mexem, no plano de
# energia que estiver ativo e só na tomada (na bateria nada muda).
#   Padrão do Windows = o plano do jeito que estava antes do Th Boost mexer (é o que a página mostra ao abrir);
#   Desempenho        = sobe de clock rápido, núcleos acordados, turbo liberado;
#   Máximo            = sempre em velocidade alta, turbo no máximo, preferência total por desempenho.
# Antes de mudar, o Th Boost guarda os valores originais no th_boost_config.json e "Padrão do Windows" devolve exatamente eles.

_SUB_PROC = "54533251-82be-4824-96c1-47b60b740d00"
_CFG_CPU = {
    "min": (_SUB_PROC, "893dee8e-2bef-41e0-89c6-b55d0929964c"),      # estado mínimo do processador (%)
    "max": (_SUB_PROC, "bc5038f7-23e0-4960-96da-33abaf5935ec"),      # estado máximo do processador (%)
    "nucleos": (_SUB_PROC, "0cc5b647-c1df-4637-891a-dec35c318583"),  # núcleos que ficam sempre acordados (%)
    "turbo": (_SUB_PROC, "be337238-0d82-4146-a960-4f3749d470c7"),    # modo do turbo (2 = agressivo)
    "turbo_pol": (_SUB_PROC, "45bcc044-d885-43e2-8605-ee0ec6e96b59"),  # política do turbo (%)
    "epp": (_SUB_PROC, "36687f9e-e3a5-4dbf-b1dc-15eb381c6863"),      # preferência energia x desempenho (0 = desempenho)
    "ventoinha": (_SUB_PROC, "94d3a615-a899-4ac5-ae2b-e4d8f634367f"),  # refrigeração ativa (1)
}
PERFIS_CPU = {
    "desempenho": {"min": 50, "max": 100, "nucleos": 100, "turbo": 2, "epp": 30, "ventoinha": 1},
    "maximo": {"min": 100, "max": 100, "nucleos": 100, "turbo": 2, "turbo_pol": 100, "epp": 0, "ventoinha": 1},
    # v8.8: perfis para ESFRIAR o PC ou o notebook (página Resfriamento): o turbo é a velocidade extra que mais esquenta
    "fresco": {"max": 90, "turbo": 0, "epp": 60, "ventoinha": 1},
    "gelado": {"min": 5, "max": 70, "turbo": 0, "epp": 80, "ventoinha": 1},
}
NOMES_CPU = {"padrao": "Padrão do Windows", "desempenho": "Desempenho", "maximo": "Máximo", "fresco": "Fresco", "gelado": "Gelado"}
_TEXTOS_CPU = [
    {"id": "padrao", "titulo": "Padrão do Windows", "tag": "0%",
     "texto": "O processador se comporta do jeito que o seu plano de energia já tinha. É assim que a página abre.",
     "itens": ["Nada é mexido", "Se o Th Boost mudou algo antes, isso volta exatamente como estava"]},
    {"id": "desempenho", "titulo": "Desempenho", "tag": "MÉDIO",
     "texto": "O processador sobe de velocidade mais rápido, nenhum núcleo dorme e o turbo fica liberado. Esquenta e gasta um pouco mais.",
     "itens": ["Velocidade mínima: 50%", "Núcleos sempre acordados: 100%", "Turbo agressivo", "Preferência por desempenho"]},
    {"id": "maximo", "titulo": "Máximo", "tag": "ALTO",
     "texto": "Processador sempre em velocidade alta, turbo no máximo e preferência total por desempenho. Mais calor, ventoinha mais alta e mais consumo: bom para jogar, na tomada.",
     "itens": ["Velocidade mínima: 100%", "Núcleos sempre acordados: 100%", "Turbo agressivo e política 100%", "Preferência: só desempenho", "Ventoinha ativa"]},
]
_TEXTOS_FRIO = [
    {"id": "padrao", "titulo": "Normal", "tag": "NORMAL",
     "texto": "O processador se comporta do jeito que o seu plano de energia já tinha. Se o Th Boost esfriou o PC antes, tudo volta exatamente como estava.",
     "itens": ["Nada é mexido", "Os valores de antes voltam inteiros"]},
    {"id": "fresco", "titulo": "Fresco", "tag": "MAIS FRIO",
     "texto": "O processador não passa de 90% da velocidade e o turbo (a velocidade extra, que é o que mais esquenta) fica desligado. Costuma baixar vários graus e quase não se nota no dia a dia.",
     "itens": ["Velocidade máxima: 90%", "Turbo desligado", "Prefere gastar menos energia", "Ventoinha ativa antes de reduzir a velocidade"]},
    {"id": "gelado", "titulo": "Gelado", "tag": "BEM FRIO",
     "texto": "O processador não passa de 70%, sem turbo, e volta a ficar bem lento quando está parado. É o que mais esfria, mas o PC fica mais devagar em tarefas pesadas e em jogos.",
     "itens": ["Velocidade máxima: 70%", "Velocidade mínima: 5%", "Turbo desligado", "Prefere economizar energia", "Ventoinha ativa antes de reduzir a velocidade"]},
]
_ROTULOS_CPU = {"min": "Velocidade mínima", "max": "Velocidade máxima", "nucleos": "Núcleos sempre acordados", "turbo": "Modo do turbo",
                "turbo_pol": "Política do turbo", "epp": "Preferência por desempenho", "ventoinha": "Ventoinha ativa"}


# Temperatura: o Windows só informa a "zona térmica" da placa (ACPI), que em muitos notebooks acompanha o calor do processador e em
# alguns PCs de mesa é um número fixo. Por isso a página chama de aproximada. Precisa de Administrador. Lê em segundo plano e guarda
# por 20 segundos, para a tela não esperar o PowerShell.
PS_TEMP_ZONA = ("$t=@(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | "
                "ForEach-Object {[math]::Round($_.CurrentTemperature/10-273.15)}); if($t.Count){($t | Measure-Object -Maximum).Maximum}")
_TEMP_ZONA = {"v": None, "t": 0.0, "lendo": False}


def interpretar_temp_zona(saida):
    """O número que o PowerShell imprimiu -> graus Celsius plausíveis (10 a 120), ou None. Função pura."""
    m = re.fullmatch(r"\s*(-?\d{1,3})(?:[.,]\d+)?\s*", saida or "")
    if not m:
        return None
    v = int(m.group(1))
    return v if 10 <= v <= 120 else None


def _atualizar_temp_zona():
    try:
        cod, saida = powershell(PS_TEMP_ZONA, tempo=25)
        _TEMP_ZONA["v"] = interpretar_temp_zona(saida) if cod == 0 else None
    except Exception:
        _TEMP_ZONA["v"] = None
    _TEMP_ZONA["t"] = time.time()
    _TEMP_ZONA["lendo"] = False


def temperatura_zona_windows():
    """(graus ou None, de onde veio). Nunca espera: devolve o que já foi lido e pede uma leitura nova em segundo plano."""
    if not IS_WIN:
        return None, ""
    if time.time() - _TEMP_ZONA["t"] > 20 and not _TEMP_ZONA["lendo"]:
        _TEMP_ZONA["lendo"] = True
        threading.Thread(target=_atualizar_temp_zona, daemon=True).start()
    return _TEMP_ZONA["v"], ("zona térmica do Windows" if _TEMP_ZONA["v"] is not None else "")


def _hex_ac(saida):
    """O valor de CA (tomada) que o 'powercfg /query' imprime. As duas últimas linhas com 0x são CA e CC, em qualquer idioma."""
    achados = re.findall(r"0x[0-9a-fA-F]{8}", saida or "")
    return int(achados[-2], 16) if len(achados) >= 2 else None


def cpu_plano_ativo():
    """(guid, nome) do plano de energia ativo, ou (None, '')."""
    cod, saida = executar(["powercfg", "/getactivescheme"])
    m = re.search(rf"({_GUID})\s*(?:\(([^)]*)\))?", saida or "") if cod == 0 else None
    return (m.group(1).lower(), (m.group(2) or "").strip()) if m else (None, "")


def cpu_valores_ac(guid):
    """Valores atuais (tomada) de cada ajuste de CPU do plano. None onde o Windows não informa."""
    saida = {}
    for chave, (sub, cfg) in _CFG_CPU.items():
        cod, txt = executar(["powercfg", "/qh", guid, sub, cfg])  # v9.1: /qh mostra também os ajustes escondidos
        saida[chave] = _hex_ac(txt) if cod == 0 else None
    return saida


def cpu_perfil_detectar(valores):
    """Qual perfil os valores de agora já correspondem: 'maximo', 'desempenho', 'gelado', 'fresco' ou 'padrao'."""
    for nome in ("maximo", "desempenho", "gelado", "fresco"):
        comparaveis = [(k, v) for k, v in PERFIS_CPU[nome].items() if valores.get(k) is not None]  # o que o PC não tem não conta
        if len(comparaveis) >= 3 and all(valores[k] == v for k, v in comparaveis):
            return nome
    return "padrao"


def cpu_x3d_duplo(nome=None, logicos=None):
    """AMD Ryzen X3D com mais de 8 núcleos (dois blocos, só um com V-Cache). Função pura quando recebe os dados."""
    nome = nome if nome is not None else (nome_do_processador() if IS_WIN else "")
    logicos = logicos if logicos is not None else (psutil.cpu_count() or 0)
    return bool(re.search(r"X3D\b", nome or "", re.I)) and logicos > 16


def cpu_alvo(nivel, antes):
    """Valor de cada ajuste ao ir para um perfil: o do perfil, ou o original guardado nos que o perfil não mexe. Função pura."""
    perfil = PERFIS_CPU.get(nivel) or {}
    alvo = {}
    for chave in _CFG_CPU:
        if antes.get(chave) is None:
            continue  # v9.1: sem o valor original guardado, não mexe (não daria para voltar depois)
        v = perfil.get(chave, antes.get(chave))
        if isinstance(v, int) and not isinstance(v, bool):
            alvo[chave] = v
    return alvo


class CpuPerfilMixin:
    """Perfis de desempenho da CPU (página Processador)."""

    def cpu_perfil_iniciar_estado(self):
        self._cpup = {"t": 0.0, "dados": None}
        self._cpup_trava = threading.Lock()

    @staticmethod
    def _cpup_cfg():
        c = CONFIG.get("cpu_perfil")
        return c if isinstance(c, dict) and c.get("nivel") in PERFIS_CPU and isinstance(c.get("antes"), dict) else None

    def cpu_perfil_lista(self):
        """O que a página Processador mostra. Lê o plano com o powercfg (guarda por 4 segundos)."""
        agora = time.time()
        with self._cpup_trava:
            if self._cpup["dados"] and agora - self._cpup["t"] < 4.0:
                return self._cpup["dados"]
            freq = None
            try:
                freq = psutil.cpu_freq()
            except Exception:
                pass
            d = {"windows": bool(IS_WIN), "admin": e_admin(), "cpu": nome_do_processador() if IS_WIN else "",
                 "fisicos": psutil.cpu_count(logical=False) or 0, "logicos": psutil.cpu_count() or 0,
                 "mhz": round(freq.current) if freq and freq.current else None, "mhz_max": round(freq.max) if freq and freq.max else None,
                 "perfis": _TEXTOS_CPU, "frios": _TEXTOS_FRIO, "rotulos": _ROTULOS_CPU, "temp": None, "temp_fonte": "", "uso": None, "plano": "", "valores": {}, "atual": "padrao", "aplicado": False,
                 "guardado": False}
            try:
                d["uso"] = round(psutil.cpu_percent(interval=None))
            except Exception:
                pass
            if IS_WIN:
                d["temp"], d["temp_fonte"] = temperatura_zona_windows()
                guid, nome = cpu_plano_ativo()
                if guid:
                    d["plano"] = nome
                    d["valores"] = cpu_valores_ac(guid)
                    d["atual"] = cpu_perfil_detectar(d["valores"])
                cfg = self._cpup_cfg()
                d["aplicado"] = bool(cfg and cfg["nivel"] == d["atual"])
                d["guardado"] = bool(cfg)
            self._cpup.update(t=agora, dados=d)
            return d

    def cpu_perfil_definir(self, nivel):
        if nivel not in NOMES_CPU:
            raise ValueError("perfil inválido")
        if not IS_WIN:
            return self.msg("O perfil da CPU só existe no Windows.")
        if not e_admin():
            return self.msg("Mudar o plano de energia precisa do Th Boost aberto como Administrador. Feche e abra pelo atalho da área de trabalho.")
        self.msg("Aplicando o perfil da CPU...")
        self.em_fundo(lambda: self.t_cpu_perfil_definir(nivel))

    def t_cpu_perfil_definir(self, nivel):
        trava = self.__dict__.setdefault("_cpup_aplicando", threading.Lock())
        if not trava.acquire(blocking=False):
            return "Já estou aplicando um perfil. Espere terminar."
        try:
            return self._t_cpu_perfil_definir(nivel)
        finally:
            trava.release()

    def _t_cpu_perfil_definir(self, nivel):
        planos = {p["guid"] for p in listar_planos()}
        cfg = self._cpup_cfg()
        if nivel == "padrao":
            if not cfg:
                return "A CPU já está no padrão do seu plano de energia: o Th Boost não tinha mudado nada."
            guid, antes = cfg.get("plano"), cfg["antes"]
            if guid not in planos:  # o plano que ele tinha mexido foi apagado
                CONFIG.pop("cpu_perfil", None)
                salvar_config()
                self._cpup["t"] = 0.0
                return "O plano de energia que o Th Boost tinha mudado não existe mais. Não há nada para desfazer."
            nivel_alvo = "padrao"
        else:
            guid, nome = cpu_plano_ativo()
            if not guid:
                return "Não consegui ler o plano de energia do Windows."
            if cfg and cfg.get("plano") == guid:
                antes = cfg["antes"]  # já guardado: nunca sobrescreve o original
            else:
                if cfg and cfg.get("plano") in planos:  # trocou de plano: devolve o antigo antes de mexer no novo
                    self._cpu_perfil_gravar(cfg["plano"], cpu_alvo("padrao", cfg["antes"]), False)
                antes = cpu_valores_ac(guid)
            nivel_alvo = nivel
        alvo = cpu_alvo(nivel_alvo, antes)
        if nivel_alvo == "padrao" and cfg and "turbo" not in alvo and "turbo" in (PERFIS_CPU.get(cfg.get("nivel")) or {}):
            # v9.1: versões antigas não conseguiam ler o turbo (ajuste escondido) e não o guardavam; o Fresco/Gelado o
            # desligavam e o "Normal" não o devolvia. Volta para o padrão do Windows na tomada (2 = agressivo).
            alvo["turbo"] = 2
        if nivel_alvo != "padrao" and cpu_x3d_duplo():
            alvo.pop("nucleos", None)  # v9.1: X3D de dois blocos: o driver da AMD cuida dos núcleos durante o jogo
        # v9.1: "Padrão" devolve os valores do plano guardado, mas só ativa esse plano se ele já era o ativo
        # (se você está na Extrema ou numa sessão de jogo, não troca de plano por baixo dela)
        ativar = nivel_alvo != "padrao" or cpu_plano_ativo()[0] == guid
        feitos = self._cpu_perfil_gravar(guid, alvo, ativar)
        if feitos < 2:  # não deixa pela metade: devolve o plano ao que estava
            anterior = cfg["nivel"] if cfg and cfg.get("plano") == guid else "padrao"
            self._cpu_perfil_gravar(guid, cpu_alvo(anterior, antes), ativar)
            return "O Windows recusou a mudança no plano de energia. Confira se abriu como Administrador."
        if nivel_alvo == "padrao":
            CONFIG.pop("cpu_perfil", None)
        else:
            CONFIG["cpu_perfil"] = {"nivel": nivel_alvo, "plano": guid, "antes": {k: v for k, v in antes.items() if isinstance(v, int)}}
        salvar_config()
        self._cpup["t"] = 0.0
        nomes = NOMES_CPU
        return f"Perfil da CPU: {nomes[nivel_alvo]}." + (" Os valores de antes voltaram." if nivel_alvo == "padrao" else " Para desfazer, escolha Padrão do Windows.")

    @staticmethod
    def _cpu_perfil_gravar(guid, alvo, ativar):
        """Grava os valores no plano. Devolve quantos o Windows aceitou (o que o PC não tem é ignorado)."""
        feitos = 0
        for chave, valor in alvo.items():
            sub, cfg = _CFG_CPU[chave]
            cod, _ = executar(["powercfg", "/setacvalueindex", guid, sub, cfg, str(int(valor))])
            feitos += 1 if cod == 0 else 0
        if ativar:
            executar(["powercfg", "/setactive", guid])
        return feitos
