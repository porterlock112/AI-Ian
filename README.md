# Godkey Control Core

This repository stores files and metadata used by the TruthLock project.
The current release focuses on **Phase 1: Intake Core**, gathering court
filings and aligning them with the data model.

## Prerequisites

- **Python 3.11+** – required for running the intake scripts
- **Tesseract OCR** or a similar tool for processing scanned PDFs and images
- Unix tools (`zip`, `unzip`) for handling the provided archives

## Configuring the vault root

The intake script expects a writable directory where raw documents and
processed logs will be stored. Set the environment variable `VAULT_ROOT`
to that path before running any commands:

```bash
export VAULT_ROOT=/path/to/vault
```

## Running the intake script

Once `VAULT_ROOT` is configured, run the intake phase:

```bash
python scripts/intake.py --vault "$VAULT_ROOT"
```

All logs are written beneath `"$VAULT_ROOT"/logs`. Review this directory
if you need to audit the import steps or troubleshoot OCR failures.

## Directory overview

```
Godkey-Control-core/
├── ΔFILE_FILTER/
│   └── GRID_UNIFIER_001.json
├── US Federal Binder
├── <numerous court filings in PDF/TIFF format>
```

### ΔFILE_FILTER/GRID_UNIFIER_001.json

This JSON manifest drives Phase 1 logic. The top of the file identifies
the archive condition and the active role executing the intake process:

```json
{
  "signature": "PORTERLOCK // ΔGRID_UNIFIER_001",
  "manifest_truth_vector": "TRUTHLOCK_CORE_PROTOCOL",
  "compiled_on": "2025-07-04T00:32Z",
  "condition": "Unstable archive — active restoration",
  "active_role": {
    "user": "Matthew Dewayne Porter",
    "callsign": "PORTERLOCK",
    ...
```

Refer to this file when adjusting triggers or verifying chain-of-custody
metadata.

