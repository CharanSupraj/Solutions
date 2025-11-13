#!/usr/bin/env python3
"""
Auto-stop script for SageMaker Notebook Instances
Stops the instance if Jupyter kernels have been idle for a given number of seconds.
No describe_notebook_instance() call needed.
"""

import os
import sys
import getopt
import json
import time as time_mod
from datetime import datetime
import boto3
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Usage info ---
USAGE = """Usage:
python autostop.py --time <seconds>
"""

HELP = """Options:
-t, --time <seconds>         Idle threshold in seconds before shutdown.
"""

# --- Parse args ---
idle_threshold = None
port = "8443"    # Jupyter server port (default: 8443)

try:
    opts, _ = getopt.getopt(sys.argv[1:], "ht:p:c", ["help", "time="])
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(HELP)
            sys.exit(0)
        elif opt in ("-t", "--time"):
            idle_threshold = int(arg)
except getopt.GetoptError:
    print(USAGE)
    sys.exit(1)

if not idle_threshold:
    print("Error: Missing required parameter --time")
    sys.exit(2)

# --- Helpers ---
def get_notebook_name():
    """Read the notebook instance name from local metadata."""
    meta_path = "/opt/ml/metadata/resource-metadata.json"
    with open(meta_path, "r") as f:
        meta = json.load(f)
    return meta["ResourceName"]

def parse_time(ts):
    """Parse Jupyter's timestamp string into datetime."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fz")

def get_kernels():
    """Fetch kernel session info from local Jupyter API."""
    try:
        r = requests.get(f"https://localhost:{port}/api/sessions", verify=False, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ Could not fetch Jupyter sessions: {e}")
        return []

def get_latest_activity(kernels):
    """Return datetime of most recent execution or connection activity."""
    if not kernels:
        return None
    timestamps = []
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fz")
    for k in kernels:
        kernel = k.get("kernel", {})
        last = kernel.get("last_activity", now_str) # gets the time when the cell was last executed.
        # If kernel busy, treat as active
        if kernel.get("execution_state") != "idle":
            last = now_str
        # If connections is not ignored, treat as active
        if kernel.get("connections", 0) > 0:
            last = now_str
        timestamps.append(parse_time(last))
    return max(timestamps)

def main():
    notebook_name = get_notebook_name()
    sm_client = boto3.client("sagemaker")

    kernels = get_kernels()
    last_activity = get_latest_activity(kernels)

    if not last_activity:
        print("⚠️ No active kernels found — treating as idle.")
        should_shutdown = True
    else:
        idle_for = (datetime.utcnow() - last_activity).total_seconds()
        print(f"🕒 Last activity: {last_activity} UTC ({idle_for:.0f} seconds ago)")
        should_shutdown = idle_for > idle_threshold

    if should_shutdown:
        print(f"💤 Notebook '{notebook_name}' idle for > {idle_threshold}s. Shutting down.")
        try:
            sm_client.stop_notebook_instance(NotebookInstanceName=notebook_name)
        except Exception as e:
            print(f"⚠️ Failed to stop instance: {e}")
    else:
        print(f"✅ Notebook '{notebook_name}' still active. No action taken.")

if __name__ == "__main__":
    main()