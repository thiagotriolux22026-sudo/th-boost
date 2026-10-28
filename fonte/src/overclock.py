# ---------------- overclock da placa de vídeo NVIDIA (a barra de 0 a 150%) ----------------
#
# Como funciona: o Th Boost fala com a NVML, a biblioteca que já vem no driver da NVIDIA (a mesma que o nvidia-smi usa).
# Uma barra só, de 0 a 150%, sobe três coisas juntas: o clock do núcleo, o clock da memória e o limite de potência.
#   0%   = padrão da placa (é onde a barra SEMPRE começa quando o programa abre);
#   150% = o máximo que o Th Boost aplica: núcleo +OC_NUCLEO_150 MHz, memória +OC_MEM_150 MHz e potência no teto da placa.
# Cada valor também fica limitado ao que a própria placa/driver informa como permitido. Placa de vídeo não aguenta
# "150% de clock": a barra é uma escala do que é seguro tentar, e quem manda no limite é a placa.
#
# Travas de segurança:
#  - nada fica gravado na placa: tudo volta ao padrão ao reiniciar o PC;
#  - o Th Boost zera ao fechar, e ao abrir se a vez anterior fechou do nada com o overclock ligado;
#  - se a placa passar de OC_TEMP_LIMITE graus, volta sozinho a 0%;
#  - precisa de Administrador e de placa NVIDIA com driver novo; AMD e Intel não são mexidas.

OC_MAX = 150
OC_PASSO = 5
OC_NUCLEO_150 = 150     # MHz no núcleo quando a barra está em 150%
OC_MEM_150 = 500        # MHz na memória quando a barra está em 150%
OC_TEMP_LIMITE = 88     # graus: passou disso, o overclock é desligado sozinho
OC_TEMP_AVISO = 83      # graus: a tela avisa que está esquentando

_NVML_ERROS = {1: "a NVML não foi iniciada", 2: "valor recusado pela placa", 3: "esta placa ou este driver não aceita esse ajuste",
               4: "precisa abrir o Th Boost como Administrador", 9: "o driver da NVIDIA não está carregado",
               13: "este driver é antigo demais para esse ajuste (atualize o driver da NVIDIA)", 15: "a placa parou de responder",
               16: "a placa pede reinício do PC", 17: "o Windows bloqueou o ajuste"}


def oc_plano(nivel, teto):
    """(núcleo MHz, memória MHz, watts) para um nível de 0 a 150. teto = {core, mem, padrao, max}. Função pura."""
    try:
        n = max(0, min(OC_MAX, int(nivel)))
    except (TypeError, ValueError):
        n = 0
    f = n / float(OC_MAX)
    tc, tm = teto.get("core") or 0, teto.get("mem") or 0
    core = min(int(round(f * tc / 15.0)) * 15, tc) if tc else 0  # arredonda para o passo da placa, sem passar do limite dela
    mem = min(int(round(f * tm / 25.0)) * 25, tm) if tm else 0
    pad, mx = teto.get("padrao") or 0, teto.get("max") or 0
    watts = int(round(pad + f * (mx - pad))) if pad and mx > pad else int(pad)
    return core, mem, watts


def oc_tabela(teto):
    """Uma linha por passo da barra: [nível, núcleo, memória, watts]. A tela só escolhe a linha (nunca refaz a conta)."""
    return [[n, *oc_plano(n, teto)] for n in range(0, OC_MAX + 1, OC_PASSO)]


class _Nvml:
    """Envelope fino em volta da NVML (ctypes). Nunca levanta erro: devolve o código da NVML (0 = deu certo)."""

    _SIGS = {
        "nvmlInit_v2": [], "nvmlShutdown": [],
        "nvmlDeviceGetHandleByIndex_v2": [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)],
        "nvmlDeviceGetName": [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint],
        "nvmlDeviceGetTemperature": [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceGetClockInfo": [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceGetPowerUsage": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceGetPowerManagementLimit": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceGetPowerManagementDefaultLimit": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceGetPowerManagementLimitConstraints": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)],
        "nvmlDeviceSetPowerManagementLimit": [ctypes.c_void_p, ctypes.c_uint],
        "nvmlDeviceGetGpcClkVfOffset": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)],
        "nvmlDeviceSetGpcClkVfOffset": [ctypes.c_void_p, ctypes.c_int],
        "nvmlDeviceGetGpcClkMinMaxVfOffset": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
        "nvmlDeviceGetMemClkVfOffset": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)],
        "nvmlDeviceSetMemClkVfOffset": [ctypes.c_void_p, ctypes.c_int],
        "nvmlDeviceGetMemClkMinMaxVfOffset": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
    }

    def __init__(self):
        self.lib = None
        self.dev = None
        self.erro = ""
        self.tentou = False

    @staticmethod
    def _candidatas():
        extra = os.environ.get("TOTIMIZE_NVML")
        if extra:
            return [extra]
        if not IS_WIN:
            return []
        sistema = os.environ.get("SystemRoot", r"C:\Windows")
        arquivos = os.environ.get("ProgramFiles", r"C:\Program Files")
        return ["nvml.dll", os.path.join(sistema, "System32", "nvml.dll"),
                os.path.join(arquivos, "NVIDIA Corporation", "NVSMI", "nvml.dll")]

    def abrir(self):
        """Carrega a NVML e pega a primeira placa NVIDIA. True se deu certo."""
        if self.dev is not None:
            return True
        if self.tentou:
            return False
        self.tentou = True
        for caminho in self._candidatas():
            try:
                self.lib = ctypes.CDLL(caminho)
                break
            except OSError:
                self.lib = None
        if self.lib is None:
            self.erro = "Não achei a biblioteca da NVIDIA (nvml.dll): placa NVIDIA e driver instalados?"
            return False
        for nome, args in self._SIGS.items():
            f = getattr(self.lib, nome, None)
            if f is not None:
                f.restype = ctypes.c_int
                f.argtypes = args
        if self.chamar("nvmlInit_v2") not in (0, 5):
            self.erro = "A biblioteca da NVIDIA não iniciou."
            self.lib = None
            return False
        h = ctypes.c_void_p()
        if self.chamar("nvmlDeviceGetHandleByIndex_v2", 0, ctypes.byref(h)) != 0 or not h.value:
            self.erro = "Nenhuma placa NVIDIA encontrada."
            self.lib = None
            return False
        self.dev = h
        return True

    def chamar(self, nome, *args):
        f = getattr(self.lib, nome, None) if self.lib is not None else None
        if f is None:
            return 13
        try:
            return int(f(*args))
        except (OSError, ValueError, ctypes.ArgumentError):
            return 999

    def _com_dev(self, nome, *args):
        return self.chamar(nome, self.dev, *args)

    def u32(self, nome):
        v = ctypes.c_uint()
        cod = self._com_dev(nome, ctypes.byref(v))
        return cod, (v.value if cod == 0 else None)

    def u32_dois(self, nome):
        a, b = ctypes.c_uint(), ctypes.c_uint()
        cod = self._com_dev(nome, ctypes.byref(a), ctypes.byref(b))
        return cod, ((a.value, b.value) if cod == 0 else None)

    def i32(self, nome):
        v = ctypes.c_int()
        cod = self._com_dev(nome, ctypes.byref(v))
        return cod, (v.value if cod == 0 else None)

    def i32_dois(self, nome):
        a, b = ctypes.c_int(), ctypes.c_int()
        cod = self._com_dev(nome, ctypes.byref(a), ctypes.byref(b))
        return cod, ((a.value, b.value) if cod == 0 else None)

    def definir(self, nome, valor):
        return self._com_dev(nome, int(valor))

    def nome(self):
        buf = ctypes.create_string_buffer(96)
        if self._com_dev("nvmlDeviceGetName", buf, 96) != 0:
            return "Placa NVIDIA"
        return buf.value.decode("utf-8", "replace").strip() or "Placa NVIDIA"

    def temperatura(self):
        v = ctypes.c_uint()
        return int(v.value) if self._com_dev("nvmlDeviceGetTemperature", 0, ctypes.byref(v)) == 0 else None

    def clock(self, tipo):
        """Clock de agora em MHz (tipo 0 = núcleo, 2 = memória). None se não der para ler."""
        v = ctypes.c_uint()
        return int(v.value) if self._com_dev("nvmlDeviceGetClockInfo", tipo, ctypes.byref(v)) == 0 else None


def _motivo_nvml(cod):
    return _NVML_ERROS.get(cod, f"erro {cod} da biblioteca da NVIDIA")


class OverclockMixin:
    """Barra de overclock da placa de vídeo (página GPU & NVIDIA)."""

    def oc_iniciar_estado(self):
        self.oc_nv = _Nvml()
        self._oc_trava = threading.RLock()
        self._oc = {"nivel": 0, "info": None, "aviso": "", "pronto": False}
        if CONFIG.get("oc_ativo"):  # a vez anterior fechou sem zerar: volta tudo ao padrão antes de qualquer coisa
            threading.Thread(target=self._oc_zerar_antigo, daemon=True).start()
        threading.Thread(target=self._vigiar_oc, daemon=True).start()

    # ----- leitura -----

    def _oc_ler(self):
        """Lê a placa: limites, valores de agora e a tabela da barra. Sempre devolve um dict."""
        nv = self.oc_nv
        if not nv.abrir():
            return {"suporte": False, "motivo": nv.erro or "Sem placa NVIDIA."}
        i = {"suporte": True, "nome": nv.nome()}
        cod_f, faixa = nv.i32_dois("nvmlDeviceGetGpcClkMinMaxVfOffset")
        cod_a, agora = nv.i32("nvmlDeviceGetGpcClkVfOffset")
        i["nucleo"] = {"ok": cod_f == 0 and cod_a == 0, "agora": agora or 0, "max": max(0, faixa[1]) if faixa else 0,
                       "motivo": "" if cod_f == 0 and cod_a == 0 else _motivo_nvml(cod_f or cod_a)}
        cod_f, faixa = nv.i32_dois("nvmlDeviceGetMemClkMinMaxVfOffset")
        cod_a, agora = nv.i32("nvmlDeviceGetMemClkVfOffset")
        i["memoria"] = {"ok": cod_f == 0 and cod_a == 0, "agora": agora or 0, "max": max(0, faixa[1]) if faixa else 0,
                        "motivo": "" if cod_f == 0 and cod_a == 0 else _motivo_nvml(cod_f or cod_a)}
        cod_p, padrao = nv.u32("nvmlDeviceGetPowerManagementDefaultLimit")
        cod_l, limites = nv.u32_dois("nvmlDeviceGetPowerManagementLimitConstraints")
        cod_n, atual = nv.u32("nvmlDeviceGetPowerManagementLimit")
        pot_ok = cod_p == 0 and cod_l == 0 and cod_n == 0
        i["potencia"] = {"ok": pot_ok, "agora": round((atual or 0) / 1000.0), "padrao": round((padrao or 0) / 1000.0),
                         "min": round(limites[0] / 1000.0) if limites else 0, "max": round(limites[1] / 1000.0) if limites else 0,
                         "padrao_mw": padrao or 0, "min_mw": limites[0] if limites else 0, "max_mw": limites[1] if limites else 0,
                         "motivo": "" if pot_ok else _motivo_nvml(cod_p or cod_l or cod_n)}
        i["temp"] = nv.temperatura()
        i["mhz"] = nv.clock(0)
        i["mhz_mem"] = nv.clock(2)
        cod_u, uso = nv.u32("nvmlDeviceGetPowerUsage")
        i["consumo"] = round(uso / 1000.0) if cod_u == 0 and uso is not None else None
        teto = {"core": min(OC_NUCLEO_150, i["nucleo"]["max"]) if i["nucleo"]["ok"] else 0,
                "mem": min(OC_MEM_150, i["memoria"]["max"]) if i["memoria"]["ok"] else 0,
                "padrao": i["potencia"]["padrao"] if pot_ok else 0, "max": i["potencia"]["max"] if pot_ok else 0}
        i["teto"] = teto
        i["tabela"] = oc_tabela(teto)
        i["algum"] = bool(i["nucleo"]["ok"] or i["memoria"]["ok"] or pot_ok)
        return i

    def oc_estado(self):
        o = self._oc
        return {"info": o["info"], "nivel": o["nivel"], "aviso": o["aviso"], "pronto": o["pronto"],
                "limite_temp": OC_TEMP_LIMITE, "max": OC_MAX, "passo": OC_PASSO}

    # ----- aplicar -----

    def oc_definir(self, nivel):
        if not isinstance(nivel, int) or isinstance(nivel, bool) or not 0 <= nivel <= OC_MAX:
            raise ValueError("nível inválido")
        if nivel and not e_admin():
            return self.msg("O overclock precisa do Th Boost aberto como Administrador. Feche e abra pelo atalho da área de trabalho.")
        self.msg("Aplicando o overclock..." if nivel else "Voltando a placa ao padrão...")
        self.em_fundo(lambda: self.t_oc_definir(nivel))

    def t_oc_definir(self, nivel, motivo=""):
        with self._oc_trava:
            nv = self.oc_nv
            info = self._oc_ler()
            if not info["suporte"]:
                return info["motivo"]
            if not info["algum"]:
                return "Esta placa não aceita overclock por aqui: " + (info["nucleo"]["motivo"] or info["potencia"]["motivo"]) + "."
            core, mem, watts = oc_plano(nivel, info["teto"])
            passos = []  # (nome, função da NVML, valor, valor ao zerar, ok?)
            if info["potencia"]["ok"]:
                pot = info["potencia"]  # em miliwatts exatos: 0% devolve o padrão da placa sem arredondar
                alvo_mw = pot["padrao_mw"] if not nivel else max(pot["min_mw"], min(watts * 1000, pot["max_mw"]))
                passos.append(("potência", "nvmlDeviceSetPowerManagementLimit", alvo_mw, pot["padrao_mw"]))
            if info["memoria"]["ok"]:
                passos.append(("memória", "nvmlDeviceSetMemClkVfOffset", mem, 0))
            if info["nucleo"]["ok"]:
                passos.append(("núcleo", "nvmlDeviceSetGpcClkVfOffset", core, 0))
            falhas = []
            for nome, fn, valor, _ in passos:
                cod = nv.definir(fn, valor)
                if cod != 0:
                    falhas.append(f"{nome}: {_motivo_nvml(cod)}")
                    if nivel:
                        break
            if falhas and nivel:  # não deixa pela metade: volta tudo ao padrão
                for _, fn, _, zero in passos:
                    nv.definir(fn, zero)
                self._oc["nivel"] = 0
                CONFIG.pop("oc_ativo", None)
                salvar_config()
                return "Não consegui aplicar (" + "; ".join(falhas) + "). A placa ficou no padrão."
            self._oc["nivel"] = nivel
            self._oc["aviso"] = motivo
            if nivel:
                CONFIG["oc_ativo"] = True
            else:
                CONFIG.pop("oc_ativo", None)
            salvar_config()
            self._oc["info"] = self._oc_ler()
            if not nivel:
                return motivo or ("Overclock em 0%: a placa voltou ao padrão." + (" Alguns itens não responderam: " + "; ".join(falhas) if falhas else ""))
            partes = []
            if info["nucleo"]["ok"]:
                partes.append(f"núcleo +{core} MHz")
            if info["memoria"]["ok"]:
                partes.append(f"memória +{mem} MHz")
            if info["potencia"]["ok"]:
                partes.append(f"potência {watts} W")
            ausentes = [n for n, k in (("núcleo", "nucleo"), ("memória", "memoria"), ("potência", "potencia")) if not info[k]["ok"]]
            fim = f" (esta placa não aceita ajuste de {', '.join(ausentes)})" if ausentes else ""
            return f"Overclock em {nivel}%: " + ", ".join(partes) + "." + fim + " Acompanhe a temperatura."

    def _oc_zerar_antigo(self):
        try:
            texto = self.t_oc_definir(0, "O overclock de antes foi desligado (o programa tinha fechado com ele ligado).")
            self.msg(texto)
        except Exception:
            pass

    def oc_fechar(self):
        """Ao encerrar o Th Boost: devolve a placa ao padrão (só se ele mexeu)."""
        try:
            if self._oc["nivel"] or CONFIG.get("oc_ativo"):
                self.t_oc_definir(0, "")
        except Exception:
            pass

    # ----- vigia de temperatura -----

    def _vigiar_oc(self):
        while not self.fechando:
            nivel = self._oc["nivel"]
            try:
                if nivel or not self.ocioso:
                    info = self._oc_ler()
                    self._oc["info"] = info
                    self._oc["pronto"] = True
                    if not info["suporte"]:
                        return  # sem placa NVIDIA: nada a vigiar
                    t = info.get("temp")
                    if nivel and t is not None and t >= OC_TEMP_LIMITE:
                        texto = self.t_oc_definir(0, f"A placa chegou a {t}°C: o overclock foi desligado sozinho (voltou a 0%).")
                        self.msg(texto)
                    elif nivel and t is not None and t >= OC_TEMP_AVISO:
                        self._oc["aviso"] = f"A placa está em {t}°C. Se passar de {OC_TEMP_LIMITE}°C o overclock desliga sozinho."
                    elif nivel and self._oc["aviso"].startswith("A placa está"):
                        self._oc["aviso"] = ""
            except Exception:
                pass
            time.sleep(2.0 if nivel else 3.0)
