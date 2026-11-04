# Th Boost

Painel de otimização e monitoramento para Windows (preto e azul). Versão atual: **v8.9**.

## Como baixar (em qualquer computador, sem login)

1. Clique neste link para baixar o ZIP pronto:
   **[⬇ Baixar o Th Boost v8.9](https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v8.9.zip)**
   (endereço: https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v8.9.zip)
2. Clique com o botão direito no arquivo baixado e escolha **Extrair para "Th-Boost-v8.9\"**.
3. Abra a pasta e leia o **LEIAME.txt** (ele explica tudo com calma).

## Novidades da v8.9

- Programa inteiro em **preto e azul** (o vermelho ficou só para avisar algo ruim, como "muito quente").
- **Logo em 3D**: o "T" e as letras "Th Boost" com profundidade azul.
- **Menu em quadradinhos**: só os ícones; encoste o mouse e ele abre cheio, com os nomes.
- **Ícone novo** do atalho.
- Desde a v8.8: imagem do mouse pelo modelo, "Modo competitivo" do mouse, teste de cliques, teclado mais rápido e a página **Resfriamento** (Normal / Fresco / Gelado) para o PC ou notebook esquentar menos.

**Já usa uma versão antiga?** Feche o Th Boost, troque o `th_boost.py` e o `Th Boost.ico` pelos do ZIP novo e rode de novo o **Criar atalho na area de trabalho.bat**.

## Resumo para abrir

1. Se o computador nunca teve Python: baixe em https://www.python.org/downloads/ , abra o instalador e **marque a caixa "Add python.exe to PATH"** antes de clicar em Install Now.
2. Dê dois cliques em **Criar atalho na area de trabalho.bat** (só uma vez).
3. Abra pelo atalho **Th Boost** na área de trabalho. Quando o Windows pedir permissão de Administrador, clique em **Sim**.

Para levar a outro computador sem instalar Python, dê dois cliques em **Gerar executavel.bat** uma vez e copie só o arquivo `Th Boost.exe`.

## O que tem aqui

| Pasta | O que é |
|---|---|
| `download/` | O ZIP pronto de cada versão. É isso que se baixa. |
| `fonte/` | O código-fonte, como cópia de segurança. `python build.py` (dentro de `fonte`) gera o `th_boost.py` completo na pasta `out`. |
