# Product Requirements

## Product name

RedactRight

## One-sentence summary

RedactRight is a web application that helps users remove sensitive information from text and PDFs, then save and review each redaction run with downloadable artifacts.

## Problem

Teams often need to share documents quickly for review, demos, audits, or support workflows, but those documents may contain PII or confidential identifiers. Manual redaction is slow, error-prone, and difficult to verify.

## Target users

- Internal compliance and audit teams
- Operations teams preparing documents for external sharing
- Demo teams that need safe sample data quickly
- Hackathon judges or reviewers who need a simple redaction workflow

## Goals

- Make it easy to redact common sensitive data from text and PDFs
- Provide a low-friction UI that works in a live demo
- Preserve a history of runs for review and artifact download
- Support both automated pattern redaction and user-guided exact-term redaction

## Non-goals

- Full enterprise DLP coverage
- Highly accurate named-entity recognition across all document types
- Multi-user workflows, role-based access control, or approvals
- Production-grade records retention and governance

## Core user stories

1. As a user, I can paste text and redact common PII in one step.
2. As a user, I can upload a PDF and download a redacted PDF artifact.
3. As a user, I can review likely person-name matches before applying them.
4. As a user, I can add custom names or phrases that must be redacted exactly.
5. As a user, I can browse previous redaction runs and inspect what changed.

## Functional requirements

### Input

- Accept pasted text input
- Accept uploaded `.txt`, `.log`, `.csv`, `.json`, and `.pdf` files
- Preserve uploaded content between name detection and final redaction

### Detection and redaction

- Support detector toggles for email, phone, SSN, credit card, and IP address
- Support custom exact-match terms supplied by the user
- Detect likely person names and allow manual review before applying them
- Replace matches in text with typed placeholders
- Apply visual redactions to supported PDFs

### Persistence

- Save each run to Oracle
- Store original text, redacted text, options, findings, timestamps, and file artifacts
- List historical runs in reverse chronological order
- Show a detail page for each run

### Output

- Allow users to download redacted text
- Allow users to download redacted PDFs when applicable
- Allow users to download a JSON findings report

## User experience requirements

- The main redaction flow should complete in a single page
- The app should be understandable without training during a demo
- The user should be able to move from upload to downloadable output in under two minutes

## Success criteria

- A user can redact text and view the saved run without needing the terminal
- A user can upload a text-based PDF and receive a redacted PDF output
- The app clearly shows what detectors ran and what findings were captured

## Demo scenario

1. Open `/redact`
2. Paste a text sample or upload a PDF with visible PII
3. Click `Detect Names` and review suggested names
4. Run the final redaction
5. Open the saved run detail page
6. Download the redacted output and findings report

## Risks

- Regex-based detection can miss non-standard formats
- Name detection may over-match capitalized phrases
- Scanned PDFs without selectable text will not redact correctly
- Saving source content in the database increases sensitivity and compliance burden

## Future enhancements

- OCR for scanned PDFs
- Authentication and per-user run ownership
- Additional detector classes such as addresses and account numbers
- Confidence scoring and review queues
- Bulk upload workflows
