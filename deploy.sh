#!/bin/bash
# Deploy script for Raspberry Pi observatory nodes
# Sets up fresh Pi with KStars/EKOS, INDI drivers, and automation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 {test|deploy} [user@host]"
    echo "  test   - Check deployment prerequisites"
    echo "  deploy - Perform full node deployment"
    echo "Example: $0 test pi@192.168.1.100"
}

check_ssh() {
    local target="$1"
    echo "Testing SSH connection to $target..."
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$target" exit 2>/dev/null; then
        echo "ERROR: Cannot connect via SSH to $target"
        echo "Ensure SSH is enabled and key-based auth is configured"
        return 1
    fi
    echo "SSH connection OK"
}

check_target_system() {
    local target="$1"
    echo "Checking target system..."
    
    # Check if target is Raspberry Pi OS
    if ! ssh "$target" "grep -q 'Raspberry Pi' /proc/device-tree/model 2>/dev/null || grep -q raspbian /etc/os-release"; then
        echo "WARNING: Target may not be Raspberry Pi OS"
    fi
    
    # Check available space
    local available=$(ssh "$target" "df / | tail -1 | awk '{print \$4}'")
    if [ "$available" -lt 2000000 ]; then
        echo "WARNING: Less than 2GB free space available"
    fi
    
    # Check internet connectivity
    if ! ssh "$target" "ping -c1 8.8.8.8 >/dev/null 2>&1"; then
        echo "ERROR: Target has no internet connectivity"
        return 1
    fi
    
    echo "Target system checks passed"
}

install_base_packages() {
    local target="$1"
    echo "Installing base packages..."
    
    ssh "$target" "sudo apt update"
    ssh "$target" "sudo apt install -y \
        kstars-bleeding \
        indi-full \
        phd2 \
        siril \
        python3-pip \
        python3-yaml \
        python3-astropy \
        gphoto2 \
        libgphoto2-dev \
        openssh-server \
        rsync \
        htop \
        screen"
}

configure_indi() {
    local target="$1"
    echo "Configuring INDI server..."
    
    # Create INDI startup script
    ssh "$target" "cat > ~/start_indi.sh << 'EOF'
#!/bin/bash
# Start INDI server with common drivers
indiserver -v \
    indi_simulator_telescope \
    indi_simulator_ccd \
    indi_canon_ccd \
    indi_gphoto_ccd \
    indi_playerone_ccd \
    indi_asi_ccd
EOF"
    
    ssh "$target" "chmod +x ~/start_indi.sh"
}

setup_automation() {
    local target="$1"
    echo "Setting up automation scripts..."
    
    # Create capture directory structure
    ssh "$target" "mkdir -p ~/observatory/{config,data,logs,scripts}"
    
    # Copy basic automation script
    ssh "$target" "cat > ~/observatory/scripts/capture.py << 'EOF'
#!/usr/bin/env python3
# Basic capture automation script
import os
import sys
import yaml
import time
from datetime import datetime

def load_schedule(schedule_file):
    with open(schedule_file) as f:
        return yaml.safe_load(f)

def capture_target(target):
    print(f\"Starting capture: {target['name']}\")
    # Placeholder for actual KStars/EKOS integration
    time.sleep(2)  # Simulate capture
    print(f\"Capture complete: {target['name']}\")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(\"Usage: capture.py schedule.yaml\")
        sys.exit(1)
    
    schedule = load_schedule(sys.argv[1])
    for target in schedule.get('targets', []):
        capture_target(target)
EOF"
    
    ssh "$target" "chmod +x ~/observatory/scripts/capture.py"
}

test_deployment() {
    local target="$1"
    echo "Running deployment tests..."
    
    check_ssh "$target" || return 1
    check_target_system "$target" || return 1
    
    # Test package availability
    echo "Checking package availability..."
    if ! ssh "$target" "apt-cache show kstars-bleeding >/dev/null 2>&1"; then
        echo "ERROR: KStars packages not available"
        echo "Consider adding astronomy repositories or using different package names"
        return 1
    fi
    
    echo "All tests passed - deployment ready"
}

deploy_node() {
    local target="$1"
    echo "Deploying to $target..."
    
    check_ssh "$target" || return 1
    install_base_packages "$target"
    configure_indi "$target"
    setup_automation "$target"
    
    echo "Deployment complete"
    echo "Node accessible at: ssh $target"
    echo "Start INDI: ssh $target '~/start_indi.sh'"
    echo "Capture: ssh $target '~/observatory/scripts/capture.py schedule.yaml'"
}

# Main execution
case "${1:-}" in
    "test")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required for test"
            show_usage
            exit 1
        fi
        test_deployment "$2"
        ;;
    "deploy")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required for deploy"
            show_usage
            exit 1
        fi
        deploy_node "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
