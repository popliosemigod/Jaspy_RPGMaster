#!/usr/bin/env python3
"""Servidor local do Jaspy RPG Master — sem TLS, sem login, sem WebSocket.

Por que tão simples
--------------------
É ferramenta de mestre, uso raro, rodando na própria máquina. Nada aqui
sai da rede local; não há jogador remoto autenticando, não há estado para
sincronizar em tempo real (ver README.md, "O que este projeto NÃO é").
`ponte/servidor.py` do laboratório Jaspy precisa de TLS e WebSocket porque
fala com um robô físico e um avatar em AR ao vivo — problema diferente.
Copiar aquela complexidade para cá seria complexidade sem motivo.

Dados
-----
Cada campanha é uma pasta em campanhas/<slug>/, fora do git (dado
pessoal, não código — ver .gitignore). Token é a primeira fatia: nome,
imagem, e um JSON por campanha (tokens.json) que indexa os dois.

Uso
---
    python servidor/servidor.py [porta]     # padrao 8642
"""
from __future__ import annotations

import base64
import json
import mimetypes
import re
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parent.parent
CAMPANHAS = RAIZ / "campanhas"
CLIENTE = RAIZ / "cliente"

ROTA_API = re.compile(r"^/api/campanhas/(?P<slug>[^/]+)/tokens(?:/(?P<id>[^/]+))?$")
ROTA_IMAGEM = re.compile(r"^/campanhas/(?P<slug>[^/]+)/tokens/(?P<arquivo>[^/]+)$")


def nome_pasta(slug: str) -> Path:
    """Impede sair de campanhas/ via slug malicioso (../../etc)."""
    alvo = (CAMPANHAS / slug).resolve()
    if not str(alvo).startswith(str(CAMPANHAS.resolve())) or slug in ("", ".", ".."):
        raise ValueError("slug invalido")
    return alvo


def le_tokens(slug: str) -> list[dict]:
    arq = nome_pasta(slug) / "tokens.json"
    if not arq.exists():
        return []
    return json.loads(arq.read_text(encoding="utf-8"))


def salva_tokens(slug: str, tokens: list[dict]) -> None:
    pasta = nome_pasta(slug)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "tokens.json").write_text(
        json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def campanhas_existentes() -> list[dict]:
    if not CAMPANHAS.is_dir():
        return []
    resultado = []
    for pasta in sorted(CAMPANHAS.iterdir()):
        arq = pasta / "campanha.json"
        if arq.is_file():
            dado = json.loads(arq.read_text(encoding="utf-8"))
            resultado.append({"slug": pasta.name, **dado})
    return resultado


class Manipulador(BaseHTTPRequestHandler):
    server_version = "JaspyRPGMaster/0.1"

    def log_message(self, formato, *args):  # silencia o log padrao (porta/data repetitivos)
        print(f"[servidor] {self.address_string()} {formato % args}")

    def _json(self, status: int, corpo) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _erro(self, status: int, mensagem: str) -> None:
        self._json(status, {"erro": mensagem})

    def _corpo_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(tamanho).decode("utf-8")) if tamanho else {}

    def _serve_arquivo(self, caminho: Path) -> None:
        if not caminho.is_file():
            self._erro(404, "nao encontrado")
            return
        dados = caminho.read_bytes()
        tipo = mimetypes.guess_type(str(caminho))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        caminho = unquote(self.path.split("?")[0])

        if caminho == "/":
            self._serve_arquivo(CLIENTE / "index.html")
            return
        if caminho.startswith("/cliente/"):
            self._serve_arquivo(CLIENTE / caminho[len("/cliente/"):])
            return
        if caminho == "/api/campanhas":
            self._json(200, campanhas_existentes())
            return

        m = ROTA_IMAGEM.match(caminho)
        if m:
            try:
                pasta = nome_pasta(m["slug"])
            except ValueError:
                self._erro(400, "slug invalido")
                return
            self._serve_arquivo(pasta / "tokens" / m["arquivo"])
            return

        m = ROTA_API.match(caminho)
        if m and m["id"] is None:
            try:
                self._json(200, le_tokens(m["slug"]))
            except ValueError:
                self._erro(400, "slug invalido")
            return

        self._erro(404, "rota desconhecida")

    def do_POST(self):
        m = ROTA_API.match(unquote(self.path))
        if not (m and m["id"] is None):
            self._erro(404, "rota desconhecida")
            return
        try:
            slug = m["slug"]
            nome_pasta(slug)  # so para validar o slug
        except ValueError:
            self._erro(400, "slug invalido")
            return

        corpo = self._corpo_json()
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._erro(422, "token precisa de nome")
            return

        token = {"id": uuid.uuid4().hex[:12], "nome": nome, "imagem": None}
        if corpo.get("imagem_base64"):
            token["imagem"] = self._grava_imagem(slug, token["id"], corpo)

        tokens = le_tokens(slug)
        tokens.append(token)
        salva_tokens(slug, tokens)
        self._json(201, token)

    def do_PUT(self):
        m = ROTA_API.match(unquote(self.path))
        if not (m and m["id"]):
            self._erro(404, "rota desconhecida")
            return
        slug, id_ = m["slug"], m["id"]
        try:
            nome_pasta(slug)
        except ValueError:
            self._erro(400, "slug invalido")
            return

        corpo = self._corpo_json()
        tokens = le_tokens(slug)
        alvo = next((t for t in tokens if t["id"] == id_), None)
        if not alvo:
            self._erro(404, "token nao existe")
            return

        if "nome" in corpo and corpo["nome"].strip():
            alvo["nome"] = corpo["nome"].strip()
        if corpo.get("imagem_base64"):
            alvo["imagem"] = self._grava_imagem(slug, id_, corpo)

        salva_tokens(slug, tokens)
        self._json(200, alvo)

    def do_DELETE(self):
        m = ROTA_API.match(unquote(self.path))
        if not (m and m["id"]):
            self._erro(404, "rota desconhecida")
            return
        slug, id_ = m["slug"], m["id"]
        try:
            pasta = nome_pasta(slug)
        except ValueError:
            self._erro(400, "slug invalido")
            return

        tokens = le_tokens(slug)
        alvo = next((t for t in tokens if t["id"] == id_), None)
        if alvo is None:
            self._erro(404, "token nao existe")
            return
        if alvo.get("imagem"):
            (pasta / "tokens" / alvo["imagem"]).unlink(missing_ok=True)
        salva_tokens(slug, [t for t in tokens if t["id"] != id_])
        self._json(200, {"ok": True})

    def _grava_imagem(self, slug: str, id_: str, corpo: dict) -> str:
        pasta = nome_pasta(slug) / "tokens"
        pasta.mkdir(parents=True, exist_ok=True)
        extensao = Path(corpo.get("imagem_nome", "")).suffix or ".png"
        nome_arquivo = f"{id_}{extensao}"
        dados = base64.b64decode(corpo["imagem_base64"])
        (pasta / nome_arquivo).write_bytes(dados)
        return nome_arquivo


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
    CAMPANHAS.mkdir(parents=True, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
    print(f"Jaspy RPG Master em http://127.0.0.1:{porta}/")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
