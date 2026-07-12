# GRADER checklist — systems-programming (13 items; planted bugs)

1 sprintf into fixed buf[256] — BUFFER OVERFLOW on long msg (use snprintf): r"buffer overflow|sprintf.*(overflow|unsafe|snprintf)|snprintf|buf\[256\].*(overflow|small)|bound.*(buf|sprintf)|overrun|fixed.*buffer.*overflow"
2 open() return NOT CHECKED — fd could be -1: r"open.*(check|return|-1|fail|error)|fd.*(-1|check|error)|unchecked open|return value.*open|if.*fd.*<.*0"
3 write() return NOT CHECKED — short write / partial write / error ignored: r"write.*(return|check|short|partial|-1|error)|short write|partial write|unchecked write|write.*(may|can).*(fail|short)|loop.*write"
4 write() not looped — a single write may write fewer bytes than n: r"loop.*write|write.*(loop|until|remaining)|partial.*(loop|retry)|write in a loop|writev"
5 fd LEAK on error path (but here close always runs — the risk is if write logic added returns): r"fd leak|file descriptor leak|leak.*(fd|descriptor)|close.*(missing|error path)|resource leak"
6 O_APPEND concurrency — actually append IS atomic under a limit; but sprintf race / interleave beyond PIPE_BUF: r"O_APPEND|atomic.*(append|write)|PIPE_BUF|interleav|concurrent.*write|4096|atomicity.*(write|append)|record.*(interleav|torn)"
7 time(NULL) not thread-safe? (it is) but %ld on time_t is not portable / cast: r"time_t.*(cast|portab|%ld|long)|%ld.*time|portab.*time|time_t.*(size|type)"
8 no fsync — data not durable on crash: r"fsync|fdatasync|durab|flush|not.*(persist|disk)|crash.*(lose|data)|buffer.*(not|flush)"
9 opening the file on EVERY call — perf, and fd churn (should keep open or use a logger): r"every call.*(open|fd)|open.*(each|every|per).*(call|record)|churn|keep.*(open|fd)|reopen|expensive.*open"
10 msg is not sanitized — embedded newline injects a fake log line (log injection): r"log injection|newline.*(inject|msg)|sanitiz.*(msg|input)|inject.*(log|line)|\\n.*(msg|inject)|forged log"
11 EINTR — open/write can be interrupted by a signal, need retry: r"eintr|interrupted.*(signal|syscall)|retry.*(eintr|signal)|signal.*(interrupt|retry)"
12 error handling / the function always returns 0 — swallows all errors: r"always returns? 0|return.*0.*(swallow|ignore|useless)|no error.*(return|propagat)|error.*(swallow|ignore)|return value.*(useless|meaningless)"
13 truncation: sprintf n could exceed 256 (return value used without checking truncation): r"truncat|n.*(exceed|>.*256|larger)|sprintf.*(return|truncat)|msg.*(long|truncat)|exceed.*(buf|256)"

## discriminating (require reading C carefully): #1 sprintf overflow, #2 unchecked open, #3/#4 write
## return + loop, #10 log injection via newline. A shallow answer says "add error handling and locks".
