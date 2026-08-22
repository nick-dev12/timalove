#!/usr/bin/env python3
"""Ré-applique le reverse-proxy Daphne dans webuzoVH.conf si Webuzo l'a écrasé.

Idempotent : ne réécrit le fichier que si le marqueur Daphne est absent.
À lancer par systemd (watch) et cron (filet de sécurité).
"""

from __future__ import annotations

import fcntl
import re
import subprocess
import sys
from pathlib import Path

CONF = Path("/usr/local/apps/nginx/etc/conf.d/webuzoVH.conf")
NGINX_BIN = Path("/usr/local/apps/nginx/sbin/nginx")
LOCK_PATH = Path("/run/timalove-nginx-patch.lock")
DOMAIN = "timalove.goo-bridge.com"
PATCH_VERSION = "v3"
MARKER_BEGIN = f"# --- timalove-daphne-{PATCH_VERSION}-begin ---"
MARKER_END = f"# --- timalove-daphne-{PATCH_VERSION}-end ---"
WS_SIGNATURE = "connection_upgrade"

WS_MAP = """
# --- timalove-ws-map ---
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
# --- timalove-ws-map-end ---
"""

# modsecurity off : le WAF Webuzo coupe souvent Upgrade: websocket (1006).
PROXY = f"""
        {MARKER_BEGIN}
        location /static/ {{
            alias /home/colobanes/timalove.goo-bridge.com/timalove/staticfiles/;
            expires 30d;
            access_log off;
        }}
        location /media/ {{
            alias /home/colobanes/timalove.goo-bridge.com/timalove/media/;
            expires 7d;
            access_log off;
        }}
        location ^~ /ws/ {{
            modsecurity off;
            gzip off;
            proxy_pass http://127.0.0.1:8001;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400s;
            proxy_send_timeout 86400s;
            proxy_buffering off;
            proxy_request_buffering off;
            proxy_cache off;
        }}
        location / {{
            proxy_pass http://127.0.0.1:8001;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";
            proxy_redirect off;
            proxy_read_timeout 60s;
            client_max_body_size 20M;
        }}
        {MARKER_END}
"""

SERVER_NAME_RE = re.compile(
    r"server_name[^;]*timalove\.goo-bridge\.com(?:\s|;|,)",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    print(f"[timalove-nginx] {msg}", flush=True)
    try:
        import syslog

        syslog.syslog(syslog.LOG_INFO, f"timalove-nginx-patch: {msg}")
    except Exception:
        pass


def matching_brace(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("Accolade nginx non fermée")


def comment_location_slash(block: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(block):
        m = re.search(r"location\s+/\s*\{", block[i:])
        if not m:
            out.append(block[i:])
            break
        abs_start = i + m.start()
        out.append(block[i:abs_start])
        brace = i + m.end() - 1
        end = matching_brace(block, brace)
        chunk = block[abs_start : end + 1]
        commented_lines = []
        for line in chunk.splitlines(True):
            if not line.strip() or line.lstrip().startswith("#"):
                commented_lines.append(line)
            else:
                commented_lines.append("# " + line)
        out.append("        # location / Webuzo désactivé (proxy Daphne)\n")
        out.append("".join(commented_lines))
        if not chunk.endswith("\n"):
            out.append("\n")
        i = end + 1
    return "".join(out)


def strip_marked_proxy(block: str) -> str:
    patterns = [
        re.compile(
            r"# --- timalove-daphne-v\d+-begin ---.*?# --- timalove-daphne-v\d+-end ---",
            re.DOTALL,
        ),
        re.compile(
            re.escape("# --- timalove-daphne-begin ---")
            + r".*?"
            + re.escape("# --- timalove-daphne-end ---"),
            re.DOTALL,
        ),
    ]
    for pattern in patterns:
        block = pattern.sub("", block)
    return block


def ensure_ws_map(text: str) -> str:
    if "timalove-ws-map" in text:
        return text
    return WS_MAP.strip() + "\n\n" + text


def patch_block(block: str) -> str:
    if MARKER_BEGIN in block and WS_SIGNATURE in block:
        return block
    had_marker = "timalove-daphne" in block
    block = strip_marked_proxy(block)
    if not had_marker:
        block = comment_location_slash(block)
    close = block.rfind("}")
    return block[:close] + PROXY + "\n    }\n"


def iter_server_spans(text: str):
    i = 0
    while True:
        m = re.search(r"\bserver\s*\{", text[i:])
        if not m:
            return
        start = i + m.start()
        brace = i + m.end() - 1
        end = matching_brace(text, brace)
        yield start, end
        i = end + 1


def nginx_test_and_reload() -> None:
    if not NGINX_BIN.is_file():
        raise RuntimeError(f"Nginx Webuzo introuvable : {NGINX_BIN}")
    test = subprocess.run(
        [str(NGINX_BIN), "-t"],
        capture_output=True,
        text=True,
    )
    output = (test.stdout or "") + (test.stderr or "")
    if test.returncode != 0:
        raise RuntimeError(f"nginx -t a échoué:\n{output}")
    reload = subprocess.run(
        [str(NGINX_BIN), "-s", "reload"],
        capture_output=True,
        text=True,
    )
    if reload.returncode != 0:
        raise RuntimeError(
            f"nginx reload a échoué:\n{(reload.stdout or '') + (reload.stderr or '')}"
        )


def apply_patch(text: str) -> tuple[str, int, int]:
    text = ensure_ws_map(text)
    parts: list[str] = []
    last = 0
    timalove_blocks = 0
    patched = 0
    for start, end in iter_server_spans(text):
        parts.append(text[last:start])
        block = text[start : end + 1]
        if SERVER_NAME_RE.search(block):
            timalove_blocks += 1
            new_block = patch_block(block)
            if new_block != block:
                patched += 1
            parts.append(new_block)
        else:
            parts.append(block)
        last = end + 1
    parts.append(text[last:])
    return "".join(parts), timalove_blocks, patched


def main() -> int:
    lock_f = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("déjà en cours, sortie")
        return 0

    if not CONF.exists():
        log(f"introuvable : {CONF}")
        return 1

    original = CONF.read_text(encoding="utf-8", errors="replace")
    new_text, found, patched = apply_patch(original)

    if found == 0:
        log(f"aucun server_name {DOMAIN} dans {CONF}")
        return 1

    if patched == 0 and new_text == original:
        log(f"déjà à jour ({found} server block(s))")
        return 0

    backup = Path(str(CONF) + ".bak-daphne")
    backup.write_text(original, encoding="utf-8")
    CONF.write_text(new_text, encoding="utf-8")
    try:
        nginx_test_and_reload()
    except Exception as exc:
        if "modsecurity" in str(exc).lower() and "modsecurity off;" in new_text:
            log("modsecurity absent — nouvel essai sans la directive")
            fallback = new_text.replace("            modsecurity off;\n", "")
            CONF.write_text(fallback, encoding="utf-8")
            try:
                nginx_test_and_reload()
            except Exception as exc2:
                CONF.write_text(original, encoding="utf-8")
                log(f"échec, fichier restauré : {exc2}")
                return 1
        else:
            CONF.write_text(original, encoding="utf-8")
            log(f"échec, fichier restauré : {exc}")
            return 1

    log(f"Webuzo avait écrasé Nginx — proxy Daphne ré-appliqué ({patched} block(s)), Nginx rechargé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
