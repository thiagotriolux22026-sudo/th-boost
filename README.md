# Th Boost

Painel de otimização e monitoramento para Windows (preto e azul, ou a cor que você escolher). Versão atual: **v9.5**.

## Como baixar (em qualquer computador, sem login)

1. Clique neste link para baixar o ZIP pronto:
   **[⬇ Baixar o Th Boost v9.5](https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v9.5.zip)**
   (endereço: https://github.com/thiagotriolux22026-sudo/th-boost/raw/main/download/Th-Boost-v9.5.zip)
2. Clique com o botão direito no arquivo baixado e escolha **Extrair para "Th-Boost-v9.5\"**.
3. Abra a pasta e leia o **LEIAME.txt** (ele explica tudo com calma).

## Novidades da v9.5

- **Quem segura o seu FPS:** o Th Boost mostra o gargalo, processador (CPU) ou placa de vídeo (GPU), no **FPS na tela** (linha "Gargalo") e no **Monitor**, com o que fazer. Exemplo: processador em 100% e placa em 20% = gargalo no processador; aí o overclock da placa não aumenta o FPS.
- **Gráfico leve, perfil "Processador fraco":** o que pesa no processador (sombras, distância, partículas, efeitos) fica no mínimo e o que só pesa na placa (texturas médias, materiais, MSAA 2x, filtro 16x) sobe. O FPS fica igual ao mínimo, a imagem melhora e a placa trabalha mais.

## Novidades da v9.4

- **Gráfico leve nos jogos** (Modos › Modo FPS On, chave "Gráfico leve nos jogos", já vem ligada): ao ligar o Modo FPS On, o **Valorant**, o **CS2** e o **Roblox** ficam com o gráfico no mínimo (sombras, efeitos, texturas e detalhes baixos), com a **resolução em 100%**. Ao desligar, cada item volta ao valor que você usava; sensibilidade, volume e o resto do arquivo não mudam.
- O jogo precisa estar fechado: se estiver aberto, a troca espera ele fechar. Antes de mexer, o Th Boost guarda uma cópia de cada arquivo em `%LOCALAPPDATA%\ThBoost\grafico`.

## Novidades da v9.3

- **Overclock nas placas NVIDIA mais antigas:** nas GTX 600 em diante (por exemplo a GTX 750), núcleo e memória não aparecem mais como "não aceita". Quando a NVML não deixa, o Th Boost usa a NVAPI do driver (deslocamento do clock no estado P0, dentro do limite que o driver informa). Na barra, 150% = núcleo +150 MHz e memória +250 MHz nessas placas. Nada fica gravado na placa, zera ao fechar e desliga sozinho acima de 88°C.
- Se algum item continuar sem aceitar, a página mostra o motivo (em notebook o driver costuma travar).
- Placas AMD e Intel: a página indica o programa do fabricante (AMD Software: Adrenalin; Intel Graphics Software / Arc Control).

## Novidades da v9.2

- **FPS na tela** (página nova): uma janelinha num canto, por cima do jogo, com FPS, 1% baixo, tempo de cada quadro, CPU, placa de vídeo, temperaturas (quando o PC informa) e RAM. Escolha o canto, o tamanho e os itens. **Ctrl+Shift+F** esconde e mostra. Não pega clique nem teclado e não entra no jogo. Funciona com jogos em janela ou em tela cheia sem bordas.
- **Contador de FPS com um clique:** "Instalar contador" baixa o PresentMon 2.6.0 oficial da Intel e só grava se a impressão digital do arquivo bater.
- **Modo FPS On arrumado:** agora liga sempre (antes dependia do contador), dá prioridade ao jogo e põe um plano de energia de desempenho; ao desligar, tudo volta. Junto com uma sessão de jogo, nada fica preso no Modo Leve.
- **Cor do painel** (página nova): o painel inteiro muda de cor na hora (8 cores prontas ou qualquer tom). As cores de aviso continuam verde, amarelo e vermelho.
- **Logo azul no que foi fixado** (menu Iniciar, barra de tarefas, área de trabalho): o Th Boost troca o ícone dos atalhos dele e o botão Atualizar também passa a trocar o `Th Boost.ico`.

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
