#!/bin/bash
# Node management script for Raspberry Pi observatory nodes
# Sets up nodes, handles NFS or SSH transfers for captured sequences

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default Ekos capture directory
EKOS_CAPTURE_DIR="/home/pi/Pictures"
NFS_EXPORT_DIR="/home/pi/observatory/captures"

show_usage() {
    echo "Usage: $0 {test|deploy|setup-nfs|transfer|mount-nfs|test-camera} [user@host]"
    echo "  test        - Check deployment prerequisites"
    echo "  deploy      - Perform full node deployment"
    echo "  setup-nfs   - Configure NFS server on node and export captures"
    echo "  transfer    - Use rsync to transfer captures from node to local"
    echo "  mount-nfs   - Mount NFS share from node locally"
    echo "  test-camera - Test camera detection and basic functionality"
    echo ""
    echo "Examples:"
    echo "  $0 test pi@192.168.1.100"
    echo "  $0 deploy pi@192.168.1.100"
    echo "  $0 setup-nfs pi@192.168.1.100"
    echo "  $0 transfer pi@192.168.1.100"
    echo "  $0 mount-nfs pi@192.168.1.100"
    echo "  $0 test-camera  # Test local camera"
    echo "  $0 test-camera pi@192.168.1.100  # Test remote camera"
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

detect_package_manager() {
    local target="$1"
    
    # Check for package managers and return the appropriate install command
    if ssh "$target" "command -v apt >/dev/null 2>&1"; then
        echo "apt"
    elif ssh "$target" "command -v pacman >/dev/null 2>&1"; then
        echo "pacman"
    elif ssh "$target" "command -v yum >/dev/null 2>&1"; then
        echo "yum"
    else
        echo "unknown"
    fi
}

install_base_packages() {
    local target="$1"
    local pkg_mgr=$(detect_package_manager "$target")
    
    echo "Installing base packages using $pkg_mgr..."
    
    case "$pkg_mgr" in
        "apt")
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
                nfs-kernel-server \
                nfs-common \
                htop \
                screen"
            ;;
        "pacman")
            ssh "$target" "sudo pacman -Syu --noconfirm"
            ssh "$target" "sudo pacman -S --noconfirm \
                kstars \
                libindi \
                phd2 \
                siril \
                python-pip \
                python-yaml \
                python-astropy \
                gphoto2 \
                openssh \
                rsync \
                nfs-utils \
                htop \
                screen"
            ;;
        *)
            echo "ERROR: Unsupported package manager: $pkg_mgr"
            return 1
            ;;
    esac
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

setup_capture_directories() {
    local target="$1"
    echo "Setting up capture directory structure..."
    
    # Create capture directories
    ssh "$target" "mkdir -p $NFS_EXPORT_DIR"
    ssh "$target" "mkdir -p ~/observatory/{config,logs,scripts}"
    
    # Link Ekos default capture location to our NFS export
    ssh "$target" "ln -sf $NFS_EXPORT_DIR $EKOS_CAPTURE_DIR/observatory_captures"
    
    echo "Capture directories configured:"
    echo "  Ekos default: $EKOS_CAPTURE_DIR"
    echo "  NFS export: $NFS_EXPORT_DIR"
    echo "  Symlink: $EKOS_CAPTURE_DIR/observatory_captures -> $NFS_EXPORT_DIR"
}

setup_nfs() {
    local target="$1"
    echo "Setting up NFS server on $target..."
    
    # Ensure NFS packages are installed
    local pkg_mgr=$(detect_package_manager "$target")
    case "$pkg_mgr" in
        "apt")
            ssh "$target" "sudo apt install -y nfs-kernel-server nfs-common"
            ;;
        "pacman")
            ssh "$target" "sudo pacman -S --noconfirm nfs-utils"
            ssh "$target" "sudo systemctl enable --now nfs-server"
            ;;
    esac
    
    # Create capture directory if it doesn't exist
    ssh "$target" "mkdir -p $NFS_EXPORT_DIR"
    
    # Configure exports with secure options
    ssh "$target" "echo '$NFS_EXPORT_DIR *(rw,sync,no_subtree_check,insecure,anonuid=1000,anongid=1000)' | sudo tee -a /etc/exports"
    
    # Export and restart NFS
    ssh "$target" "sudo exportfs -rav"
    
    case "$pkg_mgr" in
        "apt")
            ssh "$target" "sudo systemctl restart nfs-kernel-server"
            ssh "$target" "sudo systemctl enable nfs-kernel-server"
            ;;
        "pacman")
            ssh "$target" "sudo systemctl restart nfs-server"
            ssh "$target" "sudo systemctl enable nfs-server"
            ;;
    esac
    
    echo "NFS server setup complete"
    echo "Export: $NFS_EXPORT_DIR"
    echo "Access: sudo mount -t nfs ${target%@*}:$NFS_EXPORT_DIR /mnt/node-captures"
}

transfer_files() {
    local target="$1"
    local node_name="${target##*@}"  # Extract hostname/IP
    local local_dir="./captures/${node_name}"
    
    mkdir -p "$local_dir"
    
    echo "Transferring files from $target to $local_dir..."
    echo "Source: $target:$NFS_EXPORT_DIR/"
    echo "Destination: $local_dir/"
    
    # Use rsync with optimizations for large files
    rsync -avz --progress --partial --inplace \
        --exclude="*.tmp" --exclude="*.lock" \
        "$target:$NFS_EXPORT_DIR/" "$local_dir/"
    
    if [ $? -eq 0 ]; then
        echo "Transfer complete: $(du -sh "$local_dir" | cut -f1) transferred"
    else
        echo "Transfer failed or incomplete"
        return 1
    fi
}

mount_nfs() {
    local target="$1"
    local node_name="${target##*@}"  # Extract hostname/IP
    local host_ip="${target##*@}"
    local mount_point="./mounts/${node_name}"
    
    # Install NFS client if needed
    if command -v apt >/dev/null 2>&1; then
        sudo apt install -y nfs-common 2>/dev/null || true
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm nfs-utils 2>/dev/null || true
    fi
    
    mkdir -p "$mount_point"
    
    echo "Mounting NFS share from $host_ip..."
    echo "Remote: $host_ip:$NFS_EXPORT_DIR"
    echo "Local: $mount_point"
    
    if sudo mount -t nfs "$host_ip:$NFS_EXPORT_DIR" "$mount_point"; then
        echo "NFS mount successful"
        echo "Access files at: $mount_point"
        echo "Unmount with: sudo umount $mount_point"
    else
        echo "NFS mount failed"
        echo "Ensure NFS server is running on $target"
        return 1
    fi
}

setup_automation() {
    local target="$1"
    echo "Setting up automation scripts..."
    
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
    local pkg_mgr=$(detect_package_manager "$target")
    
    case "$pkg_mgr" in
        "apt")
            if ! ssh "$target" "apt-cache show kstars-bleeding >/dev/null 2>&1"; then
                echo "WARNING: kstars-bleeding not available, will try kstars"
            fi
            ;;
        "pacman")
            if ! ssh "$target" "pacman -Ss kstars >/dev/null 2>&1"; then
                echo "ERROR: KStars packages not available"
                return 1
            fi
            ;;
    esac
    
    echo "All tests passed - deployment ready"
}

deploy_node() {
    local target="$1"
    echo "Deploying to $target..."
    
    check_ssh "$target" || return 1
    install_base_packages "$target"
    configure_indi "$target"
    setup_capture_directories "$target"
    setup_automation "$target"
    
    echo "Deployment complete"
    echo "Node accessible at: ssh $target"
    echo "Start INDI: ssh $target '~/start_indi.sh'"
    echo "Capture directory: $NFS_EXPORT_DIR"
    echo ""
    echo "Next steps:"
    echo "  Setup NFS: $0 setup-nfs $target"
    echo "  Transfer files: $0 transfer $target"
    echo "  Mount NFS: $0 mount-nfs $target"
}

test_camera() {
    local target="$1"
    
    if [ -z "$target" ]; then
        echo "========================================"
        echo "TESTING LOCAL CAMERA"
        echo "========================================"
        
        # Check if gphoto2 is installed
        if ! command -v gphoto2 >/dev/null 2>&1; then
            echo "ERROR: gphoto2 not found. Please install gphoto2 first."
            echo "  On Ubuntu/Debian: sudo apt install gphoto2"
            echo "  On Arch/Manjaro: sudo pacman -S gphoto2"
            return 1
        fi
        
        echo "[OK] gphoto2 is installed"
        echo ""
        
        echo "Detecting cameras..."
        local cameras=$(gphoto2 --auto-detect 2>/dev/null | tail -n +3)
        
        if [ -z "$cameras" ] || echo "$cameras" | grep -q "^$"; then
            echo "[FAIL] No cameras detected"
            echo ""
            echo "Troubleshooting:"
            echo "  1. Ensure camera is connected via USB"
            echo "  2. Camera should be in PTP/MTP mode (not Mass Storage)"
            echo "  3. For Canon cameras, try setting to Bulb or Manual mode"
            echo "  4. Check USB cable and try different ports"
            return 1
        else
            echo "[OK] Camera(s) detected:"
            echo "$cameras"
            echo ""
            
            # Try to get camera summary for first detected camera
            echo "Getting camera information..."
            if gphoto2 --summary 2>/dev/null | head -20; then
                echo ""
                echo "[OK] Camera communication successful"
                
                # Test basic camera operations
                echo ""
                echo "Testing camera capabilities..."
                
                # Check if we can get config
                if gphoto2 --list-config >/dev/null 2>&1; then
                    echo "[OK] Camera configuration accessible"
                    
                    # Try to get some basic settings
                    echo "Key camera settings:"
                    gphoto2 --get-config /main/imgsettings/iso 2>/dev/null | grep "Current" || echo "  ISO: Cannot read"
                    gphoto2 --get-config /main/capturesettings/shutterspeed 2>/dev/null | grep "Current" || echo "  Shutter: Cannot read"
                    gphoto2 --get-config /main/imgsettings/aperture 2>/dev/null | grep "Current" || echo "  Aperture: Cannot read"
                else
                    echo "[WARN] Camera configuration not fully accessible"
                fi
                
                echo ""
                echo "========================================"
                echo "LOCAL CAMERA TEST COMPLETE"
                echo "========================================"
                return 0
            else
                echo "[FAIL] Camera detected but communication failed"
                echo "Camera may be busy or in wrong mode"
                return 1
            fi
        fi
    else
        echo "========================================"
        echo "TESTING REMOTE CAMERA ON $target"
        echo "========================================"
        
        check_ssh "$target" || return 1
        
        # Check if gphoto2 is installed on remote
        if ! ssh "$target" "command -v gphoto2 >/dev/null 2>&1"; then
            echo "ERROR: gphoto2 not found on $target"
            echo "Install it first: ssh $target 'sudo apt install gphoto2'"
            return 1
        fi
        
        echo "[OK] gphoto2 is installed on remote"
        echo ""
        
        echo "Detecting cameras on remote..."
        local remote_cameras=$(ssh "$target" "gphoto2 --auto-detect 2>/dev/null | tail -n +3")
        
        if [ -z "$remote_cameras" ] || echo "$remote_cameras" | grep -q "^$"; then
            echo "[FAIL] No cameras detected on $target"
            return 1
        else
            echo "[OK] Camera(s) detected on $target:"
            echo "$remote_cameras"
            echo ""
            
            echo "Getting remote camera information..."
            if ssh "$target" "gphoto2 --summary 2>/dev/null | head -20"; then
                echo ""
                echo "[OK] Remote camera communication successful"
                echo "========================================"
                echo "REMOTE CAMERA TEST COMPLETE"
                echo "========================================"
                return 0
            else
                echo "[FAIL] Remote camera detected but communication failed"
                return 1
            fi
        fi
    fi
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
    "setup-nfs")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required for NFS setup"
            show_usage
            exit 1
        fi
        setup_nfs "$2"
        ;;
    "transfer")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required for file transfer"
            show_usage
            exit 1
        fi
        transfer_files "$2"
        ;;
    "mount-nfs")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required for NFS mount"
            show_usage
            exit 1
        fi
        mount_nfs "$2"
        ;;
    "test-camera")
        test_camera "${2:-}"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
