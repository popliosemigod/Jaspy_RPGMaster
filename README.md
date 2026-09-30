# Jaspy RPG Master

Gerenciador de campanhas de RPG de mesa — fichas editáveis, mapas, tokens,
história e trilha sonora organizados num lugar só. Fundado em 30/09/2026 a
partir de campanhas já jogadas de verdade (ver `assets/catalogo.md`), não
de dado sintético.

## O nome, e por que este repositório é separado

"Jaspy" aqui não é o laboratório de hardware nem o agente Jaspa — é o
mesmo nome emprestado para um projeto de software diferente. Repositório
próprio, dedicado, sem nenhuma dependência do resto do laboratório: "um
repositório por projeto" vale aqui também, mesmo o projeto não sendo
engenharia de bancada.

## O que este projeto É

Henrique: "vou usar para preparar e mestrar campanhas, raramente vou
usá-lo. Mas também pretendo mesclar algumas ferramentas VR e de tabletop
simulator para fazer uns testes mais profissionais." Isso decide o
formato: **um organizador e editor de conteúdo de campanha**, não uma
mesa virtual com renderização 3D ou sincronização ao vivo entre
jogadores. A parte "profissional" (VR, física de mesa, jogo ao vivo) vem
de ferramentas que já fazem isso bem — Tabletop Simulator e afins; o
Jaspy RPG Master prepara e organiza o material que alimenta essas
ferramentas, não compete com elas.

Uso raro, de propósito simples: sem servidor sempre ligado, sem conta de
jogador, sem infraestrutura que apodrece entre uma campanha e a próxima.

## O que este projeto NÃO é (por enquanto)

- Não é uma VTT ao vivo (sem sincronização de estado entre jogadores
  conectados).
- Não renderiza mapa em 3D nem faz física de peça — isso é para o
  Tabletop Simulator.
- Não tem conta de jogador nem permissão por usuário — é ferramenta do
  mestre, para o mestre.

Se algum dia isso mudar, é decisão nova, não vem de graça com o nome.

## O que é público e o que não é

A mesma política do `acervo/` do laboratório Jaspy, com um motivo a mais
aqui: **este repositório é público no GitHub.**

| Diretório | Vai para o git? | Por quê |
| --- | --- | --- |
| `assets/originais/` | **Não** | Espelho bruto do Drive: fotos de campanha, PDFs de regra **comerciais** (Ordem Paranormal, Arquivos Secretos, Sobrevivendo ao Horror — Jambô Editora), soundtrack de autoria não confirmada. Publicar isso num repo público seria redistribuir conteúdo comprado sem autorização — decisão tomada com o Henrique em 30/09/2026, não filtro meu sozinho. `python scripts/drive_puxar.py` traz tudo de volta a qualquer momento. |
| `campanhas/` | **Não** | O dado de verdade do app — tokens que você criar, fichas, mapas. É dado pessoal de quem joga, não código; mesma cautela de proveniência de `assets/originais/`. |
| `assets/catalogo.md` | **Sim** | Índice do que existe, sem o conteúdo em si — nomes, descrição, contagem. |
| `servidor/`, `cliente/`, `scripts/` | **Sim** | É o que este repositório é feito para guardar. |

**Se algum dia o app precisar de exemplos versionados** (ícone de token
placeholder, mapa de demonstração), eles precisam ser autorais ou de
licença permissiva clara — nunca puxados direto de `assets/originais/`
sem checar.

## Estrutura

```
Jaspy_RPGMaster/
├── README.md
├── .gitignore
├── scripts/
│   ├── drive_puxar.py      ← baixa assets/originais/ do Drive (fontes.json)
│   └── fontes.json          ← qual pasta do Drive, adaptado de Jaspy/acervo
├── servidor/
│   └── servidor.py          ← API + arquivos estáticos, stdlib puro, sem TLS/login
├── cliente/
│   └── index.html            ← editor de token (o primeiro), vanilla JS
├── assets/
│   ├── catalogo.md           ← o que existe, versionado
│   └── originais/            ← espelho bruto do Drive, fora do git
└── campanhas/                ← dado de verdade do app, fora do git
    └── idolo-de-pedra/       ← semeada com a campanha real (ver Estado)
```

## Como rodar

```powershell
python scripts/drive_puxar.py      # traz assets/originais/ do Drive (so na 1a vez)
python servidor/servidor.py         # abre em http://127.0.0.1:8642/
```

Sem instalação nenhuma além do Python — tudo stdlib, de propósito (ver
"Stack", abaixo).

## Estado — 30/09/2026

**Fundação + primeira fatia vertical funcionando, testada com dado real
— não é só esqueleto.**

- `scripts/drive_puxar.py` — adaptado de `Jaspy/scripts/acervo/drive_puxar.py`,
  testado nesta sessão (47 arquivos, idempotente, path correto fora do
  repositório de origem — achei e corrigi um bug real no script original
  do laboratório fazendo esse teste: ele travava calculando caminho
  relativo quando o destino não era o `acervo/` do próprio Jaspy).
- `assets/catalogo.md` — o inventário da primeira campanha ("A Maldição
  do Ídolo de Pedra", sistema Ordem Paranormal): handouts, fichas, mapas
  em estágios, tokens, trilha sonora.
- **Editor de tokens, ponta a ponta:** `servidor/servidor.py` (API REST
  sobre HTTP puro, sem dependência externa) + `cliente/index.html` (grade
  de tokens, adicionar por nome+imagem, remover). Semeado com os 5 tokens
  reais da campanha (Alan, Edgar, Eloísa, Kênia, Victor) copiados de
  `assets/originais/TOKENS/`. Testado de verdade, não só "parece certo":
  - screenshot headless (Edge) confirmando os 5 retratos renderizando
    certo na grade;
  - criar + apagar via API confirmado ponta a ponta (script Python batendo
    na API real, não teste unitário isolado);
  - **dois bugs achados e corrigidos nesse processo:** apagar um token não
    apagava o arquivo de imagem (órfão ficava em disco — corrigido,
    `do_DELETE` agora remove os dois); e dois servidores concorrentes
    ficaram escutando a mesma porta depois de um `kill` que não matou o
    processo certo no Windows — descoberto pelo `netstat`, não pela
    aparência (a API respondia normal, só que com o código velho).

**Decisão já tomada, sem pergunta:** stack é Python stdlib (servidor) +
HTML/JS sem build step (cliente) — mesmo padrão de baixa manutenção do
`assistente/cliente-web` do laboratório Jaspy. Justificativa: "uso raro,
raramente vou usá-lo" (Henrique, 30/09/2026) — um projeto que fica meses
parado não deveria depender de `node_modules` nem de TLS/login que
`ponte/servidor.py` precisa por falar com hardware físico; aqui é
ferramenta de mestre, local, sem jogador remoto.

**O que falta, em ordem:**

1. Modelo de dado das fichas — as 5 fichas da campanha estão em imagem
   (`assets/originais/FICHAS/`); ainda não viraram dado estruturado
   editável. É o próximo editor natural, usando o mesmo padrão do de
   token (servidor stdlib + página sem build).
2. Editor de mapa — os 3 mapas em estágios ("O Porão", "+ Sala Secreta",
   "+ Duto de Ventilação") já provam que precisa suportar variantes da
   mesma planta, não só upload de imagem única.
3. História/handouts e trilha sonora — ainda sem editor nem visualizador.
