from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import repository
from app.config import settings
from app.db import init_pool
from app.redactor import DETECTOR_KEYS, PATTERNS, detect_person_name_candidates, redact_pdf, redact_text

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
DRAFT_DIR = Path("/tmp/redactright_drafts")


@app.on_event("startup")
def _startup() -> None:
    init_pool()
    repository.ensure_schema()
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)


def _enabled_detectors(
    redact_email: Optional[str],
    redact_phone: Optional[str],
    redact_ssn: Optional[str],
    redact_credit_card: Optional[str],
    redact_ip_address: Optional[str],
) -> dict[str, bool]:
    return {
        "email": redact_email == "on",
        "phone": redact_phone == "on",
        "ssn": redact_ssn == "on",
        "credit_card": redact_credit_card == "on",
        "ip_address": redact_ip_address == "on",
    }


def _source_name(upload: UploadFile | None) -> str:
    if upload and upload.filename:
        return Path(upload.filename).name
    return "pasted_text"


def _parse_custom_terms(raw_terms: str) -> list[str]:
    separators_normalized = raw_terms.replace("\r", "\n").replace(",", "\n")
    return [term.strip() for term in separators_normalized.split("\n") if term.strip()]


def _is_pdf_upload(upload: UploadFile | None) -> bool:
    if not upload or not upload.filename:
        return False
    return Path(upload.filename).suffix.lower() == ".pdf" or upload.content_type == "application/pdf"


def _page_context(request: Request, **overrides):
    context = {
        "request": request,
        "patterns": list(PATTERNS.keys()),
        "redacted": None,
        "counts": None,
        "source": "",
        "custom_terms": "",
        "draft_token": "",
        "draft_source_name": "",
        "draft_source_kind": "",
        "detected_name_candidates": [],
        "selected_detected_terms": [],
        "notice": None,
        "active": "redact",
        "error": None,
        "redact_email": True,
        "redact_phone": True,
        "redact_ssn": True,
        "redact_credit_card": True,
        "redact_ip_address": True,
    }
    context.update(overrides)
    return context


def _draft_meta_path(token: str) -> Path:
    return DRAFT_DIR / f"{token}.json"


def _draft_blob_path(token: str) -> Path:
    return DRAFT_DIR / f"{token}.bin"


def _save_draft(source_name: str, source_kind: str, text_input: str, file_bytes: bytes | None) -> str:
    token = uuid4().hex
    _draft_meta_path(token).write_text(
        json.dumps(
            {
                "source_name": source_name,
                "source_kind": source_kind,
                "text_input": text_input,
                "has_file": bool(file_bytes),
            }
        ),
        encoding="utf-8",
    )
    if file_bytes is not None:
        _draft_blob_path(token).write_bytes(file_bytes)
    return token


def _load_draft(token: str) -> dict[str, object] | None:
    if not token or any(char not in "0123456789abcdef" for char in token.lower()):
        return None

    meta_path = _draft_meta_path(token)
    if not meta_path.exists():
        return None

    draft = json.loads(meta_path.read_text(encoding="utf-8"))
    if draft.get("has_file"):
        blob_path = _draft_blob_path(token)
        draft["file_bytes"] = blob_path.read_bytes() if blob_path.exists() else None
    else:
        draft["file_bytes"] = None
    return draft


def _delete_draft(token: str) -> None:
    for path in (_draft_meta_path(token), _draft_blob_path(token)):
        if path.exists():
            path.unlink()


def _extract_source_text(upload: UploadFile, raw: bytes) -> str:
    if _is_pdf_upload(upload):
        return redact_pdf(raw, {}, [], []).source_text
    return raw.decode("utf-8", errors="replace")


def _resolve_source(source_text: str, source_file: UploadFile | None, draft_token: str) -> dict[str, object]:
    if source_file and source_file.filename:
        raw = source_file.file.read()
        return {
            "source_name": _source_name(source_file),
            "source_kind": "pdf" if _is_pdf_upload(source_file) else "text",
            "text_input": _extract_source_text(source_file, raw),
            "input_file_blob": raw,
            "pdf_bytes": raw if _is_pdf_upload(source_file) else None,
        }

    if draft_token:
        draft = _load_draft(draft_token)
        if not draft:
            raise ValueError("The saved draft expired. Please upload the document again.")
        return {
            "source_name": str(draft["source_name"]),
            "source_kind": str(draft["source_kind"]),
            "text_input": str(draft["text_input"]),
            "input_file_blob": draft.get("file_bytes"),
            "pdf_bytes": draft.get("file_bytes") if draft.get("source_kind") == "pdf" else None,
        }

    return {
        "source_name": "pasted_text",
        "source_kind": "text",
        "text_input": source_text,
        "input_file_blob": None,
        "pdf_bytes": None,
    }


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/redact", status_code=303)


@app.get("/redact")
def redact_page(request: Request):
    return templates.TemplateResponse("redact.html", _page_context(request))


@app.post("/redact")
def run_redaction(
    request: Request,
    action: str = Form("redact"),
    source_text: str = Form(""),
    source_file: Optional[UploadFile] = File(None),
    draft_token: str = Form(""),
    custom_terms: str = Form(""),
    selected_detected_terms: Optional[list[str]] = Form(None),
    redact_email: Optional[str] = Form(None),
    redact_phone: Optional[str] = Form(None),
    redact_ssn: Optional[str] = Form(None),
    redact_credit_card: Optional[str] = Form(None),
    redact_ip_address: Optional[str] = Form(None),
):
    enabled = _enabled_detectors(
        redact_email,
        redact_phone,
        redact_ssn,
        redact_credit_card,
        redact_ip_address,
    )
    parsed_custom_terms = _parse_custom_terms(custom_terms)
    selected_names = selected_detected_terms or []

    try:
        source = _resolve_source(source_text, source_file, draft_token)
        text_input = str(source["text_input"] or "")

        if not text_input.strip():
            raise ValueError("Provide source text or upload a text or PDF file.")

        if action == "detect_names":
            candidates = detect_person_name_candidates(text_input)
            new_draft_token = _save_draft(
                source_name=str(source["source_name"]),
                source_kind=str(source["source_kind"]),
                text_input=text_input,
                file_bytes=source["input_file_blob"] if isinstance(source["input_file_blob"], (bytes, bytearray)) else None,
            )
            if draft_token:
                _delete_draft(draft_token)

            notice = (
                f"Detected {len(candidates)} possible names. Review the list below and keep only the ones you want to redact."
                if candidates
                else "No likely person names were detected automatically. You can still use the custom names field for exact redaction."
            )
            return templates.TemplateResponse(
                "redact.html",
                _page_context(
                    request,
                    source=source_text if not source_file or not source_file.filename else "",
                    custom_terms=custom_terms,
                    draft_token=new_draft_token,
                    draft_source_name=str(source["source_name"]),
                    draft_source_kind=str(source["source_kind"]),
                    detected_name_candidates=candidates,
                    selected_detected_terms=candidates,
                    notice=notice,
                    redact_email=enabled["email"],
                    redact_phone=enabled["phone"],
                    redact_ssn=enabled["ssn"],
                    redact_credit_card=enabled["credit_card"],
                    redact_ip_address=enabled["ip_address"],
                ),
            )

        redacted_file_blob: bytes | None = None
        if source["source_kind"] == "pdf":
            pdf_bytes = source["pdf_bytes"]
            if not isinstance(pdf_bytes, (bytes, bytearray)):
                raise ValueError("The saved PDF draft is missing. Please upload the PDF again.")
            result = redact_pdf(
                bytes(pdf_bytes),
                enabled,
                custom_terms=parsed_custom_terms,
                person_name_terms=selected_names,
            )
            redacted_file_blob = result.redacted_file
        else:
            result = redact_text(
                text_input,
                enabled,
                custom_terms=parsed_custom_terms,
                person_name_terms=selected_names,
            )

        options = dict(enabled)
        options["source_name"] = str(source["source_name"])
        options["source_kind"] = str(source["source_kind"])
        options["has_redacted_pdf"] = bool(redacted_file_blob)
        options["custom_terms"] = parsed_custom_terms
        options["selected_detected_terms"] = selected_names
        run_id = repository.create_run(
            input_text=text_input,
            redacted_text=result.redacted_text,
            options=options,
            counts=result.counts,
            findings=result.findings,
            input_file_blob=source["input_file_blob"] if isinstance(source["input_file_blob"], (bytes, bytearray)) else None,
            redacted_file_blob=redacted_file_blob,
        )
        if draft_token:
            _delete_draft(draft_token)
    except Exception as exc:
        return templates.TemplateResponse(
            "redact.html",
            _page_context(
                request,
                source=source_text,
                custom_terms=custom_terms,
                draft_token=draft_token,
                selected_detected_terms=selected_names,
                redact_email=enabled["email"],
                redact_phone=enabled["phone"],
                redact_ssn=enabled["ssn"],
                redact_credit_card=enabled["credit_card"],
                redact_ip_address=enabled["ip_address"],
                error=f"Error: {exc}",
            ),
        )

    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


@app.get("/runs")
def runs_page(request: Request):
    runs = repository.list_runs()
    return templates.TemplateResponse(
        "runs.html",
        {"request": request, "runs": runs, "active": "runs"},
    )


@app.get("/runs/{run_id}")
def run_detail_page(request: Request, run_id: int):
    run = repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return templates.TemplateResponse(
        "run_detail.html",
        {"request": request, "run": run, "active": "runs"},
    )


@app.get("/runs/{run_id}/download")
def download_redacted_text(run_id: int):
    run = repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return PlainTextResponse(
        content=run["redacted_text"],
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=redacted_run_{run_id}.txt"},
    )


@app.get("/runs/{run_id}/download-pdf")
def download_redacted_pdf(run_id: int):
    run = repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.get("redacted_file_blob"):
        raise HTTPException(status_code=404, detail="Redacted PDF not available for this run")

    source_name = run.get("options", {}).get("source_name", "redacted.pdf")
    base_name = Path(source_name).stem or "redacted"
    return Response(
        content=run["redacted_file_blob"],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={base_name}.redacted.pdf"},
    )


@app.get("/runs/{run_id}/download-report")
def download_redaction_report(run_id: int):
    run = repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    report = {
        "run_id": run["run_id"],
        "created_at": str(run["created_at"]),
        "source_name": run.get("options", {}).get("source_name", "unknown"),
        "source_kind": run.get("options", {}).get("source_kind", "text"),
        "enabled_detectors": {k: bool(v) for k, v in run.get("options", {}).items() if k in DETECTOR_KEYS},
        "custom_terms": run.get("options", {}).get("custom_terms", []),
        "selected_detected_terms": run.get("options", {}).get("selected_detected_terms", []),
        "counts": run.get("counts", {}),
        "findings": run.get("findings", []),
        "artifacts": {
            "redacted_text": True,
            "redacted_pdf": bool(run.get("redacted_file_blob")),
        },
    }
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=redaction_report_{run_id}.json"},
    )
