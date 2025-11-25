#!/bin/bash
set -euo pipefail

echo "OnCreate Configuration running..."

# ---------- paths ----------
DIR="/home/ec2-user/SageMaker/autostop"
PYTHON_BIN="/usr/bin/python3"

mkdir -p "$DIR"
chown -R ec2-user:ec2-user "$DIR"

# ---------- WRITE autostop.py (absolute execution-only inactivity rule) ----------
cat > "$DIR/autostop.py" << 'PY'
#!/usr/bin/env python3
# autostop.py — automatically stops the SageMaker Notebook instance when idle
# Works on modern JupyterLab versions (v3/v4) using /api/sessions activity only

import boto3
import os, json, time, ssl
import urllib.request
from datetime import datetime, timezone, timedelta


LOG_FILE = "/home/ec2-user/SageMaker/autostop/auto.log"

def log(msg):
    IST = timezone(timedelta(hours=5, minutes=30))
    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} {msg}\n")

# Idle time from environment variable (default 2hrs)
IDLE_SECONDS = int(os.environ.get("IDLE_TIME",7200))

# Disable SSL verification (SageMaker uses self-signed cert)
CTX = ssl._create_unverified_context()

# ---------------------------------------------------------------------------
# Helper: call Jupyter API safely
# ---------------------------------------------------------------------------
def jupyter_api(path):
    try:
        with urllib.request.urlopen(f"https://localhost:8443{path}", context=CTX, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log(f"[error calling {path}] {e}")
        return None

def get_notebook_name():
    with open("/opt/ml/metadata/resource-metadata.json", "r") as f:
        meta = json.load(f)
    return meta["ResourceName"]

def timestamp_parse(last_activity_ts):

    if last_activity_ts:

        # strip timezone/millis
        clean = last_activity_ts.replace("Z", "")
        if "." in clean:
            clean = clean.split(".")[0]
        if "+" in clean:
            clean = clean.split("+")[0]

        try:
            last_dt = datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            age = time.time() - last_dt.timestamp()
            return age
        except Exception as e:
            log(f"[terminal timestamp error] {e}")
            return IDLE_SECONDS + 1
    else:
        return IDLE_SECONDS + 1


# ---------------------------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------------------------
def main():

    active_terminals = []
    active_sessions = []

    # 1. Notebook kernels / sessions
    sessions = jupyter_api("/api/sessions") or []
    for s in sessions:
        last_activity_ts = s.get('kernel').get("last_activity") if s.get('kernel') else None
        activity = timestamp_parse(last_activity_ts)
        if activity < IDLE_SECONDS:
            active_sessions.append(s)
            log(f"notebook kernels active: {len(sessions)}")
            log(f"keep-alive: Session activity detected {int(activity)}s < threshold {IDLE_SECONDS}s")
            return   # first active session is enough
    # 2. Terminal activity check (use last_activity)
    else:   # only if there are no active sessions then only check for terminals
        terminals = jupyter_api("/api/terminals") or []
        for t in terminals:
            last = t.get("last_activity")
            activity = timestamp_parse(last)
            if activity < IDLE_SECONDS:
                active_terminals.append(t)
                log(f"terminal kernels active: {len(terminals)}")
                log(f"keep-alive: Terminal activity detected {int(activity)}s < threshold {IDLE_SECONDS}s")
                return

    # 3. No real activity
    if sessions == [] and terminals == []:
        log("[info] no sessions or terminals → treating as idle → shutting down instance now.")
    elif active_terminals and active_sessions:
        log("[info] There are sessions or terminals, but all are idle → shutting down instance now.")

    try:
        notebook_name = get_notebook_name()
        sm_client = boto3.client("sagemaker")
        sm_client.stop_notebook_instance(NotebookInstanceName=notebook_name)
        # os.system("sudo shutdown -h now")   # shutdown only the session
    except Exception as e:
        log(str(e))

    return


if __name__ == "__main__":
    main()
PY

chmod +x "$DIR/autostop.py"
chown ec2-user:ec2-user "$DIR/autostop.py"

echo ">>> OnCreate complete: autostop.py and systemd timer installed (timer enabled)."
