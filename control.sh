#!/bin/bash
# Manual control script for observatory nodes
# Provides interactive SSH access to KStars/Ekos on a node

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 {connect|test} [user@host]"
    echo "  connect [target] - Start interactive KStars session"
    echo "  test [target]    - Check connection and KStars status"
    echo "Example: $0 connect pi@192.168.1.100"
}

check_connection() {
    local target="$1"
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$target" exit 2>/dev/null; then
        echo "ERROR: Cannot connect via SSH to $target"
        return 1
    fi
}

check_kstars() {
    local target="$1"
    
    echo "Checking for KStars on $target..."
    if ! ssh "$target" "command -v kstars >/dev/null 2>&1"; then
        echo "ERROR: KStars not found on target"
        return 1
    fi
    
    echo "KStars installation found"
}

connect_node() {
    local target="$1"
    
    echo "Connecting to $target..."
    echo "Starting interactive KStars/Ekos session"
    echo "Close KStars or exit shell to end session"
    
    # Start KStars in a new X11 session if possible
    # This allows GUI applications over SSH
    ssh -X "$target" "kstars"
}

test_control() {
    local target="$1"
    echo "Testing manual control for $target..."
    
    check_connection "$1" || return 1
    check_kstars "$1" || return 1
    
    echo "Control prerequisites met"
}

# Main execution
case "${1:-}" in
    "connect")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required"
            show_usage
            exit 1
        fi
        connect_node "$2"
        ;;
    "test")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Target required"
            show_usage
            exit 1
        fi
        test_control "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
