# Review: `log_record()`

```c
// appends one record; called concurrently from many threads
int log_record(const char *path, const char *msg) {
    int fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0644);
    char buf[256];
    int n = sprintf(buf, "[%ld] %s\n", time(NULL), msg);
    write(fd, buf, n);
    close(fd);
    return 0;
}
```

Below is every real bug and unsafe practice, roughly ordered by severity, followed by a corrected version and design recommendations.

---

## Critical bugs

### 1. Buffer overflow: unbounded `sprintf` into a fixed 256-byte stack buffer
`sprintf(buf, "[%ld] %s\n", time(NULL), msg)` copies `msg` with no length limit. The timestamp plus framing consumes up to ~24 bytes (`[`, up to 19–20 digits for a 64-bit `time_t`, `] `, `\n`, NUL), so any `msg` longer than roughly 230 bytes overflows `buf` and smashes the stack. In a server, `msg` frequently contains request data, client-supplied strings, filenames, etc. — this is a classic remotely-triggerable stack buffer overflow (CWE-121), potentially exploitable for code execution, and at minimum a crash/DoS. Fix: `snprintf(buf, sizeof buf, ...)` and handle truncation explicitly (the truncated record should still end in `\n` so it doesn't merge with the next record).

### 2. `open()` return value never checked
If `open` fails (`EACCES`, `ENOENT` for a missing directory, `EMFILE`/`ENFILE` fd exhaustion — very plausible here since every call opens a new fd under high thread concurrency — `ENOSPC`, `EROFS`, `EINTR`, `ELOOP`, ...), `fd` is `-1`. The code then calls `write(-1, ...)` and `close(-1)`, both of which fail with `EBADF`, and the function still returns 0. Every record is silently dropped with no error indication. `write`/`close` on -1 is "only" a reported error, but the silent data loss and the lie of `return 0` are real bugs.

### 3. `write()` return value never checked (errors and short writes)
`write` can:
- **Fail outright**: `ENOSPC`, `EDQUOT`, `EIO`, `EFBIG`/`SIGXFSZ` at `RLIMIT_FSIZE`, `EBADF` (see #2), `EINTR` if a signal arrives before any byte is written and the handler was installed without `SA_RESTART`.
- **Write fewer bytes than requested** (short write): possible on `ENOSPC` mid-write, `RLIMIT_FSIZE`, signal interruption after partial transfer, or if `path` turns out to be something other than a regular file (FIFO, socket, device).

The result is silently lost or *truncated* records — and with concurrent writers, a short write means the tail of this record and another thread's record can end up interleaved, corrupting the log format. Errors must be checked; `EINTR` should be retried. Note that naively looping to finish a short write does **not** restore correctness under concurrency (the continuation lands after other threads' appends), so a short write on a shared append-only log should be treated as an error/corrupted record, not silently patched.

### 4. The function always returns 0
The signature advertises an error code, but every failure path (open, format, write, close) is swallowed and `0` is returned. Callers cannot detect that logging is failing (disk full, permissions, fd exhaustion), which is exactly when you most need to know. Return `-1` with `errno` set (taking care that `close()` doesn't clobber the `errno` from a failed `write`), or a meaningful error code.

---

## Correctness / portability bugs

### 5. `%ld` with `time_t` is undefined behavior on many platforms
`time_t` is an opaque arithmetic type; it is **not** guaranteed to be `long`. On 64-bit Windows (`time_t` is `__int64`, `long` is 32-bit), on 32-bit Linux built with `-D_TIME_BITS=64` (glibc ≥ 2.34), on some BSDs, etc., passing a 64-bit `time_t` through varargs where `%ld` expects a 32-bit `long` is undefined behavior — and also misaligns the following `%s` argument, so `msg` gets read from garbage. Portable fix: cast explicitly, e.g. `(long long)time(NULL)` with `%lld`, or `(intmax_t)` with `%jd`. (Related: on platforms with 32-bit `time_t` this code is also a Y2038 time bomb, but the varargs mismatch is the immediate UB.)

### 6. `sprintf`/`snprintf` can return a negative value
On an output/encoding error `sprintf` returns a negative `int`. The code then calls `write(fd, buf, n)` where `n` is negative; `write`'s `count` parameter is `size_t`, so `-1` becomes `SIZE_MAX` — `write` will attempt a gigantic write from a 256-byte buffer (usually `EFAULT` or `EINVAL`, but it's reading past the buffer either way). Check `n < 0` before using it as a length.

### 7. No NULL/argument validation
`msg == NULL` makes `%s` undefined behavior (glibc happens to print `(null)`, but that's not guaranteed and other libcs crash). `path == NULL` is UB in `open`. A logging function is exactly the place that gets called from error paths with half-initialized state; it should be defensive.

---

## Concurrency issues

### 8. Append atomicity is only *mostly* right — and breaks on NFS
Using `O_APPEND` with a **single `write` per record** is the correct core idea: POSIX guarantees the seek-to-end and write happen atomically, and on local Linux filesystems (ext4, xfs, btrfs — which serialize writes on the inode lock) concurrent appends won't interleave byte-wise. But:
- **NFS does not support atomic `O_APPEND`.** The client emulates it (get size, then write at that offset), so concurrent writers from multiple clients (and historically even multiple processes) race and overwrite/interleave each other's records. If the log can live on NFS, you need `flock()`/`fcntl` record locking around the write.
- POSIX only strictly guarantees non-interleaving for pipes (≤ `PIPE_BUF`); for regular files the "one write = one contiguous record" property is a (near-universal) implementation guarantee on local filesystems, not a portability guarantee. Keep each record in **one** `write` call and document the assumption — never split a record across two `write`s (see #3).
- The invariant "one record = one write" is exactly what the unbounded `sprintf` bug (#1) and the unhandled short write (#3) silently violate.

### 9. Missing `O_CLOEXEC` — fd leaks into child processes (a real race in multithreaded servers)
Every call briefly holds an open fd without `O_CLOEXEC`. In a multithreaded server, if any other thread does `fork()`+`exec()` (spawning a helper, CGI, `popen`, etc.) in the window while this fd is open, the child inherits a writable descriptor to the log file. That's a resource leak and a security issue (an exec'd, possibly less-trusted program can write to / hold open your log, and it defeats log rotation by keeping the old inode alive). You cannot fix this race with a separate `fcntl(F_SETFD)` call — `O_CLOEXEC` at `open` time is the only race-free option.

### 10. Timestamps can appear out of order
`time(NULL)` is captured before the append, and there's no ordering between threads' format-then-write sequences, so records can land in the file with non-monotonic timestamps. Usually acceptable for logs, but worth knowing; also `time()` gives only 1-second granularity, which is coarse for a busy server (consider `clock_gettime(CLOCK_REALTIME)`).

---

## Security issues (beyond the overflow)

### 11. TOCTOU / symlink attack via `O_CREAT` without `O_EXCL`/`O_NOFOLLOW`
The path is re-resolved on **every call**. If any component of `path` is in a directory writable by another user (e.g., `/tmp`, a shared spool dir), an attacker can plant a symlink at `path` between calls and the server — often running with elevated privileges — will happily append log data to an arbitrary file (`/etc/passwd`-style clobbering, CWE-59/CWE-367). Mitigations: open the file once at startup, use `O_NOFOLLOW` (and consider `O_EXCL` at creation time), keep logs in a directory only the server can write, or use `openat` with a pre-opened directory fd.

### 12. Log injection via unsanitized `msg`
`msg` is written verbatim. If it contains attacker-controlled data with embedded `\n` (or terminal escape sequences), an attacker can forge additional log lines with fake timestamps, corrupt line-oriented log parsers, or inject ANSI escapes that attack anyone who `cat`s the log (CWE-117). Escape or strip control characters/newlines.

### 13. File permissions
`0644` makes the log world-readable (modulo umask). Server logs routinely contain IPs, usernames, tokens, session IDs, internal paths. `0600`/`0640` is usually more appropriate. Also note the mode is only applied at creation and is filtered by the process umask — if the caller expects exactly `0644`, that's not guaranteed.

---

## Robustness / design problems

### 14. `close()` return value ignored, and `errno` clobbering
On NFS and some filesystems, deferred write errors are only reported at `close()` (`EIO`, `ENOSPC`, `EDQUOT`). Ignoring it loses the last chance to detect that the record didn't make it. Also, once you *do* check `write`, an unconditional `close` afterwards can clobber `errno` before the caller sees it — save/restore `errno` around cleanup. (Do **not** retry `close` on `EINTR` on Linux — the fd is closed anyway, and retrying can close another thread's freshly-allocated fd, a nasty multithreaded bug.)

### 15. `EINTR` not handled on `open`/`write`
If the process installs any signal handler without `SA_RESTART`, both `open` and `write` can fail with `EINTR`. A logging primitive should retry these.

### 16. open/write/close on every record is a performance and reliability anti-pattern
Three-plus syscalls, a full path resolution, dentry/inode lookups, and an fd allocation *per log line*, from many threads concurrently:
- Serious throughput cost and contention on the fd table and path lookup.
- Under load, transient `EMFILE`/`ENFILE` (see #2) — the logger itself competes with the server's sockets for descriptors.
- Amplifies the TOCTOU window (#11).

The standard design is to open the log fd once (with `O_CLOEXEC`), keep it for the process lifetime, and just `write` per record; handle log rotation via a reopen-on-signal (SIGHUP) path or by re-`stat`ing periodically. (The one virtue of reopening every time — it cooperates with external rotation — is better achieved deliberately.)

### 17. No durability guarantee
There is no `fsync`/`fdatasync`, so records sit in the page cache and can be lost on power failure/crash. For most logs that's an acceptable, deliberate trade-off — but for an audit log it isn't. Whichever is intended should be a documented decision, not an accident. (Per-record `fsync` is very slow; batch or make it configurable.)

### 18. Truncation policy is undefined
Even after switching to `snprintf`, you must decide what happens to over-long messages: truncate (and still terminate the record with `\n` so the log stays line-parseable), split, or allocate dynamically. The current code has no policy — it just corrupts the stack.

### 19. Not async-signal-safe
Minor but worth stating: `sprintf` is not async-signal-safe (and `snprintf` isn't guaranteed to be either), so this function must not be called from signal handlers despite "logging" being a tempting thing to do there.

---

## Corrected version

```c
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

/* Appends one record. Thread-safe via O_APPEND + single write per record.
 * Returns 0 on success, -1 on failure with errno set.
 * NOTE: atomic append is NOT guaranteed on NFS; use file locking there. */
int log_record(const char *path, const char *msg) {
    if (path == NULL || msg == NULL) {
        errno = EINVAL;
        return -1;
    }

    char buf[1024];
    int n = snprintf(buf, sizeof buf, "[%lld] %s\n",
                     (long long)time(NULL), msg);   /* portable time_t */
    if (n < 0) {
        errno = EIO;
        return -1;
    }
    if ((size_t)n >= sizeof buf) {          /* truncated: keep record framed */
        n = (int)(sizeof buf - 1);
        buf[n - 1] = '\n';
    }

    int fd;
    do {
        fd = open(path,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    } while (fd < 0 && errno == EINTR);
    if (fd < 0)
        return -1;

    /* Exactly one write per record: this is the atomicity invariant. */
    ssize_t w;
    do {
        w = write(fd, buf, (size_t)n);
    } while (w < 0 && errno == EINTR);

    int rc = 0;
    int saved_errno = 0;
    if (w < 0) {
        rc = -1;
        saved_errno = errno;
    } else if (w != n) {
        /* Partial write on a shared append log: record is corrupted;
         * do NOT "finish" it with a second write. */
        rc = -1;
        saved_errno = EIO;
    }

    if (close(fd) < 0 && rc == 0) {         /* surfaces deferred I/O errors */
        rc = -1;
        saved_errno = errno;
    }
    if (rc < 0)
        errno = saved_errno;
    return rc;
}
```

Remaining caveats even in the fixed version, which argue for a different design:
- Open the fd **once at startup** and reuse it (fixes per-call cost, fd exhaustion, and shrinks the symlink window to startup, where you can validate with `fstat`); reopen on SIGHUP for rotation.
- Sanitize `msg` (strip/escape `\n` and control characters) before writing to prevent log injection.
- If the log may live on NFS or the "single write is contiguous" assumption can't be relied on, wrap the write in `flock(fd, LOCK_EX)` / `LOCK_UN`.
- Decide and document the durability policy (`fdatasync` or not).
- Consider `clock_gettime` for sub-second timestamps, and note timestamps are not guaranteed monotonic across records.

## Summary table

| # | Issue | Class | Severity |
|---|-------|-------|----------|
| 1 | Unbounded `sprintf` → stack buffer overflow on long `msg` | Memory safety / RCE | Critical |
| 2 | `open` failure unchecked → `write(-1)`, silent drop | Error handling | Critical |
| 3 | `write` errors and short writes unchecked → silent loss/corruption | Error handling | Critical |
| 4 | Always returns 0 — failures invisible to callers | API contract | High |
| 5 | `%ld` vs `time_t` — UB on 64-bit `time_t`/32-bit `long` platforms | Portability / UB | High |
| 6 | Negative `sprintf` return used as `write` length (`size_t` wrap) | UB / overread | High |
| 7 | No NULL checks on `path`/`msg` | Defensive coding | Medium |
| 8 | Append atomicity not guaranteed on NFS; POSIX caveat for regular files | Concurrency | High (if NFS) |
| 9 | Missing `O_CLOEXEC` — fd leaks across fork/exec race | Security / resource leak | Medium |
| 10 | Non-monotonic, 1-second-granularity timestamps | Correctness (minor) | Low |
| 11 | Per-call path re-resolution, `O_CREAT` w/o `O_NOFOLLOW` → symlink/TOCTOU | Security | High (shared dirs) |
| 12 | Unsanitized `msg` → log injection / escape-sequence injection | Security | Medium |
| 13 | `0644` world-readable log; mode subject to umask | Security / hygiene | Low–Medium |
| 14 | `close` unchecked; `errno` clobbering; don't retry `close` on EINTR | Error handling | Medium |
| 15 | No `EINTR` retry on `open`/`write` | Robustness | Medium |
| 16 | open/close per record: syscall cost, fd exhaustion under load | Design / performance | Medium |
| 17 | No fsync — undurable by accident, not by decision | Design | Situational |
| 18 | No truncation policy for over-long records | Design | Medium |
| 19 | Not async-signal-safe (must not be called from handlers) | Documentation | Low |
