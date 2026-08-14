# Video Tools CLI - Project Architecture Context

**Version:** 1.7.2  
**Purpose:** This document provides essential structural and historical context for AI developers working on this codebase. It documents why certain architectural decisions were made and highlights non-obvious rules that must be followed to prevent regressions.

---

## 1. Concurrency & Cache Isolation (`WinError 32` Prevention)

This application uses `concurrent.futures.ThreadPoolExecutor` to process multiple video downloads, splits, and joins concurrently based on the user's `MAX_QUEUE` setting.

- **The Rule:** Temp files used for FFmpeg concatenation **MUST ALWAYS** use cryptographically unique identifiers (UUIDs), not Process IDs (`os.getpid()`) or static file names.
- **Why?** Since a `ThreadPoolExecutor` shares the same Python Process ID, using `os.getpid()` (e.g., `concat_list_{os.getpid()}.txt`) causes parallel workers to write to the exact same temporary text file simultaneously. This triggers a `[WinError 32]` lock crash during the `join_videos` or `_merge_chunks` phases.
- **Implementation:** Both `core/downloader.py` and `core/ffmpeg_handler.py` use `uuid.uuid4().hex[:8]` to generate isolated, unique `join_list` and `concat_list` filenames. **Never hardcode array caching files.**

## 2. Telegram Link Resolution (TDL Batching)

Telegram video links (e.g., `https://t.me/example/12345`) are processed using the internal `tdl.exe` binary.

- **The Rule:** Do **not** run `tdl` resolution inside the parallel workers.
- **Why?** Running multiple parallel instances of `tdl.exe` to resolve links simultaneously will cause its internal database to lock, failing the downloads.
- **Implementation:** `main.py` (`process_json_input`) performs a **Sequential Batch Pre-Resolution** step:
  1. Collects all Telegram links from the JSON queue.
  2. Starts a single server: `tdl dl -u <url1> -u <url2> --serve`.
  3. Scrapes the `localhost` server via `BeautifulSoup` to map the direct stream links (`127.0.0.1:xxx/...`) back to the original dictionary items.
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

- **The Rule:** Temp folders shouldn't rely on individual function `finally` blocks for garbage collection, as hard crashes can leave orphaned folders behind.
- **Implementation:** `main.py` explicitly captures the Python terminal lifecycle via a `try... finally` block encapsulating `cli.run()`. When the program finishes or is interrupted, `shutil.rmtree(CACHE_DIR, ignore_errors=True)` wipes the absolute cache folder cleanly, guaranteeing zero disk footprint between runs.

## 6. HLS Stream Web Extraction (`.m3u8`)

When extracting segment chunks from HLS playlists, CDNs often disguise `.ts` chunks with non-standard file extensions (like `.jpeg` or `.png`), or lack extensions entirely (like Google Drive `...=d` IDs).

- **The Rule:** FFmpeg defaults to high security and rejects unrecognized video extensions in remote playlists unless explicitly overridden.
- **Implementation:** All HTTP/HTTPS URL inputs processed by `downloader.py` and `ffmpeg_handler.py` are dynamically prefixed with the `["-allowed_extensions", "ALL", "-allowed_segment_extensions", "ALL", "-extension_picky", "0"]` flags immediately before the `-i` parameter, **only if `.m3u8` is present in the String**. This guarantees the CLI successfully downloads disguised web fragments without breaking standard TDL Localhost stream inputs with `Option not found` failures.

## 7. Bug Regression Testing

When a severe logical framework error is exposed (such as the WinError 32 File Lock, Cache Orphans, or HLS Parameter Crashing), an automated regression test **must** be added to `test_features.py`.

- **Subprocess Mocking (`test_hls_extensions`):** For functions reliant on hard internet requests (like downloading an external `.m3u8`), we intercept `core.downloader.subprocess.run = mock_run` instead to analyze exactly what parameters Python is passing to FFmpeg without wasting CI runner bandwidth.
- **Garbage Simulations (`test_cache_cleanup`):** Simulating hardware teardowns is handled by manually injecting dummy sub-folders, then manually firing `shutil.rmtree(CACHE_DIR)` to recreate the state `main.py` utilizes upon `sys.exit`.
- **Parallel Chunk Integrity (`.ts` wrapper):** Parallel chunks must **never** be downloaded directly as `.mp4`. Slicing HTTP `.mp4` instances over `-c copy` routinely corrupts `moov` sequences. Hence, `downloader.py` relies on `chunk.ts` proxies which merge via `concat` seamlessly back to `.mp4` container outputs.

## 8. Secure Data Headers Parsing

To bypass robust CDNs parsing explicit User Agents or requiring secure sessions, FFmpeg parameters `-referer`, `-user_agent`, and `-headers` have been thoroughly piped.

- **The Flow:** `main.py::_process_json_item` natively checks for optional `referer`, `user_agent`, and `headers` tags, and injects them down all the way through the sequence of `Downloader` ThreadPoolWorkers to `_download_chunk()`, passing cleanly to subprocess logic.

---

> **Note to Maintainers:** Updating this codebase? Please read and update this context file whenever core mechanics affecting state, threading, or outputs are modified. Updates should include a markdown section noting the changes.

## 9. TDL Multi-Session Batching (Added 2026-06-28)

To avoid Telegram download speed limits during batch processing, the CLI now supports splitting resolution requests across multiple concurrent TDL sessions.

- **The Flow:** Instead of processing all Telegram links through a single TDL server, `main.py::_process_json_input` reads `TDL_SESSIONS` from `.env`. It instantiates multiple `TDLHandler` processes dynamically on free open ports via `socket`. 
- **Rule Update (Round-Robin):** Never use sequential chunking (e.g. `chunks[0:4]`) to distribute URLs among sessions. Because `ThreadPoolExecutor` processes the queue sequentially, chunking causes sequential workers to bombard a single session, triggering Telegram DC rate limits. Always use **Round-Robin** (`url[i % len(sessions)]`) to distribute load evenly across workers.
- **Rule Update (Connection Drops):** FFmpeg HTTP streams from local TDL proxies drop frequently. Always include `-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5` flags when pulling chunks from TDL to survive connection resets.

## 10. HLS Disguised Segment Extension Fix (Added 2026-08-14)

Fixed HLS chunk downloading failure for disguised segment extensions (such as `.jpeg`, `.png` used by CDNs like `surrit.com`).

- **Summary of Changes:** Updated HLS parameter injection in `core/downloader.py` and `core/ffmpeg_handler.py` to pass `["-allowed_extensions", "ALL", "-allowed_segment_extensions", "ALL", "-extension_picky", "0"]` instead of hardcoded extension list missing `-allowed_segment_extensions`. Also fixed `-reconnect` flags in `_download_chunk()` to only apply to remote HTTP/HTTPS requests.
- **Architecture Updates:** Ensured FFmpeg's HLS demuxer accepts all internal segment file extensions (`-allowed_segment_extensions ALL`) when processing `.m3u8` playlists.
- **Strict Local Bin Resolution:** `core/config.py::get_binary_path` now strictly enforces using `bin/` executables (`ffmpeg`, `ffprobe`, `tdl`) and raises `FileNotFoundError` if missing, completely disabling fallback to system PATH binaries to prevent version mismatch bugs.
- **Open Issues / Next Steps:** All HLS tests passing in `test_features.py`.


