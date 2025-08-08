import os
import yaml
import logging
import hashlib
import subprocess
import time
import csv
import json
from datetime import datetime
import shutil
from pathlib import Path
from argparse import ArgumentParser
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import pdfplumber
from git import Repo


def load_config(path="config.yaml"):
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def check_dependencies(cmds):
    """Ensure required external commands are available."""
    missing = [c for c in cmds if not shutil.which(c)]
    if missing:
        raise EnvironmentError(f"Missing required command(s): {', '.join(missing)}")


class IntakeHandler(FileSystemEventHandler):
    def __init__(self, config, repo):
        super().__init__()
        self.config = config
        self.repo = repo
        self.log_file = config.get("log_file", "Chain_of_Custody_Log.csv")
        # create log file if not exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "filename",
                    "sha256",
                    "commit_id",
                ])

    def _out_paths(self, src_path):
        processed_dir = self.config.get("processed_dir", "processed")
        os.makedirs(processed_dir, exist_ok=True)
        base = os.path.basename(src_path)
        name, _ = os.path.splitext(base)
        out_pdf = os.path.join(processed_dir, f"{name}_ocr.pdf")
        sidecar_txt = os.path.join(processed_dir, f"{name}.txt")
        sidecar_json = os.path.join(processed_dir, f"{name}.json")
        return out_pdf, sidecar_txt, sidecar_json

    def _already_processed(self, src_path):
        out_pdf, _, _ = self._out_paths(src_path)
        return os.path.exists(out_pdf)

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def _handle_event(self, path):
        if self._already_processed(path):
            return
        try:
            self.process(path)
        except Exception:
            logging.exception("Error processing %s", path)

    def process(self, path):
        logging.info("Processing %s", path)
        out_pdf, sidecar_txt, sidecar_json = self._out_paths(path)
        base = os.path.basename(path)

        # OCR and convert to PDF/A using ocrmypdf
        logging.info("Running OCRmyPDF")
        cmd = [
            "ocrmypdf",
            "--output-type",
            "pdfa",
            "--sidecar",
            sidecar_txt,
            "--image-dpi",
            "300",
            "--tesseract",
            self.config.get("tesseract_cmd", "tesseract"),
            path,
            out_pdf,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error("OCRmyPDF failed: %s", e.stderr.decode())
            return

        # Extract text and tables with pdfplumber
        logging.info("Extracting text and tables")
        text = []
        tables = []
        with pdfplumber.open(out_pdf) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text.append(page.extract_text())
                for table in page.extract_tables():
                    tables.append(table)
        with open(sidecar_json, "w") as f:
            json.dump({"text": "\n".join(text), "tables": tables}, f, indent=2)

        # Calculate SHA256
        logging.info("Hashing file")
        sha256 = hashlib.sha256()
        with open(out_pdf, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()

        # Add files to git and commit
        self.repo.git.add([out_pdf, sidecar_txt, sidecar_json])
        commit = self.repo.index.commit(f"Process {base}")

        # Append to chain of custody log
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.utcnow().isoformat(),
                path,
                digest,
                commit.hexsha,
            ])
        self.repo.git.add(self.log_file)
        self.repo.index.commit(f"Log {base}")
        logging.info("Finished processing %s", path)


def main():
    parser = ArgumentParser(description="Watch a vault for new documents")
    parser.add_argument(
        "--config", default="config.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()

    config = load_config(args.config)

    log_params = {
        "level": logging.INFO,
        "format": "%(asctime)s %(levelname)s %(message)s",
    }
    if config.get("app_log"):
        log_params["filename"] = config["app_log"]
    logging.basicConfig(**log_params)

    check_dependencies(["ocrmypdf", config.get("tesseract_cmd", "tesseract")])

    repo = Repo(Path.cwd())

    vault = config.get("vault_root", "incoming")
    processed = config.get("processed_dir", "processed")
    os.makedirs(vault, exist_ok=True)
    os.makedirs(processed, exist_ok=True)

    handler = IntakeHandler(config, repo)

    # Process existing files once at startup
    for fname in os.listdir(vault):
        path = os.path.join(vault, fname)
        if os.path.isfile(path) and not handler._already_processed(path):
            handler._handle_event(path)

    observer = PollingObserver()
    observer.schedule(handler, path=vault, recursive=False)
    observer.start()
    logging.info("Watching %s", vault)

    try:
        while True:
            time.sleep(config.get("poll_interval", 5))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
