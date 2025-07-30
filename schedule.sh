#!/bin/bash
# Schedule generation script for observatory nodes
# Creates YAML observation schedules based on user input

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 {create|send} [schedule.yaml] [user@host]"
    echo "  create [file] - Interactively create schedule file"
    echo "  send [file] [target] - Send schedule to a node"
    echo "Example: $0 create targets.yaml"
}

create_schedule() {
    local output_file="$1"
    
    echo "Creating new observation schedule: $output_file"
    echo "(Enter blank line for target name to finish)"
    
    local targets=()
    while true; do
        read -p "Target name (e.g., M31): " name
        [ -z "$name" ] && break
        read -p "Right Ascension (HH:MM:SS): " ra
        read -p "Declination (+/-DD:MM:SS): " dec
        read -p "Exposure time (seconds): " exposure
        
        targets+=("  - name: \"$name\"")
        targets+=("    coordinates:")
        targets+=("      ra: \"$ra\"")
        targets+=("      dec: \"$dec\"")
        targets+=("    exposure: $exposure")
    done
    
    # Write YAML file
    echo "scheduling:" > "$output_file"
    echo "  priority_mode: visibility_optimized" >> "$output_file"
    echo "targets:" >> "$output_file"
    
    for line in "${targets[@]}"; do
        echo "$line" >> "$output_file"
    done
    
    echo "Schedule saved to $output_file"
    cat "$output_file"
}

send_schedule() {
    local source_file="$1"
    local target="$2"
    
    if [ ! -f "$source_file" ]; then
        echo "ERROR: Schedule file not found: $source_file"
        return 1
    fi
    
    echo "Sending $source_file to $target..."
    scp "$source_file" "$target:~/observatory/config/schedule.yaml"
    echo "Schedule sent"
}

# Main execution
case "${1:-}" in
    "create")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Output file required"
            show_usage
            exit 1
        fi
        create_schedule "$2"
        ;;
    "send")
        if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
            echo "ERROR: File and target required"
            show_usage
            exit 1
        fi
        send_schedule "$2" "$3"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
