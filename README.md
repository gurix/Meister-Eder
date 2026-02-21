# Meister-Eder

## Running the Email Agent

The email agent is a plain script invoked periodically via cron — no long-running daemon needed.

### Scheduling with cron

```cron
*/5 * * * * flock -n /tmp/meister-eder-email.lock python /path/to/check_email.py
```

`flock -n` acquires an exclusive lock before running the script. If a previous run is still in progress when the next cron tick fires, the new invocation exits immediately (non-blocking). The lock is released automatically by the kernel when the process ends — even on crash — so stuck locks are not a concern.

Adjust `*/5` to whatever polling interval makes sense (e.g. `*/2` for every 2 minutes).