# Nonblocking GDB

Load this reference for long-running, conditional, or repeated GDB observations where a foreground debugger would block the current task.

Adapted from the MIT-licensed betab0t GDB skill; no upstream shell helper is bundled because it is POSIX-specific and can leave processes/pipes behind when misused.

## Session design

Use the execution environment's persistent PTY/session mechanism when available. Keep a dedicated command channel and bounded log, record debugger/inferior PIDs separately, disable pagination, and sample output between commands. For running inferiors, interrupt, wait for a confirmed prompt, issue the query/update, then resume.

Prefer `dprintf` or tracepoints for low-frequency observation that automatically continues. Bound hit counts and log size; avoid hot-loop tracing. Before applying a condition to a monotonic value, observe its current value so the condition remains reachable.

## Safety

Require a precise executable or authorized PID. Starting under GDB and attaching to a process are distinct permissions. Do not change ptrace/system policy automatically. Interactive commands that wait for more input are unsuitable unless the session can supply and verify every prompt.

Cleanup order matters: stop/quit the debugger and inferior as authorized, confirm process exit, then remove session-local pipes/log metadata. Never delete the command channel first and assume cleanup succeeded.

The deliverable records tracepoint/query, address resolution, hit evidence, log bounds, cleanup state, and unanswered questions.
