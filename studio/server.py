#!/usr/bin/env python3
"""Local KDP Publishing Studio. Standard-library only; binds to localhost."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 8765
MAX_UPLOAD = 35 * 1024 * 1024
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_").lower()
    return value[:60] or "mon-livre"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def typst_string(value: str) -> str:
    # JSON string escaping is compatible with Typst's quoted string syntax.
    return json.dumps(value, ensure_ascii=False)


def docx_paragraphs(data: bytes) -> list[tuple[int, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "source.docx"
        archive.write_bytes(data)
        with zipfile.ZipFile(archive) as zf:
            xml = ET.fromstring(zf.read("word/document.xml"))
    output: list[tuple[int, str]] = []
    body = xml.find("w:body", NS)
    if body is None:
        return output
    for node in list(body):
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "p":
            chunks = []
            for child in node.iter():
                name = child.tag.rsplit("}", 1)[-1]
                if name == "t":
                    chunks.append(child.text or "")
                elif name == "tab":
                    chunks.append("    ")
                elif name in ("br", "cr"):
                    chunks.append("\n")
            text = "".join(chunks).strip()
            if not text:
                continue
            style = node.find("w:pPr/w:pStyle", NS)
            style_id = style.get("{%s}val" % NS["w"], "") if style is not None else ""
            level = 1 if style_id.lower().startswith("heading1") else 2 if style_id.lower().startswith("heading2") else 0
            output.append((level, text))
        elif tag == "tbl":
            for row in node.findall(".//w:tr", NS):
                cells = []
                for cell in row.findall("./w:tc", NS):
                    cells.append(" ".join("".join(t.text or "" for t in p.findall(".//w:t", NS)) for p in cell.findall("./w:p", NS)).strip())
                line = " | ".join(c for c in cells if c)
                if line:
                    output.append((0, line))
    return output


def plain_paragraphs(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            result.append((2, line[4:].strip()))
        elif line.startswith("## ") or line.startswith("# "):
            result.append((1, line.lstrip("#").strip()))
        elif line.startswith(("- ", "* ", "+ ")):
            result.append((0, "• " + line[2:].strip()))
        else:
            result.append((0, line))
    return result


def make_typst(paragraphs: list[tuple[int, str]]) -> str:
    if not paragraphs:
        raise ValueError("Le manuscrit ne contient aucun paragraphe exploitable.")
    lines = ["// Généré par KDP Publishing Studio. Vous pouvez modifier ce fichier."]
    for level, value in paragraphs:
        safe = typst_string(value)
        if level == 1:
            lines.append(f"#heading(level: 1)[#text({safe})]")
        elif level == 2:
            lines.append(f"#heading(level: 2)[#text({safe})]")
        else:
            lines.append(f"#par(justify: true)[#text({safe})]")
        lines.append("")
    return "\n".join(lines)


def new_project(payload: dict) -> dict:
    title = str(payload.get("title", "")).strip()
    author = str(payload.get("author", "")).strip()
    if not title or not author:
        raise ValueError("Le titre et le nom de l'auteur sont obligatoires.")
    filename = str(payload.get("filename", "manuscrit.txt"))
    ext = Path(filename).suffix.lower()
    if ext not in {".txt", ".md", ".docx"}:
        raise ValueError("Formats acceptés : .docx, .txt et .md.")
    raw = base64.b64decode(payload.get("file_base64", ""), validate=True)
    if not raw or len(raw) > MAX_UPLOAD:
        raise ValueError("Fichier vide ou supérieur à 35 Mo.")
    if ext == ".docx":
        paragraphs = docx_paragraphs(raw)
    else:
        text = raw.decode("utf-8-sig")
        paragraphs = plain_paragraphs(text)
    body = make_typst(paragraphs)

    books_root = Path.home() / "KDP-Books"
    books_root.mkdir(parents=True, exist_ok=True)
    base = slug(title)
    project = books_root / base
    suffix = 2
    while project.exists():
        project = books_root / f"{base}-{suffix}"
        suffix += 1
    (project / "manuscript").mkdir(parents=True)
    (project / "templates").mkdir()
    (project / "listing").mkdir()
    (project / "assets" / "fonts").mkdir(parents=True)
    for name in ("interior.typ", "cover.typ"):
        source = ROOT / "templates" / name
        if not source.is_file():
            raise RuntimeError(f"Modèle introuvable dans le dépôt : {source}")
        shutil.copy2(source, project / "templates" / name)

    subtitle = str(payload.get("subtitle", "")).strip()
    trim = str(payload.get("trim", "6x9"))
    paper = str(payload.get("paper", "cream-bw"))
    bleed = bool(payload.get("bleed", False))
    toc = bool(payload.get("toc", True))
    description = str(payload.get("description", "")).strip()
    manifest = f'''[book]
title = {toml_string(title)}
title_lines = [{toml_string(title)}]
subtitle = {toml_string(subtitle)}
author = {toml_string(author)}
contributors = []

[print]
trim = {toml_string(trim)}
paper = {toml_string(paper)}
bleed = {str(bleed).lower()}
cover_finish = "matte"
fonts = ["Libertinus"]

[paths]
body = "manuscript/body.typ"
interior_template = "templates/interior.typ"
cover_template = "templates/cover.typ"
fonts = "assets/fonts"
description = "listing/description.txt"
dist = "dist"

[interior]
table_of_contents = {str(toc).lower()}

[listing]
language = "English"
primary_audience = "Adult"
publishing_rights = "I own the copyright and hold necessary publishing rights"
isbn = "Free KDP ISBN"
categories = []
keywords = []
price_note = "Unverified — check KDP current printing rates"
'''
    (project / "book.toml").write_text(manifest, encoding="utf-8")
    (project / "manuscript" / "body.typ").write_text(body, encoding="utf-8")
    (project / "listing" / "description.txt").write_text(description, encoding="utf-8")
    (project / "SOURCE-" + Path(filename).name).write_bytes(raw) if False else None
    (project / "README-STUDIO.txt").write_text(
        "Projet créé par KDP Publishing Studio.\n"
        "Le manuscrit converti est dans manuscript/body.typ.\n"
        "Les paramètres sont dans book.toml.\n"
        "Les PDF finaux seront dans dist/kdp-upload/.\n",
        encoding="utf-8")
    return {"project": str(project), "title": title, "paragraphs": len(paragraphs)}


def tool_status() -> dict:
    names = ["typst", "pdfinfo", "pdftotext", "pdffonts", "pdfimages"]
    found = {name: shutil.which(name) is not None for name in names}
    return {"python": sys.version.split()[0], "tools": found, "ready": all(found.values())}


def build_project(project_text: str) -> dict:
    project = Path(project_text).expanduser().resolve()
    home = (Path.home() / "KDP-Books").resolve()
    if not project.is_relative_to(home) or not (project / "book.toml").is_file():
        raise ValueError("Projet KDP non reconnu. Créez-le depuis l'application.")
    status = tool_status()
    if not status["ready"]:
        missing = [k for k, v in status["tools"].items() if not v]
        raise RuntimeError("Outils manquants : " + ", ".join(missing) + ". Consultez le guide Windows.")
    steps = [
        ("Intérieur PDF", ["build-interior.py"]),
        ("Couverture complète", ["build-cover.py"]),
        ("Contrôle technique", ["preflight.py"]),
        ("Dossier KDP", ["kdp-package.py"]),
    ]
    logs = []
    for label, args in steps:
        cmd = [sys.executable, str(ROOT / "scripts" / args[0]), "--project", str(project)]
        if args[0] == "preflight.py":
            cmd.append("--json")
        try:
            proc = subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{label} : délai dépassé après 4 minutes.")
        output = (proc.stdout + "\n" + proc.stderr).strip()
        logs.append({"step": label, "returncode": proc.returncode, "output": output[-12000:]})
        if proc.returncode != 0:
            return {"ok": False, "logs": logs, "message": f"Échec : {label}. Corrigez les erreurs avant de continuer."}
    package = project / "dist" / "kdp-upload"
    return {"ok": True, "logs": logs, "package": str(package),
            "files": sorted(p.name for p in package.iterdir() if p.is_file())}


class Handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path == "/api/status":
            return self._json(tool_status())
        if path in ("/", "/index.html"):
            target = WEB / "index.html"
        elif path in ("/app.js", "/style.css"):
            target = WEB / path.lstrip("/")
        else:
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8" if target.suffix == ".html" else "text/javascript; charset=utf-8" if target.suffix == ".js" else "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path not in ("/api/create", "/api/build"):
            return self._json({"error": "Route inconnue."}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD + 1024 * 1024:
                return self._json({"error": "Requête vide ou trop volumineuse."}, 413)
            payload = json.loads(self.rfile.read(length))
            result = new_project(payload) if self.path == "/api/create" else build_project(str(payload.get("project", "")))
            return self._json(result, 200 if result.get("ok", True) else 422)
        except Exception as exc:
            return self._json({"error": str(exc)}, 400)

    def log_message(self, fmt, *args):
        print("[KDP Studio] " + (fmt % args))


if __name__ == "__main__":
    print(f"KDP Publishing Studio disponible sur http://{HOST}:{PORT}")
    print("Cette application reste locale sur votre ordinateur. Fermez cette fenêtre pour l'arrêter.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
