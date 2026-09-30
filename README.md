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
| `assets/catalogo.md` | **Sim** | Índice do que existe, sem o conteúdo em si — nomes, descrição, contagem. |
| Código do app (quando existir) | **Sim** | É o que este repositório é feito para guardar. |

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
└── assets/
    ├── catalogo.md           ← o que existe, versionado
    └── originais/            ← espelho bruto do Drive, fora do git
```

## Como trazer os assets de volta

```powershell
python -m pip install --user requests   # so por seguranca; o script usa so stdlib
python scripts/drive_puxar.py
```

Idempotente — rodar de novo só baixa o que falta ou mudou.

## Estado — 30/09/2026

**Só a fundação, ainda não existe aplicativo.** O que está pronto:

- `scripts/drive_puxar.py` — adaptado de `Jaspy/scripts/acervo/drive_puxar.py`,
  testado nesta sessão (47 arquivos, idempotente, path correto fora do
  repositório de origem — achei e corrigi um bug real no script original
  do laboratório fazendo esse teste: ele travava calculando caminho
  relativo quando o destino não era o `acervo/` do próprio Jaspy).
- `assets/catalogo.md` — o inventário da primeira campanha ("A Maldição
  do Ídolo de Pedra", sistema Ordem Paranormal): handouts, fichas, mapas
  em estágios, tokens, trilha sonora.

**O que falta, em ordem — não decidido ainda, precisa de conversa
própria:**

1. Stack do aplicativo (ainda não escolhida). Recomendação a validar:
   Python + HTML/JS sem build step, no mesmo padrão de baixa manutenção
   do `assistente/cliente-web` do laboratório — justificável pelo "uso
   raro": um projeto que fica meses parado não deveria depender de um
   `node_modules` que apodrece nesse tempo.
2. Modelo de dados: o que é uma "campanha", uma "ficha", um "token" — a
   ficha vira dado estruturado (editável de verdade) ou continua imagem?
   O catálogo já aponta para isso (5 fichas em imagem, prontas para virar
   o primeiro teste real do editor).
3. Primeiro editor a construir — meu palpite é o de token (é o dado mais
   simples: nome, imagem, talvez tamanho), mas não decidi sozinho.
