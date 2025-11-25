#!/bin/bash
set -euo pipefail

echo "OnStart Configuration running..."

############################################
# 1. Idle time configuration
############################################
IDLE_TIME_VALUE=3600
sudo mkdir -p /etc/sysconfig
echo "IDLE_TIME=$IDLE_TIME_VALUE" | sudo tee /etc/sysconfig/autostop >/dev/null
echo ">>> Set IDLE_TIME=$IDLE_TIME_VALUE"

############################################
# 2. Recreate systemd autostop.service
############################################
sudo tee /etc/systemd/system/autostop.service >/dev/null <<'EOF'
[Unit]
Description=Auto-stop SageMaker notebook when idle
Wants=network-online.target
After=network-online.target sagemaker-jupyter.service

[Service]
Type=simple
User=ec2-user
EnvironmentFile=/etc/sysconfig/autostop
WorkingDirectory=/home/ec2-user/SageMaker/autostop
ExecStart=/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python /home/ec2-user/SageMaker/autostop/autostop.py

# Restart the service ONLY on failure
Restart=on-failure
RestartSec=10

# Prevent systemd from considering timeouts as failures
TimeoutStartSec=300

# Always create an independent process (prevents SSH hang issues)
KillMode=process

StandardOutput=journal
StandardError=journal

EOF

############################################
# 3. Recreate autostop.timer
############################################
sudo tee /etc/systemd/system/autostop.timer >/dev/null <<'EOF'
[Unit]
Description=Run autostop every 10 minutes

[Timer]
OnBootSec=30min
OnUnitActiveSec=10min
Unit=autostop.service

# Persistent makes missed runs (e.g., during reboot) trigger immediately
Persistent=true

[Install]
WantedBy=timers.target
EOF

############################################
# 4. Reload + start timer
############################################

chmod 644 /etc/systemd/system/autostop.service
chmod 644 /etc/systemd/system/autostop.timer

sudo systemctl daemon-reload
sudo systemctl enable autostop.timer
sudo systemctl start autostop.timer

echo ">>> autostop.timer enabled & started"

# ---------- SAFE PACKAGE INSTALLS (pip only) ----------
KERNEL_PYTHON="/home/ec2-user/anaconda3/envs/python3/bin/python"

sudo -u ec2-user -i bash <<EOF
set -e
source /home/ec2-user/.bashrc 2>/dev/null || true

KERNEL_PYTHON="$KERNEL_PYTHON"

echo ">>> Installing packages using: \$KERNEL_PYTHON"

PKGS=(pip s3fs requests pandas redshift_connector polars)

for P in "\${PKGS[@]}"; do
    echo ">>> Installing/upgrading \$P"
    "\$KERNEL_PYTHON" -m pip install --upgrade --no-cache-dir --quiet "\$P" || true
done

echo ">>> Notebook kernel package installation complete"
EOF
