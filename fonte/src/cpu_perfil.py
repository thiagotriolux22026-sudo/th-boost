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
}
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
_ROTULOS_CPU = {"min": "Velocidade mínima", "max": "Velocidade máxima", "nucleos": "Núcleos sempre acordados", "turbo": "Modo do turbo",
                "turbo_pol": "Política do turbo", "epp": "Preferência por desempenho", "ventoinha": "Ventoinha ativa"}


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
        cod, txt = executar(["powercfg", "/query", guid, sub, cfg])
        saida[chave] = _hex_ac(txt) if cod == 0 else None
    return saida


def cpu_perfil_detectar(valores):
    """Qual perfil os valores de agora já correspondem: 'maximo', 'desempenho' ou 'padrao'."""
    for nome in ("maximo", "desempenho"):
        comparaveis = [(k, v) for k, v in PERFIS_CPU[nome].items() if valores.get(k) is not None]  # o que o PC não tem não conta
        if len(comparaveis) >= 3 and all(valores[k] == v for k, v in comparaveis):
            return nome
    return "padrao"


def cpu_alvo(nivel, antes):
    """Valor de cada ajuste ao ir para um perfil: o do perfil, ou o original guardado nos que o perfil não mexe. Função pura."""
    perfil = PERFIS_CPU.get(nivel) or {}
    alvo = {}
    for chave in _CFG_CPU:
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
                 "perfis": _TEXTOS_CPU, "rotulos": _ROTULOS_CPU, "plano": "", "valores": {}, "atual": "padrao", "aplicado": False,
                 "guardado": False}
            if IS_WIN:
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
        if nivel not in ("padrao", "desempenho", "maximo"):
            raise ValueError("perfil inválido")
        if not IS_WIN:
            return self.msg("O perfil da CPU só existe no Windows.")
        if not e_admin():
            return self.msg("Mudar o plano de energia precisa do Th Boost aberto como Administrador. Feche e abra pelo atalho da área de trabalho.")
        self.msg("Aplicando o perfil da CPU...")
        self.em_fundo(lambda: self.t_cpu_perfil_definir(nivel))

    def t_cpu_perfil_definir(self, nivel):
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
        feitos = self._cpu_perfil_gravar(guid, alvo, True)
        if feitos < 2:  # não deixa pela metade: devolve o plano ao que estava
            anterior = cfg["nivel"] if cfg and cfg.get("plano") == guid else "padrao"
            self._cpu_perfil_gravar(guid, cpu_alvo(anterior, antes), True)
            return "O Windows recusou a mudança no plano de energia. Confira se abriu como Administrador."
        if nivel_alvo == "padrao":
            CONFIG.pop("cpu_perfil", None)
        else:
            CONFIG["cpu_perfil"] = {"nivel": nivel_alvo, "plano": guid, "antes": {k: v for k, v in antes.items() if isinstance(v, int)}}
        salvar_config()
        self._cpup["t"] = 0.0
        nomes = {"padrao": "Padrão do Windows", "desempenho": "Desempenho", "maximo": "Máximo"}
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
