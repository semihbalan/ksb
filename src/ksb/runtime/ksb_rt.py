"""Agent-facing standard library for KSB programs."""

from __future__ import annotations

import builtins
import json as _json
import os
import shutil
import subprocess
import sys
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_str = builtins.str


def _attr(obj: Any, name: str) -> Any:
    """Attribute access that also works on dicts (JSON-friendly)."""
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


# ---------------------------------------------------------------------------
# fs
# ---------------------------------------------------------------------------


class fs:
    @staticmethod
    def read(path: str, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def write(path: str, data: str, encoding: str = "utf-8") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding=encoding)

    @staticmethod
    def exists(path: str) -> bool:
        return Path(path).exists()

    @staticmethod
    def list(path: str = ".") -> list[str]:
        return sorted(os.listdir(path))

    @staticmethod
    def mkdir(path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def remove(path: str) -> None:
        p = Path(path)
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    @staticmethod
    def copy(src: str, dst: str) -> None:
        s, d = Path(src), Path(dst)
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)

    @staticmethod
    def cwd() -> str:
        return _str(Path.cwd())


# ---------------------------------------------------------------------------
# json
# ---------------------------------------------------------------------------


class json:
    @staticmethod
    def parse(text: str) -> Any:
        return _json.loads(text)

    @staticmethod
    def dump(obj: Any, indent: int | None = None) -> str:
        return _json.dumps(obj, ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------------------
# env / log / sh
# ---------------------------------------------------------------------------


class env:
    @staticmethod
    def get(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

    @staticmethod
    def set(key: str, value: str) -> None:
        os.environ[key] = value


class log:
    @staticmethod
    def info(*args: Any) -> None:
        print(*args)

    @staticmethod
    def err(*args: Any) -> None:
        print(*args, file=sys.stderr)


class sh:
    @staticmethod
    def run(cmd: str | list[str], timeout: float | None = None) -> dict[str, Any]:
        if isinstance(cmd, str):
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
        else:
            proc = subprocess.run(
                cmd, shell=False, capture_output=True, text=True, timeout=timeout
            )
        return {"code": proc.returncode, "out": proc.stdout, "err": proc.stderr}


# ---------------------------------------------------------------------------
# http
# ---------------------------------------------------------------------------


class _HttpResult:
    __slots__ = ("status", "body", "headers")

    def __init__(self, status: int, body: str, headers: dict[str, str]) -> None:
        self.status = status
        self.body = body
        self.headers = headers

    def json(self) -> Any:
        return _json.loads(self.body) if self.body else None

    def __repr__(self) -> str:
        preview = self.body[:80] if self.body else ""
        return f"HttpResult(status={self.status}, body={preview!r}...)"


class http:
    @staticmethod
    def get(
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
    ) -> _HttpResult:
        if params:
            q = urllib.parse.urlencode({k: _str(v) for k, v in params.items()})
            url = f"{url}{'&' if '?' in url else '?'}{q}"
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        return http._open(req, timeout=timeout)

    @staticmethod
    def post(
        url: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        timeout: float = 30,
    ) -> _HttpResult:
        return http._write("POST", url, data=data, headers=headers, json_body=json_body, timeout=timeout)

    @staticmethod
    def put(
        url: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        timeout: float = 30,
    ) -> _HttpResult:
        return http._write("PUT", url, data=data, headers=headers, json_body=json_body, timeout=timeout)

    @staticmethod
    def delete(
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
    ) -> _HttpResult:
        req = urllib.request.Request(url, headers=headers or {}, method="DELETE")
        return http._open(req, timeout=timeout)

    @staticmethod
    def get_json(url: str, **kwargs: Any) -> Any:
        r = http.get(url, **kwargs)
        return r.json()

    @staticmethod
    def post_json(url: str, json_body: Any = None, **kwargs: Any) -> Any:
        r = http.post(url, json_body=json_body, **kwargs)
        return r.json()

    @staticmethod
    def _write(
        method: str,
        url: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        timeout: float = 30,
    ) -> _HttpResult:
        hdrs = dict(headers or {})
        body: bytes | None = None
        if json_body is not None:
            body = _json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif data is not None:
            if isinstance(data, (dict, list)):
                body = urllib.parse.urlencode(data).encode("utf-8")
                hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
            elif isinstance(data, str):
                body = data.encode("utf-8")
            elif isinstance(data, bytes):
                body = data
            else:
                body = _str(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        return http._open(req, timeout=timeout)

    @staticmethod
    def _open(req: urllib.request.Request, timeout: float = 30) -> _HttpResult:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                hdrs = {k: v for k, v in resp.headers.items()}
                return _HttpResult(resp.status, text, hdrs)
        except urllib.error.HTTPError as e:
            raw = e.read()
            text = raw.decode("utf-8", errors="replace") if raw else ""
            return _HttpResult(e.code, text, dict(e.headers.items()) if e.headers else {})


# ---------------------------------------------------------------------------
# time / path / cli / str / tool
# ---------------------------------------------------------------------------


class time:
    @staticmethod
    def now() -> float:
        return _time.time()

    @staticmethod
    def ms() -> int:
        return int(_time.time() * 1000)

    @staticmethod
    def sleep(seconds: float) -> None:
        _time.sleep(float(seconds))

    @staticmethod
    def iso() -> str:
        return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())


class path:
    @staticmethod
    def join(*parts: str) -> str:
        return _str(Path(*parts)) if parts else ""

    @staticmethod
    def dirname(p: str) -> str:
        return _str(Path(p).parent)

    @staticmethod
    def basename(p: str) -> str:
        return Path(p).name

    @staticmethod
    def abs(p: str) -> str:
        return _str(Path(p).resolve())

    @staticmethod
    def ext(p: str) -> str:
        return Path(p).suffix


class cli:
    @staticmethod
    def args() -> list[str]:
        return list(sys.argv[1:])

    @staticmethod
    def argc() -> int:
        return max(0, len(sys.argv) - 1)

    @staticmethod
    def arg(i: int, default: str | None = None) -> str | None:
        idx = int(i) + 1  # 0 = first user arg
        if 0 <= idx < len(sys.argv):
            return sys.argv[idx]
        return default


class str:  # noqa: A001 — intentional agent-facing name
    @staticmethod
    def split(s: str, sep: str | None = None) -> list[str]:
        return s.split(sep) if sep is not None else s.split()

    @staticmethod
    def join(parts: list[Any], sep: str = "") -> str:
        return sep.join(_str(p) for p in parts)

    @staticmethod
    def trim(s: str) -> str:
        return s.strip()

    @staticmethod
    def replace(s: str, old: str, new: str) -> str:
        return s.replace(old, new)

    @staticmethod
    def contains(s: str, sub: str) -> bool:
        return sub in s

    @staticmethod
    def lower(s: str) -> str:
        return s.lower()

    @staticmethod
    def upper(s: str) -> str:
        return s.upper()

    @staticmethod
    def startswith(s: str, prefix: str) -> bool:
        return s.startswith(prefix)

    @staticmethod
    def endswith(s: str, suffix: str) -> bool:
        return s.endswith(suffix)


class tool:
    """Tiny helpers for agent tool-result shapes."""

    @staticmethod
    def ok(data: Any = None, **extra: Any) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": True, "data": data}
        out.update(extra)
        return out

    @staticmethod
    def err(message: str, **extra: Any) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": False, "error": message}
        out.update(extra)
        return out

    @staticmethod
    def wrap(fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return tool.ok(fn(*args, **kwargs))
        except Exception as e:  # noqa: BLE001
            return tool.err(_str(e))
