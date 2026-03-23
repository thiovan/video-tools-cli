# Video Tools CLI - Project Architecture Context

**Version:** 1.6.2  
**Purpose:** This document provides essential structural and historical context for AI developers working on this codebase. It documents why certain architectural decisions were made and highlights non-obvious rules that must be followed to prevent regressions.

---

## 1. Concurrency & Cache Isolation (`WinError 32` Prevention)

This application uses `concurrent.futures.ThreadPoolExecutor` to process multiple video downloads, splits, and joins concurrently based on the user's `MAX_QUEUE` setting.

**The Rule:** Temp files used for FFmpeg concatenation **MUST ALWAYS** use cryptographically unique identifiers (UUIDs), not Process IDs (`os.getpid()`) or static file names.
- **Why?** Since a `ThreadPoolExecutor` shares the same Python Process ID, using `os.getpid()` (e.g., `concat_list_{os.getpid()}.txt`) causes parallel workers to write to the exact same temporary text file simultaneously. This triggers a `[WinError 32]` lock crash during the `join_videos` or `_merge_chunks` phases.
- **Implementation:** Both `core/downloader.py` and `core/ffmpeg_handler.py` use `uuid.uuid4().hex[:8]` to generate isolated, unique `join_list` and `concat_list` filenames. **Never hardcode array caching files.**

## 2. Telegram Link Resolution (TDL Batching)

Telegram video links (e.g., `https://t.me/yijiqwq/38698`) are processed using the internal `tdl.exe` binary.

**The Rule:** Do **not** run `tdl` resolution inside the parallel workers.
- **Why?** Running multiple parallel instances of `tdl.exe` to resolve links simultaneously will cause its internal database to lock, failing the downloads.
- **Implementation:** `main.py` (`process_json_input`) performs a **Sequential Batch Pre-Resolution** step. 
  1. It collects all Telegram links from the JSON queue.
  2. It starts a single server: `tdl dl -u <url1> -u <url2> --serve`.
  3. It scrapes the `localhost` server via `BeautifulSoup` to map the direct stream links (`127.0.0.1:xxx/...`) back to the original dictionary items.
  4. The `ThreadPoolExecutor` then safely uses these direct localhost links. 

## 3. Split & Join Naming Convention

When a user executes the `Split & Join Video` flow via CLI or JSON:
- **The Rule:** The final output file must always be suffixed with **`_join.mp4`** (e.g., `my_video_join.mp4`). Segment suffixes like `_1.mp4` or `_2.mp4` must never be left in the final output directory.
- **Implementation Details:** 
  - If a video evaluates to > 1 segment, FFmpeg merges them and names the result `_join.mp4`.
  - If the JSON instructs the system to split a video into exactly **1 segment**, the system skips the FFmpeg `join` pipeline but explicitly uses `shutil.move` to manually rename that single `_1.mp4` segment to `_join.mp4`.

## 4. Test Suite Execution (`tests/test_features.py`)

The test suite validates the logic above. 
- **Console Encoding:** Windows `charmap` codecs often crash when rendering complex Unicode characters (like progress bars) in constrained test pipes. The `utils/logger.py` uses fallback ASCII characters (`#`, `-`) in its progress method if it's running via test redirects.
- **Split Testing Note:** `test_features.py` generates a dummy video using `testsrc` with the `ultrafast` preset to save time. This preset generates extremely sparse I-frames. Therefore, `-c copy` slices in `ffmpeg_handler.py` usually fail to copy valid streams from it. `test_split_join` explicitly overrides this by manually encoding (`libx264`) the testing segments to ensure the `join` multiplexer has valid data to piece together.

## 5. Global Cache Management

During complex or multithreaded operations, numerous chunk directories (e.g., `chunks_{UUID}`) and text lists are rapidly created in `CACHE_DIR`.
**The Rule:** Temp folders shouldn't rely on individual function `finally` blocks for garbage collection, as hard crashes can leave orphaned folders behind.
- **Implementation:** `main.py` explicitly captures the Python terminal lifecycle via a `try... finally` block encapsulating `cli.run()`. When the program finishes or is interrupted, `shutil.rmtree(CACHE_DIR, ignore_errors=True)` wipes the absolute cache folder cleanly, guaranteeing zero disk footprint between runs.

## 6. HLS Stream Web Extraction (`.m3u8`)

When extracting segment chunks from HLS playlists, CDNs often disguise `.ts` chunks with non-standard file extensions (like `.jpeg` or `.png`).
**The Rule:** FFmpeg defaults to high security and rejects unrecognized video extensions in remote playlists unless explicitly overridden.
- **Implementation:** All HTTP/HTTPS URL inputs processed by `downloader.py` and `ffmpeg_handler.py` are dynamically prefixed with the `["-allowed_extensions", "ALL"]` flag immediately before the `-i` parameter. This guarantees the CLI continues successfully downloading disguised web fragments without throwing `consider updating hls.c` compiler errors.

---
*Maintainers updating this codebase should read and update this context file whenever core mechanics affecting state, threading, or outputs are modified.*
