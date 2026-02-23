from __future__ import annotations

import hashlib
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy.orm import Session

from backend.app.models import ProcessedImage, ProductRun
from backend.app.services.logger import log_event

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}


class MonitorManager:
    def __init__(self, db_factory: Callable[[], Session], processor: Callable[[str], dict]):
        self.db_factory = db_factory
        self.processor = processor
        self.work_queue: queue.Queue[str] = queue.Queue()
        self.running = False
        self.current_file: Optional[str] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.poll_thread: Optional[threading.Thread] = None
        self.watch_folder: Optional[str] = None

    def start(self, folder: str):
        if self.running:
            return

        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)

        self.watch_folder = folder
        self.running = True

        db = self.db_factory()
        try:
            for p in folder_path.iterdir():
                if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES:
                    self._mark_baseline(db, str(p))
            log_event(db, f"Monitoring started for {folder}")
        finally:
            db.close()

        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

        self.poll_thread = threading.Thread(target=self._poll_folder, daemon=True)
        self.poll_thread.start()

    def stop(self):
        self.running = False

    def enqueue_path(self, image_path: str):
        path = Path(image_path)
        if path.suffix.lower() in ALLOWED_SUFFIXES and path.exists():
            self.work_queue.put(str(path))
            return True
        return False

    def _poll_folder(self):
        while self.running and self.watch_folder:
            folder = Path(self.watch_folder)
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in ALLOWED_SUFFIXES:
                    self.work_queue.put(str(file))
            time.sleep(3)  # Render-safe polling interval

    def _worker(self):
        while self.running:
            try:
                image_path = self.work_queue.get(timeout=1)
            except queue.Empty:
                continue

            self.current_file = image_path
            db = self.db_factory()

            try:
                self._process_single(db, image_path)
            except Exception as exc:
                log_event(db, f"Unhandled processing failure: {exc}", "ERROR", image_path)
            finally:
                self.current_file = None
                db.close()
                self.work_queue.task_done()

    @staticmethod
    def _file_hash(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    def _mark_baseline(self, db: Session, path: str):
        file_hash = self._file_hash(path)
        exists = db.query(ProcessedImage).filter(ProcessedImage.path == path).first()
        if not exists:
            db.add(
                ProcessedImage(
                    path=path,
                    file_hash=file_hash,
                    status="baseline",
                    message="Existing before monitoring started",
                )
            )
            db.commit()

    def _process_single(self, db: Session, path: str):
        path_obj = Path(path)
        if not path_obj.exists():
            return

        time.sleep(0.5)
        file_hash = self._file_hash(path)

        existing = db.query(ProcessedImage).filter(ProcessedImage.file_hash == file_hash).first()
        if existing:
            return

        processed = ProcessedImage(path=path, file_hash=file_hash, status="processing")
        run = ProductRun(image_path=path, file_hash=file_hash, status="processing", success=False)
        db.add(processed)
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            result = self.processor(path)

            run.status = "done"
            run.success = True
            run.analysis_json = result.get("analysis_json")
            run.listing_json = result.get("listing_json")
            run.printify_upload_id = result.get("printify_upload_id")
            run.printify_product_id = result.get("printify_product_id")

            processed.status = "done"
            processed.message = f"Draft product created: {run.printify_product_id}"
            log_event(db, "Product draft created successfully", "INFO", path)

        except Exception as exc:
            run.status = "error"
            run.success = False
            run.error_message = str(exc)

            processed.status = "error"
            processed.message = str(exc)
            log_event(db, f"Processing failed: {exc}", "ERROR", path)

        db.commit()
