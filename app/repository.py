from __future__ import annotations

import json
from typing import Any

from app.db import get_conn


def _lob_to_str(value: Any) -> Any:
    if hasattr(value, "read"):
        return value.read()
    return value


def _rows_to_dicts(cursor, rows):
    cols = [d[0].lower() for d in cursor.description]
    normalized = []
    for row in rows:
        normalized.append({k: _lob_to_str(v) for k, v in zip(cols, row)})
    return normalized


def _json_load(value: Any) -> Any:
    if value is None:
        return {}
    if not isinstance(value, (str, bytes, bytearray)):
        value = _lob_to_str(value)
    return json.loads(value or "{}")


def ensure_schema() -> None:
    column_definitions = {
        "FINDINGS_JSON": "CLOB",
        "INPUT_FILE_BLOB": "BLOB",
        "REDACTED_FILE_BLOB": "BLOB",
    }
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_name
            FROM user_tab_cols
            WHERE table_name = 'REDACTION_RUNS'
            """
        )
        existing_columns = {row[0] for row in cur.fetchall()}
        for column_name, ddl_type in column_definitions.items():
            if column_name in existing_columns:
                continue
            cur.execute(f"ALTER TABLE redaction_runs ADD ({column_name} {ddl_type})")
        conn.commit()


def create_run(
    input_text: str,
    redacted_text: str,
    options: dict[str, Any],
    counts: dict[str, int],
    findings: list[dict[str, Any]],
    input_file_blob: bytes | None = None,
    redacted_file_blob: bytes | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        out_id = cur.var(int)
        cur.execute(
            """
            INSERT INTO redaction_runs(
                input_text,
                redacted_text,
                options_json,
                counts_json,
                findings_json,
                input_file_blob,
                redacted_file_blob
            )
            VALUES (
                :input_text,
                :redacted_text,
                :options_json,
                :counts_json,
                :findings_json,
                :input_file_blob,
                :redacted_file_blob
            )
            RETURNING run_id INTO :out_id
            """,
            {
                "input_text": input_text,
                "redacted_text": redacted_text,
                "options_json": json.dumps(options),
                "counts_json": json.dumps(counts),
                "findings_json": json.dumps(findings),
                "input_file_blob": input_file_blob,
                "redacted_file_blob": redacted_file_blob,
                "out_id": out_id,
            },
        )
        conn.commit()
        return int(out_id.getvalue()[0])


def list_runs() -> list[dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT run_id, options_json, counts_json, created_at
            FROM redaction_runs
            ORDER BY created_at DESC
            """
        )
        rows = _rows_to_dicts(cur, cur.fetchall())

    for row in rows:
        row["options"] = _json_load(row.get("options_json"))
        row["counts_json"] = _lob_to_str(row["counts_json"]) or "{}"
    return rows


def get_run(run_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                run_id,
                input_text,
                redacted_text,
                options_json,
                counts_json,
                findings_json,
                input_file_blob,
                redacted_file_blob,
                created_at
            FROM redaction_runs
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
        )
        row = cur.fetchone()
        if not row:
            return None

        item = _rows_to_dicts(cur, [row])[0]
        item["options"] = _json_load(item.get("options_json"))
        item["counts"] = _json_load(item.get("counts_json"))
        item["findings"] = _json_load(item.get("findings_json")) if item.get("findings_json") else []
        return item
