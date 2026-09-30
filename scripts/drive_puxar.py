#!/usr/bin/env python3
"""Baixa uma pasta publica do Google Drive para o disco, recursivamente.

Copia adaptada de scripts/acervo/drive_puxar.py do repositorio Jaspy
(laboratorio) - mesma ferramenta, outro projeto. "Um repositorio por
projeto" (CLAUDE.md do laboratorio) significa que o codigo mora aqui, nao
um symlink ou import cruzando repositorios.

Por que existe
--------------
A base do Jaspy RPG Master nasceu de campanhas ja jogadas, guardadas no
Drive: fichas, mapas, tokens, trilha sonora, handouts. Este script
transforma "uma pasta compartilhada" em "arquivos no disco com procedencia
registrada".

Como funciona
-------------
A pagina de uma pasta publica do Drive traz, no HTML, o nome e o id de cada
item num atributo `ssk`. O script le esse HTML, monta a lista, desce nas
subpastas e baixa cada arquivo:

  * arquivo comum  -> https://drive.google.com/uc?export=download&id=<id>
  * Google Docs    -> .../export?format=docx

E idempotente: arquivo ja baixado com o mesmo tamanho nao baixa de novo.

Limitacao honesta
-----------------
Depende do HTML que o Drive serve hoje. Arquivo grande demais (ZIP, em
particular) as vezes cai numa pagina de aviso de antivirus sem o token de
confirmacao que este script sabe seguir - quando isso acontece, baixe esse
arquivo a mao pelo navegador.

Uso
---
    python scripts/drive_puxar.py                    # usa fontes.json
    python scripts/drive_puxar.py <url-ou-id> [destino]
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FONTES = Path(__file__).resolve().parent / "fontes.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Cada item da listagem aparece como um aria-label seguido do id em `ssk`.
# O aria-label termina com o tipo: "... PDF Shared", "... Shared folder".
PADRAO_ITEM = re.compile(
    r'aria-label="([^"]+?)"[^>]*?ssk=.5:[^:]+:([-A-Za-z0-9_]{20,})-\d+-\d+.'
)

# Rotulos que o Drive repete por item e que nao sao nome de arquivo.
RUIDO = ("Modified", "Size:", "Storage used", "Size not available")

# Sufixos de tipo que o Drive anexa ao nome no aria-label.
SUFIXOS_TIPO = (
    " Shared folder", " PDF Shared", " Image Shared", " Microsoft Word Shared",
    " Microsoft Excel Shared", " Microsoft PowerPoint Shared", " Google Docs Shared",
    " Google Sheets Shared", " Google Slides Shared", " Video Shared", " Audio Shared",
    " Archive Shared", " Text Shared", " Shared",
)

# Google Docs nativo nao tem bytes para baixar: exporta.
EXPORTACAO_NATIVA = {
    "Google Docs": ("document", "docx"),
    "Google Sheets": ("spreadsheets", "xlsx"),
    "Google Slides": ("presentation", "pptx"),
}


def id_da_url(alvo: str) -> str:
    """Aceita a URL inteira ou so o id."""
    m = re.search(r"/folders/([-A-Za-z0-9_]{20,})", alvo)
    return m.group(1) if m else alvo.strip()


def busca(url: str, tentativas: int = 3) -> bytes:
    """GET com User-Agent de navegador. A rede oscila, entao repete antes
    de desistir."""
    ultimo = None
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - qualquer falha de rede merece retry
            ultimo = e
            time.sleep(2 * (n + 1))
    raise RuntimeError(f"falhou apos {tentativas} tentativas: {url}\n  {ultimo}")


def limpa_nome(rotulo: str) -> tuple[str, str]:
    """Separa 'arquivo.pdf PDF Shared' em ('arquivo.pdf', 'PDF')."""
    for sufixo in SUFIXOS_TIPO:
        if rotulo.endswith(sufixo):
            tipo = sufixo.replace(" Shared", "").strip() or "Arquivo"
            if sufixo == " Shared folder":
                tipo = "pasta"
            return rotulo[: -len(sufixo)].strip(), tipo
    return rotulo.strip(), "Arquivo"


def lista_pasta(id_pasta: str) -> list[dict]:
    """Devolve os itens diretos de uma pasta publica, sem repetir."""
    html = busca(f"https://drive.google.com/drive/folders/{id_pasta}").decode(
        "utf-8", errors="ignore"
    )
    itens: list[dict] = []
    vistos: set[tuple[str, str]] = set()
    for rotulo, ident in PADRAO_ITEM.findall(html):
        if rotulo.startswith(RUIDO):
            continue
        nome, tipo = limpa_nome(rotulo)
        if not nome or (ident, nome) in vistos:
            continue
        vistos.add((ident, nome))
        itens.append({"id": ident, "nome": nome, "tipo": tipo})
    return itens


def url_de_download(item: dict) -> str:
    tipo = item["tipo"]
    if tipo in EXPORTACAO_NATIVA:
        recurso, formato = EXPORTACAO_NATIVA[tipo]
        return (f"https://docs.google.com/{recurso}/d/{item['id']}"
                f"/export?format={formato}")
    return f"https://drive.google.com/uc?export=download&id={item['id']}"


def nome_seguro(nome: str, tipo: str) -> str:
    """Nome utilizavel no Windows, preservando a extensao quando existe."""
    limpo = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(" .")
    if tipo in EXPORTACAO_NATIVA and "." not in limpo[-6:]:
        limpo += "." + EXPORTACAO_NATIVA[tipo][1]
    return limpo or "sem_nome"


def baixa(item: dict, destino: Path, raiz_fonte: Path) -> dict:
    alvo = destino / nome_seguro(item["nome"], item["tipo"])
    registro = {
        "nome_original": item["nome"],
        "arquivo": str(alvo.relative_to(raiz_fonte)).replace("\\", "/"),
        "drive_id": item["id"],
        "tipo_drive": item["tipo"],
        "url": f"https://drive.google.com/file/d/{item['id']}/view",
    }

    if alvo.exists() and alvo.stat().st_size > 0:
        registro["bytes"] = alvo.stat().st_size
        registro["situacao"] = "ja existia"
        print(f"    = {alvo.name}  ({registro['bytes']:,} B)")
        return registro

    dados = busca(url_de_download(item))

    # Arquivo grande cai numa pagina de confirmacao em vez dos bytes.
    if dados[:15].lstrip().lower().startswith(b"<!doctype html"):
        token = re.search(rb"confirm=([0-9A-Za-z_-]+)", dados)
        if token:
            dados = busca(f"https://drive.google.com/uc?export=download&id="
                          f"{item['id']}&confirm={token.group(1).decode()}")
        else:
            registro["situacao"] = "recusado: o Drive devolveu HTML, nao o arquivo"
            print(f"    ! {alvo.name}  (nao baixou: veio HTML)")
            return registro

    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(dados)
    registro["bytes"] = len(dados)
    registro["situacao"] = "baixado"
    print(f"    + {alvo.name}  ({len(dados):,} B)")
    return registro


def desce(id_pasta: str, destino: Path, raiz_fonte: Path | None = None, nivel: int = 0) -> list[dict]:
    raiz_fonte = raiz_fonte or destino  # a chamada de topo define a raiz para o resto da recursao
    itens = lista_pasta(id_pasta)
    pastas = [i for i in itens if i["tipo"] == "pasta"]
    arquivos = [i for i in itens if i["tipo"] != "pasta"]
    print(f"{'  ' * nivel}[pasta {id_pasta}] {len(arquivos)} arquivo(s), "
          f"{len(pastas)} subpasta(s)")

    destino.mkdir(parents=True, exist_ok=True)
    registros = [baixa(a, destino, raiz_fonte) for a in arquivos]

    for p in pastas:
        sub = destino / nome_seguro(p["nome"], "pasta")
        registros += desce(p["id"], sub, raiz_fonte, nivel + 1)
    return registros


def main(argv: list[str]) -> int:
    if argv:
        alvos = [{"id": id_da_url(argv[0]),
                  "destino": argv[1] if len(argv) > 1 else "assets/originais"}]
    elif FONTES.exists():
        alvos = json.loads(FONTES.read_text(encoding="utf-8"))["fontes"]
    else:
        print(__doc__)
        return 2

    total_geral = 0
    novos_geral = 0
    for alvo in alvos:
        destino_bruto = Path(alvo.get("destino", "assets/originais"))
        destino = destino_bruto if destino_bruto.is_absolute() else RAIZ / destino_bruto
        print(f"\n=== {alvo.get('rotulo', alvo['id'])} -> {destino} ===")
        registros = desce(id_da_url(alvo["id"]), destino)

        proc = destino / "_procedencia.json"
        proc.write_text(
            json.dumps({"baixado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "arquivos": registros}, ensure_ascii=False, indent=2),
            encoding="utf-8")

        novos = sum(1 for r in registros if r.get("situacao") == "baixado")
        total_geral += len(registros)
        novos_geral += novos
        print(f"{len(registros)} arquivo(s) | {novos} novo(s) | procedencia: {proc}")

    print(f"\n{total_geral} arquivo(s) no total | {novos_geral} novo(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
