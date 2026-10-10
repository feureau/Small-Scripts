"""
SCRIPT: iaupload.py
PURPOSE: Internet Archive (archive.org) Smart Uploader & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-08-22
VERSION: 6.60 (Comprehensive Reliability & Integrity Fix)

================================================================================
DOCUMENTATION & UPDATE POLICY
================================================================================
1. STRICT UPDATE RULE:
   Any future modifications to this script MUST be documented in the "CHANGE LOG".

2. RECURSIVE NOTICE REQUIREMENT:
   This documentation block must be included in every version of the script.

================================================================================
ARCHITECTURE & DESIGN RATIONALE
================================================================================
1. ARGUMENT PARSING (argparse)
   - REASON: To support standard flags like -h and custom configurations without
     fragile manual list index checking of sys.argv.
   - LOGIC: We use 'argparse' to handle positional arguments (folder, id) optionally,
     while adding flagged arguments for settings (threads).

2. CUSTOM THREADING & RATE LIMITING
   - REASON: Different users have different bandwidths, while IA enforces per-account
     and per-bucket rate limits.
   - LOGIC: Uploads use bounded worker threads with a global rate-limiter and
     in-flight request slot (_inflight_slot) to prevent 503 SlowDown throttling.

3. CORE LOGIC & RESILIENT S3 / MULTIPART
   - Resumable SigV2 multipart uploads with exact chunk reconciliation.
   - Graceful Shutdown (two-stage Ctrl+C preserving resume state).
   - Content and path verification before upload.
   - Visual Dashboard (tqdm) with true progress tracking.

================================================================================
CHANGE LOG
================================================================================
[2026-10-10] VERSION 6.60 UPDATE
   - FIXED: Multipart resume chunk boundary desynchronization. If concurrency
            or chunk arguments changed between runs, auto-chunking computed
            different boundaries while keeping parts from server ListParts,
            causing silent file corruption on reassembly. Resumed uploads
            now validate mtime and adopt the exact chunk_bytes / n_parts from
            the saved state.
   - FIXED: Orphan deletion (-o / --orphan-deletion) called non-existent
            `item.delete_file()`. Now properly calls `item.get_file(name).delete()`
            routed through `_inflight_slot()` with rate limiting.
   - FIXED: Path truncation collision with orphan deletion. Files exceeding
            IA's 230-byte path limit were indexed under their original name
            but uploaded under truncated names; on subsequent runs they were
            falsely flagged as new files and their remote counterparts were
            deleted as orphans. Local indexing now indexes by safe_rel_path.
   - FIXED: Small-file bundling & cleanup false positives. Previously, any file
            matching a bundle group's extensions in a folder with texts.zip /
            images.zip was assumed covered and omitted from upload, then deleted
            by --delete-originals-after-upload even if not actually inside the
            archive. Now checks actual zip contents before marking covered or
            planning deletion.
   - FIXED: S3 503 SlowDown retries sent empty bodies. Streaming file readers
            were not rewound to offset 0 before retrying the request in
            IAS3Client.request(). Added seek() support to SliceReader and
            rewind before retry.
   - FIXED: First file upload on new item creation failed when routed through
            S3 / multipart workers due to 404 preflight and missing metadata
            headers. New item creation now always routes the first file through
            upload_worker with full metadata.
   - FIXED: Metadata updates via -m for existing items were discarded if files
            were queued for upload. Now applies immediately via modify_metadata().
   - FIXED: Ctrl+C prematurely aborted multipart uploads and deleted saved
            resume state, discarding tens of gigabytes of uploaded parts. State
            is now preserved on interrupt so re-running resumes seamlessly.
   - FIXED: Metadata questionnaire lost defaults (language, date, coverage,
            temporal) when prefills existed but lacked those specific keys.
   - FIXED: 7z watchdog in do_split() killed splits longer than 1 hour. Timer
            now resets on streaming output activity.
   - FIXED: Global rate limiter (--max-rpm) race condition in _inflight_slot().
   - FIXED: Resumed multipart progress bar started at 0% instead of accounting
            for already-confirmed bytes.
   - CLEANUP: Removed unused boto3 imports and dead constants.

[2026-10-10] VERSION 6.59 UPDATE
   - FIXED: Multipart resume double-counted already-uploaded parts.
            When a run resumed from state (e.g. "server has 2/32
            parts"), the 2 resumed parts were seeded into `parts` AND
            re-returned by their executor task, so `parts` ended up
            with 34 entries for a 32-part file. The final sanity check
            `len(parts) != n_parts` then aborted with the misleading
            message "only 34/32 parts uploaded", and the file was
            never completed. Parts are now tracked in a dict keyed
            by part number, so resumed and freshly-uploaded parts
            merge idempotently. Re-running after the crash now
            completes the upload instead of growing the count.

[2026-10-09] VERSION 6.58 UPDATE
   - FIXED: Split parts and sidecar meta were keyed on path.stem, so
            foo.mp4 and foo.mkv in the same directory collided.
            The second do_split() deleted the first file's volumes,
            and both originals looked "covered" by whichever .001
            survived. Parts/meta are now keyed on the FULL filename:
              foo.mp4.zip.001, foo.mp4.zip.meta.json
   - FIXED: has_valid_split() only checked that at least one part
            existed. A split interrupted after .001 (but before .002)
            was treated as complete, so missing volumes were never
            regenerated and IA got a truncated set. Part numbers must
            now be contiguous 1..N and match the part_count recorded
            in the meta sidecar.
   - FIXED: Split parts were not bounded by IA's 230-byte path-
            component limit. A long original filename produced
            "<long>.zip.001" which IA rejected with HTTP 400.
            split_stem_for() now truncates the stem with a short
            MD5 hash suffix so the final component always fits.
   - FIXED: do_split() captured all of 7z's output, so a multi-hour
            split showed nothing. 7z output is now streamed live to
            the terminal.
   - ADDED: meta sidecar now writes "version": 2 and "split_stem"
            so future readers can reconstruct the naming scheme.
   - MODIFIED: --no-split now prints a deprecation notice; splitting
            remains opt-in via --split. Default is still OFF.
   - COMPAT: Legacy .zip.001 sets (v6.57 and earlier) are still
            detected via the meta's "original" field, so upgrading
            does not orphan existing volumes or force a re-split.

[2026-10-09] VERSION 6.57 UPDATE
   - MODIFIED: internetarchive.upload() is now the DEFAULT upload path
               for small/medium files. Files under --multipart-threshold
               go through upload_worker() instead of the built-in S3
               single PUT.
   - ADDED: --use-s3-put flag to opt back into the built-in SigV2 S3
            single-PUT path for small/medium files.
   - MODIFIED: --use-ia-library kept for CLI compatibility; it is now
               a no-op because its behavior is the default. The two
               flags are mutually exclusive.
   - MODIFIED: Banner text "Small-file path: internetarchive library"
               no longer implies a flag was passed.
   - FIXED: --no-multipart --use-s3-put now correctly routes through
            s3_upload_worker() instead of upload_worker(). Previously
            --no-multipart unconditionally forced the IA library path.

[2026-10-09] VERSION 6.56 UPDATE
   - FIXED: HTTP 411 Length Required on every single-PUT upload.
            requests was falling back to chunked encoding for
            file-like bodies; IA's Apache front-end rejects those.
            Content-Length is now set explicitly in IAS3Client._do().
   - FIXED: HTTP 403 RequestTimeTooSkewed. _sign_v2() ran before
            _inflight_slot(), so x-amz-date was stale after long
            cooldowns. Signing now happens inside the slot.
   - FIXED: 503 SlowDown with accesskey_tasks_queued (per-account
            quota) is now treated as fatal: the run aborts with a
            clear message instead of retrying for 45 minutes.
            bucket_tasks_queued still uses the shared cooldown.
   - ADDED: Startup HEAD probe. Aborts before scanning if the
            account is already over quota.
   - ADDED: Distinct account-quota banner in the final report.
   - MODIFIED: Default parallelism raised: THREADS 4 -> 8,
               MULTIPART_CONCURRENCY 2 -> 4, MAX_INFLIGHT 4 -> 8.

[2026-10-09] VERSION 6.55 UPDATE
   - MODIFIED: DEFAULT_MULTIPART_CONCURRENCY 2 -> 4
   - MODIFIED: DEFAULT_MAX_INFLIGHT 4 -> 8
   - MODIFIED: DEFAULT_THREADS was already 8; left as-is.
               Raise all three together; -t alone is capped by
               --max-inflight, and multipart chunks are capped by
               --multipart-concurrency.

[2026-10-09] VERSION 6.54 UPDATE
   - ADDED: --max-rpm N. Global cap on HTTP requests per minute to
            archive.org, shared across all threads. Default 30.
            The previous v6.53 cooldown only pauses threads after a
            503 is seen; this rate limiter keeps us under IA's queue
            depth in the first place.
   - ADDED: Live HTTP counters. [LIVENESS] lines now report in-flight
            request count and rolling requests-per-minute.
   - ADDED: _reset_rate_limiter(), _current_rate_stats().
   - MODIFIED: _inflight_slot() now gates on the rate limiter in
               addition to the shared cooldown and semaphore.

[2026-10-09] VERSION 6.53 UPDATE
   - FIXED: Parallel multipart uploads triggered 503 SlowDown
            (bucket_tasks_queued exceeds bucket_limit). The
            --max-inflight cap limits concurrency, not request RATE,
            so several concurrent multipart uploads could still
            flood IA's per-bucket task queue.
   - ADDED: Shared global cooldown. When any thread sees a 503
            SlowDown, ALL threads pause together until the queue
            drains. Cooldown escalates 30s -> 300s.
   - FIXED: datetime.utcnow() deprecation warning (use timezone-aware).

[2026-10-09] VERSION 6.52 UPDATE
   - MODIFIED: auto_chunk_mb() now aims for ~8 parts per thread
               instead of ~40. Produces coarser chunks: a 5 GB file
               at concurrency 2 gets 512 MB chunks (10 parts) instead
               of 64 MB chunks (80 parts). Fewer round trips, less
               pressure on IA's bucket queue, same total runtime.
   - MODIFIED: --chunk-size help text updated.

[2026-10-09] VERSION 6.51 UPDATE
   - MODIFIED: File splitting is now OPT-IN. Default is OFF; pass
               --split to enable. Previously splitting was on by
               default with --no-split to disable.
   - MODIFIED: --no-split kept as a hidden no-op for compatibility.
   - MODIFIED: Banner shows 'Splitting: OFF (use --split to enable)'
               when disabled.
   (Includes v6.50: S3 single PUT by default, --use-ia-library,
    s3_upload_worker, 7z auto-detect, Ctrl+C EOFError fix.)

[2026-10-09] VERSION 6.50 UPDATE
   - ADDED: s3_upload_worker() — single PUT via SigV2 IAS3Client,
            streaming from disk. Retries on transient errors.
            Metadata attached via modify_metadata() after success.
   - MODIFIED: S3 single PUT is now the DEFAULT for files under the
            multipart threshold. internetarchive.upload() is available
            via --use-ia-library.
   - ADDED: --use-ia-library flag.
   - MODIFIED: Effective multipart threshold clamped to S3's ~5 GB
            single-PUT limit when S3 path is active.
   - ADDED: Banner shows the small-file path (S3 PUT / IA library).
   - FIXED: _find_7z() checks standard Windows install locations
            (Program Files / Program Files x86) when 7z is not on PATH.
   - FIXED: get_input() catches EOFError too, so Ctrl+C during a
            metadata prompt exits cleanly instead of raising.

[2026-10-09] VERSION 6.48 UPDATE
   - Consolidated release: bundles features from v6.45-v6.47.
   - MODIFIED: Multipart default threshold 128 MB -> 15 GB.
   - ADDED: Built-in small-file bundling (texts.zip / images.zip).
   - ADDED: Built-in large-file splitting via 7z (video.zip.001...).
   - ADDED: Scan skips files covered by an existing bundle or split.
   - ADDED: --delete-originals-after-upload with IA verification.
   - ADDED: New flags --no-zip, --no-split, --split-size, --bundle-min,
            --delete-originals-after-upload, --verify-timeout.

[2026-10-09] VERSION 6.44 UPDATE
   - FIXED: Ctrl+C could not close the script while worker threads
            were stuck inside blocking socket calls. Added two-stage
            Ctrl+C: first press = graceful, second press within 3s =
            os._exit(1) bypassing thread joins.
   - MODIFIED: (if v6.43 semaphore present) _inflight_slot() now
            polls shutdown_event with 1s timeout instead of blocking
            on sem.acquire() indefinitely.

[2026-10-09] VERSION 6.43 UPDATE
   - ADDED: Global in-flight request semaphore. All HTTP requests to
            archive.org pass through a single shared cap, preventing
            stacked concurrency (-t N * --multipart-concurrency M)
            from tripping IA's per-account rate limit
            (accesskey_tasks_queued).
   - ADDED: --max-inflight N flag (default 4).
   - MODIFIED: DEFAULT_THREADS 6 -> 4.
   - MODIFIED: DEFAULT_MULTIPART_CONCURRENCY 4 -> 2.
   - MODIFIED: Banner shows the in-flight cap.

[2026-10-09] VERSION 6.41 UPDATE
   - FIXED: Scan and orphan-detection now skip *.iaupload.json and
            *.iaupload.json.tmp resume-state files. Previously these
            were queued as new uploads on the next run, hit IA's
            per-account rate limit, and stalled all real uploads.
   - FIXED: IAS3Client.request() now recognizes accesskey_tasks_queued
            and 'rationed' as rate-limit indicators (was only matching
            bucket_tasks_queued and 'reduce your request rate').
   - FIXED: Multipart uploads that complete successfully (HTTP 200 on
            CompleteMultipartUpload) are now recorded as success
            immediately. Removed the 300s server-side visibility poll
            which was falsely failing genuinely-uploaded files and
            causing full re-uploads on the next run.
   - MODIFIED: _MULTIPART_ENABLED is no longer gated on boto3 presence
            (multipart has used raw requests since v6.31).
   - MODIFIED: Banner string for boto3-not-installed removed.

[2026-10-09] VERSION 6.40 UPDATE
   - ADDED: Automatic chunk-size selection based on file size and
            concurrency (~40 parts per thread, clamped 8 MB - 2 GB,
            rounded up to a power-of-two MB). --chunk-size N overrides.
   - ADDED: SliceReader streams each part from disk. Peak memory per
            thread drops from chunk_size (~1 GB) to ~8 KB, so large
            chunks are safe on any machine.
   - MODIFIED: --chunk-size default is now None (auto). Banner shows
            'chunk auto' when omitted.

[2026-10-09] VERSION 6.39 UPDATE
   - ADDED: Resumable multipart uploads. UploadId and confirmed part
            ETags are persisted to <local_file>.iaupload.json. On the
            next run, ListParts reconciles with the server and only
            missing parts are re-uploaded. Full 88GB uploads no longer
            restart from zero after a network drop.
   - ADDED: IAS3Client.list_parts() with pagination support.
   - ADDED: --no-resume (ignore state file) and --reset-state (delete
            state file and exit) flags.
   - ADDED: State file is written atomically and throttled.
   - ADDED: If local file size or key changed, state is discarded.

[2026-10-08] VERSION 6.38 UPDATE
   - FIXED: IA 503 SlowDown (bucket_tasks_queued exceeds bucket_limit)
            was not retried by v6.37's method-level wrapper. Retry is
            now built into IAS3Client.request() itself, so every call
            site (preflight, initiate, part, complete) is covered.
   - MODIFIED: request() retries 503 SlowDown with exponential backoff
            30s -> 300s (up to 12 attempts, ~45 min worst case).
            Sleep is interruptible so Ctrl+C stays responsive.
   - REMOVED: IAS3Client._request_with_retry (redundant).

[2026-10-08] VERSION 6.37 UPDATE
   - FIXED: InitiateMultipartUpload returned 503 SlowDown when IA's
            bucket_tasks_queued limit was exceeded (typically from
            orphaned parts of a previous aborted multipart upload).
            Initiate / complete / preflight now retry with exponential
            backoff (30s -> 300s, up to 12 attempts, ~45 min worst case).
   - ADDED: IAS3Client._request_with_retry() helper for 503 SlowDown
            with interruptible sleep so Ctrl+C stays responsive.
   - ADDED: (from v6.36) Per-part retry with exponential backoff. A
            single stalled part no longer aborts the entire multipart
            upload, discarding all previously uploaded parts.

[2026-10-08] VERSION 6.35 UPDATE
   - FIXED: IAS3Client signed the raw path but requests sent the path
            percent-encoded on the wire. IA's SigV2 verifier rebuilds
            the StringToSign from the encoded wire request, so keys
            containing spaces/brackets failed with 403 SignatureDoes
            NotMatch (simple keys like `_s3v2diag.bin` happened to work).
            The path is now percent-encoded (preserving '/') before
            signing and before URL construction.
   - IMPROVED: initiate/upload_part/complete errors now print the exact
            StringToSign we sent and the full IA error body.

[2026-10-08] VERSION 6.34 UPDATE
   - FIXED: IAS3Client cached the 307 storage-node redirect from the
            preflight HEAD and reused it for the initiate POST. IA's
            redirect body explicitly says to keep using the original
            endpoint for future requests. Writes now always go to the
            master; only GET/HEAD follow the 307 (once, without caching).
   - FIXED: preflight HEAD now treats 307 as success (bucket exists on
            a storage node) instead of caching the node.

[2026-10-08] VERSION 6.33 UPDATE
   - FIXED: IAS3Client._sign_v2 sent both Date and x-amz-date headers,
            but signed with an empty Date line (SigV2 rule: x-amz-date
            supersedes Date). IA's verifier rebuilt the StringToSign with
            the wire Date header and returned 403 SignatureDoesNotMatch.
            The Date header is no longer sent; only x-amz-date is used.

[2026-10-08] VERSION 6.32 UPDATE
   - FIXED: v6.31 accidentally deleted _filter_ia_s3_dns (it lived between
            multipart_upload_worker and handle_dji_lrf, and v6.31 replaced
            that whole span). Function restored; DNS pinning active again.
   - FIXED: IAS3Client doubled the path when following IA's 307 redirect,
            because Location already contains the bucket path. Now only
            scheme://host:port is extracted from Location.

[2026-10-08] VERSION 6.31 UPDATE
   - REWRITTEN: multipart_upload_worker no longer uses boto3/botocore.
                IA's S3 endpoint requires SigV2 signatures (rejects SigV4),
                and botocore's S3 region-redirect handler mishandled IA's
                307 storage-node redirects, causing an infinite loop.
   - ADDED: IAS3Client: minimal SigV2 signer + manual 307 follow with
            per-bucket storage-node caching. Supports initiate/upload_part/
            complete/abort. Parallel part uploads via ThreadPoolExecutor.
   - ADDED: Automatic chunk-size scaling for S3's 10,000-part limit.
   - ADDED: Post-upload server-side verification before recording success.
   - MODIFIED: Progress bar tracks server-confirmed bytes, not local reads.

[2026-10-08] VERSION 6.30 UPDATE
   - FIXED: s3.us.archive.org occasionally resolves to a dead IP that
            blackholes TCP/443. New startup DNS filter probes each IP
            and monkey-patches socket.getaddrinfo to return only the
            reachable ones. Self-heals as IA rotates IPs.
   - FIXED: boto3 client now sets connect_timeout=30 and read_timeout=120
            with retries max_attempts=2, so stuck connects fail in
            seconds instead of hanging for many minutes.
   - ADDED: Preflight list_objects_v2 before each multipart PUT to
            surface unreachable endpoints at startup.
   - FIXED: Ctrl+C could not interrupt blocked network calls on Windows.
            socket.setdefaulttimeout(30) now applies at import time, and
            a SIGINT handler sets shutdown_event immediately.
   - ADDED: botocore debug logging when -v is passed.

[2026-10-08] VERSION 6.27 UPDATE
   - FIXED: TransferConfig was constructed with 'max_request_queue_size',
            which is not a valid parameter; the real name is 'max_io_queue'.
            This caused multipart uploads to fail immediately on v6.25/v6.26.
   - MODIFIED: TransferConfig construction now introspects s3transfer at
            runtime and only passes max_io_queue when the installed version
            actually accepts it. Future parameter renames won't break us.

[2026-10-08] VERSION 6.26 UPDATE
   - FIXED: Main loop discarded future results, so a worker could return
            success/failure without recording either. Every future is now
            read, exceptions captured, and unrecorded failures logged.
   - FIXED: multipart_upload_worker could return in <1s without uploading.
            It now verifies (a) the reader consumed the full file, and
            (b) the file appears on the server with the correct size.
   - ADDED: MULTIPART_VERIFY_TIMEOUT (default 300s) for post-upload
            server-side confirmation.
   - ADDED: _SilentReader tracks bytes_read for sanity checks.
   - ADDED: _progress_callback wrapped so a callback error cannot abort
            the upload.

[2026-10-08] VERSION 6.25 UPDATE
   - FIXED: Multipart progress bar was tracking local disk read speed, not
            network upload speed, because s3transfer's use_threads=True mode
            runs the file reader ahead of the network uploaders.
   - MODIFIED: Progress is now driven by the Callback= parameter of
            s3.upload_fileobj, which fires after each part is confirmed
            uploaded by the server.
   - ADDED: max_request_queue_size capped at max_concurrency*2 to prevent
            s3transfer from buffering many GB of read-ahead data in RAM.

[2026-10-08] VERSION 6.24 UPDATE
   - FIXED: 'S3Transfer' object has no attribute 'upload_fileobj' on
            s3transfer >= 0.19.x. Switched to the stable client-level
            s3.upload_fileobj() API, which is compatible across all boto3
            versions and delegates to whichever transfer backend is current.

[2026-10-08] VERSION 6.23 UPDATE
   - MODIFIED: Multipart upload is now ON BY DEFAULT. Use --no-multipart to
               disable it. --multipart is kept as a no-op for compatibility.
   - MODIFIED: Default multipart threshold lowered 256 MB -> 128 MB.
   - FIXED: New-item first file now honors multipart routing; previously it
            was hard-coded to single-stream upload_worker even for huge files.
   - FIXED: multipart_upload_worker now attaches full metadata via
            item.modify_metadata() after the S3 PUT, so list-valued fields
            (subject, format, relation) are preserved.
   - ADDED: Automatic chunk-size scaling when file/chunk would exceed S3's
            10,000-part limit (up to 5 GB per part).

[2026-10-08] VERSION 6.22 UPDATE
   - ADDED: S3 multipart upload path for large files (--multipart flag).
           Large files are split into parallel chunks and reassembled into a
           single object on Archive.org's servers.
   - ADDED: --chunk-size MB flag (default 64 MB per part).
   - ADDED: --multipart-threshold MB flag (default 256 MB).
   - ADDED: --multipart-concurrency N flag (default 4 parallel parts/file).
   - ADDED: multipart_upload_worker() using boto3 + IA's S3 API.
   - MODIFIED: worker_wrapper now routes files by size.

[2026-08-22] VERSION 6.21 UPDATE
   - FIXED: Added explicit timeout and try/except block to initial `get_item()` call to prevent crashes when Archive.org's metadata API is slow.
   - CLEANUP: Removed leftover unreachable GUI code inside the metadata collection block.

[2026-04-15] VERSION 6.20 UPDATE
   - ADDED: Automatic filename truncation for path components exceeding 230 bytes.
   - ADDED: IA rejects uploads with path components > 230 bytes; script now auto-truncates
           while preserving extension and appending a short hash for uniqueness.
   - ADDED: Warning printed when a filename is truncated during the scan phase.

[2026-04-15] VERSION 6.19 UPDATE
   - ADDED: "Skip to Defaults" shortcut during metadata questionnaire.
   - ADDED: Typing '!!' at any prompt auto-accepts all remaining fields with their defaults.
   - ADDED: Descriptive hint shown at the start of METADATA PREPARATION section.

[2026-04-13] VERSION 6.18 UPDATE
   - REMOVED: Entire Tkinter GUI system and --gui flag.
   - CLEANUP: Codebase is now strictly console-only for minimal weight.

[2026-04-13] VERSION 6.17 UPDATE
   - MODIFIED: Major GUI v2.0 overhaul. (REMOVED in 6.18)

[2026-04-13] VERSION 6.16 UPDATE
   - ADDED: Advanced range detection in folder names (e.g., 1900-1950).
   - MODIFIED: Date field defaults to full YYYY-MM-DD.
   - MODIFIED: Coverage and Temporal fields default to Year or Year Range.

[2026-04-13] VERSION 6.15 UPDATE

[2026-04-13] VERSION 6.14 UPDATE

[2026-04-13] VERSION 6.13 UPDATE

[2026-04-13] VERSION 6.12 UPDATE
   - MODIFIED: GUI disabled by default. Console-only mode is now the default for metadata entry.
   - ADDED: --gui flag to enable the Tkinter GUI for metadata entry.

[2026-04-13] VERSION 6.11 UPDATE
   - ADDED: --no-gui flag to disable GUI and use console-only mode for metadata entry.

[2026-04-13] VERSION 6.10 UPDATE
   - ADDED: Tkinter GUI for metadata entry with dark mode theme.
   - ADDED: All basic and extended metadata fields in GUI.
   - ADDED: Custom fields section with add/remove functionality.
   - ADDED: Reset to Defaults, Clear buttons for each field.
   - ADDED: Proceed to Upload and Cancel buttons.

[2026-04-13] VERSION 6.9 UPDATE
   - ADDED: Support for _meta.xml alongside metadata.xml for metadata file detection.
   - ADDED: Extended metadata field support for XML and JSON: language, date, publisher, rights, contributor, source, coverage, temporal, spatial, citation, type, relation, format, and custom fields.
   - ADDED: Interactive prompts for all additional metadata fields during upload.

[2026-04-11] VERSION 6.8 UPDATE
   - ADDED: Automatic detection and renaming of DJI .LRF files to .MP4 with '_s' suffix.
   - ADDED: --fix-lrf flag for automated LRF renaming without a prompt.

[2026-04-03] VERSION 6.7 UPDATE
   - ADDED: Best-effort display of collections available to the current account during metadata prompt.
   - MODIFIED: Collection prompt now shows account collection options (when retrievable) before input.

[2026-04-03] VERSION 6.6 UPDATE
   - ADDED: Empty (0-byte) local files are skipped during scan and never queued for upload.
   - ADDED: Summary now reports the number of skipped empty files.
   - ADDED: Defensive upload_worker guard to skip zero-byte files if encountered.
   - MODIFIED: Collection metadata is now explicitly prompted, with safer fallback for restricted prefilled collections.
[2026-03-24] VERSION 6.5 UPDATE
   - ADDED: --verbose / -v flag for detailed debug logging during uploads.
   - ADDED: HTTP socket timeout (30s connect, 300s read) to prevent infinite hangs.
   - ADDED: Periodic liveness reporting showing in-flight files during upload.
   - ADDED: Thread lifecycle, slot acquisition, and HTTP timing logs in verbose mode.
   - FIXED: Upload freeze caused by missing HTTP timeout on item.upload() calls.

[2026-03-24] VERSION 6.4 UPDATE
   - ADDED: Fast size comparison check during scan phase to identify incomplete uploads instantly.
   - MODIFIED: Size verification is now checked on all files. MD5 runs afterwards if enabled.

[2026-03-04] VERSION 6.3 UPDATE
   - ADDED: `--md5-verify` flag to enable same-path MD5 comparison during scan.
   - MODIFIED: Default scan now uses path-only matching unless MD5 flag is provided.
   - VERIFIED: `-h` / `--help` CLI help output works with argparse.

[2026-03-03] VERSION 6.2 UPDATE
   - MODIFIED: MD5 is now computed only when the same normalized path exists remotely.
   - REMOVED: Cross-path smart content matching during scan (MOVED/SMART checks).
   - MODIFIED: Orphan detection simplified to pure path-based comparison.

[2026-03-03] VERSION 6.1 UPDATE
   - ADDED: Support for metadata prefills from `metadata.json`.
   - ADDED: Unified metadata prefill loader for XML/JSON.
   - MODIFIED: Prefill source selection now checks XML first, then JSON.

[2026-01-19] VERSION 6.0 UPDATE
   - ADDED: 'argparse' library integration.
   - ADDED: '-t' / '--threads' flag to customize upload concurrency.
   - ADDED: '-h' / '--help' automatic generation.
   - MODIFIED: Replaced manual sys.argv parsing with args object.
   - MODIFIED: Dynamic UI spacing based on variable thread count.

[2026-01-19] VERSION 5.1 UPDATE
   - Fixed 'seek' error in ProgressWrapper.

[2026-01-19] VERSION 5.0 UPDATE
   - Graceful Exit & Reporting.

================================================================================
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# --- v6.29: global socket timeout so blocked connects raise and can be
# interrupted by Ctrl+C on Windows (which otherwise ignores SIGINT during
# a blocking connect()). Must run before boto3/requests load.
import socket as _socket
_socket.setdefaulttimeout(30)

from internetarchive import get_item, get_session, upload

# Import iazip's process_directory for -z/--zip flag integration
try:
    from iazip import process_directory as iazip_process
except ImportError:
    iazip_process = None



# Fix Windows console encoding for special characters
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
        sys.stdin = io.TextIOWrapper(
            sys.stdin.buffer, encoding="utf-8", errors="replace"
        )
    except Exception:
        pass

# --- TRY IMPORTING TQDM ---
try:
    from tqdm import tqdm
except ImportError:
    print("Error: This version requires 'tqdm'.")
    print("Please run: pip install tqdm")
    sys.exit(1)

# --- GLOBALS ---
shutdown_event = threading.Event()
results_lock = threading.Lock()
final_results = {"success": [], "failed": [], "cancelled": []}
VERBOSE = False  # Set by --verbose flag
_MULTIPART_ENABLED = False  # v6.23: on by default; --no-multipart disables
COMMON_LANGUAGES = ["en", "de", "fr", "es", "it", "ja", "zh", "pt", "ru", "ar", "zxx"]
_skip_to_defaults = False  # Set to True when user types '!!' at any metadata prompt
_force_defaults_global = False # Set by --force-defaults to never reset _skip_to_defaults

# --- CONFIGURATION DEFAULTS ---
DEFAULT_THREADS = 12 
MAX_RETRIES = 20
RETRY_BACKOFF_START = 30
MAX_BACKOFF_TIME = 300
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 300

# --- MULTIPART UPLOAD DEFAULTS (v6.23) ---
DEFAULT_MULTIPART_THRESHOLD_MB = 15 * 1024  # v6.48: 15 GB (was 128 MB)
DEFAULT_CHUNK_SIZE_MB = None          # v6.40: None = auto-size
DEFAULT_MULTIPART_CONCURRENCY = 4     # v6.55: raised from 2
PART_MAX_RETRIES = 5                  # v6.36: per-part retry attempts
RATE_LIMIT_MAX_RETRIES = 12           # v6.37: 503 SlowDown attempts
RATE_LIMIT_BACKOFF_START = 30         # v6.37: initial 503 wait (s)
RATE_LIMIT_BACKOFF_MAX = 300          # v6.37: cap 503 wait (s)

# --- v6.48: bundling, splitting, verified cleanup ------------------------

BUNDLE_GROUPS = {
    "texts": {
        ".txt", ".md", ".srt", ".csv", ".json", ".html", ".htm",
        ".xml", ".yaml", ".yml", ".log", ".rtf", ".ini", ".cfg",
    },
    "images": {
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
        ".tiff", ".tif",
    },
}
DEFAULT_BUNDLE_MIN = 3
DEFAULT_SPLIT_SIZE_STR = "4480M"

_BUNDLE_EXCLUDE_NAMES = {"metadata.json", "metadata.xml", "_meta.xml"}


def parse_size_mb(s):
    if s is None:
        return 0
    if isinstance(s, (int, float)):
        return int(s)
    txt = str(s).strip().lower()
    if txt in ("off", "none", "no", "0"):
        return 0
    aliases = {"cd": 700, "dvd": 4480, "dvd5": 4480, "dvd9": 8500,
               "bd": 25600, "bd25": 25600, "bd50": 51200}
    if txt in aliases:
        return aliases[txt]
    m = re.match(r"^\s*([\d.]+)\s*([kmgt]?)\s*b?\s*$", txt)
    if not m:
        raise ValueError(f"Cannot parse size: {s!r}")
    n = float(m.group(1))
    unit = m.group(2) or "m"
    factor = {"k": 1 / 1024, "m": 1, "g": 1024, "t": 1024 * 1024}[unit]
    return int(n * factor)


def _find_7z():
    """Locate 7z on PATH or in standard Windows install locations."""
    for name in ("7z", "7za", "7z.exe", "7za.exe", "7zz", "7zz.exe"):
        p = shutil.which(name)
        if p:
            return p
    if sys.platform == "win32":
        import os as _os
        candidates = []
        for env_var in ("ProgramFiles", "ProgramFiles(x86)",
                        "ProgramW6432", "LOCALAPPDATA"):
            base = _os.environ.get(env_var)
            if not base:
                continue
            candidates.extend([
                _os.path.join(base, "7-Zip", "7z.exe"),
                _os.path.join(base, "7-Zip", "7za.exe"),
                _os.path.join(base, "chocolatey", "bin", "7z.exe"),
                _os.path.join(base, "scoop", "shims", "7z.exe"),
            ])
        candidates.extend([
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ])
        for c in candidates:
            if _os.path.isfile(c):
                return c
    return None


# v6.58: split parts and sidecar meta are keyed on the FULL filename,
# not path.stem. This prevents foo.mp4 / foo.mkv collisions and lets us
# truncate over-long stems while keeping the ".zip.NNN" suffix intact.

_SPLIT_RESERVED_BYTES = 16   # room for ".zip.99999" and a few bytes slack


def split_stem_for(path):
    """
    v6.58: return the stem used for `path`'s split parts and meta.

    The stem is the full filename (including extension), truncated with
    a short MD5 suffix only when necessary to keep
    "<stem>.zip.NNNNN" within IA's 230-byte path-component limit.

    Examples:
        clip.mp4                  -> "clip.mp4"
        <228-byte name>.mp4       -> "<truncated>_<hash>.mp4"
    """
    name = path.name
    encoded = name.encode("utf-8")
    budget = IA_MAX_PATH_COMPONENT_BYTES - _SPLIT_RESERVED_BYTES
    if len(encoded) <= budget:
        return name

    short_hash = hashlib.md5(encoded).hexdigest()[:8]
    suffix = f"_{short_hash}"

    dot_idx = name.rfind(".")
    if dot_idx > 0:
        stem, ext = name[:dot_idx], name[dot_idx:]
    else:
        stem, ext = name, ""

    avail = (
        budget
        - len(suffix.encode("utf-8"))
        - len(ext.encode("utf-8"))
    )
    if avail < 1:
        avail = 1
    trunc = (
        stem.encode("utf-8")[:avail]
        .decode("utf-8", errors="ignore")
        .rstrip()
    )
    return trunc + suffix + ext


def split_meta_path(path):
    return path.parent / f"{split_stem_for(path)}.zip.meta.json"


def _find_split_parts(directory, stem):
    pat = re.compile(rf"^{re.escape(stem)}\.zip\.(\d+)$")
    found = []
    try:
        for p in directory.iterdir():
            if not p.is_file():
                continue
            m = pat.match(p.name)
            if m:
                found.append((int(m.group(1)), p))
    except Exception:
        return []
    return [p for _, p in sorted(found)]


def _split_part_numbers(parts):
    """v6.58: sorted numeric suffixes of a list of part paths."""
    nums = []
    for p in parts:
        m = re.search(r"\.zip\.(\d+)$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def _has_valid_split_with_stem(path, stem):
    """v6.58: validate one candidate stem (new or legacy)."""
    meta_path = path.parent / f"{stem}.zip.meta.json"
    if not meta_path.exists():
        return False

    parts = _find_split_parts(path.parent, stem)
    if not parts:
        return False

    # Part numbers must be contiguous 1..N. This catches an interrupted
    # split that wrote .001 but not .002, which the old code accepted.
    nums = _split_part_numbers(parts)
    if nums != list(range(1, len(nums) + 1)):
        return False

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return False

    # The meta's `original` field is the only unambiguous way to tell
    # foo.mp4's legacy split apart from foo.mkv's. Require a match.
    if meta.get("original") != path.name:
        return False

    try:
        st = path.stat()
        if int(meta.get("original_size", -1)) != st.st_size:
            return False
        if abs(float(meta.get("original_mtime", 0)) - st.st_mtime) > 1.0:
            return False
    except Exception:
        return False

    # v6.58: declared part count must match what's on disk.
    declared = meta.get("part_count")
    if declared is None:
        return False
    try:
        if int(declared) != len(nums):
            return False
    except Exception:
        return False

    return True


def _candidate_split_stems(path):
    """v6.58: try the new full-filename stem first, then the legacy
    path.stem stem for backward compatibility."""
    new_stem = split_stem_for(path)
    yield new_stem
    if path.stem != new_stem:
        yield path.stem


def has_valid_split(path):
    for stem in _candidate_split_stems(path):
        if _has_valid_split_with_stem(path, stem):
            return True
    return False


def do_split(path, size_mb):
    dir_ = path.parent
    stem = split_stem_for(path)
    zip_base = dir_ / f"{stem}.zip"
    meta_path = dir_ / f"{stem}.zip.meta.json"

    # Clean up any previous parts/meta, including legacy-scheme artifacts.
    for old_stem in {stem, path.stem}:
        for p in _find_split_parts(dir_, old_stem):
            try:
                p.unlink()
            except Exception:
                pass
        old_meta = dir_ / f"{old_stem}.zip.meta.json"
        if old_meta.exists():
            try:
                old_meta.unlink()
            except Exception:
                pass

    sevenzip = _find_7z()
    if not sevenzip:
        raise RuntimeError("7z not found on PATH")

    cmd = [sevenzip, "a", f"-v{int(size_mb)}m", "-mx=0", "-tzip",
           str(zip_base), path.name]

    # v6.58: stream 7z's output live so the user sees progress during
    # long splits, and cap the run with an out-of-band watchdog.
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(dir_),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except Exception as e_spawn:
        raise RuntimeError(f"could not launch 7z: {e_spawn}")

    def _kill_on_timeout():
        try:
            proc.kill()
        except Exception:
            pass

    # v6.60: watchdog resets on output activity so multi-hour splits
    # of massive files don't get killed after 1 hour of active work.
    # Kills only if 7z hangs with zero output for an hour.
    watchdog = threading.Timer(3600.0, _kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()

    tail = bytearray()
    try:
        # v6.58: use os.read() on the raw fd. BufferedReader.read(n)
        # blocks until n bytes or EOF, which can stall on 7z's
        # intermittent output. os.read returns as soon as data is
        # available.
        fd = proc.stdout.fileno()
        while True:
            try:
                chunk = os.read(fd, 8192)
            except OSError:
                break
            if not chunk:
                break
            watchdog.cancel()
            watchdog = threading.Timer(3600.0, _kill_on_timeout)
            watchdog.daemon = True
            watchdog.start()
            try:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            except Exception:
                try:
                    sys.stdout.write(
                        chunk.decode("utf-8", errors="replace")
                    )
                    sys.stdout.flush()
                except Exception:
                    pass
            tail.extend(chunk)
            if len(tail) > 4096:
                del tail[:-4096]
        rc = proc.wait()
    finally:
        watchdog.cancel()
        try:
            proc.stdout.close()
        except Exception:
            pass

    if rc != 0:
        # Roll back partial output so the next run doesn't think the
        # split succeeded.
        for old_stem in {stem, path.stem}:
            for p in _find_split_parts(dir_, old_stem):
                try:
                    p.unlink()
                except Exception:
                    pass
            old_meta = dir_ / f"{old_stem}.zip.meta.json"
            if old_meta.exists():
                try:
                    old_meta.unlink()
                except Exception:
                    pass
        raise RuntimeError(
            f"7z exit {rc}: "
            f"{tail.decode('utf-8', 'replace').strip()[:400]}"
        )

    parts = _find_split_parts(dir_, stem)
    if not parts:
        raise RuntimeError(f"7z produced no parts for {path.name}")

    nums = _split_part_numbers(parts)
    if nums != list(range(1, len(nums) + 1)):
        raise RuntimeError(
            f"7z produced non-contiguous parts for {path.name}: {nums}"
        )

    st = path.stat()
    meta = {
        "version": 2,                  # v6.58
        "original": path.name,
        "split_stem": stem,            # v6.58: naming scheme record
        "original_size": st.st_size,
        "original_mtime": st.st_mtime,
        "part_count": len(parts),
        "part_size_mb": int(size_mb),
        "created_utc": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat().replace("+00:00", "Z"),
    }
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1, sort_keys=True)
    except Exception:
        pass
    return parts


def bundle_dir(directory, min_files=DEFAULT_BUNDLE_MIN):
    created = []
    try:
        files = [f for f in directory.iterdir() if f.is_file()]
    except Exception:
        return created
    for group_name, exts in BUNDLE_GROUPS.items():
        bundle_path = directory / f"{group_name}.zip"
        if bundle_path.exists():
            continue
        candidates = []
        for f in files:
            if f.suffix.lower() not in exts:
                continue
            if f.name in _BUNDLE_EXCLUDE_NAMES:
                continue
            if f.name.endswith(".iaupload.json"):
                continue
            if f.suffix.lower() == ".zip":
                continue
            candidates.append(f)
        if len(candidates) < min_files:
            continue
        try:
            with zipfile.ZipFile(bundle_path, "w",
                                 zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(candidates, key=lambda x: x.name):
                    zf.write(f, arcname=f.name)
        except Exception as e:
            print(f"  [bundle] Failed to write {bundle_path.name}: {e}")
            try:
                bundle_path.unlink()
            except Exception:
                pass
            continue
        created.append((bundle_path, [f.name for f in candidates]))
    return created


_bundle_namelist_cache = {}


def _get_bundle_members(bundle_path):
    """
    v6.60: return {member_name: (file_size, CRC32)} for a bundle zip.
    Empty dict if the zip is missing or unreadable.
    """
    if not bundle_path.is_file():
        return {}
    try:
        b_stat = bundle_path.stat()
        cache_key = (str(bundle_path), b_stat.st_mtime, b_stat.st_size)
        if cache_key in _bundle_namelist_cache:
            return _bundle_namelist_cache[cache_key]
        with zipfile.ZipFile(bundle_path, "r") as zf:
            members = {
                zi.filename: (zi.file_size, zi.CRC)
                for zi in zf.infolist() if not zi.is_dir()
            }
        _bundle_namelist_cache[cache_key] = members
        return members
    except Exception:
        return {}


def _file_crc32(path, block_size=1024 * 1024):
    import zlib
    crc = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def _bundle_entry_matches(p, members, check_crc=False):
    """v6.60: is local file `p` stored, unchanged, inside the bundle?"""
    entry = members.get(p.name)
    if entry is None:
        return False
    zsize, zcrc = entry
    try:
        if p.stat().st_size != zsize:
            return False
        if check_crc and _file_crc32(p) != zcrc:
            return False
    except Exception:
        return False
    return True


def _is_covered_by_bundle(p, sibling_names):
    # v6.60: only consider covered if p is ACTUALLY inside the bundle with
    # the same size. Files added after the bundle was created, files edited
    # since, or files merely sharing an extension with an unrelated zip are
    # uploaded individually instead of being silently skipped.
    ext = p.suffix.lower()
    for group_name, exts in BUNDLE_GROUPS.items():
        bundle_name = f"{group_name}.zip"
        if ext in exts and bundle_name in sibling_names:
            members = _get_bundle_members(p.parent / bundle_name)
            if _bundle_entry_matches(p, members):
                return True
    return False


def _is_covered_by_split(p, sibling_names):
    # v6.58: new scheme keys on the full filename.
    new_stem = split_stem_for(p)
    if f"{new_stem}.zip.001" in sibling_names:
        return True

    # Legacy scheme (v6.57 and earlier) used path.stem. Because two
    # files can share a stem (foo.mp4 / foo.mkv), only trust the legacy
    # part if the sidecar meta confirms the same original name.
    if p.stem != new_stem:
        legacy_part = f"{p.stem}.zip.001"
        if legacy_part in sibling_names:
            legacy_meta = p.parent / f"{p.stem}.zip.meta.json"
            if legacy_meta.exists():
                try:
                    with open(legacy_meta, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    if m.get("original") == p.name:
                        return True
                except Exception:
                    pass

    return False


def build_cleanup_plan(folder_path):
    plan = {}
    try:
        for group_name, exts in BUNDLE_GROUPS.items():
            for bundle in folder_path.rglob(f"{group_name}.zip"):
                if not bundle.is_file():
                    continue
                try:
                    bundle_rel = str(bundle.relative_to(folder_path))
                except Exception:
                    continue
                try:
                    siblings = [f for f in bundle.parent.iterdir()
                                if f.is_file()]
                except Exception:
                    continue
                members = _get_bundle_members(bundle)
                for sib in siblings:
                    if sib == bundle:
                        continue
                    if sib.suffix.lower() not in exts:
                        continue
                    if sib.name in _BUNDLE_EXCLUDE_NAMES:
                        continue
                    if sib.name.endswith(".iaupload.json") or \
                       sib.name.endswith(".iaupload.json.tmp"):
                        continue
                    if sib.name.endswith(".zip.meta.json"):
                        continue
                    # v6.60: only plan deletion if the original is inside
                    # the archive AND byte-identical (size + CRC32).
                    if _bundle_entry_matches(sib, members, check_crc=True):
                        plan.setdefault(sib, set()).add(bundle_rel)
    except Exception as e:
        vlog(f"  build_cleanup_plan: bundle scan failed: {e}")
    try:
        for meta in folder_path.rglob("*.zip.meta.json"):
            if not meta.is_file():
                continue
            try:
                with open(meta, "r", encoding="utf-8") as f:
                    m = json.load(f)
                orig_name = m.get("original")
                if not orig_name:
                    continue
            except Exception:
                continue
            orig = meta.parent / orig_name
            if not orig.exists():
                continue

            # v6.58: prefer the stem recorded in the meta; fall back to
            # the current scheme, then the legacy path.stem scheme.
            stems = []
            recorded = m.get("split_stem")
            if isinstance(recorded, str) and recorded:
                stems.append(recorded)
            stems.append(split_stem_for(orig))
            if orig.stem not in stems:
                stems.append(orig.stem)

            parts = []
            for stem in stems:
                parts = _find_split_parts(meta.parent, stem)
                if parts:
                    break
            if not parts:
                continue

            for p in parts:
                try:
                    p_rel = str(p.relative_to(folder_path))
                except Exception:
                    continue
                plan.setdefault(orig, set()).add(p_rel)
    except Exception as e:
        vlog(f"  build_cleanup_plan: split scan failed: {e}")
    return plan


def verify_archives_on_ia(identifier, expected, session, timeout_s=180,
                          poll_interval=5.0):
    if not expected:
        return {}, {}
    deadline = time.time() + float(timeout_s)
    verified = {}
    missing = dict((k, (v, None)) for k, v in expected.items())
    while True:
        if shutdown_event.is_set():
            return verified, missing
        try:
            with _inflight_slot():
                it = get_item(
                    identifier, archive_session=session,
                    request_kwargs={
                        "timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)
                    },
                )
            listing = {}
            for f in getattr(it, "files", []):
                name = f.get("name")
                size = f.get("size")
                if not name or size is None:
                    continue
                try:
                    listing[normalize_path(name)] = int(size)
                except Exception:
                    pass
            verified = {}
            missing = {}
            for remote_path, want in expected.items():
                key = normalize_path(remote_path)
                got = listing.get(key)
                if got is not None and int(got) == int(want):
                    verified[remote_path] = got
                else:
                    missing[remote_path] = (want, got)
            if not missing:
                return verified, missing
        except Exception as e:
            vlog(f"  verify_archives_on_ia poll failed: {e}")
        if time.time() >= deadline:
            return verified, missing
        time.sleep(poll_interval)


# --- v6.48 end -----------------------------------------------------------


# --- v6.43: global in-flight request cap --------------------------------
# Every HTTP call to archive.org goes through this semaphore. The goal is
# to keep concurrent requests under IA's per-account rate limit, no matter
# how many file/part threads the user configured. Retries do not hold a
# slot while sleeping, so backoffs don't starve other requests.
DEFAULT_MAX_INFLIGHT = 12  # raised from 8
_MAX_INFLIGHT = DEFAULT_MAX_INFLIGHT
_inflight_sem = threading.BoundedSemaphore(_MAX_INFLIGHT)


def _reset_inflight(max_n):
    """v6.43: called from main() after arg parsing."""
    global _inflight_sem, _MAX_INFLIGHT
    try:
        max_n = max(1, int(max_n))
    except Exception:
        max_n = DEFAULT_MAX_INFLIGHT
    _MAX_INFLIGHT = max_n
    _inflight_sem = threading.BoundedSemaphore(max_n)


# v6.54: shared global cooldown + global rate limiter.
#
# Cooldown: when any thread sees a 503 SlowDown, it sets
# _rate_limit_until = now + backoff. Every other thread checks this
# before acquiring a semaphore slot. The whole fleet pauses together,
# giving IA's per-bucket task queue time to drain.
#
# Rate limiter: caps requests-per-minute across all threads so that
# under normal operation we never flood the queue in the first place.
DEFAULT_MAX_RPM = 30

_rate_limit_lock = threading.Lock()
_rate_limit_until = 0.0            # epoch seconds; 0 means no cooldown
_rate_limit_backoff = 30.0         # escalates on successive 503s
_rate_limit_last_hit = 0.0         # last time a 503 was seen
_RATE_LIMIT_RESET_AFTER = 30.0     # clean seconds before we reset backoff

# v6.54 rate-limiter state
_rate_lock = threading.Lock()
_rate_min_interval = 60.0 / DEFAULT_MAX_RPM
_rate_last_request = 0.0
_rate_inflight = 0
_rate_recent = []                  # timestamps of last N request starts
_RATE_RECENT_WINDOW = 60.0


def _reset_rate_limiter(max_rpm):
    """v6.54: called from main() after arg parsing."""
    global _rate_min_interval
    try:
        max_rpm = max(1, int(max_rpm))
    except Exception:
        max_rpm = DEFAULT_MAX_RPM
    _rate_min_interval = 60.0 / max_rpm


def _current_rate_stats():
    """v6.54: return (inflight_count, rpm_in_last_60s)."""
    with _rate_lock:
        now = time.time()
        recent = [t for t in _rate_recent if now - t <= _RATE_RECENT_WINDOW]
        _rate_recent[:] = recent
        return _rate_inflight, len(recent)


def _note_rate_limit():
    """
    Called by IAS3Client.request() when a 503 SlowDown is received.
    Sets a global cooldown and escalates the backoff window.
    """
    global _rate_limit_until, _rate_limit_backoff, _rate_limit_last_hit
    with _rate_limit_lock:
        now = time.time()
        # Reset backoff if we've had a clean streak.
        if now - _rate_limit_last_hit > _RATE_LIMIT_RESET_AFTER:
            _rate_limit_backoff = 30.0
        _rate_limit_last_hit = now
        _rate_limit_until = max(_rate_limit_until, now + _rate_limit_backoff)
        # Escalate for next time.
        _rate_limit_backoff = min(_rate_limit_backoff * 2, 300.0)


# v6.56: account-level quota (accesskey_tasks_queued) is different from
# bucket-level rate limiting (bucket_tasks_queued). The former is
# persistent server-side state that must drain before ANY upload works.
# Retrying just adds failed attempts to the queue.
_account_quota_event = threading.Event()


def _note_account_quota():
    """
    Called when IA returns accesskey_tasks_queued. This is per-account
    and cannot be worked around client-side. Abort the entire run.
    """
    if not _account_quota_event.is_set():
        _account_quota_event.set()
        try:
            tqdm.write("")
            tqdm.write("=" * 64)
            tqdm.write("!! ACCOUNT QUOTA EXHAUSTED  (accesskey_tasks_queued)")
            tqdm.write("=" * 64)
            tqdm.write("IA is rejecting ALL new tasks for your account.")
            tqdm.write("This is server-side state, not a client rate limit:")
            tqdm.write("orphaned multipart parts from earlier aborted runs")
            tqdm.write("are still counted against your account's queue.")
            tqdm.write("")
            tqdm.write("No amount of client-side retrying can fix this.")
            tqdm.write("IA's garbage collector must drain the queue first.")
            tqdm.write("")
            tqdm.write("Recommended action:")
            tqdm.write("  - Stop the script now.")
            tqdm.write("  - Wait 4 to 24 hours.")
            tqdm.write("  - Retry with smaller concurrency, e.g.:")
            tqdm.write('      iaupload.py "FOLDER" -t 4 \\')
            tqdm.write("          --multipart-concurrency 2 \\")
            tqdm.write("          --max-inflight 4 --max-rpm 20")
            tqdm.write("=" * 64)
            tqdm.write("")
        except Exception:
            pass
        shutdown_event.set()


@contextlib.contextmanager
def _inflight_slot():
    """
    v6.54: acquire a global wire slot for one HTTP request.

    Order of gates:
      1. Global cooldown (set on 503 by any thread)
      2. Global rate limiter (--max-rpm)
      3. Concurrency semaphore (--max-inflight)

    Sleeps are interruptible so Ctrl+C stays responsive.
    """
    global _rate_inflight, _rate_last_request

    sem = _inflight_sem
    if sem is None:
        yield
        return

    got = False
    while not got:
        if shutdown_event.is_set():
            raise RuntimeError("Cancelled by user (waiting for wire slot)")

        # 1. Global cooldown.
        with _rate_limit_lock:
            wait = _rate_limit_until - time.time()
        if wait > 0:
            time.sleep(min(wait, 1.0))
            continue

        # 2. Concurrency semaphore.
        got = sem.acquire(timeout=1.0)

    # 3. Global rate limiter (synchronized pacing once wire slot is held)
    pacing_done = False
    while not pacing_done:
        if shutdown_event.is_set():
            sem.release()
            raise RuntimeError("Cancelled by user (waiting for wire slot)")
        with _rate_lock:
            now = time.time()
            since_last = now - _rate_last_request
            pacer_wait = _rate_min_interval - since_last
            if pacer_wait <= 0:
                _rate_last_request = now
                _rate_inflight += 1
                _rate_recent.append(now)
                pacing_done = True
                break
        time.sleep(min(pacer_wait, 0.5))

    try:
        yield
    finally:
        with _rate_lock:
            _rate_inflight = max(0, _rate_inflight - 1)
        sem.release()



def vlog(msg):
    """Print a verbose debug message with timestamp and thread ID."""
    if VERBOSE:
        ts = time.strftime("%H:%M:%S")
        tid = threading.current_thread().name
        tqdm.write(f"  [VERBOSE {ts} {tid}] {msg}")


# --- HELPER CLASSES ---


class ProgressWrapper:
    """Wraps file object to update tqdm bar on read."""

    def __init__(self, filepath, bar):
        self._file = open(filepath, "rb")
        self._bar = bar
        self._len = os.path.getsize(filepath)

    def read(self, size=-1):
        if shutdown_event.is_set():
            return b""
        data = self._file.read(size)
        self._bar.update(len(data))
        return data

    def seek(self, offset, whence=0):
        return self._file.seek(offset, whence)

    def tell(self):
        return self._file.tell()

    def __len__(self):
        return self._len

    def close(self):
        self._file.close()


# --- CONSTANTS ---
IA_MAX_PATH_COMPONENT_BYTES = 230  # IA rejects path components longer than 230 bytes

# --- HELPER FUNCTIONS ---


def normalize_path(path_str):
    return path_str.lower().replace("\\", "/").replace(" ", "_")


def truncate_path_components(rel_path, max_bytes=IA_MAX_PATH_COMPONENT_BYTES):
    """
    Ensure every component of a relative path is at most `max_bytes` bytes (UTF-8).
    If a component (typically a filename) is too long, it is truncated while
    preserving the file extension and appending a short hash for uniqueness.
    Returns (new_path, was_truncated).
    """
    parts = rel_path.replace("\\", "/").split("/")
    changed = False
    new_parts = []

    for part in parts:
        encoded = part.encode("utf-8")
        if len(encoded) <= max_bytes:
            new_parts.append(part)
            continue

        # Need to truncate this component
        changed = True

        # Separate stem and extension (keep extension intact)
        dot_idx = part.rfind(".")
        if dot_idx > 0:
            stem = part[:dot_idx]
            ext = part[dot_idx:]  # e.g. ".jpg"
        else:
            stem = part
            ext = ""

        # Build a short hash from the ORIGINAL full name for uniqueness
        short_hash = hashlib.md5(encoded).hexdigest()[:8]
        suffix = f"_{short_hash}{ext}"  # e.g. "_a1b2c3d4.jpg"
        suffix_bytes = len(suffix.encode("utf-8"))

        # Truncate the stem so that stem + suffix fits within max_bytes
        budget = max_bytes - suffix_bytes
        stem_encoded = stem.encode("utf-8")
        # Trim byte-by-byte then decode safely (avoid splitting multi-byte chars)
        truncated_stem = stem_encoded[:budget].decode("utf-8", errors="ignore").rstrip()
        new_part = truncated_stem + suffix
        new_parts.append(new_part)

    return "/".join(new_parts), changed


def extract_date_from_string(text):
    """
    Attempts to find dates and ranges in the string.
    Returns a dict with 'date' (full YYYY-MM-DD or partial) and 'period' (Year or Range).
    """
    if not text:
        return {"date": None, "period": None}

    clean_text = text.strip().strip("\"").strip("'")

    # 1. Look for year ranges: 1900-1950 or 1900/1950
    range_match = re.search(r"(\d{4}[-/]\d{4})", clean_text)

    # 2. Look for full date: YYYY-MM-DD
    full_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", clean_text)

    # 3. Look for partial dates: YYYY-MM or YYYY
    month_match = re.search(r"(\d{4}-\d{2})", clean_text)
    year_match = re.search(r"(\d{4})", clean_text)

    # Determine full_date
    date_val = None
    if full_date_match:
        date_val = full_date_match.group(1)
    elif month_match:
        date_val = month_match.group(1)
    elif year_match:
        date_val = year_match.group(1)

    # Determine period (Priority to Range, then Year)
    period_val = None
    if range_match:
        # Standardize range to YYYY-YYYY or YYYY/YYYY (using dash as default for IA)
        period_val = range_match.group(1).replace("/", "-")
    elif year_match:
        period_val = year_match.group(1)

    return {"date": date_val, "period": period_val}


def calculate_md5(filepath, block_size=8192):
    md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                if shutdown_event.is_set():
                    return None
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None


def print_requirements():
    print("\n" + "=" * 50)
    print("PRE-UPLOAD CHECKLIST")
    print("=" * 50)
    print("1. [TARGET FOLDER] Path to files.")
    print("2. [IDENTIFIER]    Unique URL slug.")
    print("3. [METADATA]      Title, Mediatype, etc.")
    print("-" * 50)
    input("Press Enter to continue...")


def get_input(prompt_text, required=False, default=None, valid_options=None):
    global _skip_to_defaults

    # If skip mode is active, immediately return the default (or empty string)
    if _skip_to_defaults:
        val = default if default is not None else ""
        print(f"  {prompt_text}: {val}  [default]")
        return val

    while True:
        display = (
            f"{prompt_text} [{default}]: "
            if default is not None
            else f"{prompt_text}: "
        )
        try:
            val = input(display).strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit(1)

        # '!!' triggers skip-to-defaults for this and all remaining prompts
        if val == "!!":
            _skip_to_defaults = True
            val = default if default is not None else ""
            print(f"  >> Skipping to defaults. Remaining fields will use their default values.")
            print(f"  >> {prompt_text}: {val}")
            return val

        if not val and default is not None:
            return default
        if required and not val:
            print("  Error: Required.")
            continue
        if valid_options and val not in valid_options:
            print(f"  Error: Choose from {valid_options}")
            continue
        return val


def get_account_collections(session):
    """
    Best-effort fetch of collections writable/available to the current account.
    Returns a sorted list of collection identifiers, or [] on failure.
    """
    if not session:
        return []

    endpoints = [
        "https://archive.org/services/xauthn/?op=userinfo",
        "https://archive.org/services/xauthn/?op=account",
    ]

    for url in endpoints:
        try:
            resp = session.get(url, timeout=(10, 30))
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        collections = []
        if isinstance(data, dict):
            if isinstance(data.get("collections"), list):
                collections = data["collections"]
            elif isinstance(data.get("user"), dict) and isinstance(
                data["user"].get("collections"), list
            ):
                collections = data["user"]["collections"]

        out = []
        for c in collections:
            if isinstance(c, str) and c.strip():
                out.append(c.strip())
            elif isinstance(c, dict):
                val = c.get("identifier") or c.get("name")
                if isinstance(val, str) and val.strip():
                    out.append(val.strip())

        if out:
            return sorted(set(out))

    return []


def collect_metadata(
    default_title,
    prefills=None,
    account_collections=None,
    suggested_date=None,
    suggested_period=None,
):
    global _skip_to_defaults, _force_defaults_global
    if not _force_defaults_global:
        _skip_to_defaults = False  # Reset at the start of each metadata collection

    print("\n--- METADATA PREPARATION ---")
    print("Required: Title, Mediatype.")
    print(
        "Title: Human-readable name shown on the item page; keep it clear and descriptive."
    )
    print(
        "Mediatype: One of the allowed categories; choose the closest match for the content."
    )
    print("Creator: Person, group, or organization responsible (optional).")
    print("Description: Short summary of the item contents and context (optional).")
    print("Tags: Comma-separated keywords for search and discovery (optional).")
    print()
    print("  TIP: Type !! at any prompt to skip all remaining fields and use their defaults.")
    if prefills:
        print(
            "Found metadata file: fields are prefilled where available. Press Enter to keep defaults."
        )

    title_default = prefills.get("title") if prefills else None
    if not title_default:
        title_default = default_title
    title = get_input("Title", required=True, default=title_default)

    mediatype_default = prefills.get("mediatype") if prefills else None
    mediatype = get_input(
        "Mediatype (data|image|audio|texts|movies|software)",
        required=True,
        default=mediatype_default,
        valid_options=["data", "image", "audio", "texts", "movies", "software"],
    )

    creator_default = prefills.get("creator") if prefills else None
    description_default = prefills.get("description") if prefills else None
    tags_default = prefills.get("tags") if prefills else None
    collection_default = prefills.get("collection") if prefills else None
    creator = get_input("Creator", required=False, default=creator_default)
    description = get_input("Description", required=False, default=description_default)
    subjects_val = get_input("Tags (comma sep)", required=False, default=tags_default)
    subjects = [t.strip() for t in subjects_val.split(",")] if subjects_val else []

    # --- LICENSE SELECTION ---
    print("\nSelect a License (Press Enter for GPLv3 default):")
    license_options = {
        "1": ("GPLv3", "https://www.gnu.org/licenses/gpl-3.0.html"),
        "2": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
        "3": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
        "4": ("CC BY-ND 4.0", "https://creativecommons.org/licenses/by-nd/4.0/"),
        "5": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
        "6": ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
        "7": ("CC BY-NC-ND 4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
        "8": (
            "CC0 1.0 (Public Domain)",
            "https://creativecommons.org/publicdomain/zero/1.0/",
        ),
        "9": (
            "PDM 1.0 (Public Domain Mark)",
            "https://creativecommons.org/publicdomain/mark/1.0/",
        ),
        "0": ("Custom URL / None", None),
    }

    for key, (name, _) in license_options.items():
        print(f"  [{key}] {name}")

    license_default = prefills.get("licenseurl") if prefills else None

    # Map prefilled URL back to an option number if possible for display
    default_key = "1"  # GPLv3 default
    if license_default:
        for k, (name, url) in license_options.items():
            if url == license_default:
                default_key = k
                break
        else:
            default_key = "0"  # Custom

    choice = get_input("Choose license", default=default_key)

    selected_url = None
    if choice in license_options:
        selected_url = license_options[choice][1]

    if choice == "0" or (choice not in license_options and choice):
        # If they chose custom or typed a random string that isn't a key
        if choice not in license_options:
            selected_url = choice  # Treat as custom URL if not a key
        else:
            selected_url = get_input(
                "Custom License URL (leave empty for none)", default=license_default
            )

    metadata = {"title": title, "mediatype": mediatype}
    if selected_url:
        metadata["licenseurl"] = selected_url

    # Map mediatype to default community collection
    collection_map = {
        "texts": "opensource",
        "audio": "opensource_audio",
        "movies": "opensource_movies",
        "image": "opensource_image",
        "software": "open_source_software",
        "data": "opensource_media",
    }

    public_collections = set(collection_map.values())
    suggested_collection = collection_default
    if suggested_collection and suggested_collection not in public_collections:
        print(
            f"Warning: Prefilled collection '{suggested_collection}' may be restricted for your account."
        )
        suggested_collection = collection_map.get(mediatype)
    if not suggested_collection:
        suggested_collection = collection_map.get(mediatype)

    if account_collections:
        print("Available collections for this account:")
        print("  " + ", ".join(account_collections))

    collection = get_input("Collection", required=False, default=suggested_collection)
    if collection:
        metadata["collection"] = collection

    if creator:
        metadata["creator"] = creator
    if description:
        metadata["description"] = description
    if subjects:
        metadata["subject"] = subjects

    # Additional optional fields from prefills (preserving default fallbacks if key is absent)
    language_default = (prefills.get("language") if prefills else None) or "en"
    date_default = (prefills.get("date") if prefills else None) or suggested_date
    publisher_default = prefills.get("publisher") if prefills else None
    rights_default = prefills.get("rights") if prefills else None
    contributor_default = prefills.get("contributor") if prefills else None
    source_default = prefills.get("source") if prefills else None

    # Sync Rights with License selection if not prefilled
    if choice in license_options and not rights_default:
        rights_default = license_options[choice][0]

    coverage_default = (prefills.get("coverage") if prefills else None) or suggested_period
    temporal_default = (prefills.get("temporal") if prefills else None) or suggested_period
    spatial_default = prefills.get("spatial") if prefills else None
    citation_default = prefills.get("citation") if prefills else None
    type_default = prefills.get("type") if prefills else None
    relation_default = prefills.get("relation") if prefills else None
    format_list = prefills.get("format") if prefills else None
    custom_fields = prefills.get("_custom") if prefills else None

    language = get_input(
        "Language (e.g., en, zxx)", required=False, default=language_default
    )
    date = get_input("Date (e.g., 2024, 2024-01)", required=False, default=date_default)
    publisher = get_input("Publisher", required=False, default=publisher_default)
    rights = get_input(
        "Rights (e.g., CC BY 4.0)", required=False, default=rights_default
    )
    contributor = get_input("Contributor", required=False, default=contributor_default)
    source = get_input("Source", required=False, default=source_default)
    coverage = get_input(
        "Coverage (e.g., World, 1900-1950)", required=False, default=coverage_default
    )
    temporal = get_input(
        "Temporal (e.g., 1900/1950)", required=False, default=temporal_default
    )
    spatial = get_input(
        "Spatial (e.g., USA, Germany)", required=False, default=spatial_default
    )
    citation = get_input("Citation", required=False, default=citation_default)
    item_type = get_input("Type", required=False, default=type_default)
    relation = get_input(
        "Relation (comma-separated URLs)", required=False, default=relation_default
    )

    if language:
        metadata["language"] = language
    if date:
        metadata["date"] = date
    if publisher:
        metadata["publisher"] = publisher
    if rights:
        metadata["rights"] = rights
    if contributor:
        metadata["contributor"] = contributor
    if source:
        metadata["source"] = source
    if coverage:
        metadata["coverage"] = coverage
    if temporal:
        metadata["temporal"] = temporal
    if spatial:
        metadata["spatial"] = spatial
    if citation:
        metadata["citation"] = citation
    if item_type:
        metadata["type"] = item_type
    if relation:
        rel_list = [r.strip() for r in relation.split(",")]
        metadata["relation"] = rel_list

    if format_list:
        if isinstance(format_list, list):
            metadata["format"] = format_list

    if custom_fields:
        for key, val in custom_fields.items():
            metadata[key] = val

    return metadata


def _xml_text(node):
    if node is None:
        return None
    text = (node.text or "").strip()
    return text if text else None


def load_metadata_xml(folder_path):
    # Check for metadata.xml first, then _meta.xml
    xml_path = folder_path / "metadata.xml"
    if not xml_path.exists():
        xml_path = folder_path / "_meta.xml"
    if not xml_path.exists():
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return None

    def find_text(tag_names):
        for name in tag_names:
            node = root.find(f".//{name}")
            txt = _xml_text(node)
            if txt:
                return txt
        return None

    title = find_text(["title", "Title"])
    identifier_xml = find_text(["identifier", "Identifier"])
    mediatype = find_text(["mediatype", "Mediatype"])
    creator = find_text(["creator", "Creator"])
    description = find_text(["description", "Description"])
    collection = find_text(["collection", "Collection"])
    licenseurl = find_text(["licenseurl", "LicenseURL", "license", "License"])

    # subjects/tags: support repeated <subject> or <tag> nodes
    subjects = [(_xml_text(n) or "") for n in root.findall(".//subject")]
    subjects += [(_xml_text(n) or "") for n in root.findall(".//tag")]
    subjects = [s for s in subjects if s]
    tags = ", ".join(subjects) if subjects else None

    # Additional common fields
    language = find_text(["language", "Language"])
    date = find_text(["date", "Date"])
    publisher = find_text(["publisher", "Publisher"])
    rights = find_text(["rights", "Rights"])
    contributor = find_text(["contributor", "Contributor"])
    source = find_text(["source", "Source"])
    coverage = find_text(["coverage", "Coverage"])
    temporal = find_text(["temporal", "Temporal"])
    spatial = find_text(["spatial", "Spatial"])
    citation = find_text(["citation", "Citation"])
    item_type = find_text(["type", "Type"])

    # relation: support repeated nodes
    relations = [_xml_text(n) for n in root.findall(".//relation")]
    relations = [r for r in relations if r]
    relation = ", ".join(relations) if relations else None

    # format: support repeated nodes (list)
    formats = [_xml_text(n) for n in root.findall(".//format")]
    formats = [f for f in formats if f]

    # Custom fields: capture any additional elements not in the standard list
    custom_fields = {}
    standard_fields = {
        "title",
        "Title",
        "identifier",
        "Identifier",
        "mediatype",
        "Mediatype",
        "creator",
        "Creator",
        "description",
        "Description",
        "collection",
        "Collection",
        "licenseurl",
        "LicenseURL",
        "license",
        "License",
        "subject",
        "tag",
        "language",
        "Language",
        "date",
        "Date",
        "publisher",
        "Publisher",
        "rights",
        "Rights",
        "contributor",
        "Contributor",
        "relation",
        "citation",
        "Coverage",
        "coverage",
        "temporal",
        "Temporal",
        "spatial",
        "Spatial",
        "source",
        "Source",
        "type",
        "Type",
        "format",
    }
    for child in root:
        if child.tag not in standard_fields and not child.tag.startswith("{"):
            val = _xml_text(child)
            if val:
                custom_fields[child.tag] = val

    prefills = {}
    if title:
        prefills["title"] = title
    if identifier_xml:
        prefills["identifier"] = identifier_xml
    if mediatype:
        prefills["mediatype"] = mediatype
    if creator:
        prefills["creator"] = creator
    if description:
        prefills["description"] = description
    if tags:
        prefills["tags"] = tags
    if collection:
        prefills["collection"] = collection
    if licenseurl:
        prefills["licenseurl"] = licenseurl
    if language:
        prefills["language"] = language
    if date:
        prefills["date"] = date
    if publisher:
        prefills["publisher"] = publisher
    if rights:
        prefills["rights"] = rights
    if contributor:
        prefills["contributor"] = contributor
    if source:
        prefills["source"] = source
    if coverage:
        prefills["coverage"] = coverage
    if temporal:
        prefills["temporal"] = temporal
    if spatial:
        prefills["spatial"] = spatial
    if citation:
        prefills["citation"] = citation
    if item_type:
        prefills["type"] = item_type
    if relation:
        prefills["relation"] = relation
    if formats:
        prefills["format"] = formats
    if custom_fields:
        prefills["_custom"] = custom_fields

    return prefills or None


def load_metadata_json(folder_path):
    json_path = folder_path / "metadata.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    if isinstance(data.get("metadata"), dict):
        data = data["metadata"]

    def get_str(keys):
        for key in keys:
            val = data.get(key)
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned:
                    return cleaned
        return None

    title = get_str(["title", "Title"])
    identifier_json = get_str(["identifier", "Identifier"])
    mediatype = get_str(["mediatype", "Mediatype"])
    creator = None
    creator_val = data.get("creator")
    if isinstance(creator_val, list):
        creators = [str(c).strip() for c in creator_val if str(c).strip()]
        if creators:
            creator = "; ".join(creators)
    elif isinstance(creator_val, str) and creator_val.strip():
        creator = creator_val.strip()
    if not creator:
        creator = get_str(["Creator"])
    description = get_str(["description", "Description"])
    collection = get_str(["collection", "Collection"])
    licenseurl = get_str(["licenseurl", "LicenseURL", "license", "License"])

    tags = None
    subjects_val = data.get("subject")
    if subjects_val is None:
        subjects_val = data.get("Subject")

    if isinstance(subjects_val, list):
        subjects = [str(s).strip() for s in subjects_val if str(s).strip()]
        if subjects:
            tags = ", ".join(subjects)
    elif isinstance(subjects_val, str) and subjects_val.strip():
        tags = subjects_val.strip()

    if not tags:
        tags_val = data.get("tags")
        if tags_val is None:
            tags_val = data.get("Tags")

        if isinstance(tags_val, list):
            tag_list = [str(s).strip() for s in tags_val if str(s).strip()]
            if tag_list:
                tags = ", ".join(tag_list)
        elif isinstance(tags_val, str) and tags_val.strip():
            tags = tags_val.strip()

    # Additional common fields
    language = get_str(["language", "Language"])
    date = get_str(["date", "Date"])
    publisher = get_str(["publisher", "Publisher"])
    rights = get_str(["rights", "Rights"])
    contributor = get_str(["contributor", "Contributor"])
    source = get_str(["source", "Source"])
    coverage = get_str(["coverage", "Coverage"])
    temporal = get_str(["temporal", "Temporal"])
    spatial = get_str(["spatial", "Spatial"])
    citation = get_str(["citation", "Citation"])
    item_type = get_str(["type", "Type"])

    # relation: list or comma-separated string
    relation_val = data.get("relation")
    if relation_val is None:
        relation_val = data.get("Relation")
    relation = None
    if isinstance(relation_val, list):
        rels = [str(r).strip() for r in relation_val if str(r).strip()]
        if rels:
            relation = ", ".join(rels)
    elif isinstance(relation_val, str) and relation_val.strip():
        relation = relation_val.strip()

    # format: list
    format_val = data.get("format")
    if format_val is None:
        format_val = data.get("Format")
    formats = None
    if isinstance(format_val, list):
        fmt_list = [str(f).strip() for f in format_val if str(f).strip()]
        if fmt_list:
            formats = fmt_list
    elif isinstance(format_val, str) and format_val.strip():
        formats = [format_val.strip()]

    # Custom fields: everything else
    standard_keys = {
        "title",
        "Title",
        "identifier",
        "Identifier",
        "mediatype",
        "Mediatype",
        "creator",
        "Creator",
        "description",
        "Description",
        "collection",
        "Collection",
        "licenseurl",
        "LicenseURL",
        "license",
        "License",
        "subject",
        "Subject",
        "tags",
        "Tags",
        "language",
        "Language",
        "date",
        "Date",
        "publisher",
        "Publisher",
        "rights",
        "Rights",
        "contributor",
        "Contributor",
        "relation",
        "Relation",
        "citation",
        "Coverage",
        "coverage",
        "temporal",
        "Temporal",
        "spatial",
        "Spatial",
        "source",
        "Source",
        "type",
        "Type",
        "format",
        "Format",
    }
    custom_fields = {}
    for key, val in data.items():
        if key not in standard_keys:
            if isinstance(val, str) and val.strip():
                custom_fields[key] = val.strip()
            elif isinstance(val, list) and val:
                custom_fields[key] = [str(v).strip() for v in val if str(v).strip()]

    prefills = {}
    if title:
        prefills["title"] = title
    if identifier_json:
        prefills["identifier"] = identifier_json
    if mediatype:
        prefills["mediatype"] = mediatype
    if creator:
        prefills["creator"] = creator
    if description:
        prefills["description"] = description
    if tags:
        prefills["tags"] = tags
    if collection:
        prefills["collection"] = collection
    if licenseurl:
        prefills["licenseurl"] = licenseurl
    if language:
        prefills["language"] = language
    if date:
        prefills["date"] = date
    if publisher:
        prefills["publisher"] = publisher
    if rights:
        prefills["rights"] = rights
    if contributor:
        prefills["contributor"] = contributor
    if source:
        prefills["source"] = source
    if coverage:
        prefills["coverage"] = coverage
    if temporal:
        prefills["temporal"] = temporal
    if spatial:
        prefills["spatial"] = spatial
    if citation:
        prefills["citation"] = citation
    if item_type:
        prefills["type"] = item_type
    if relation:
        prefills["relation"] = relation
    if formats:
        prefills["format"] = formats
    if custom_fields:
        prefills["_custom"] = custom_fields

    return prefills or None


def load_metadata_prefills(folder_path):
    # Prefer XML when both files exist to preserve existing behavior.
    prefills = load_metadata_xml(folder_path)
    if prefills:
        return prefills
    return load_metadata_json(folder_path)


def sanitize_identifier(raw_identifier):
    # Normalize to ASCII, replace spaces with underscores, and strip invalid chars
    import unicodedata

    norm = unicodedata.normalize("NFKD", raw_identifier)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii")
    cleaned = ascii_only.replace(" ", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in "._-")
    cleaned = cleaned.strip("._-")
    if len(cleaned) < 5:
        return cleaned
    return cleaned[:100]


def record_result(category, name):
    with results_lock:
        final_results[category].append(name)


def print_report():
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)

    s_count = len(final_results["success"])
    f_count = len(final_results["failed"])
    c_count = len(final_results["cancelled"])

    print(f"Successful: {s_count}")
    print(f"Failed:     {f_count}")
    print(f"Cancelled:  {c_count}")

    if f_count > 0:
        print("-" * 60)
        print("FAILED FILES:")
        for name in final_results["failed"]:
            print(f" [x] {name}")

    if c_count > 0:
        print("-" * 60)
        print("CANCELLED FILES (Not uploaded):")
        for i, name in enumerate(final_results["cancelled"]):
            if i >= 10:
                print(f" ... and {c_count - 10} more.")
                break
            print(f" [-] {name}")

    print("=" * 60)

    # v6.56: distinct banner if the run was aborted by account quota.
    if _account_quota_event.is_set():
        print("")
        print("!" * 60)
        print("RUN WAS ABORTED BY IA ACCOUNT QUOTA (accesskey_tasks_queued)")
        print("Wait 4-24 hours, then retry with lower concurrency.")
        print("!" * 60)
        print("")


try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    pass  # Managed in main check

# ... (Previous imports)


def upload_worker(identifier, file_data, metadata=None, position=0, session=None):
    remote_key, local_path = file_data

    if shutdown_event.is_set():
        record_result("cancelled", remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        tqdm.write(f"Skipping empty file: {remote_key}")
        record_result("cancelled", remote_key)
        return (False, "Skipped empty file (0 bytes)")

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"START upload_worker for '{remote_key}' ({file_size:,} bytes)")

    # leave=False cleans up the bar line when done
    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=display_name,
        position=position,
        leave=False,
        dynamic_ncols=True,
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} | Speed: {rate_fmt} | Time: {elapsed}<{remaining}",
    ) as bar:
        # RETRY LOOP for Rate Limits
        max_retries = MAX_RETRIES
        attempt = 0
        backoff_time = RETRY_BACKOFF_START  # Start wait for rate limits

        while attempt < max_retries:
            wrapped_file = None
            try:
                vlog(f"  Attempt {attempt + 1}/{max_retries} for '{remote_key}'")
                wrapped_file = ProgressWrapper(local_path, bar)
                files_arg = {remote_key: wrapped_file}

                r = None
                upload_start = time.time()
                # v6.43: single-stream upload holds ONE global in-flight slot.
                # (Its internal HTTP is one long-lived connection, so treating
                # the whole call as one slot matches actual wire usage.)
                with _inflight_slot():
                    # Use the passed session if available to recycle connections
                    if session:
                        # We must use the Item-level API to pass the session
                        # 'session' here is expected to be an ArchiveSession
                        vlog(f"  get_item('{identifier}') via session...")
                        item = get_item(identifier, archive_session=session)
                        vlog(f"  Calling item.upload() for '{remote_key}'...")
                        r = item.upload(
                            files=files_arg,
                            metadata=metadata,
                            verbose=False,
                            retries=3,
                            request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
                        )
                    else:
                        # Fallback to default global upload
                        vlog(f"  Calling upload() (no session) for '{remote_key}'...")
                        r = upload(
                            identifier,
                            files=files_arg,
                            metadata=metadata,
                            verbose=False,
                            retries=3,
                            request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
                        )

                upload_elapsed = time.time() - upload_start
                vlog(f"  upload() returned for '{remote_key}' in {upload_elapsed:.1f}s")

                # CRITICAL LOOPHOLE FIX: Explicitly close responses to free connection pool slots immediately
                if r:
                    for resp in r:
                        vlog(f"  Response status={resp.status_code} for '{remote_key}'")
                        resp.close()

                if shutdown_event.is_set():
                    record_result("cancelled", remote_key)
                    return (False, "Cancelled")

                if r and r[0].status_code == 200:
                    vlog(f"  SUCCESS for '{remote_key}' (took {upload_elapsed:.1f}s)")
                    record_result("success", remote_key)
                    return (True, remote_key)

                # Check for rate limiting in status code (if 429 or 503 wasn't handled by custom adapter)
                if r and r[0].status_code in [429, 503, 509]:
                    tqdm.write(
                        f"Rate limited ({r[0].status_code}) for {display_name}. Retrying in {backoff_time}s..."
                    )
                    vlog(
                        f"  Rate limited ({r[0].status_code}), sleeping {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                    backoff_time = min(
                        backoff_time * 1.5, MAX_BACKOFF_TIME
                    )  # Cap max sleep
                    attempt += 1
                    bar.reset()  # Reset progress bar for retry
                    continue

                code = r[0].status_code if r else "Unknown"
                tqdm.write(f"FAILED {display_name}: HTTP {code}")
                vlog(f"  FAILED '{remote_key}' with HTTP {code}")
                record_result("failed", f"{remote_key} (Status {code})")
                return (False, f"Status {code}")

            except Exception as e:
                if shutdown_event.is_set():
                    record_result("cancelled", remote_key)
                    return (False, "Cancelled")

                error_str = str(e).lower()
                vlog(f"  EXCEPTION for '{remote_key}': {type(e).__name__}: {e}")

                # Check specifically for network issues, bucket limits, or timeouts
                retryable_errors = [
                    "bucket_tasks_queued",
                    "reduce your request rate",
                    "timed out",
                    "connection aborted",
                    "connection reset",
                    "remotely closed",
                ]

                if any(err in error_str for err in retryable_errors):
                    tqdm.write(
                        f"Rate Limit/Network issue for {display_name}: {e}. Pausing {backoff_time}s..."
                    )
                    vlog(f"  Retryable error, sleeping {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, MAX_BACKOFF_TIME)
                    attempt += 1
                    bar.reset()
                    continue

                # Real error
                tqdm.write(
                    f"Error uploading {remote_key}: {e}"
                )  # Print to console properly with tqdm
                record_result("failed", f"{remote_key} ({str(e)})")
                return (False, str(e))
            finally:
                if wrapped_file:
                    try:
                        wrapped_file.close()
                        vlog(f"  wrapped_file closed for '{remote_key}'")
                    except:
                        pass

        tqdm.write(f"FAILED {display_name}: Max retries exceeded")
        vlog(f"  Max retries exceeded for '{remote_key}'")
        record_result("failed", f"{remote_key} (Max Retries)")
        return (False, "Max Retries Exceeded (Rate Limit)")


# --- v6.39: multipart resume state ----------------------------------------

_MULTIPART_STATE_VERSION = 1


def _state_path(local_path):
    """Where the resume state for a given local file lives."""
    p = Path(local_path)
    return p.with_suffix(p.suffix + ".iaupload.json")


def _load_state(local_path):
    """Load resume state, or None if missing/unreadable/stale."""
    sp = _state_path(local_path)
    if not sp.exists():
        return None
    try:
        import json as _json
        with open(sp, "r", encoding="utf-8") as f:
            st = _json.load(f)
    except Exception as e:
        vlog(f"  state load failed ({sp}): {e}")
        return None
    if not isinstance(st, dict):
        return None
    if st.get("version") != _MULTIPART_STATE_VERSION:
        vlog(f"  state version mismatch: {st.get('version')}")
        return None
    return st


def _save_state(local_path, st):
    """Write state atomically."""
    sp = _state_path(local_path)
    try:
        import json as _json
        tmp = sp.with_suffix(sp.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            _json.dump(st, f, indent=1, sort_keys=True)
        tmp.replace(sp)
    except Exception as e:
        vlog(f"  state save failed ({sp}): {e}")


def _clear_state(local_path):
    """Delete the state file if present."""
    sp = _state_path(local_path)
    try:
        if sp.exists():
            sp.unlink()
            vlog(f"  state cleared: {sp}")
    except Exception as e:
        vlog(f"  state clear failed ({sp}): {e}")


def _state_matches(st, identifier, remote_key, local_path, local_size,
                   chunk_bytes=None):
    """v6.60: Does this state file belong to the current upload?"""
    if not st:
        return False
    if st.get("identifier") != identifier:
        return False
    if st.get("remote_key") != remote_key:
        return False
    if int(st.get("local_size") or -1) != int(local_size):
        return False
    try:
        cur_mtime = os.path.getmtime(local_path)
        saved_mtime = float(st.get("local_mtime") or 0)
        if saved_mtime and abs(cur_mtime - saved_mtime) > 1.0:
            vlog(f"  state mtime mismatch (saved={saved_mtime}, cur={cur_mtime})")
            return False
    except Exception:
        return False
    if chunk_bytes is not None:
        saved_chunk = int(st.get("chunk_bytes") or -1)
        if saved_chunk != int(chunk_bytes):
            vlog(f"  state chunk_bytes mismatch (saved={saved_chunk}, req={chunk_bytes})")
            return False
    return True


class IAS3Client:
    """
    v6.31: Minimal SigV2 S3 client for Internet Archive's endpoint.

    - Signs with AWS SigV2 (IA does not accept SigV4).
    - Follows the 307 storage-node redirect once per bucket, then caches it.
    - Supports multipart uploads: initiate / upload_part / complete / abort.
    - Depends only on `requests`, which is already imported by iaupload.

    The canonical resource used in signing is path + query only; the host
    is not signed. That's why the same Authorization header works on both
    s3.us.archive.org and the storage node it redirects to.
    """

    ENDPOINT = "https://s3.us.archive.org"

    def __init__(self, access_key, secret_key, timeout=(15, 300)):
        import requests
        from requests.adapters import HTTPAdapter

        self.ak = access_key
        self.sk = secret_key
        self.timeout = timeout
        self._node_cache = {}
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def _sign_v2(self, method, path, query="", content_md5="",
                 content_type="", extra_amz=None):
        import base64, hashlib, hmac
        from email.utils import formatdate

        date_str = formatdate(usegmt=True)
        amz = dict(extra_amz or {})
        amz["x-amz-date"] = date_str

        canon_amz = "".join(
            f"{k.lower()}:{v}\n" for k, v in sorted(amz.items())
        )
        canon_res = path + (f"?{query}" if query else "")

        # SigV2 string-to-sign: Date line is EMPTY when x-amz-date is set.
        string_to_sign = (
            f"{method}\n"
            f"{content_md5}\n"
            f"{content_type}\n"
            f"\n"
            f"{canon_amz}"
            f"{canon_res}"
        )
        # v6.35: stash the exact StringToSign for error reporting.
        self._last_string_to_sign = string_to_sign

        sig = base64.b64encode(
            hmac.new(self.sk.encode(), string_to_sign.encode(),
                     hashlib.sha1).digest()
        ).decode()

        # SigV2 rule: when x-amz-date is present, the Date header must be
        # omitted, and the StringToSign's Date line must be empty (which it
        # already is above). Sending both caused IA's verifier to rebuild a
        # different StringToSign and reject with 403 SignatureDoesNotMatch.
        headers = {
            "Authorization": f"AWS {self.ak}:{sig}",
        }
        headers.update(amz)
        if content_md5:
            headers["Content-MD5"] = content_md5
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _do(self, method, url, path, query, data, content_type, stream):
        # v6.56: sign INSIDE the slot so x-amz-date is fresh even after
        # a long cooldown. Also set Content-Length explicitly for any
        # body we can measure: IA's Apache front-end rejects chunked
        # PUTs with HTTP 411.
        with _inflight_slot():
            headers = self._sign_v2(
                method, path, query, content_type=content_type
            )
            if data is not None:
                length = None
                if isinstance(data, (bytes, bytearray)):
                    length = len(data)
                elif isinstance(data, str):
                    length = len(data.encode("utf-8"))
                else:
                    try:
                        length = len(data)
                    except (TypeError, AttributeError):
                        length = None
                if length is not None:
                    headers["Content-Length"] = str(length)
            return self._session.request(
                method, url, headers=headers, data=data,
                allow_redirects=False, timeout=self.timeout, stream=stream,
            )

    def request(self, method, path, query="", data=b"", content_type="",
                stream=False):
        """
        v6.38: retry on HTTP 503 SlowDown centrally here.

        IA returns 503 SlowDown when its bucket task queue is full
        (bucket_tasks_queued exceeds bucket_limit) — typically because a
        previous aborted multipart upload left orphaned parts pending
        server-side garbage collection.

        Every call site (preflight, initiate, part, complete) now gets
        automatic retry with exponential backoff. Sleep is interruptible.

        Writes always go to the master endpoint. IA redirects only reads
        (GET/HEAD) to storage nodes via 307, and the redirect body tells
        us to keep using the original endpoint for future requests.

        Path is percent-encoded (preserving '/') and used in BOTH the
        signature and the URL — IA's SigV2 verifier rebuilds the
        StringToSign from the encoded wire request.
        """
        from urllib.parse import quote, urlparse
        enc_path = quote(path, safe="/")

        backoff = RATE_LIMIT_BACKOFF_START
        last_r = None

        for attempt in range(1, RATE_LIMIT_MAX_RETRIES + 1):
            if shutdown_event.is_set():
                return last_r

            # v6.60: rewind streaming file readers before retry so we don't
            # send an empty body with a non-zero Content-Length!
            if attempt > 1 and hasattr(data, "seek"):
                try:
                    data.seek(0)
                    if hasattr(data, "_bar") and hasattr(data._bar, "reset"):
                        data._bar.reset()
                except Exception as e_rewind:
                    vlog(f"  could not rewind data before retry: {e_rewind}")

            url = self.ENDPOINT + enc_path + (f"?{query}" if query else "")
            r = self._do(method, url, enc_path, query, data,
                         content_type, stream)

            # Follow 307 for reads only, once per request.
            if r.status_code == 307 and method in ("GET", "HEAD"):
                loc = r.headers.get("location")
                if loc:
                    parsed = urlparse(loc)
                    node_root = f"{parsed.scheme}://{parsed.netloc}"
                    url = node_root + enc_path + (
                        f"?{query}" if query else ""
                    )
                    r = self._do(method, url, enc_path, query, data,
                                 content_type, stream)

            last_r = r

            if r.status_code != 503:
                return r

            body_lower = (r.text or "").lower()

            # v6.56: distinguish per-account quota (fatal) from per-bucket
            # rate limit (transient, backed off).
            is_account_quota = (
                "accesskey_tasks_queued" in body_lower
                or "rationed" in body_lower
            )
            is_slowdown = any(s in body_lower for s in (
                "slowdown",
                "reduce your request rate",
                "bucket_tasks_queued",
                "accesskey_tasks_queued",
                "rationed",
                "too many requests",
            ))
            if not is_slowdown:
                return r

            if is_account_quota:
                # Abort the run; do not retry.
                _note_account_quota()
                return r

            # Bucket-level rate limit — shared cooldown + retry.
            _note_rate_limit()

            if attempt >= RATE_LIMIT_MAX_RETRIES:
                tqdm.write(
                    f"  [rate-limit] IA 503 SlowDown persisted after "
                    f"{RATE_LIMIT_MAX_RETRIES} attempts; giving up"
                )
                return r

            tqdm.write(
                f"  [rate-limit] IA 503 SlowDown "
                f"(attempt {attempt}/{RATE_LIMIT_MAX_RETRIES}); "
                f"bucket queue full, waiting {backoff}s"
            )
            vlog(f"  request(): 503 SlowDown, sleeping {backoff}s "
                 f"(attempt {attempt}/{RATE_LIMIT_MAX_RETRIES})")
            waited = 0
            while waited < backoff and not shutdown_event.is_set():
                time.sleep(min(1, backoff - waited))
                waited += 1
            backoff = min(backoff * 2, RATE_LIMIT_BACKOFF_MAX)

        return last_r

    def list_parts(self, bucket, key, upload_id):
        """
        v6.39: Return {part_number: etag} for parts the server already has.

        Returns None if the upload id is invalid/expired (NoSuchUpload),
        which the caller uses as a signal to start a fresh upload.

        Handles S3's pagination (up to 1000 parts per page).
        """
        from urllib.parse import quote
        parts = {}
        marker = 0
        while True:
            q = f"uploadId={quote(upload_id, safe='')}"
            if marker:
                q += f"&part-number-marker={marker}"
            r = self.request("GET", f"/{bucket}/{key}", query=q)
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                # Any non-200 that isn't clearly transient: treat as unknown.
                # The caller will fall back to a fresh upload.
                body = (r.text or "").lower()
                if "nosuchupload" in body or r.status_code == 400:
                    return None
                raise RuntimeError(
                    f"ListParts failed: HTTP {r.status_code}: "
                    f"{r.text[:300]}"
                )
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(r.content)
            except Exception:
                return None

            is_truncated = False
            next_marker = None
            for el in root.iter():
                tag = el.tag.split("}")[-1]
                if tag == "Part":
                    pnum = None
                    etag = None
                    for child in el:
                        ctag = child.tag.split("}")[-1]
                        if ctag == "PartNumber":
                            try:
                                pnum = int(child.text)
                            except Exception:
                                pnum = None
                        elif ctag == "ETag":
                            etag = (child.text or "").strip().strip('"')
                    if pnum is not None and etag:
                        parts[pnum] = etag
                elif tag == "IsTruncated":
                    is_truncated = (el.text or "").lower() == "true"
                elif tag == "NextPartNumberMarker":
                    try:
                        next_marker = int(el.text)
                    except Exception:
                        next_marker = None

            if not is_truncated or next_marker is None or next_marker == marker:
                break
            marker = next_marker
        return parts

    def initiate_multipart(self, bucket, key, content_type=""):
        r = self.request("POST", f"/{bucket}/{key}", query="uploads",
                         content_type=content_type)
        if r.status_code != 200:
            raise RuntimeError(
                f"initiate failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(r.content)
        except Exception as e:
            raise RuntimeError(f"initiate parse failed: {e}")
        for el in root.iter():
            if el.tag.endswith("UploadId") and el.text:
                return el.text
        raise RuntimeError(f"no UploadId in response: {r.text[:200]}")

    def upload_part(self, bucket, key, upload_id, part_number, data):
        from urllib.parse import quote
        q = f"partNumber={part_number}&uploadId={quote(upload_id, safe='')}"
        r = self.request("PUT", f"/{bucket}/{key}", query=q, data=data)
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"part {part_number} failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        etag = r.headers.get("etag") or r.headers.get("ETag")
        if not etag:
            raise RuntimeError(f"part {part_number} returned no ETag")
        return etag.strip('"')

    def complete_multipart(self, bucket, key, upload_id, parts):
        from urllib.parse import quote
        q = f"uploadId={quote(upload_id, safe='')}"
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<CompleteMultipartUpload>')
        for pnum, etag in sorted(parts):
            xml += (f"<Part><PartNumber>{pnum}</PartNumber>"
                    f"<ETag>\"{etag}\"</ETag></Part>")
        xml += "</CompleteMultipartUpload>"
        r = self.request("POST", f"/{bucket}/{key}", query=q,
                         data=xml.encode(),
                         content_type="application/xml")
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"complete failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        return r

    def abort_multipart(self, bucket, key, upload_id):
        from urllib.parse import quote
        q = f"uploadId={quote(upload_id, safe='')}"
        try:
            self.request("DELETE", f"/{bucket}/{key}", query=q)
        except Exception:
            pass


# v6.39: module-level holder so workers can read CLI args without
# threading them through every call site. Set in main() after parse_args().
args_ref = None


def auto_chunk_mb(file_size, concurrency, target_parts_per_thread=8,
                  min_mb=8, max_mb=2048):
    """
    v6.52: pick a chunk size that balances three pressures:
      - Few parts per file: keeps IA's bucket_tasks_queued counter happy.
      - Short tail: with N threads, the last part per thread should be a
        small fraction of total runtime.
      - S3 hard limit: <= 10,000 parts per upload.

    Aim for `concurrency * target_parts_per_thread` total parts, then
    round up to the next power-of-two MB within [min_mb, max_mb].

    The 8-per-thread target produces coarser chunks than earlier versions
    (which used 40). A 5 GB file at concurrency 2 gets 512 MB chunks
    (10 parts) instead of 64 MB chunks (80 parts). Same total runtime,
    fewer round trips to IA.
    """
    try:
        concurrency = max(1, int(concurrency))
    except Exception:
        concurrency = 1
    try:
        file_size = max(1, int(file_size))
    except Exception:
        return min_mb

    target_total = max(1, concurrency * max(1, int(target_parts_per_thread)))
    raw_mb = file_size // (target_total * 1024 * 1024)

    if raw_mb <= min_mb:
        return min_mb
    if raw_mb >= max_mb:
        return max_mb
    # Round up to next power-of-two MB for tidiness.
    mb = 1 << (int(raw_mb) - 1).bit_length()
    return min(mb, max_mb)


MAX_S3_PARTS = 10000


def _resolve_chunk_bytes(file_size, chunk_size_mb, concurrency):
    """
    v6.60: single source of truth for multipart chunk sizing.
    Returns (chunk_bytes, n_parts). Applies auto-sizing when
    chunk_size_mb is falsy, a 5 MB floor, and upscaling to stay
    within S3's 10,000-part limit.
    """
    if not chunk_size_mb:
        chunk_size_mb = auto_chunk_mb(file_size, concurrency)
    chunk_bytes = max(5, int(chunk_size_mb)) * 1024 * 1024
    min_chunk_bytes = -(-int(file_size) // MAX_S3_PARTS)  # ceil div
    if chunk_bytes < min_chunk_bytes:
        chunk_bytes = -(-min_chunk_bytes // (1024 * 1024)) * 1024 * 1024
    n_parts = max(1, -(-int(file_size) // chunk_bytes))
    return chunk_bytes, n_parts


class SliceReader:
    """
    v6.40: file-like object exposing a bounded slice [offset, offset+size)
    of a local file for streaming multipart PUTs.

    When passed to requests, requests sees __len__ and sets Content-Length;
    http.client then calls read(blocksize) in ~8 KB blocks. Peak memory
    per thread is a few KB, so chunk_size can be large without OOM risk.

    No tell() — we want requests to use __len__ and not try to compute
    remaining bytes via tell().
    """
    def __init__(self, path, offset, size):
        self._path = path
        self._offset = int(offset)
        self._f = open(path, "rb")
        try:
            self._f.seek(offset)
        except Exception:
            self._f.close()
            raise
        self._remaining = int(size)
        self._size = int(size)

    def __len__(self):
        return self._size

    def seek(self, offset=0, whence=0):
        """v6.60: allow rewinding the slice for request retries."""
        if whence == 0:
            target = self._offset + offset
            self._f.seek(target)
            self._remaining = self._size - offset
            return offset
        elif whence == 1:
            current_pos = self._size - self._remaining
            target_pos = current_pos + offset
            self._f.seek(self._offset + target_pos)
            self._remaining = self._size - target_pos
            return target_pos
        elif whence == 2:
            target_pos = self._size + offset
            self._f.seek(self._offset + target_pos)
            self._remaining = self._size - target_pos
            return target_pos
        raise ValueError(f"Invalid whence: {whence}")

    def read(self, n=-1):
        if self._remaining <= 0:
            return b""
        if n is None or n < 0 or n > self._remaining:
            n = self._remaining
        data = self._f.read(n)
        if not data:
            # Unexpected EOF; return what we have and mark exhausted.
            self._remaining = 0
            return b""
        self._remaining -= len(data)
        return data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


def s3_upload_worker(identifier, file_data, metadata=None, position=0,
                     session=None):
    """
    v6.50: Single-stream upload via IA's S3 endpoint.

    - SigV2 signed PUT via IAS3Client
    - 307 storage-node redirect handled by the client
    - Streams from disk through ProgressWrapper (no full-file buffering)
    - Retries on transient network errors with exponential backoff
    - Metadata attached via modify_metadata() after the PUT succeeds
    """
    remote_key, local_path = file_data

    if shutdown_event.is_set():
        record_result("cancelled", remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        tqdm.write(f"Skipping empty file: {remote_key}")
        record_result("cancelled", remote_key)
        return (False, "Skipped empty file (0 bytes)")

    access_key = os.environ.get("IAS3_ACCESS_KEY")
    secret_key = os.environ.get("IAS3_SECRET_KEY")
    if not access_key and session is not None:
        access_key = getattr(session, "access_key", None)
    if not secret_key and session is not None:
        secret_key = getattr(session, "secret_key", None)
    if not access_key or not secret_key:
        err = "missing IA S3 credentials (run 'ia configure')"
        tqdm.write(f"[s3] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"S3 SINGLE PUT START for '{remote_key}' ({file_size:,} bytes)")

    client = IAS3Client(access_key, secret_key)

    try:
        pf = client.request("HEAD", f"/{identifier}")
        if pf.status_code not in (200, 204, 307):
            err = f"preflight failed: HTTP {pf.status_code}"
            tqdm.write(f"[s3] {remote_key}: {err}")
            record_result("failed", f"{remote_key} ({err})")
            return (False, err)
    except Exception as e_pf:
        err = f"preflight failed: {e_pf}"
        tqdm.write(f"[s3] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    max_retries = 5
    backoff = 30

    with tqdm(
        total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
        desc=display_name, position=position, leave=False,
        dynamic_ncols=True,
        bar_format=("{desc}: {percentage:3.0f}%|{bar}| "
                    "{n_fmt}/{total_fmt} | Speed: {rate_fmt} | "
                    "Time: {elapsed}<{remaining}"),
    ) as bar:
        for attempt in range(1, max_retries + 1):
            if shutdown_event.is_set():
                record_result("cancelled", remote_key)
                return (False, "Cancelled")

            reader = None
            try:
                reader = ProgressWrapper(local_path, bar)
                vlog(f"  attempt {attempt}/{max_retries}: PUT "
                     f"/{identifier}/{remote_key}")
                r = client.request(
                    "PUT",
                    f"/{identifier}/{remote_key}",
                    data=reader,
                )
            except Exception as e:
                if shutdown_event.is_set():
                    record_result("cancelled", remote_key)
                    return (False, "Cancelled")
                err_str = str(e).lower()
                retryable = any(s in err_str for s in (
                    "timed out", "timeout",
                    "connection aborted", "connection reset",
                    "remotely closed", "connection refused",
                    "broken pipe",
                ))
                if retryable and attempt < max_retries:
                    tqdm.write(
                        f"[s3] {display_name}: attempt {attempt}/"
                        f"{max_retries} failed ({e}); retrying in "
                        f"{backoff}s"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF_TIME)
                    bar.reset()
                    continue
                tqdm.write(f"[s3] {remote_key}: {e}")
                record_result("failed", f"{remote_key} ({e})")
                return (False, str(e))
            finally:
                if reader is not None:
                    try:
                        reader.close()
                    except Exception:
                        pass

            if shutdown_event.is_set():
                record_result("cancelled", remote_key)
                return (False, "Cancelled")

            if r.status_code in (200, 201):
                vlog(f"  S3 PUT SUCCESS for '{remote_key}'")
                if metadata:
                    try:
                        with _inflight_slot():
                            md_item = get_item(
                                identifier, archive_session=session,
                                request_kwargs={
                                    "timeout": (CONNECT_TIMEOUT,
                                                READ_TIMEOUT)
                                },
                            )
                            md_item.modify_metadata(metadata)
                    except Exception as e_md:
                        tqdm.write(
                            f"[s3] {remote_key}: data OK but metadata "
                            f"failed: {e_md}"
                        )
                        record_result(
                            "failed",
                            f"{remote_key} (metadata: {e_md})",
                        )
                        return (False, f"metadata: {e_md}")
                record_result("success", remote_key)
                return (True, remote_key)

            code = r.status_code
            body = (r.text or "")[:200]
            if code in (429, 503, 509) and attempt < max_retries:
                tqdm.write(
                    f"[s3] {display_name}: HTTP {code} (rate limit); "
                    f"retrying in {backoff}s"
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_TIME)
                bar.reset()
                continue

            tqdm.write(f"[s3] {display_name}: FAILED HTTP {code} {body}")
            record_result("failed", f"{remote_key} (S3 {code})")
            return (False, f"S3 {code}")

    tqdm.write(f"[s3] {display_name}: max retries exceeded")
    record_result("failed", f"{remote_key} (S3 Max Retries)")
    return (False, "S3 Max Retries Exceeded")


def multipart_upload_worker(
    identifier,
    file_data,
    metadata=None,
    position=0,
    session=None,
    chunk_size_mb=DEFAULT_CHUNK_SIZE_MB,
    max_concurrency=DEFAULT_MULTIPART_CONCURRENCY,
):
    """
    v6.31: Upload a large file using IA's S3 multipart API with SigV2
    signing and manual 307-follow, bypassing boto3/botocore entirely.

    Same signature/return contract as upload_worker, so the caller's
    thread-pool and result-recording logic works unchanged.
    """
    remote_key, local_path = file_data

    if shutdown_event.is_set():
        record_result("cancelled", remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        record_result("cancelled", remote_key)
        return (False, "Skipped empty file (0 bytes)")

    # --- credentials (same fallback chain as before) ---
    access_key = os.environ.get("IAS3_ACCESS_KEY")
    secret_key = os.environ.get("IAS3_SECRET_KEY")
    if not access_key and session is not None:
        access_key = getattr(session, "access_key", None)
    if not secret_key and session is not None:
        secret_key = getattr(session, "secret_key", None)
    if not access_key or not secret_key:
        err = "missing IA S3 credentials (run 'ia configure')"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"MULTIPART START for '{remote_key}' ({file_size:,} bytes, "
         f"chunk={chunk_size_mb}MB, concurrency={max_concurrency})")

    # --- v6.60: resolve chunk size and check resume state ---
    client = IAS3Client(access_key, secret_key)

    _state = None
    _state_last_write = 0.0
    try:
        _state = _load_state(local_path)
    except Exception as _se:
        vlog(f"  state load outer exception: {_se}")
        _state = None

    # Effective chunk size for an EXPLICIT --chunk-size, computed exactly
    # like a fresh upload would (5 MB floor, 10,000-part scaling), so it
    # is comparable with the chunk_bytes stored in the state file.
    req_chunk_bytes = None
    if chunk_size_mb:
        req_chunk_bytes, _ = _resolve_chunk_bytes(
            file_size, chunk_size_mb, max_concurrency
        )

    def _discard_state(reason):
        nonlocal _state
        vlog(f"  discarding resume state: {reason}")
        # v6.60: abort the stale server-side upload so its parts don't
        # linger and count against the account's task quota.
        _old_uid = _state.get("upload_id") if _state else None
        if _old_uid:
            try:
                client.abort_multipart(
                    _state.get("identifier") or identifier,
                    _state.get("remote_key") or remote_key,
                    _old_uid,
                )
            except Exception:
                pass
        _clear_state(local_path)
        _state = None

    if _state and getattr(args_ref, "no_resume", False):
        _discard_state("--no-resume given")
    elif _state and not _state_matches(
        _state, identifier, remote_key, local_path, file_size,
        chunk_bytes=req_chunk_bytes,
    ):
        _discard_state("state does not match current file/settings")

    if _state and _state.get("chunk_bytes") and _state.get("n_parts"):
        chunk_bytes = int(_state["chunk_bytes"])
        n_parts = int(_state["n_parts"])
        if n_parts != -(-file_size // chunk_bytes):
            _discard_state("n_parts inconsistent with chunk_bytes")
    if _state and _state.get("chunk_bytes") and _state.get("n_parts"):
        tqdm.write(
            f"[multipart] {remote_key}: adopting resumed chunk size = "
            f"{chunk_bytes // (1024 * 1024)} MB ({n_parts} parts)"
        )
    else:
        if not chunk_size_mb:
            tqdm.write(
                f"[multipart] {remote_key}: auto chunk = "
                f"{auto_chunk_mb(file_size, max_concurrency)} MB "
                f"(file {file_size/1e9:.2f} GB, {max_concurrency} threads)"
            )
        chunk_bytes, n_parts = _resolve_chunk_bytes(
            file_size, chunk_size_mb, max_concurrency
        )
        if chunk_size_mb and chunk_bytes != max(5, chunk_size_mb) * 1024 * 1024:
            tqdm.write(
                f"[multipart] {remote_key}: file is {file_size/1e9:.1f} GB; "
                f"scaling chunk {chunk_size_mb} MB -> "
                f"{chunk_bytes // (1024 * 1024)} MB (S3 10,000-part limit)"
            )

    vlog(f"  chunk_bytes={chunk_bytes:,}  n_parts={n_parts}")

    # --- preflight: HEAD bucket (read; 307 is expected and OK) ---
    try:
        pf_t0 = time.time()
        vlog(f"  preflight: HEAD /{identifier} ...")
        pf = client.request("HEAD", f"/{identifier}")
        # 200/204 = bucket answered directly.
        # 307 = master redirected us to a storage node; request() followed it.
        if pf.status_code not in (200, 204, 307):
            raise RuntimeError(f"HTTP {pf.status_code}")
        vlog(f"  preflight OK in {time.time()-pf_t0:.2f}s "
             f"(status={pf.status_code})")
    except Exception as e_pf:
        err = f"preflight failed: {e_pf}"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    upload_id = None
    parts = []
    resumed_from = 0

    if _state and not getattr(args_ref, "no_resume", False):
        _prev_uid = _state.get("upload_id")
        vlog(f"  found resume state (upload_id={_prev_uid}); "
             f"reconciling with server via ListParts ...")
        try:
            server_parts = client.list_parts(
                identifier, remote_key, _prev_uid
            )
        except Exception as _lpe:
            vlog(f"  ListParts failed: {_lpe}; starting fresh")
            server_parts = None

        if server_parts is None:
            tqdm.write(
                f"  [resume] previous upload id expired or unknown; "
                f"starting fresh"
            )
            _clear_state(local_path)
            _state = None
        else:
            upload_id = _prev_uid
            # Rebuild parts list from server response. Server is truth.
            # We only keep parts whose part_number <= n_parts.
            valid = {pn: et for pn, et in server_parts.items()
                     if 1 <= pn <= n_parts}
            parts = [(pn, et) for pn, et in sorted(valid.items())]
            resumed_from = len(parts)
            tqdm.write(
                f"  [resume] server has {resumed_from}/{n_parts} parts; "
                f"uploading the remaining {n_parts - resumed_from}"
            )
            vlog(f"  resumed: upload_id={upload_id} "
                 f"resumed_parts={resumed_from}")

    if upload_id is None:
        try:
            # --- initiate ---
            vlog(f"  initiate multipart ...")
            t_init = time.time()
            upload_id = client.initiate_multipart(identifier, remote_key)
            vlog(f"  upload_id={upload_id}  ({time.time()-t_init:.2f}s)")
            # Persist initial state immediately so a crash right after
            # initiate can still resume.
            _state = {
                "version": _MULTIPART_STATE_VERSION,
                "identifier": identifier,
                "remote_key": remote_key,
                "local_path": str(local_path),
                "local_size": file_size,
                "local_mtime": os.path.getmtime(local_path),
                "chunk_bytes": chunk_bytes,
                "n_parts": n_parts,
                "upload_id": upload_id,
                "parts": {},  # part_num (str) -> etag
                "created_utc": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            }
            _save_state(local_path, _state)
        except Exception as _init_err:
            raise

    # Helper: persist progress.
    def _persist_part(pnum, etag):
        nonlocal _state, _state_last_write
        if _state is None:
            return
        _state["parts"][str(pnum)] = etag
        _state_last_write = time.time()
        _save_state(local_path, _state)

    try:

        # --- upload parts (parallel) with progress ---
        with tqdm(
            total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
            desc=display_name, position=position, leave=False,
            dynamic_ncols=True,
            bar_format=("{desc}: {percentage:3.0f}%|{bar}| "
                        "{n_fmt}/{total_fmt} | Speed: {rate_fmt} | "
                        "Time: {elapsed}<{remaining}"),
        ) as bar:
            pbar_lock = threading.Lock()

            # v6.60: initialize progress bar with already-confirmed resumed bytes!
            if resumed_from > 0:
                resumed_bytes = sum(
                    min(chunk_bytes, file_size - (pn - 1) * chunk_bytes)
                    for pn, et in parts
                )
                if resumed_bytes > 0:
                    bar.update(resumed_bytes)

            # --- v6.36: per-part retry with exponential backoff ---
            _PART_BACKOFF_START = 5
            _PART_BACKOFF_MAX = 60

            _RETRYABLE_SUBSTRINGS = (
                "timed out", "timeout",
                "connection aborted", "connection reset",
                "connection refused", "broken pipe",
                "remotely closed", "temporarily unavailable",
                "server error", "internal error",
                "slowdown", "reduce your request rate",
                "bucket_tasks_queued",
                "throttl",
            )
            _RETRYABLE_STATUS = (408, 425, 429, 500, 502, 503, 504, 509)

            def _is_retryable(exc):
                msg = str(exc).lower()
                for s in _RETRYABLE_SUBSTRINGS:
                    if s in msg:
                        return True
                for code in _RETRYABLE_STATUS:
                    if f"http {code}" in msg or f" {code}:" in msg:
                        return True
                return False

            def _upload_part_with_retry(part_num, offset, size):
                if shutdown_event.is_set():
                    raise RuntimeError("Cancelled by user")
                backoff = _PART_BACKOFF_START
                last_exc = None
                for attempt in range(1, PART_MAX_RETRIES + 1):
                    if shutdown_event.is_set():
                        raise RuntimeError("Cancelled by user")
                    _reader = None
                    try:
                        # v6.40: stream the part from disk (no RAM buffering).
                        _reader = SliceReader(local_path, offset, size)
                        etag = client.upload_part(
                            identifier, remote_key, upload_id,
                            part_num, _reader,
                        )
                        with pbar_lock:
                            bar.update(size)
                        vlog(
                            f"  part {part_num}/{n_parts} OK "
                            f"(attempt {attempt}/{PART_MAX_RETRIES}, "
                            f"etag={etag[:12]}...)"
                        )
                        return (part_num, etag)
                    except Exception as e:
                        last_exc = e
                        if shutdown_event.is_set():
                            raise RuntimeError("Cancelled by user")
                        retryable = _is_retryable(e)
                        if not retryable or attempt >= PART_MAX_RETRIES:
                            raise
                        tqdm.write(
                            f"  part {part_num}/{n_parts} attempt "
                            f"{attempt}/{PART_MAX_RETRIES} failed: "
                            f"{e} — retrying in {backoff}s"
                        )
                        vlog(f"  part {part_num} retry in {backoff}s")
                        slept = 0
                        while slept < backoff and not shutdown_event.is_set():
                            time.sleep(min(1, backoff - slept))
                            slept += 1
                        backoff = min(backoff * 2, _PART_BACKOFF_MAX)
                    finally:
                        if _reader is not None:
                            try:
                                _reader.close()
                            except Exception:
                                pass
                raise RuntimeError(
                    f"part {part_num} failed after {PART_MAX_RETRIES} "
                    f"attempts: {last_exc}"
                )

            part_failures = []
            _parts_done = {pn for pn, _et in parts}

            # v6.59: track parts by number, not by list-append. Previously
            # resumed parts were seeded into `parts` AND re-returned by
            # their executor task, so `parts` ended up longer than
            # n_parts (e.g. 34 entries for a 32-part file) and the final
            # sanity check aborted with "only 34/32 parts uploaded".
            # A dict keyed on part number makes resume idempotent.
            parts_by_num = {pn: et for pn, et in parts if et}

            # Wrap upload-one to persist state on each successful part.
            _orig_upload_part = _upload_part_with_retry

            def _upload_part_with_persist(part_num, offset, size):
                # Skip if already done (state file or server).
                if part_num in _parts_done:
                    vlog(f"  part {part_num}/{n_parts} skipped "
                         f"(already uploaded)")
                    # v6.59: return None. The ETag is already recorded in
                    # parts_by_num from the resume; re-returning it would
                    # double-count it in the collector below.
                    return None
                res = _orig_upload_part(part_num, offset, size)
                if res is not None:
                    pn, et = res
                    if et is not None:
                        _persist_part(pn, et)
                return res

            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                futures = {}
                for i in range(n_parts):
                    pnum = i + 1
                    offset = i * chunk_bytes
                    size = min(chunk_bytes, file_size - offset)
                    futures[executor.submit(
                        _upload_part_with_persist, pnum, offset, size
                    )] = pnum

                for fut in as_completed(futures):
                    if shutdown_event.is_set():
                        part_failures.append((futures[fut], "cancelled"))
                        continue
                    try:
                        res = fut.result()
                    except Exception as e_part:
                        part_failures.append((futures[fut], e_part))
                        tqdm.write(
                            f"  [multipart] part {futures[fut]}/{n_parts} "
                            f"failed permanently: {e_part}"
                        )
                    else:
                        if res is not None:
                            pn, et = res
                            parts_by_num[pn] = et

            # v6.59: rebuild `parts` from the dict so resumed parts are
            # included exactly once and the length check below is honest.
            parts = sorted(parts_by_num.items())

            if part_failures:
                err = (
                    f"{len(part_failures)} part(s) failed after retries "
                    f"(first: part {part_failures[0][0]}: "
                    f"{part_failures[0][1]})"
                )
                raise RuntimeError(err)

        if shutdown_event.is_set():
            tqdm.write(
                f"  [resume] upload paused; state preserved at {_state_path(local_path)}"
            )
            record_result("cancelled", remote_key)
            return (False, "Cancelled")

        if len(parts) != n_parts:
            raise RuntimeError(
                f"only {len(parts)}/{n_parts} parts uploaded"
            )

        # --- complete ---
        vlog(f"  completing multipart ({len(parts)} parts) ...")
        t_complete = time.time()
        client.complete_multipart(identifier, remote_key, upload_id, parts)
        vlog(f"  complete returned ({time.time()-t_complete:.2f}s); "
             f"server may still be reassembling")

        # v6.41: complete_multipart returned HTTP 200, which means IA has
        # accepted the multipart upload. Reassembly happens server-side and
        # can take minutes for large items; polling get_item().files was
        # marking genuinely-uploaded files as failed and forcing full
        # re-uploads on the next run. We trust the 200.

        # --- metadata ---
        if metadata:
            try:
                vlog(f"  applying metadata via modify_metadata() ...")
                # v6.43: metadata calls also go through the in-flight cap.
                with _inflight_slot():
                    md_item = get_item(
                        identifier, archive_session=session,
                        request_kwargs={
                            "timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)
                        },
                    )
                    md_item.modify_metadata(metadata)
            except Exception as e_md:
                tqdm.write(f"[multipart] {remote_key}: data OK but "
                           f"metadata failed: {e_md}")
                record_result("failed",
                              f"{remote_key} (metadata: {e_md})")
                return (False, f"metadata: {e_md}")

        vlog(f"MULTIPART SUCCESS for '{remote_key}'")
        # v6.39: clear resume state on full success.
        _clear_state(local_path)
        record_result("success", remote_key)
        return (True, remote_key)

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        vlog(f"  multipart exception: {err}")
        # v6.60: do NOT abort on user cancellation / Ctrl+C either — preserve state
        # so re-running resumes from where it stopped. Only --reset-state wipes state.
        tqdm.write(
            f"  [resume] state saved at {_state_path(local_path)}; "
            f"re-run to continue from where we left off"
        )
        if shutdown_event.is_set():
            record_result("cancelled", remote_key)
            return (False, "Cancelled by user")
        record_result("failed", f"{remote_key} (multipart: {err})")
        return (False, err)


def _filter_ia_s3_dns(host="s3.us.archive.org", port=443, probe_timeout=3):
    """
    s3.us.archive.org sometimes resolves to multiple IPs, some of which
    blackhole TCP/443. Probe each resolved IP and monkey-patch
    socket.getaddrinfo to return only reachable ones for that host.

    Idempotent. No-op if all IPs are reachable or none are.
    """
    import socket as _sock

    try:
        infos = _sock.getaddrinfo(host, port, proto=_sock.IPPROTO_TCP)
    except Exception as e:
        print(f"[dns-filter] {host}: resolution failed: {e}")
        return

    seen = set()
    candidates = []
    for info in infos:
        ip = info[4][0]
        if ip not in seen:
            seen.add(ip)
            candidates.append((ip, info))

    good_infos = []
    bad_ips = []
    for ip, info in candidates:
        try:
            s = _sock.create_connection((ip, port), timeout=probe_timeout)
            s.close()
            good_infos.append(info)
        except Exception:
            bad_ips.append(ip)

    good_ips = [i[4][0] for i in good_infos]

    if not good_infos:
        print(
            f"[dns-filter] WARNING: no reachable IPs for {host} "
            f"(probed: {[ip for ip, _ in candidates]})"
        )
        return

    if not bad_ips:
        return

    print(
        f"[dns-filter] {host}: pinning to reachable IP(s) {good_ips} "
        f"(dropped dead: {bad_ips})"
    )

    _orig_gai = _sock.getaddrinfo
    _good_set = set(good_ips)
    _patched_marker = "_iaupload_v630_patched"

    if getattr(_orig_gai, _patched_marker, False):
        return

    def _patched_gai(host_arg, port_arg, family=0, type=0, proto=0, flags=0):
        results = _orig_gai(host_arg, port_arg, family, type, proto, flags)
        if host_arg == host:
            filtered = [r for r in results if r[4][0] in _good_set]
            if filtered:
                return filtered
        return results

    setattr(_patched_gai, _patched_marker, True)
    _sock.getaddrinfo = _patched_gai


def handle_dji_lrf(folder_path, auto_confirm=False):
    """
    Finds .LRF files, renames them to _s.MP4 for Archive.org compatibility.
    Checks for collisions to prevent overwriting.
    """
    lrf_files = list(folder_path.rglob("*.[lL][rR][fF]"))
    if not lrf_files:
        return

    print(
        f"\n[!] Detected {len(lrf_files)} DJI LRF files (unsupported by Archive.org)."
    )

    if not auto_confirm:
        try:
            confirm = (
                input(
                    "Rename them to .mp4 with '_s' suffix to allow upload? (y/n) [y]: "
                )
                .strip()
                .lower()
            )
            if confirm and confirm not in ["y", "yes"]:
                print("Skipping LRF renaming.")
                return
        except KeyboardInterrupt:
            print("\nSkipping LRF renaming.")
            return

    renamed = 0
    skipped = 0
    for p in lrf_files:
        # DJI_0003.LRF -> DJI_0003_s.mp4
        new_name = p.stem + "_s.mp4"
        new_path = p.with_name(new_name)

        if new_path.exists():
            tqdm.write(f"  [SKIP] {p.name} -> {new_name} (File already exists)")
            skipped += 1
            continue

        try:
            p.rename(new_path)
            renamed += 1
        except Exception as e:
            tqdm.write(f"  [ERROR] Could not rename {p.name}: {e}")

    if renamed > 0:
        print(f"Successfully renamed {renamed} file(s).")
    if skipped > 0:
        print(f"Skipped {skipped} file(s) to avoid collisions.")


def safe_rmtree(path, retries=5, delay=1.0):
    """
    Attempts to delete a directory tree, retrying on failure (common on Windows).
    """
    for i in range(retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError:
            if i < retries - 1:
                vlog(f"PermissionError during rmtree, retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
        except Exception:
            raise
    return False


def main():
    # --- v6.44: two-stage SIGINT handler ---
    # First Ctrl+C: graceful shutdown (sets the flag).
    # Second Ctrl+C within 3s: hard exit. Necessary because blocking
    # socket calls on Windows don't respond to Python signals, so worker
    # threads and ThreadPoolExecutor.join can hang for minutes.
    try:
        import signal as _signal
        import os as _os
        import time as _time

        _sigint_state = {"count": 0, "last": 0.0}

        def _sigint_handler(signum, frame):
            try:
                now = _time.time()
                if now - _sigint_state["last"] > 3.0:
                    _sigint_state["count"] = 0
                _sigint_state["count"] += 1
                _sigint_state["last"] = now

                if _sigint_state["count"] >= 2:
                    # Hard exit from the signal handler. Kills all threads
                    # including any stuck in uninterruptible C calls.
                    print("\n\n!!! SECOND CTRL+C — FORCE EXIT !!!",
                          flush=True)
                    _os._exit(1)

                print("\n\n!!! CTRL+C RECEIVED !!!", flush=True)
                print("Shutting down gracefully. "
                      "Press Ctrl+C again within 3s to force exit.",
                      flush=True)
                shutdown_event.set()
            except Exception:
                # Never let the handler itself raise.
                try:
                    _os._exit(1)
                except Exception:
                    pass

        _signal.signal(_signal.SIGINT, _sigint_handler)
    except Exception as _sig_err:
        print(f"Warning: could not install SIGINT handler: {_sig_err}")

    # --- v6.30: filter dead s3.us.archive.org IPs before any S3 call ---
    try:
        _filter_ia_s3_dns()
    except Exception as _dns_err:
        print(f"[dns-filter] setup error (continuing): {_dns_err}")

    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Archive.org Smart Uploader & Syncer")
    parser.add_argument("folder", nargs="?", help="Path to local folder")
    parser.add_argument("identifier", nargs="?", help="Unique Archive.org identifier")
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"Number of parallel upload/delete threads (default: {DEFAULT_THREADS})",
    )
    parser.add_argument(
        "-s", "--sync", action="store_true", help="Sync mode (Upload/Update only)"
    )
    parser.add_argument(
        "-o",
        "--orphan-deletion",
        action="store_true",
        help="Delete remote files that do not exist locally",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        action="store_true",
        help="Force metadata update prompt for existing items",
    )
    parser.add_argument(
        "--md5-verify",
        action="store_true",
        help="Enable MD5 comparison for files that already exist remotely by path",
    )
    parser.add_argument(
        "--fix-lrf",
        action="store_true",
        help="Automatically rename DJI .LRF files to _s.MP4 without prompting",
    )
    parser.add_argument(
        "-z",
        "--zip",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Disable automatic small-file bundling (texts.zip/images.zip).",
    )
    parser.add_argument(
        "--batch-dirs",
        action="store_true",
        help="Process all subdirectories in 'folder' sequentially as separate items.",
    )
    parser.add_argument(
        "--batch-prompt",
        action="store_true",
        help="When using --batch-dirs, prompt for metadata for each directory instead of auto-accepting defaults.",
    )
    parser.add_argument(
        "--force-defaults",
        action="store_true",
        help=argparse.SUPPRESS,  # Hidden flag for internal batch use
    )
    parser.add_argument(
        "--delete-folder-on-success",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--keep-folder-on-success",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help=("Enable automatic large-file splitting into multi-volume "
              "zips (requires 7z). Off by default; use this flag to "
              "opt in."),
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--split-size",
        type=str,
        default=DEFAULT_SPLIT_SIZE_STR,
        help=("Volume size for split archives: '4480M', '4G', 'dvd', "
              "'dvd9', 'bd', or 'off'. "
              f"Default: {DEFAULT_SPLIT_SIZE_STR}."),
    )
    parser.add_argument(
        "--bundle-min",
        type=int,
        default=DEFAULT_BUNDLE_MIN,
        help=("Min same-directory files before bundling into "
              f"texts.zip/images.zip. Default: {DEFAULT_BUNDLE_MIN}."),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging for each upload step",
    )
    parser.add_argument(
        "--no-multipart",
        action="store_true",
        help="Disable S3 multipart uploads (use single-stream uploads for all files)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore any saved resume state; start multipart uploads fresh",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Delete saved resume state for the target file/folder and exit",
    )
    parser.add_argument(
        "--multipart",
        action="store_true",
        help=("Force multipart for every file >= 1 MB. Default is auto: "
              "multipart only for files >= 15 GB."),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help=("Chunk size in MB for multipart uploads. Omit to auto-size "
              "from file size and concurrency (~8 parts per thread, "
              "rounded up to a power-of-two MB, clamped 8 MB - 2 GB)."),
    )
    parser.add_argument(
        "--multipart-threshold",
        type=int,
        default=DEFAULT_MULTIPART_THRESHOLD_MB,
        help=f"Files >= this many MB use multipart (default: {DEFAULT_MULTIPART_THRESHOLD_MB})",
    )
    parser.add_argument(
        "--multipart-concurrency",
        type=int,
        default=DEFAULT_MULTIPART_CONCURRENCY,
        help=f"Parallel chunk uploads per large file (default: {DEFAULT_MULTIPART_CONCURRENCY})",
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=DEFAULT_MAX_INFLIGHT,
        help=(f"Global cap on concurrent HTTP requests to archive.org, "
              f"across all threads. (default: {DEFAULT_MAX_INFLIGHT})"),
    )
    parser.add_argument(
        "--max-rpm",
        type=int,
        default=DEFAULT_MAX_RPM,
        help=(f"Global cap on HTTP requests per minute to archive.org, "
              f"across all threads. Lower this if you see frequent 503 "
              f"SlowDown. (default: {DEFAULT_MAX_RPM})"),
    )
    parser.add_argument(
        "--delete-originals-after-upload",
        action="store_true",
        help=("After bundles/split parts upload, verify visible on IA, "
              "then delete the source files they replace. Off by default."),
    )
    parser.add_argument(
        "--verify-timeout",
        type=int,
        default=180,
        help="Seconds to wait for IA listing refresh during verification.",
    )
    _upload_path = parser.add_mutually_exclusive_group()
    _upload_path.add_argument(
        "--use-ia-library",
        dest="use_ia_library",
        action="store_true",
        help=("Route small/medium files through internetarchive.upload() "
              "(this is the default)."),
    )
    _upload_path.add_argument(
        "--use-s3-put",
        dest="use_ia_library",
        action="store_false",
        help=("Route small/medium files through the built-in SigV2 S3 "
              "single PUT instead of internetarchive.upload()."),
    )
    parser.set_defaults(use_ia_library=True)
    args = parser.parse_args()

    # v6.58: --no-split is a compatibility no-op. Splitting is already
    # opt-in via --split; warn so users don't think it did something.
    if getattr(args, "no_split", False):
        print("Note: --no-split is deprecated; splitting is off by "
              "default. Use --split to enable it.")

    global VERBOSE, _MULTIPART_ENABLED, args_ref
    VERBOSE = args.verbose
    args_ref = args  # v6.39: share with multipart_upload_worker

    # v6.43: apply the in-flight request cap now that we have args
    try:
        _reset_inflight(args.max_inflight)
    except Exception as _ri_err:
        print(f"Warning: could not set in-flight cap: {_ri_err}")

    # v6.54: apply the rate limiter
    try:
        _reset_rate_limiter(args.max_rpm)
    except Exception as _rr_err:
        print(f"Warning: could not set rate limit: {_rr_err}")

    # v6.48: three-way multipart mode.
    if args.no_multipart:
        _MULTIPART_ENABLED = False
    elif args.multipart:
        _MULTIPART_ENABLED = True
        args.multipart_threshold = 1
    else:
        _MULTIPART_ENABLED = True

    max_workers = args.threads

    print(f"--- Archive.org Smart Uploader (iaupload v6.59) ---")
    print(f"--- Threads: {max_workers} ---")
    print(f"--- Max in-flight requests: {getattr(args, 'max_inflight', DEFAULT_MAX_INFLIGHT)} ---")
    print(f"--- Max request rate: {getattr(args, 'max_rpm', DEFAULT_MAX_RPM)} req/min ---")
    print(f"--- MD5 Verify: {'ON' if args.md5_verify else 'OFF (Path-only)'} ---")
    if not _MULTIPART_ENABLED:
        print(f"--- Multipart: OFF (--no-multipart) ---")
    else:
        _chunk_disp = (
            f"{args.chunk_size} MB" if args.chunk_size else "auto"
        )
        if args.multipart:
            print(
                f"--- Multipart: FORCED ON "
                f"(chunk {_chunk_disp}, "
                f"{args.multipart_concurrency} parts/file, "
                f"all files >= 1 MB) ---"
            )
        else:
            _thresh = args.multipart_threshold
            _S3_PUT_MAX_MB = 5 * 1024
            if not args.no_multipart and not args.use_ia_library:
                if _thresh > _S3_PUT_MAX_MB:
                    _thresh = _S3_PUT_MAX_MB
            if _thresh >= 1024 and _thresh % 1024 == 0:
                _thresh_disp = f"{_thresh // 1024} GB"
            elif _thresh >= 1024:
                _thresh_disp = f"{_thresh / 1024:.1f} GB"
            else:
                _thresh_disp = f"{_thresh} MB"
            print(
                f"--- Multipart: AUTO "
                f"(threshold {_thresh_disp}, chunk {_chunk_disp}, "
                f"{args.multipart_concurrency} parts/file) ---"
            )
    if args.no_multipart or args.use_ia_library:
        print(f"--- Small-file path: internetarchive library ---")
    else:
        print(f"--- Small-file path: S3 single PUT (built-in) ---")
    if args.no_zip:
        print(f"--- Bundling: OFF (--no-zip) ---")
    else:
        print(f"--- Bundling: ON  (texts/images, min {args.bundle_min} files/group) ---")
    if not args.split:
        print(f"--- Splitting: OFF (use --split to enable) ---")
    else:
        _split_disp = args.split_size
        if _find_7z() is None:
            print(f"--- Splitting: REQUESTED but 7z not found on PATH ---")
        else:
            print(f"--- Splitting: ON  (volume size {_split_disp}) ---")
    if VERBOSE:
        print(f"--- Verbose: ON ---")
    if args.sync:
        print("--- Mode: SYNC (Uploads) ---")
    if args.orphan_deletion:
        print("--- Mode: DELETE (Orphan Removal Enabled) ---")

    # 0. Auth
    try:
        session = get_session()
        if not session.access_key:
            print("Error: Not logged in. Run 'ia configure'.")
            sys.exit(1)
    except:
        sys.exit(1)

    try:
        # 1. Inputs (Using args if available, else interactive)
        folder_path_str = args.folder
        identifier = args.identifier

        if not folder_path_str and getattr(args, "batch_dirs", False):
            folder_path_str = "."

        if folder_path_str:
            folder_path_str = folder_path_str.strip('"').strip("'")
        else:
            print_requirements()
            folder_path_str = (
                get_input("Target Folder", required=True).strip('"').strip("'")
            )

        if not os.path.isdir(folder_path_str):
            print("Error: Folder not found.")
            sys.exit(1)

        folder_path = Path(folder_path_str)

        # --- BATCH DIRS LOGIC ---
        global _force_defaults_global, _skip_to_defaults
        if getattr(args, "force_defaults", False):
            _force_defaults_global = True
            _skip_to_defaults = True

        if getattr(args, "batch_dirs", False):
            subdirs = sorted([d for d in folder_path.iterdir() if d.is_dir()])
            if not subdirs:
                print(f"No subdirectories found in '{folder_path_str}'. Exiting.")
                sys.exit(0)
            
            print(f"\n=== BATCH MODE: Found {len(subdirs)} folders to process ===")
            
            child_flags = []
            if not getattr(args, "delete_folder_on_success", False) and not getattr(args, "keep_folder_on_success", False):
                try:
                    ans = input("\nAutomatically delete each local folder after it uploads successfully? (y/n) [n]: ").strip().lower()
                    if ans == "y":
                        args.delete_folder_on_success = True
                    else:
                        args.keep_folder_on_success = True
                except KeyboardInterrupt:
                    args.keep_folder_on_success = True
                    print("\nKeeping folders by default.")
            
            if getattr(args, "delete_folder_on_success", False): child_flags.append("--delete-folder-on-success")
            if getattr(args, "keep_folder_on_success", False): child_flags.append("--keep-folder-on-success")
            if getattr(args, 'threads', DEFAULT_THREADS) != DEFAULT_THREADS: child_flags.extend(["-t", str(args.threads)])
            if getattr(args, 'sync', False): child_flags.append("-s")
            if getattr(args, 'orphan_deletion', False): child_flags.append("-o")
            if getattr(args, 'metadata', False): child_flags.append("-m")
            if getattr(args, 'md5_verify', False): child_flags.append("--md5-verify")
            if getattr(args, 'fix_lrf', False): child_flags.append("--fix-lrf")
            if getattr(args, 'no_zip', False): child_flags.append("--no-zip")
            if getattr(args, 'split', False): child_flags.append("--split")
            if getattr(args, 'split_size', DEFAULT_SPLIT_SIZE_STR) != DEFAULT_SPLIT_SIZE_STR: child_flags.extend(["--split-size", args.split_size])
            if getattr(args, 'bundle_min', DEFAULT_BUNDLE_MIN) != DEFAULT_BUNDLE_MIN: child_flags.extend(["--bundle-min", str(args.bundle_min)])
            if getattr(args, 'verbose', False): child_flags.append("-v")
            if getattr(args, 'no_multipart', False): child_flags.append("--no-multipart")
            if getattr(args, 'no_resume', False): child_flags.append("--no-resume")
            if getattr(args, 'multipart', False): child_flags.append("--multipart")
            if getattr(args, 'chunk_size', None): child_flags.extend(["--chunk-size", str(args.chunk_size)])
            if getattr(args, 'multipart_threshold', DEFAULT_MULTIPART_THRESHOLD_MB) != DEFAULT_MULTIPART_THRESHOLD_MB: child_flags.extend(["--multipart-threshold", str(args.multipart_threshold)])
            if getattr(args, 'multipart_concurrency', DEFAULT_MULTIPART_CONCURRENCY) != DEFAULT_MULTIPART_CONCURRENCY: child_flags.extend(["--multipart-concurrency", str(args.multipart_concurrency)])
            if getattr(args, 'max_inflight', DEFAULT_MAX_INFLIGHT) != DEFAULT_MAX_INFLIGHT: child_flags.extend(["--max-inflight", str(args.max_inflight)])
            if getattr(args, 'max_rpm', DEFAULT_MAX_RPM) != DEFAULT_MAX_RPM: child_flags.extend(["--max-rpm", str(args.max_rpm)])
            if getattr(args, 'delete_originals_after_upload', False): child_flags.append("--delete-originals-after-upload")
            if getattr(args, 'verify_timeout', 60) != 60: child_flags.extend(["--verify-timeout", str(args.verify_timeout)])
            if not getattr(args, 'use_ia_library', True): child_flags.append("--use-s3-put")
            
            if not getattr(args, 'batch_prompt', False):
                child_flags.append("--force-defaults")
            
            import subprocess
            success_count = 0
            for i, d in enumerate(subdirs):
                print(f"\n{'='*60}")
                print(f"BATCH {i+1}/{len(subdirs)}: Processing '{d.name}'")
                print(f"{'='*60}")
                
                metadata_prefills = load_metadata_prefills(d)
                ident = metadata_prefills.get("identifier") if metadata_prefills else None
                if not ident:
                    ident = sanitize_identifier(d.name)
                    
                cmd = [sys.executable, sys.argv[0]] + child_flags + [str(d), ident]
                try:
                    res = subprocess.run(cmd)
                except KeyboardInterrupt:
                    shutdown_event.set()

                if shutdown_event.is_set():
                    print("\nBatch processing aborted by user.")
                    break

                if res.returncode == 0:
                    success_count += 1
                    
            print(f"\n=== BATCH COMPLETE: {success_count}/{len(subdirs)} successful ===")
            sys.exit(0 if success_count == len(subdirs) else 1)

        # --- v6.39: --reset-state ---
        if args.reset_state:
            count = 0
            for p in folder_path.rglob('*.iaupload.json'):
                try:
                    p.unlink()
                    print(f'  removed: {p}')
                    count += 1
                except Exception as e:
                    print(f'  failed to remove {p}: {e}')
            print(f'\nRemoved {count} state file(s). Exiting.')
            sys.exit(0)

        # --- ZIP FILES BEFORE UPLOAD (if -z flag) ---
        if args.zip:
            if iazip_process is None:
                print("Error: iazip.py not found in the same directory. Cannot use -z flag.")
                sys.exit(1)
            print("\n--- Running iazip packaging before upload (keep originals, all types) ---")
            iazip_process(str(folder_path), move_mode=False, delete_mode=False)

        # Extract suggested date and period from folder name early
        date_info = extract_date_from_string(folder_path.name)
        suggested_date = date_info["date"]
        suggested_period = date_info["period"]

        # Default to today if no date found
        if not suggested_date:
            suggested_date = datetime.date.today().strftime("%Y-%m-%d")
        if not suggested_period:
            suggested_period = datetime.date.today().strftime("%Y")

        # Load metadata prefills early to get identifier suggestion
        metadata_prefills = load_metadata_prefills(folder_path)

        if not identifier:
            # Suggest from metadata file first, then folder name
            default_id = (
                metadata_prefills.get("identifier") if metadata_prefills else None
            )
            if not default_id:
                default_id = Path(folder_path_str).name if folder_path_str else None
            identifier = get_input("Identifier", required=True, default=default_id)

        # Store the suggested title before sanitizing the identifier
        title_suggestion = identifier

        # Sanitize identifier to ensure IA-accepted bucket name
        sanitized_identifier = sanitize_identifier(identifier)
        if sanitized_identifier != identifier:
            print(f"Sanitized identifier: {sanitized_identifier}")
            identifier = sanitized_identifier

        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{4,100}", identifier):
            print("Error: Identifier is still invalid after sanitization.")
            print(
                "Please provide a valid identifier matching: ^[A-Za-z0-9][A-Za-z0-9_.-]{4,100}$"
            )
            sys.exit(1)

        folder_path = Path(folder_path_str)

        # --- PRE-UPLOAD FIXES ---
        handle_dji_lrf(folder_path, auto_confirm=args.fix_lrf)

        # --- v6.48 PHASE 0: bundle small files + split large files ---
        if not args.no_zip:
            print("\n--- PHASE 0a: Bundling small files ---")
            try:
                dirs = set()
                for f in folder_path.rglob("*"):
                    if f.is_file():
                        dirs.add(f.parent)
                made_total = 0
                for d in sorted(dirs):
                    created = bundle_dir(d, min_files=args.bundle_min)
                    for bundle_path, srcs in created:
                        rel = bundle_path.relative_to(folder_path)
                        print(f"  [bundle] {rel}  ({len(srcs)} files)")
                        made_total += 1
                if made_total == 0:
                    print("  (no new bundles needed)")
                else:
                    print(f"  Created {made_total} bundle(s).")
            except Exception as e_b:
                print(f"  Bundling error (continuing): {e_b}")

        try:
            _split_size_mb = parse_size_mb(args.split_size)
        except Exception as e_sp:
            print(f"WARNING: could not parse --split-size "
                  f"{args.split_size!r}: {e_sp}")
            _split_size_mb = 0

        if args.split and _split_size_mb > 0:
            sevenzip = _find_7z()
            if sevenzip is None:
                print(f"\n--- PHASE 0b: Splitting skipped "
                      f"(7z not found on PATH) ---")
            else:
                print(f"\n--- PHASE 0b: Splitting files > "
                      f"{_split_size_mb} MB ---")
                threshold_bytes = _split_size_mb * 1024 * 1024
                made_total = 0
                try:
                    for f in folder_path.rglob("*"):
                        if not f.is_file():
                            continue
                        if f.name.endswith(".iaupload.json") or \
                           f.name.endswith(".iaupload.json.tmp"):
                            continue
                        if f.name.endswith(".zip.meta.json"):
                            continue
                        if re.search(r"\.zip\.\d+$", f.name):
                            continue
                        if f.suffix.lower() == ".zip":
                            continue
                        try:
                            if f.stat().st_size < threshold_bytes:
                                continue
                        except Exception:
                            continue
                        if has_valid_split(f):
                            continue
                        try:
                            parts = do_split(f, _split_size_mb)
                            rel = f.relative_to(folder_path)
                            print(f"  [split] {rel} -> {len(parts)} parts")
                            made_total += 1
                        except Exception as e_sp2:
                            print(f"  [split] FAILED for "
                                  f"{f.relative_to(folder_path)}: {e_sp2}")
                except Exception as e_s:
                    print(f"  Splitting error (continuing): {e_s}")
                if made_total == 0:
                    print("  (no new splits needed)")
                else:
                    print(f"  Split {made_total} file(s).")

        # 2a. v6.56: startup account-quota probe.
        # Send a lightweight HEAD to the S3 endpoint before doing any
        # real work. If the account is over quota, exit immediately
        # instead of running the scan and then failing every upload.
        if _MULTIPART_ENABLED or not args.use_ia_library:
            try:
                _probe_ak = os.environ.get("IAS3_ACCESS_KEY")
                _probe_sk = os.environ.get("IAS3_SECRET_KEY")
                if not _probe_ak:
                    _probe_ak = getattr(session, "access_key", None)
                if not _probe_sk:
                    _probe_sk = getattr(session, "secret_key", None)
                if _probe_ak and _probe_sk:
                    _probe_client = IAS3Client(_probe_ak, _probe_sk)
                    _probe = _probe_client.request(
                        "HEAD", f"/{identifier}"
                    )
                    if _probe.status_code == 503:
                        _pb = (_probe.text or "").lower()
                        if ("accesskey_tasks_queued" in _pb
                                or "rationed" in _pb):
                            _note_account_quota()
                            sys.exit(2)
            except SystemExit:
                raise
            except Exception as _probe_err:
                vlog(f"  startup probe skipped: {_probe_err}")

        # 2. Remote Check
        print(f"\nChecking '{identifier}'...")
        try:
            with _inflight_slot():
                item = get_item(
                    identifier,
                    archive_session=session,
                    request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)}
                )
        except Exception as e:
            print(f"\n[!] Network Error while checking item: {e}")
            print("Archive.org's API is currently slow or unavailable. Please try again in a few minutes.")
            sys.exit(1)
            
        metadata = {}
        is_new_item = False
        account_collections = get_account_collections(session)

        if item.exists:
            if args.metadata:
                if get_input("Update metadata? (y/n)", default="n").lower() == "y":
                    metadata = collect_metadata(
                        title_suggestion,
                        prefills=metadata_prefills,
                        account_collections=account_collections,
                        suggested_date=suggested_date,
                        suggested_period=suggested_period,
                    )
        else:
            print(f"  > New item detected.")
            is_new_item = True
            metadata = collect_metadata(
                title_suggestion,
                prefills=metadata_prefills,
                account_collections=account_collections,
                suggested_date=suggested_date,
                suggested_period=suggested_period,
            )

        # 3. MD5 Scanning Phase
        print("\n" + "=" * 30)
        print(
            "PHASE 1: CONTENT VERIFICATION"
            if args.md5_verify
            else "PHASE 1: PATH VERIFICATION"
        )
        print("=" * 30)

        script_name = Path(sys.argv[0]).name

        # 3a. Index Local Files
        print("Indexing local files...")
        local_file_map = {}
        _dir_name_cache = {}

        def _names_in_dir(d):
            if d not in _dir_name_cache:
                try:
                    _dir_name_cache[d] = set(
                        x.name for x in d.iterdir() if x.is_file()
                    )
                except Exception:
                    _dir_name_cache[d] = set()
            return _dir_name_cache[d]

        for p in folder_path.rglob("*"):
            if not p.is_file():
                continue
            if p.name == script_name:
                continue
            if p.name.endswith(".iaupload.json") or \
               p.name.endswith(".iaupload.json.tmp"):
                continue
            if p.name.endswith(".zip.meta.json"):
                continue
            siblings = _names_in_dir(p.parent)
            if _is_covered_by_bundle(p, siblings):
                continue
            if _is_covered_by_split(p, siblings):
                continue
            rel_path = p.relative_to(folder_path).as_posix()
            safe_rel_path, was_truncated = truncate_path_components(rel_path)
            norm = normalize_path(safe_rel_path)
            local_file_map[norm] = {
                "path": p,
                "rel_path": safe_rel_path,
                "orig_rel_path": rel_path,
                "was_truncated": was_truncated,
            }

        # 3b. Index Remote Files
        remote_map = {}  # normalized_path -> dict with md5 and size
        total_remote_files = 0
        total_remote_originals = 0

        if item.exists:
            print("Fetching remote signatures...")
            total_remote_files = len(item.files)
            for f in item.files:
                if "name" in f and f["name"] != script_name:
                    if f["source"] == "original":  # Only consider original files
                        total_remote_originals += 1
                        norm_path = normalize_path(f["name"])

                        remote_map[norm_path] = {
                            "md5": f.get("md5"),
                            "size": f.get("size"),
                        }

        # 3c. Comparison
        files_to_upload = []
        orphaned_files = []  # List of remote keys to delete

        matched_count = 0
        upload_new_count = 0
        upload_update_count = 0
        skipped_empty_count = 0

        # Detect Uploads
        print(
            f"Scanning {len(local_file_map)} local files against {total_remote_originals} remote originals..."
        )

        with tqdm(
            total=len(local_file_map), desc="Verifying", unit="file", dynamic_ncols=True
        ) as scan_bar:
            for norm_name, info in local_file_map.items():
                if shutdown_event.is_set():
                    break

                local_file = info["path"]
                rel_path = info["rel_path"]
                orig_rel_path = info.get("orig_rel_path", rel_path)
                was_truncated = info.get("was_truncated", False)
                local_size = os.path.getsize(local_file)

                if local_size == 0:
                    skipped_empty_count += 1
                    tqdm.write(f"[SKIP EMPTY]  {orig_rel_path}")
                    scan_bar.update(1)
                    continue

                disp = orig_rel_path if len(orig_rel_path) < 30 else "..." + orig_rel_path[-27:]
                scan_bar.set_description(f"Check: {disp}")

                should_upload = False
                status_msg = ""

                if norm_name not in remote_map:
                    # New path: no MD5 or size needed because there is no same-path remote file to compare against.
                    should_upload = True
                    status_msg = f"[NEW]         {orig_rel_path}"
                    upload_new_count += 1

                else:
                    remote_info = remote_map[norm_name]
                    remote_size = remote_info["size"]
                    remote_md5 = remote_info["md5"]
                    # Fast size check first
                    if remote_size is not None and str(local_size) != str(remote_size):
                        should_upload = True
                        status_msg = f"[UPDATE SIZE] {orig_rel_path}"
                        upload_update_count += 1
                    else:
                        if args.md5_verify:
                            # Sizes match (or remote unknown). Verify content hash if enabled.
                            local_md5 = calculate_md5(local_file)
                            if not local_md5:
                                break

                            if local_md5 != remote_md5:
                                should_upload = True
                                status_msg = f"[UPDATE MD5]  {orig_rel_path}"
                                upload_update_count += 1
                            else:
                                matched_count += 1
                        else:
                            # Path and size match, treat as matched without downloading full file hash.
                            matched_count += 1

                if should_upload:
                    if was_truncated:
                        tqdm.write(
                            f"[TRUNCATED]   '{orig_rel_path}'\n"
                            f"           -> '{rel_path}'"
                        )
                    files_to_upload.append((rel_path, local_file))
                    tqdm.write(status_msg)

                scan_bar.update(1)

            scan_bar.set_description("Scan Complete")

        # Detect Orphans (path-based)
        if item.exists:
            for f in item.files:
                if f["source"] == "original" and f["name"] != script_name:
                    if f["name"].endswith(".iaupload.json") or \
                       f["name"].endswith(".iaupload.json.tmp"):
                        continue
                    if f["name"].endswith(".zip.meta.json"):
                        continue
                    norm = normalize_path(f["name"])

                    if norm in local_file_map:
                        continue

                    orphaned_files.append(f["name"])

        if shutdown_event.is_set():
            print("\nScan Cancelled.")
            print_report()
            sys.exit(0)

        # 4. Confirm Actions
        upload_count = len(files_to_upload)
        orphan_count = len(orphaned_files)
        total_local = len(local_file_map)

        print("\n" + "=" * 40)
        print("SUMMARY")
        print("=" * 40)
        print(f"Total Local Files:       {total_local}")
        print(
            f"Total Remote Originals:  {total_remote_originals} (of {total_remote_files} total items)"
        )
        print("-" * 40)
        matched_label = (
            "Matched (MD5 Exact)" if args.md5_verify else "Matched (Path Exists)"
        )
        print(f"{matched_label}:".ljust(28) + f"{matched_count}")
        print(f"To Upload (New):         {upload_new_count}")
        print(f"To Upload (Update):      {upload_update_count}")
        print(f"Skipped Empty Files:     {skipped_empty_count}")
        print(f"Orphans (To Delete):     {orphan_count}")
        print("=" * 40)

        files_to_delete = []

        if orphan_count > 0:
            if args.orphan_deletion:
                print(f"\n[DELETE] Auto-selecting {orphan_count} files for deletion.")
                files_to_delete = orphaned_files
            else:
                print("\n[!] Orphaned files found on remote (not in local folder).")
                print("    Use -o / --orphan-deletion to remove them.")

        # v6.60: if existing item had metadata updated via -m, apply it now!
        if not is_new_item and metadata:
            print("\nUpdating item metadata...")
            try:
                with _inflight_slot():
                    item.modify_metadata(metadata)
                print("Metadata updated successfully.")
            except Exception as e_md:
                print(f"Warning: Failed to update metadata: {e_md}")
            metadata = None

        if upload_count == 0 and len(files_to_delete) == 0:
            print("\nSync complete. No changes needed.")
            sys.exit(0)

        if upload_count > 0:
            print(f"\nQueued {upload_count} files for upload...")
        if len(files_to_delete) > 0:
            print(f"Queued {len(files_to_delete)} files for DELETION...")

        # 5. Execution Phase
        print("\n" * 1)

        # --- UPLOADS ---
        if upload_count > 0:
            # OPTIMIZATION: Sort by size (Smallest First)
            files_to_upload.sort(key=lambda x: os.path.getsize(x[1]))

            # OPTIMIZATION: Configure Persistent Session (Connection Pooling)
            # Use the official get_session() so we have an ArchiveSession compatible with get_item()
            custom_session = None
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                # Get a proper ArchiveSession
                custom_session = get_session()

                # Configure Retry and Pooling
                retry_strategy = Retry(
                    total=5,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=[
                        "HEAD",
                        "GET",
                        "PUT",
                        "POST",
                        "DELETE",
                        "OPTIONS",
                        "TRACE",
                    ],
                )

                # Pool size must handle all threads + extra for overhead
                adapter = HTTPAdapter(
                    pool_connections=max_workers + 5,
                    pool_maxsize=max_workers + 5,
                    max_retries=retry_strategy,
                )

                # Helper to mount adapter to ArchiveSession which might behave differently than requests.Session
                if hasattr(custom_session, "mount_http_adapter"):
                    # Newer IA library support
                    custom_session.mount_http_adapter("https://", adapter)
                    custom_session.mount_http_adapter("http://", adapter)
                else:
                    # Fallback: hope it inherits from Session or has .mount
                    custom_session.mount("https://", adapter)
                    custom_session.mount("http://", adapter)

                vlog(
                    f"Session configured: pool_connections={max_workers + 5}, pool_maxsize={max_workers + 5}"
                )
                vlog(f"HTTP timeout: connect=30s, read=300s")

            except Exception as e:
                print(f"Warning: Could not configure connection pool: {e}")
                vlog(f"Session config exception: {type(e).__name__}: {e}")
                # Fallback to standard session if mounting fails
                if not custom_session:
                    custom_session = get_session()

            start_index = 0
            main_bar = tqdm(
                total=upload_count,
                desc="Uploading",
                position=0,
                unit="file",
                dynamic_ncols=True,
            )

            if is_new_item:
                # Upload the first (smallest) file to initialize the item
                first_file = files_to_upload[0]
                first_size = os.path.getsize(first_file[1])
                vlog(
                    f"Creating new item with first file: '{first_file[0]}' "
                    f"({first_size:,} bytes) via IA library"
                )

                # v6.60: Always route the first file of a new item through upload_worker.
                # internetarchive.Item.upload attaches all metadata and bucket-creation
                # headers (x-archive-auto-make-bucket), avoiding S3 404 preflight failures.
                success, msg = upload_worker(
                    identifier,
                    first_file,
                    metadata,
                    position=1,
                    session=custom_session,
                )

                main_bar.update(1)
                if not success:
                    main_bar.close()
                    print(f"\nCRITICAL ERROR on creation: {msg}")
                    sys.exit(1)
                vlog(f"Item created successfully, switching to parallel uploads")
                start_index = 1
                metadata = None

            remaining_files = files_to_upload[start_index:]

            if remaining_files:
                slot_queue = queue.Queue()
                for i in range(1, max_workers + 1):
                    slot_queue.put(i)

                def worker_wrapper(f_data):
                    vlog(f"worker_wrapper: waiting for slot for '{f_data[0]}'")
                    slot = slot_queue.get()
                    vlog(f"worker_wrapper: got slot {slot} for '{f_data[0]}'")
                    try:
                        # --- v6.50: S3 single PUT by default ---
                        f_size = os.path.getsize(f_data[1])
                        _S3_PUT_MAX = 5 * 1024 * 1024 * 1024

                        if not _MULTIPART_ENABLED:
                            if args.use_ia_library:
                                return upload_worker(
                                    identifier,
                                    f_data,
                                    None,
                                    position=slot,
                                    session=custom_session,
                                )
                            return s3_upload_worker(
                                identifier,
                                f_data,
                                None,
                                position=slot,
                                session=custom_session,
                            )

                        threshold_bytes = args.multipart_threshold * 1024 * 1024
                        if not args.use_ia_library and threshold_bytes > _S3_PUT_MAX:
                            threshold_bytes = _S3_PUT_MAX

                        use_multipart = f_size >= threshold_bytes

                        if use_multipart:
                            vlog(
                                f"worker_wrapper: routing '{f_data[0]}' "
                                f"({f_size:,} bytes) to multipart_upload_worker"
                            )
                            return multipart_upload_worker(
                                identifier,
                                f_data,
                                None,
                                position=slot,
                                session=custom_session,
                                chunk_size_mb=args.chunk_size,
                                max_concurrency=args.multipart_concurrency,
                            )

                        if args.use_ia_library:
                            vlog(
                                f"worker_wrapper: routing '{f_data[0]}' "
                                f"({f_size:,} bytes) to upload_worker "
                                f"(--use-ia-library)"
                            )
                            return upload_worker(
                                identifier,
                                f_data,
                                None,
                                position=slot,
                                session=custom_session,
                            )

                        vlog(
                            f"worker_wrapper: routing '{f_data[0]}' "
                            f"({f_size:,} bytes) to s3_upload_worker"
                        )
                        return s3_upload_worker(
                            identifier,
                            f_data,
                            None,
                            position=slot,
                            session=custom_session,
                        )
                    finally:
                        vlog(
                            f"worker_wrapper: releasing slot {slot} (was '{f_data[0]}')"
                        )
                        slot_queue.put(slot)

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {
                        executor.submit(worker_wrapper, fdata): fdata
                        for fdata in remaining_files
                    }
                    vlog(f"Submitted {len(future_to_file)} futures to executor")

                    completed_count = 0
                    pending = set(future_to_file.keys())
                    last_liveness = time.time()

                    while pending:
                        if shutdown_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                        # Use timeout so we can periodically report liveness
                        done_batch = set()
                        try:
                            for future in as_completed(pending, timeout=60):
                                done_batch.add(future)
                                completed_count += 1
                                fdata = future_to_file[future]

                                # --- v6.26: read result; surface silent failures ---
                                try:
                                    res = future.result(timeout=0.1)
                                except Exception as e_fut:
                                    tqdm.write(
                                        f"[error] Worker raised for {fdata[0]}: {e_fut}"
                                    )
                                    record_result(
                                        "failed",
                                        f"{fdata[0]} (worker exception: {e_fut})",
                                    )
                                else:
                                    if isinstance(res, tuple) and len(res) == 2:
                                        ok, msg = res
                                        if not ok:
                                            already = (
                                                any(
                                                    fdata[0] in x
                                                    for x in final_results["failed"]
                                                )
                                                or any(
                                                    fdata[0] in x
                                                    for x in final_results["cancelled"]
                                                )
                                            )
                                            if not already:
                                                record_result(
                                                    "failed",
                                                    f"{fdata[0]} ({msg})",
                                                )

                                vlog(
                                    f"Future completed for '{fdata[0]}' "
                                    f"({completed_count}/{len(future_to_file)})"
                                )
                                main_bar.update(1)
                                if time.time() - last_liveness >= 60:
                                    break
                        except TimeoutError:
                            pass

                        pending -= done_batch

                        # Periodic liveness report if anything is still pending
                        if pending and time.time() - last_liveness >= 60:
                            last_liveness = time.time()
                            in_flight = [future_to_file[f][0] for f in pending]
                            _http_n, _rpm = _current_rate_stats()
                            _rate_str = (
                                f"HTTP: {_http_n} in-flight, "
                                f"{_rpm} req in last 60s"
                            )
                            if len(in_flight) <= 5:
                                tqdm.write(
                                    f"  [LIVENESS] {len(in_flight)} file(s) "
                                    f"still in-flight: {in_flight} | "
                                    f"{_rate_str}"
                                )
                            else:
                                tqdm.write(
                                    f"  [LIVENESS] {len(in_flight)} file(s) "
                                    f"still in-flight (showing first 5): "
                                    f"{in_flight[:5]} | {_rate_str}"
                                )

            main_bar.close()

        # --- DELETIONS ---
        _delete_failures = []
        if len(files_to_delete) > 0 and not shutdown_event.is_set():
            print("\nStarting Deletions...")
            # Deletes are fast but we can thread them too

            del_bar = tqdm(
                total=len(files_to_delete),
                desc="Deleting",
                position=0,
                unit="file",
                dynamic_ncols=True,
            )

            # v6.60: internetarchive's File.delete() mounts and then
            # `del`s a retry adapter on the SHARED session; concurrent
            # calls race on that dict (KeyError after a successful delete).
            # Serialize the library call; deletes are quick.
            _delete_lock = threading.Lock()

            def delete_worker(fname):
                if shutdown_event.is_set():
                    return
                try:
                    with _delete_lock, _inflight_slot():
                        item.get_file(fname).delete()
                    vlog(f"Deleted remote orphan: {fname}")
                except Exception as e:
                    _delete_failures.append(fname)
                    tqdm.write(f"Failed to delete {fname}: {e}")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(delete_worker, f) for f in files_to_delete]
                for f in as_completed(futures):
                    del_bar.update(1)

            del_bar.close()

        # Ensure enough newline space based on thread count
        print("\n" * (max_workers + 1))

        if shutdown_event.is_set():
            print("\nOperation Aborted by User.")
        else:
            print("Operation Complete.")
            print(f"URL: https://archive.org/details/{identifier}")

        print_report()

        if _delete_failures:
            print("-" * 60)
            print("ORPHAN DELETION FAILURES:")
            for fname in _delete_failures:
                print(f" [x] {fname}")
            print("-" * 60)

        # --- v6.48: verified cleanup of replaced originals ---
        full_success = (
            not shutdown_event.is_set()
            and len(final_results["failed"]) == 0
            and len(final_results["cancelled"]) == 0
            and len(_delete_failures) == 0
        )

        if full_success and args.delete_originals_after_upload:
            print("\n" + "=" * 60)
            print("VERIFYING ARCHIVES BEFORE DELETING ORIGINALS")
            print("=" * 60)

            plan = build_cleanup_plan(folder_path)

            if not plan:
                print("No bundles or split sets found; nothing to clean up.")
            else:
                all_archives = set()
                for arch_set in plan.values():
                    all_archives.update(arch_set)

                expected = {}
                for rel_archive in all_archives:
                    local_archive = folder_path / rel_archive
                    if not local_archive.exists():
                        continue
                    try:
                        safe_rel, _ = truncate_path_components(rel_archive)
                    except Exception:
                        safe_rel = rel_archive
                    try:
                        expected[safe_rel] = local_archive.stat().st_size
                    except Exception:
                        pass

                print(f"Checking {len(expected)} archive(s) on IA "
                      f"(up to {args.verify_timeout}s)...")

                verified, missing = verify_archives_on_ia(
                    identifier, expected, session,
                    timeout_s=args.verify_timeout,
                )

                if missing:
                    print(f"\n[!] {len(missing)} archive(s) NOT confirmed:")
                    for k, (want, got) in sorted(missing.items()):
                        got_disp = "not listed" if got is None else f"{got} bytes"
                        print(f"    {k}  (expected {want}, IA: {got_disp})")
                    print("\nOriginals NOT deleted. Re-run to retry.")
                else:
                    print(f"\nAll {len(verified)} archive(s) confirmed on IA.")
                    print("--- Deleting replaced originals ---")

                    verified_norm = set()
                    for k in verified.keys():
                        verified_norm.add(normalize_path(k))

                    removed = 0
                    skipped = 0
                    for original, archives in sorted(
                            plan.items(), key=lambda kv: str(kv[0])):
                        if not original.exists():
                            continue
                        all_ok = True
                        for a in archives:
                            try:
                                safe_a, _ = truncate_path_components(a)
                            except Exception:
                                safe_a = a
                            if normalize_path(safe_a) not in verified_norm:
                                all_ok = False
                                break
                        if not all_ok:
                            skipped += 1
                            print(f"  [keep]  "
                                  f"{original.relative_to(folder_path)} "
                                  f"(some archives unverified)")
                            continue
                        try:
                            original.unlink()
                            print(f"  [removed] "
                                  f"{original.relative_to(folder_path)}")
                            removed += 1
                        except Exception as e_del:
                            print(f"  [failed]  "
                                  f"{original.relative_to(folder_path)}: "
                                  f"{e_del}")

                    for meta in folder_path.rglob("*.zip.meta.json"):
                        try:
                            meta.unlink()
                        except Exception:
                            pass

                    print(f"  Removed {removed} original(s), "
                          f"kept {skipped}.")

        # --- POST-UPLOAD: Offer to delete local folder on full success ---
        if full_success:
            answer = "n"
            if getattr(args, "delete_folder_on_success", False):
                answer = "y"
            elif getattr(args, "keep_folder_on_success", False):
                answer = "n"
            else:
                try:
                    answer = (
                        input(
                            f"\nAll files uploaded successfully. Delete local folder '{folder_path}'? (y/n) [n]: "
                        )
                        .strip()
                        .lower()
                    )
                except KeyboardInterrupt:
                    print("\nSkipped deletion.")
                    answer = "n"

            if answer == "y":
                try:
                    safe_rmtree(folder_path)
                    print(f"Deleted: {folder_path}")
                except Exception as e:
                    print(f"Error deleting folder: {e}")
            else:
                if not getattr(args, "keep_folder_on_success", False):
                    print("Local folder kept.")

    except KeyboardInterrupt:
        print("\n\n!!! KEYBOARD INTERRUPT DETECTED !!!")
        print("Stopping threads... (Forcing Exit)")
        shutdown_event.set()
        time.sleep(1)
        print_report()
        os._exit(1)


if __name__ == "__main__":
    main()