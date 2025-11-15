import os
import sys
import time
import json
import signal
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from bisnis_crawler.spiders.bisnis_spider import BisnisSpider

# configuration
LAST_RUN_FILE = Path("data/last_run.txt")
OUT_DIR = Path("data/outputs")
LOCK_FILE = Path("data/standard.lock")
LATEST_SYMLINK = OUT_DIR / "latest.jsonl"

DEFAULT_INTERVAL = int(os.environ.get("STANDARD_INTERVAL", "900"))  # seconds
RETRY_ON_ERROR = 1  # how many retries for a failed crawl
DEDUPE_OUTPUT = True  # produce a .dedup.jsonl version

# graceful shutdown flag
_should_stop = False


def sigterm_handler(signum, frame):
    global _should_stop
    print(f"Received signal {signum}, will stop after current run.")
    _should_stop = True


signal.signal(signal.SIGINT, sigterm_handler)
signal.signal(signal.SIGTERM, sigterm_handler)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)


def read_last_run() -> str:
    if LAST_RUN_FILE.exists():
        txt = LAST_RUN_FILE.read_text(encoding="utf-8").strip()
        # validate ISO-like
        try:
            # attempt parse
            _ = datetime.fromisoformat(txt)
            return txt
        except Exception:
            print("last_run.txt invalid, ignoring and using default (now-24h).")
    # default: 24 hours before now (UTC)
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def write_last_run(ts_iso: str):
    tmp = LAST_RUN_FILE.with_suffix(".tmp")
    tmp.write_text(ts_iso, encoding="utf-8")
    tmp.replace(LAST_RUN_FILE)


def make_outfile_name(ts_iso: str) -> Path:
    safe_ts = ts_iso.replace(":", "-")
    return OUT_DIR / f"bisnis_standard_{safe_ts}.jsonl"


def acquire_lock() -> bool:
    try:
        # create the lock file exclusively
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def run_crawl(start_iso: str, end_iso: str, outfile: Path, settings_extra: Optional[dict] = None) -> None:
    settings = get_project_settings()
    feeds = {
        str(outfile): {"format": "jsonlines", "encoding": "utf-8", "overwrite": True}
    }
    if settings_extra:
        feeds.update(settings_extra.get("FEEDS", {}))
    settings.set("FEEDS", feeds)
    process = CrawlerProcess(settings)
    process.crawl(BisnisSpider, start_date=start_iso, end_date=end_iso)
    process.start()  # blocking; will run until finished


def dedupe_jsonl(infile: Path, outfile: Path, key: str = "link") -> int:
    seen = set()
    written = 0
    with infile.open("r", encoding="utf-8") as inf, \
            tempfile.NamedTemporaryFile("w", dir=str(outfile.parent), delete=False, encoding="utf-8") as tmpf:
        tmpname = Path(tmpf.name)
        for line in inf:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # skip invalid lines
                continue
            k = obj.get(key)
            if not k:
                # if no key, still write (but try to avoid duplicates by full-line)
                k = line
            if k in seen:
                continue
            seen.add(k)
            tmpf.write(json.dumps(obj, ensure_ascii=False) + "\n")
            written += 1
    tmpname.replace(outfile)
    return written


def atomic_move(src: Path, dest: Path):
    dest_tmp = dest.with_suffix(".tmp")
    shutil.move(str(src), str(dest_tmp))
    dest_tmp.replace(dest)
    try:
        # update symlink to latest
        if LATEST_SYMLINK.exists() or LATEST_SYMLINK.is_symlink():
            LATEST_SYMLINK.unlink()
        LATEST_SYMLINK.symlink_to(dest.name)
    except Exception:
        # ignore symlink errors on Windows or filesystems without symlink support
        pass


def main(interval: int):
    ensure_dirs()
    print("Standard crawler starting. Interval:", interval, "seconds")
    while not _should_stop:
        if not acquire_lock():
            print("Another instance seems to be running (lock present). Waiting and retrying in 10s.")
            time.sleep(10)
            continue
        try:
            last = read_last_run()
            now = now_utc_iso()
            outfile = make_outfile_name(now)
            print(f"Running crawler: {last} -> {now} -> {outfile}")
            success = False
            attempt = 0
            while attempt <= RETRY_ON_ERROR and not success:
                attempt += 1
                try:
                    run_crawl(last, now, outfile)
                    success = True
                except Exception as e:
                    print(f"Crawl attempt {attempt} failed:", e)
                    if attempt <= RETRY_ON_ERROR:
                        wait = 5 + attempt * 5
                        print(f"Retrying in {wait}s ...")
                        time.sleep(wait)
            if success:
                # optional dedupe
                if DEDUPE_OUTPUT:
                    dedup_path = outfile.with_suffix(".dedup.jsonl")
                    print("Deduping output ->", dedup_path)
                    try:
                        written = dedupe_jsonl(outfile, dedup_path)
                        # replace original with dedup
                        dedup_path.replace(outfile)
                        print(f"Dedup complete. Unique written: {written}")
                    except Exception as e:
                        print("Dedup failed:", e)
                # atomic move / symlink update (outfile already in OUT_DIR, but ensure safe)
                # here we just ensure file is visible and update last_run
                write_last_run(now)
                print("Run complete, output:", outfile)
                try:
                    # try to update a 'latest' symlink or copy on systems without symlinks
                    if LATEST_SYMLINK.is_symlink() or not LATEST_SYMLINK.exists():
                        if LATEST_SYMLINK.exists():
                            LATEST_SYMLINK.unlink()
                        LATEST_SYMLINK.symlink_to(outfile.name)
                except Exception:
                    # fallback copy for environments without symlink permission (Windows)
                    try:
                        shutil.copy2(outfile, OUT_DIR / "bisnis_standard_latest.jsonl")
                    except Exception:
                        pass
            else:
                print("All attempts failed for this run.")
        finally:
            release_lock()

        # sleep until next iteration unless stopping
        if _should_stop:
            print("Stopping as requested.")
            break
        print("Sleeping for", interval, "seconds ... (press Ctrl-C to stop)")
        slept = 0
        while slept < interval and not _should_stop:
            sleep_chunk = min(5, interval - slept)
            time.sleep(sleep_chunk)
            slept += sleep_chunk

    print("Standard crawler exited.")


if __name__ == "__main__":
    try:
        interval_arg = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INTERVAL
    except Exception:
        interval_arg = DEFAULT_INTERVAL
    main(interval_arg)
