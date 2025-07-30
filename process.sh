#!/bin/bash
# Batch processing script using Siril and astrometry.net
# Processes captured observatory data with optional plate solving

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 {batch|solve} [data_path]"
    echo "  batch [path] - Process all data in directory with Siril"
    echo "  solve [path] - Add astrometry.net plate solving"
    echo "Example: $0 batch /mnt/nas/observatory/2025-07"
}

check_dependencies() {
    local missing=()
    
    if ! command -v siril >/dev/null 2>&1; then
        missing+=("siril")
    fi
    
    if [ "$1" = "solve" ] && ! command -v solve-field >/dev/null 2>&1; then
        missing+=("astrometry.net")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo "ERROR: Missing dependencies: ${missing[*]}"
        echo "Install with: sudo apt install ${missing[*]// /-}"
        return 1
    fi
}

find_image_sequences() {
    local data_path="$1"
    
    # Find directories containing multiple FITS files
    find "$data_path" -type d -exec sh -c 'ls "$1"/*.{fits,fit,FIT,FITS} 2>/dev/null | wc -l' _ {} \; -print | \
    while read count dir; do
        if [ "$count" -gt 2 ]; then
            echo "$dir"
        fi
    done
}

generate_siril_script() {
    local work_dir="$1"
    local script_file="$work_dir/process.ssf"
    
    # Basic siril script for calibration and stacking
    cat > "$script_file" << 'EOF'
# Siril processing script
cd $1
convert light -out=../process/light
cd ../process
stack light rej 3 3 -nonorm
save result
close
EOF
    
    echo "$script_file"
}

process_directory() {
    local target_dir="$1"
    local base_name=$(basename "$target_dir")
    
    echo "Processing: $target_dir"
    
    # Create processing workspace
    local work_dir="$target_dir/../process_$base_name"
    mkdir -p "$work_dir/process"
    
    # Generate and run Siril script
    local script_file=$(generate_siril_script "$work_dir")
    
    if siril -s "$script_file" "$target_dir" 2>/dev/null; then
        echo "Processing complete: $work_dir/process/result.fit"
        
        # Clean up intermediate files
        rm -rf "$work_dir/process/light_*.fit" 2>/dev/null || true
        
        return 0
    else
        echo "Processing failed for $target_dir"
        return 1
    fi
}

solve_image() {
    local image_file="$1"
    
    echo "Solving: $image_file"
    
    # Run astrometry.net plate solving
    solve-field --overwrite --no-plots --crpix-center \
        --scale-units arcsecperpix --scale-low 0.5 --scale-high 10 \
        "$image_file"
    
    if [ -f "${image_file%.fit*}.wcs" ]; then
        echo "Plate solve successful: ${image_file%.fit*}.wcs"
        return 0
    else
        echo "Plate solve failed for $image_file"
        return 1
    fi
}

batch_process() {
    local data_path="$1"
    
    if [ ! -d "$data_path" ]; then
        echo "ERROR: Data path not found: $data_path"
        return 1
    fi
    
    check_dependencies "batch" || return 1
    
    echo "Scanning for image sequences in: $data_path"
    
    local sequences=($(find_image_sequences "$data_path"))
    
    if [ ${#sequences[@]} -eq 0 ]; then
        echo "No image sequences found"
        return 1
    fi
    
    echo "Found ${#sequences[@]} sequences to process"
    
    for seq_dir in "${sequences[@]}"; do
        if process_directory "$seq_dir"; then
            echo "SUCCESS: $seq_dir"
        else
            echo "FAILED: $seq_dir"
        fi
    done
}

solve_processed() {
    local data_path="$1"
    
    check_dependencies "solve" || return 1
    
    echo "Solving processed images in: $data_path"
    
    # Find result images
    find "$data_path" -name "result.fit" -o -name "*.fits" | while read image; do
        solve_image "$image"
    done
}

# Main execution  
case "${1:-}" in
    "batch")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Data path required"
            show_usage
            exit 1
        fi
        batch_process "$2"
        ;;
    "solve")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Data path required"
            show_usage
            exit 1
        fi
        solve_processed "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
