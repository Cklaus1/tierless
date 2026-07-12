# Systems code review

Review this C function that appends a record to a log file, used by a multithreaded server. Find
every real bug and unsafe practice.

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
