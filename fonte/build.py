import os, re
B = os.path.dirname(os.path.abspath(__file__))
rd = lambda p: open(os.path.join(B, p), encoding="utf-8").read()

DOC = '''"""
Th Boost v8.6 - painel de otimizacao e monitoramento para Windows (tema cinza).

Instalar:    pip install psutil
Executar:    python th_boost.py   (abra como Administrador para overclock, plano de energia, FPS e renovar IP)
             ou de dois cliques em "Abrir Th Boost.bat"
Gerar .exe:  de dois cliques em "Gerar executavel.bat"
             (ou: pip install pyinstaller  e  pyinstaller --onefile --windowed --uac-admin th_boost.py)

A janela abre como um aplicativo do Microsoft Edge (ou do Google Chrome), sem barra de enderecos.
O programa fica so no seu computador (127.0.0.1) e fecha sozinho quando a janela e fechada.

FPS: baixe o PresentMon (github.com/GameTechDev/PresentMon) e coloque PresentMon.exe na mesma pasta.
"""

import base64
import collections
import ctypes
import glob
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psutil

'''
html = rd("src/ui.html")
assert '"""' not in html and "\\" not in html.replace("\\n", "") or True
if '"""' in html:
    raise SystemExit('ui.html contem """')
bk = rd("src/backend_orig.py")
aj = rd("src/ajustes.py")
xt = rd("src/extremo.py")
jg = rd("src/jogos.py")
jl = rd("src/jogos_lojas.py")
mt = rd("src/manutencao.py")
pc = rd("src/processos.py")
fr = rd("src/ferramentas.py")
cp = rd("src/cpu.py")
mm = rd("src/memoria.py")
oc = rd("src/overclock.py")
cq = rd("src/cpu_perfil.py")
sv = rd("src/servidor.py")
saida = DOC + bk.rstrip() + "\n\n" + aj.rstrip() + "\n\n\n" + xt.rstrip() + "\n\n\n" + jg.rstrip() + "\n\n\n" + jl.rstrip() + "\n\n\n" + mt.rstrip() + "\n\n\n" + pc.rstrip() + "\n\n\n" + cp.rstrip() + "\n\n\n" + fr.rstrip() + "\n\n\n" + mm.rstrip() + "\n\n\n" + oc.rstrip() + "\n\n\n" + cq.rstrip() + "\n\n\n" + sv.rstrip() + '\n\n\nHTML = r"""' + html + '"""\n\n\nif __name__ == "__main__":\n    principal()\n'
open(os.path.join(B, "out/th_boost.py"), "w", encoding="utf-8").write(saida)
print("ok", len(saida.splitlines()), "linhas")
