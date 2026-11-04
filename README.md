# Th Boost

Painel de otimização e monitoramento para Windows (preto e azul). Versão atual: **v9.1**.

## Como baixar (em qualquer computador, sem login)

1. Clique neste link para baixar o ZIP pronto:
   **[⬇ Baixar o Th Boost v9.1](https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v9.1.zip)**
   (endereço: https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v9.1.zip)
2. Clique com o botão direito no arquivo baixado e escolha **Extrair para "Th-Boost-v9.1\"**.
3. Abra a pasta e leia o **LEIAME.txt** (ele explica tudo com calma).

## Novidades da v9.1

Revisão completa: cada página foi conferida.
- **Jogos sem travadinhas:** "Liberar a RAM" só age com a memória apertada e nunca mexe no jogo, no Discord, no OBS ou no áudio; a limpeza não apaga mais o cache de shader da placa de vídeo; durante o jogo o Th Boost lê menos coisas; o limite de CPU não pega mais launchers nem os jogos abertos por eles.
- **FPS:** funciona com o PresentMon 2.x e mostra o FPS do jogo da frente. O Modo FPS On devolve o Modo Leve e o plano de energia ao desligar.
- **Plano de energia:** respeita o perfil de processador escolhido, não troca na bateria e não atrapalha os Ryzen X3D de 2 blocos.
- **Mais seguro:** "Otimizar tudo" não esvazia mais a lixeira; apps que você pode ter instalado (Spotify, Netflix...) viraram risco médio; DNS automático não derruba PC com IP fixo; overclock em 0% volta ao que a placa tinha; se o PC desligar no meio de um jogo, tudo volta ao normal na próxima vez.
- **Autoteste** em Configurações, com "Copiar relatório".
- **Atualização com volta automática:** se uma versão nova não abrir, em até 2 minutos o Th Boost volta para a anterior.

## Novidades da v9.0.1

- Versão de teste do aviso de atualização (no uso, é igual à v9.0).
- A atualização ficou mais firme no Windows: se o ícone ou outro arquivo extra estiver em uso, só o programa é trocado e o resto fica como estava.

## Novidades da v9.0

- **Aviso de versão nova:** quando sair uma versão nova, aparece no meio da tela *"O dono atualizou o Th Boost"*, com as novidades e o botão **Atualizar**. Ele baixa a versão nova (só deste repositório), confere se o arquivo veio certo, guarda a versão atual na pasta `versao_anterior` e abre o programa de novo sozinho. Dá para desligar em **Configurações › Atualizações**.
- Quem está na v8.9 ou antes precisa baixar a v9.0 uma vez pelo link acima; da v9.0 em diante, o aviso cuida disso.

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
| `download/atualizacao/` | O pacote pequeno que o botão **Atualizar** baixa (só o programa e o LEIAME). |
| `versao.json` | Diz qual é a versão mais nova. O Th Boost (v9.0 em diante) lê este arquivo para mostrar o aviso de atualização. |
| `fonte/` | O código-fonte, como cópia de segurança. `python build.py` (dentro de `fonte`) gera o `th_boost.py` completo na pasta `out`. |

## Como publicar uma versão nova (para o dono)

1. Coloque o ZIP completo novo em `download/` (por exemplo `Th-Boost-v9.1.zip`) e troque o link no começo deste README.
2. Coloque em `download/atualizacao/` o pacote de atualização (um ZIP só com `th_boost.py` e `LEIAME.txt`; ponha também o ícone ou os `.bat` se eles mudaram).
3. No `versao.json`, troque `versao`, `zip` (o endereço do pacote de atualização), `tamanho`, `data`, as `novidades` e o `sha256` (a impressão digital do pacote; no Windows: `certutil -hashfile Th-Boost-v9.1-atualizacao.zip SHA256`).
4. Envie tudo junto. Em até alguns minutos, quem estiver com o Th Boost aberto vê o aviso (ele procura ao abrir e a cada 6 horas).

Se o `sha256` não bater com o ZIP, o programa não atualiza e não troca nada. **Proteja esta conta do GitHub com verificação em duas etapas:** quem conseguir publicar aqui consegue mandar uma versão para todo mundo que usa o Th Boost.
