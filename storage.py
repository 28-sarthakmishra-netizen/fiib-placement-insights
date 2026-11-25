"""Where data lives.

- SheetStore: a Google Sheet, reached through a small Apps Script web app (free).
- LocalStore: a JSON file, used when no Sheet is set up (fine for trying it on a laptop;
  on Streamlit Cloud it resets whenever the app restarts).
"""
from __future__ import annotations

import json
import os
import threading
import uuid

import requests

JSON_FIELDS = {
    "scores", "external_ratings", "claims", "red_flags", "sources", "warnings",
    "flags", "review_checks",
}
INT_FIELDS = {"base_tier", "tier", "bond_months", "rating_overall", "rating_wlb",
              "rating_culture", "rating_growth", "rating_management"}
FLOAT_FIELDS = {"ctc_lpa", "score"}
BOOL_FIELDS = {"override", "hidden", "demo", "ai_suggests_exceptional"}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")


def normalise(rec: dict) -> dict:
    out = {}
    for k, v in rec.items():
        if k in JSON_FIELDS:
            if isinstance(v, str):
                try:
                    v = json.loads(v) if v else ([] if k != "scores" else {})
                except json.JSONDecodeError:
                    v = [] if k != "scores" else {}
        elif k in INT_FIELDS:
            try:
                v = int(float(v)) if v not in ("", None) else 0
            except (TypeError, ValueError):
                v = 0
        elif k in FLOAT_FIELDS:
            try:
                v = float(v) if v not in ("", None) else 0.0
            except (TypeError, ValueError):
                v = 0.0
        elif k in BOOL_FIELDS:
            v = _to_bool(v)
        elif v is None:
            v = ""
        out[k] = v
    return out


def flatten(rec: dict) -> dict:
    return {k: (json.dumps(v, ensure_ascii=False) if k in JSON_FIELDS else v) for k, v in rec.items()}


class LocalStore:
    kind = "local"

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            self._write({"assessments": [], "reviews": []})

    def _read(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"assessments": [], "reviews": []}

    def _write(self, data: dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def list(self, table: str) -> list[dict]:
        with self._lock:
            return [normalise(r) for r in self._read().get(table, [])]

    def add(self, table: str, rec: dict) -> None:
        with self._lock:
            data = self._read()
            data.setdefault(table, []).append(rec)
            self._write(data)

    def update(self, table: str, rec_id: str, fields: dict) -> None:
        with self._lock:
            data = self._read()
            for r in data.get(table, []):
                if r.get("id") == rec_id:
                    r.update(fields)
            self._write(data)


class SheetError(Exception):
    pass


class SheetStore:
    kind = "sheet"
    TABLES = {"assessments": "Assessments", "reviews": "Reviews"}

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

    def _post(self, payload: dict):
        payload = {"token": self.token, **payload}
        try:
            r = requests.post(self.url, data=json.dumps(payload),
                              headers={"Content-Type": "text/plain"}, timeout=40)
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            raise SheetError(f"Could not reach the Google Sheet ({type(e).__name__}).") from e
        if not data.get("ok"):
            raise SheetError(f"Google Sheet said: {data.get('error', 'unknown error')}")
        return data.get("data")

    def list(self, table: str) -> list[dict]:
        rows = self._post({"action": "list", "sheet": self.TABLES[table]}) or []
        return [normalise(r) for r in rows]

    def add(self, table: str, rec: dict) -> None:
        self._post({"action": "add", "sheet": self.TABLES[table], "record": flatten(rec)})

    def update(self, table: str, rec_id: str, fields: dict) -> None:
        self._post({"action": "update", "sheet": self.TABLES[table], "id": rec_id,
                    "fields": flatten(fields)})
