"""Portable USB AI watcher for Windows.

Runs directly with Windows Embeddable Python from a USB drive.
Monitors the directory containing this script for new `.txt` files,
queries Gemini (primary) with automatic fallback to Fosta (OpenAI Responses API),
and writes the response to `<filename>_answer.txt`.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from google import genai
from openai import OpenAI
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

GEMINI_MODEL = "gemini-4-hydrogen"
FOSTA_MODEL = "gpt-6.2-sol"
DEFAULT_FOSTA_BASE_URL = "https://codex.fosta.app/v1"

DEBOUNCE_SECONDS = 3.0
WRITE_SETTLE_SECONDS = 0.6
REQUEST_TIMEOUT_SECONDS = 60.0

IGNORED_FILENAMES = {"config.json", "requirements.txt"}

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "fosta_api_key": "",
    "fosta_base_url": DEFAULT_FOSTA_BASE_URL,
}


def configure_console_encoding() -> None:
    """Ensure UTF-8 console output on Windows so Vietnamese logs render cleanly."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def log(level: str, message: str) -> None:
    """Print a timestamped log message to the console."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)


def get_base_dir() -> Path:
    """Return the root directory containing usb_ai.py."""
    return Path(os.path.dirname(os.path.abspath(__file__)))


def load_or_create_config(base_dir: Path) -> dict[str, str]:
    """Load config.json from base_dir, or create a template and exit."""
    config_path = base_dir / "config.json"

    if not config_path.exists():
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log("WARN", f"Chưa tìm thấy file cấu hình. Đã tạo file mẫu tại: {config_path}")
        log("INFO", "Vui lòng điền API key vào config.json rồi chạy lại chương trình.")
        sys.exit(1)

    try:
        raw_data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log("ERROR", f"Không thể đọc config.json ({config_path}): {exc}")
        sys.exit(1)

    if not isinstance(raw_data, dict):
        log("ERROR", "config.json không đúng định dạng JSON object.")
        sys.exit(1)

    config = {
        "gemini_api_key": str(raw_data.get("gemini_api_key", "")).strip(),
        "fosta_api_key": str(raw_data.get("fosta_api_key", "")).strip(),
        "fosta_base_url": str(
            raw_data.get("fosta_base_url") or DEFAULT_FOSTA_BASE_URL
        ).strip(),
    }

    if not config["gemini_api_key"] and not config["fosta_api_key"]:
        log(
            "ERROR",
            "Cả gemini_api_key và fosta_api_key đều đang trống trong config.json.",
        )
        sys.exit(1)

    return config


def call_gemini(prompt: str, api_key: str) -> str:
    """Query Google Gemini using google-genai SDK."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise ValueError("Gemini trả về nội dung rỗng.")
    return text


def call_fosta(prompt: str, api_key: str, base_url: str) -> str:
    """Query Fosta via OpenAI Responses API."""
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response = client.responses.create(
        model=FOSTA_MODEL,
        input=prompt,
        reasoning={"effort": "low"},
    )
    text = (getattr(response, "output_text", None) or "").strip()
    if not text:
        raise ValueError("Fosta trả về nội dung rỗng.")
    return text


def ask_ai_with_fallback(
    prompt: str, config: dict[str, str], filename: str
) -> str | None:
    """Call Gemini first, falling back to Fosta on any API/network/timeout error."""
    gemini_key = config["gemini_api_key"]
    fosta_key = config["fosta_api_key"]
    fosta_base_url = config["fosta_base_url"]

    if gemini_key:
        log("INFO", f"[{filename}] Đang gọi Gemini (model: {GEMINI_MODEL})...")
        t0 = time.perf_counter()
        try:
            answer = call_gemini(prompt, gemini_key)
            elapsed = time.perf_counter() - t0
            log(
                "OK",
                f"[{filename}] Gemini ({GEMINI_MODEL}) trả lời thành công ({elapsed:.2f}s).",
            )
            return answer
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            log(
                "WARN",
                f"[{filename}] Gemini ({GEMINI_MODEL}) thất bại sau {elapsed:.2f}s ({exc}). "
                f"Đang chuyển sang Fallback Fosta...",
            )
    else:
        log(
            "WARN",
            f"[{filename}] Chưa có gemini_api_key. Đang chuyển sang Fosta...",
        )

    if not fosta_key:
        log("ERROR", f"[{filename}] Chưa có fosta_api_key để fallback.")
        return None

    log("INFO", f"[{filename}] Đang gọi Fosta (model: {FOSTA_MODEL})...")
    t0 = time.perf_counter()
    try:
        answer = call_fosta(prompt, fosta_key, fosta_base_url)
        elapsed = time.perf_counter() - t0
        log(
            "OK",
            f"[{filename}] Fosta ({FOSTA_MODEL}) trả lời thành công ({elapsed:.2f}s).",
        )
        return answer
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        log(
            "ERROR",
            f"[{filename}] Fosta ({FOSTA_MODEL}) thất bại sau {elapsed:.2f}s: {exc}",
        )
        return None


class TxtFileHandler(FileSystemEventHandler):
    """Watchdog handler for new .txt files in the base directory."""

    def __init__(self, base_dir: Path, config: dict[str, str]) -> None:
        super().__init__()
        self.base_dir = base_dir.resolve()
        self.config = config
        self._lock = threading.Lock()
        self._last_seen: dict[str, float] = {}

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_path(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            dest_path = getattr(event, "dest_path", None)
            if dest_path:
                self._handle_path(dest_path)

    def _should_ignore(self, path: Path) -> bool:
        name_lower = path.name.lower()
        if name_lower in IGNORED_FILENAMES:
            return True
        if path.suffix.lower() != ".txt":
            return True
        if name_lower.endswith("_answer.txt"):
            return True
        if path.resolve().parent != self.base_dir:
            return True
        return False

    def _is_debounced(self, path: Path) -> bool:
        key = os.path.normcase(str(path.resolve()))
        now = time.monotonic()
        with self._lock:
            last_time = self._last_seen.get(key)
            if last_time is not None and (now - last_time) < DEBOUNCE_SECONDS:
                return True
            self._last_seen[key] = now
            if len(self._last_seen) > 500:
                cutoff = now - DEBOUNCE_SECONDS
                self._last_seen = {
                    k: v for k, v in self._last_seen.items() if v >= cutoff
                }
        return False

    def _handle_path(self, raw_path: str) -> None:
        path = Path(raw_path)
        if self._should_ignore(path):
            return
        if self._is_debounced(path):
            return

        worker = threading.Thread(
            target=self._process_file,
            args=(path,),
            daemon=True,
        )
        worker.start()

    def _process_file(self, path: Path) -> None:
        started_at = time.perf_counter()
        time.sleep(WRITE_SETTLE_SECONDS)

        if not path.exists() or not path.is_file():
            return

        log("INFO", f"Đang xử lý file: {path.name}")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            log("ERROR", f"[{path.name}] Lỗi đọc file: {exc}")
            return
        except UnicodeDecodeError as exc:
            log("ERROR", f"[{path.name}] File không đúng chuẩn UTF-8: {exc}")
            return

        if not content.strip():
            log("WARN", f"[{path.name}] File rỗng, bỏ qua.")
            return

        answer = ask_ai_with_fallback(content, self.config, path.name)
        if answer is None:
            log("ERROR", f"[{path.name}] Không nhận được phản hồi từ AI.")
            return

        answer_path = path.with_name(f"{path.stem}_answer.txt")
        try:
            answer_path.write_text(answer, encoding="utf-8")
            total_elapsed = time.perf_counter() - started_at
            log(
                "OK",
                f"[{path.name}] Đã lưu kết quả tại: {answer_path.name} "
                f"(tổng thời gian: {total_elapsed:.2f}s)",
            )
        except OSError as exc:
            log("ERROR", f"[{path.name}] Lỗi ghi file {answer_path.name}: {exc}")


def main() -> None:
    configure_console_encoding()
    base_dir = get_base_dir()
    log("INFO", f"Thư mục làm việc: {base_dir}")

    config = load_or_create_config(base_dir)
    log("INFO", "Đã nạp cấu hình từ config.json.")

    event_handler = TxtFileHandler(base_dir, config)
    observer = Observer()
    observer.schedule(event_handler, str(base_dir), recursive=False)
    observer.start()

    log("INFO", "Đang theo dõi file .txt mới (nhấn Ctrl+C để thoát)...")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        log("INFO", "Đang dừng chương trình...")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
