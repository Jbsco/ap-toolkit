#!/bin/bash
# Batch processing script using Siril and astrometry.net
# Processes captured observatory data with optional plate solving

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 batch [data_path] [options]"
    echo "  Process all data in a directory with Siril."
    echo "Expected structure: target_dir/{Light/,Dark/,Flat/}/*.fits"
    echo "Options:"
    echo "  --fwhm-sigma N     - FWHM outlier threshold (default: 2.0)"
    echo "  --star-sigma N     - Star count outlier threshold (default: 2.0)" 
    echo "  --round-sigma N    - Roundness outlier threshold (default: 1.5)"
    echo "  --no-filter        - Skip quality filtering"
    echo "  --step [phase]     - Start at a specific phase (1:preprocess, 2:quality, 3:stack)"
    echo "Example: $0 batch /mnt/nas/observatory/2025-07 --step 2"
}

check_dependencies() {
    if ! command -v siril >/dev/null 2>&1; then
        echo "ERROR: siril is not installed."
        return 1
    fi
}

validate_siril_structure() {
    local base_dir="$1"
    
    if [ ! -d "$base_dir/Light" ] || [ ! -d "$base_dir/Dark" ] || [ ! -d "$base_dir/Flat" ]; then
        echo "ERROR: Missing required directories (Light/, Dark/, Flat/) in $base_dir"
        return 1
    fi
    
    for subdir in Light Dark Flat; do
        if [ "$(ls -A "$base_dir/$subdir" 2>/dev/null)" = "" ]; then
             echo "WARNING: No FITS files found in $base_dir/$subdir/"
        fi
    done
    
    return 0
}

find_image_sequences() {
    local data_path="$1"
    
    find "$data_path" -type d -name "Light" | while read -r light_dir; do
        local base_dir
        base_dir=$(dirname "$light_dir")
        if validate_siril_structure "$base_dir" >/dev/null 2>&1; then
            echo "$base_dir"
        fi
    done
}

calculate_thresholds() {
    local metrics_file="$1"
    local fwhm_sigma="${2:-2.0}"
    local star_sigma="${3:-2.0}" 
    local round_sigma="${4:-1.5}"
    
    if [ ! -f "$metrics_file" ]; then
        echo "ERROR: Quality metrics file not found: $metrics_file" >&2
        return 1
    fi
    
    awk -v fwhm_sig="$fwhm_sigma" -v star_sig="$star_sigma" -v round_sig="$round_sigma" '
    BEGIN { n=0; fwhm_sum=0; star_sum=0; round_sum=0 }
    NR>1 && NF>=4 { 
        n++; 
        fwhm[n]=$2; fwhm_sum+=$2;
        stars[n]=$3; star_sum+=$3;
        roundness[n]=$4; round_sum+=$4;
    }
    END {
        if(n==0) exit 1;
        fwhm_mean = fwhm_sum/n;
        star_mean = star_sum/n;
        round_mean = round_sum/n;
        fwhm_sq=0; star_sq=0; round_sq=0;
        for(i=1; i<=n; i++) {
            fwhm_sq += (fwhm[i]-fwhm_mean)^2;
            star_sq += (stars[i]-star_mean)^2;
            round_sq += (roundness[i]-round_mean)^2;
        }
        fwhm_std = sqrt(fwhm_sq/(n-1));
        star_std = sqrt(star_sq/(n-1));
        round_std = sqrt(round_sq/(n-1));
        printf "FWHM_MAX=%.2f\n", fwhm_mean + fwhm_sig * fwhm_std;
        printf "STAR_MIN=%.0f\n", star_mean - star_sig * star_std;
        printf "ROUND_MIN=%.3f\n", round_mean - round_sig * round_std;
        printf "# Stats: FWHM=%.2f+-%.2f Stars=%.0f+-%.0f Round=%.3f+-%.3f\n", fwhm_mean, fwhm_std, star_mean, star_std, round_mean, round_std;
    }' "$metrics_file"
}

generate_siril_preprocess_script() {
    local target_dir="$1"
    local work_dir="$2"
    local script_file="$work_dir/preprocess.ssf"
    
    local light_frame_count
    light_frame_count=$(find "${target_dir}/Light" -maxdepth 1 -type f \( -name '*.fits' -o -name '*.fit' \) | wc -l)
    local ref_frame=1
    if [ "$light_frame_count" -gt 1 ]; then
        ref_frame=$(((light_frame_count + 1) / 2))
    fi

    cat > "$script_file" << EOF
requires 1.2.0
cd "$target_dir"

# Dark and Flat Processing
cd Dark/
convert dark -out=../dark_seq
cd ../dark_seq/
stack dark_ rej 3 3 -nonorm
load dark_stacked
save ../Dark_stacked
cd ../

cd Flat/
convert flat -out=../flat_seq
cd ../flat_seq/
stack flat_ rej 3 3 -nonorm
load flat_stacked
save ../Flat_stacked
cd ../

# Light Frame Processing
cd Light/
convert light -out=../light_seq
cd ../light_seq/
calibrate light_ -dark=../Dark_stacked -flat=../Flat_stacked -cfa -prefix=pp_
seqsubsky pp_light_ 2 -samples=20 -tolerance=2.0 -smooth=0.5 -prefix=bkg_
setref bkg_pp_light_ $ref_frame
register bkg_pp_light_ -prefix=r_ -minpairs=10 -maxstars=2000 -transf=homography

close
EOF
    echo "$script_file"
}

generate_siril_stack_script() {
    local target_dir="$1"
    local work_dir="$2"
    local fwhm_max="$3"
    local star_min="$4"
    local round_min="$5"
    local script_file="$work_dir/stack.ssf"
    
    cat > "$script_file" << EOF
requires 1.2.0
cd "$target_dir/light_seq"

EOF

    if [ -n "$fwhm_max" ] && [ -n "$star_min" ] && [ -n "$round_min" ]; then
        echo "# Quality filtering enabled" >> "$script_file"
        # Generate list of frame numbers that pass quality filter
        local selected_frames
        selected_frames=$(awk -v fmax="$fwhm_max" -v smin="$star_min" -v rmin="$round_min" 'NR>1 && NF>=4 && $2<=fmax && $3>=smin && $4>=rmin { print $1 }' "$work_dir/quality_stats.txt" | tr '\n' ' ')
        if [ -n "$selected_frames" ]; then
            # Modify sequence file to exclude poor quality frames
            # Create script to modify the sequence file
            local seq_file="$target_dir/light_seq/r_bkg_pp_light_.seq"
            local backup_file="$target_dir/light_seq/r_bkg_pp_light_.seq.backup"
            
            # Create backup
            cp "$seq_file" "$backup_file"
            
            # Create array of selected frames for awk
            local selected_array=""
            for frame in $selected_frames; do
                selected_array="$selected_array$frame "
            done
            
            # Modify sequence file to deselect poor quality frames
            awk -v frames="$selected_array" '
            BEGIN { 
                split(frames, selected, " ")
                for (i in selected) frame_selected[selected[i]] = 1
            }
            /^I / { 
                frame_num = $2
                if (frame_num in frame_selected) {
                    print $1, $2, "1"  # Keep selected frames
                } else {
                    print $1, $2, "0"  # Deselect poor quality frames
                }
                next
            }
            { print }  # Pass through all other lines unchanged
            ' "$backup_file" > "$seq_file"
            
            # Update sequence header to reflect new selection count
            local selected_count
            selected_count=$(echo $selected_frames | wc -w)
            sed -i "s/^S '\([^']*\)' \([0-9]*\) \([0-9]*\) \([0-9]*\)/S '\1' \2 \3 $selected_count/" "$seq_file"

            # Restore backup after processing
            # mv "$backup_file" "$seq_file" 
        else
            echo "# No frames pass quality filter - using all frames" >> "$script_file"
        fi
    else
        echo "# No quality filtering applied" >> "$script_file"
    fi

    cat >> "$script_file" << EOF
stack r_bkg_pp_light_ mean winsorized 3 3 -norm=additive -weight=wfwhm -filter-included -out=$work_dir/result
close
EOF
    echo "$script_file"
}

process_directory() {
    local target_dir="$1"
    local fwhm_sigma="$2"
    local star_sigma="$3"
    local round_sigma="$4"
    local no_filter="$5"
    local step="$6"
    local base_name
    base_name=$(basename "$target_dir")
    
    echo "Processing: $target_dir"
    
    local abs_target_dir
    abs_target_dir=$(realpath "$target_dir")
    local work_dir
    work_dir="$(dirname "$abs_target_dir")/process_$base_name"
    mkdir -p "$work_dir"

    if [ "$step" -le 1 ]; then
        echo "--- Phase 1: Pre-processing and Registration ---"
        local preprocess_script
        preprocess_script=$(generate_siril_preprocess_script "$abs_target_dir" "$work_dir")
        echo "Running Siril pre-processing script: $preprocess_script"
        if ! siril -s "$preprocess_script"; then
            echo "ERROR: Phase 1 failed for $target_dir"
            return 1
        fi
    else
        echo "--- Skipping Phase 1 ---"
    fi

    local fwhm_max star_min round_min
    if [ "$step" -le 2 ]; then
        echo "--- Phase 2: Quality Analysis ---"
        if [ "$no_filter" = "true" ]; then
            echo "Quality filtering disabled by user."
        elif [ ! -f "$abs_target_dir/light_seq/r_bkg_pp_light_.seq" ]; then
            echo "WARNING: Registered sequence file not found. Skipping filtering."
            no_filter=true
        else
            # Extract quality metrics from sequence file
            echo "Extracting quality metrics from sequence file..."
            grep "^R" "$abs_target_dir/light_seq/r_bkg_pp_light_.seq" | awk '{ print NR "\t" $2 "\t" $7 "\t" $4 }' > "$work_dir/quality_stats.txt"
            echo -e "image\tfwhm\tstars\troundness" > "$work_dir/quality_stats_temp.txt"
            cat "$work_dir/quality_stats.txt" >> "$work_dir/quality_stats_temp.txt"
            mv "$work_dir/quality_stats_temp.txt" "$work_dir/quality_stats.txt"
            local thresholds
            thresholds=$(calculate_thresholds "$work_dir/quality_stats.txt" "$fwhm_sigma" "$star_sigma" "$round_sigma") # Corrected path
            if [ -n "$thresholds" ]; then
                fwhm_max=$(echo "$thresholds" | grep "FWHM_MAX=" | cut -d= -f2)
                star_min=$(echo "$thresholds" | grep "STAR_MIN=" | cut -d= -f2)
                round_min=$(echo "$thresholds" | grep "ROUND_MIN=" | cut -d= -f2)
                
                echo "=== Quality Analysis Results ==="
                echo "$thresholds" | grep "# Stats:"
                echo "Sigma thresholds: FWHM=${fwhm_sigma}σ, Stars=${star_sigma}σ, Round=${round_sigma}σ"
                echo "Calculated limits: FWHM<=$fwhm_max, Stars>=$star_min, Round>=$round_min"
                
                # Count how many frames would be filtered
                local total_frames filtered_frames
                total_frames=$(awk 'NR>1 && NF>=4 { count++ } END { print count+0 }' "$work_dir/quality_stats.txt")
                filtered_frames=$(awk -v fmax="$fwhm_max" -v smin="$star_min" -v rmin="$round_min" 'NR>1 && NF>=4 && $2<=fmax && $3>=smin && $4>=rmin { count++ } END { print count+0 }' "$work_dir/quality_stats.txt")
                echo "Frame selection: $filtered_frames/$total_frames frames pass quality filter ($(( (filtered_frames * 100) / total_frames ))%)"
            else
                echo "WARNING: Could not calculate quality thresholds. Skipping filtering."
                no_filter=true
            fi
        fi
    else
        echo "--- Skipping Phase 2 ---"
    fi

    if [ "$step" -le 3 ]; then
        echo "--- Phase 3: Final Stacking ---"
        local stack_script
        if [ "$no_filter" = "true" ]; then
             stack_script=$(generate_siril_stack_script "$abs_target_dir" "$work_dir")
        else
             stack_script=$(generate_siril_stack_script "$abs_target_dir" "$work_dir" "$fwhm_max" "$star_min" "$round_min")
        fi

        echo "Running Siril stacking script: $stack_script"
        if ! siril -s "$stack_script"; then
            echo "ERROR: Phase 3 failed for $target_dir"
            return 1
        fi
        echo "Processing complete. Result: $work_dir/result.fit"
    else
        echo "--- Skipping Phase 3 ---"
    fi
}

batch_process() {
    local data_path="$1"
    local fwhm_sigma="$2"
    local star_sigma="$3"
    local round_sigma="$4"
    local no_filter="$5"
    local step="$6"

    if [ ! -d "$data_path" ]; then
        echo "ERROR: Data path not found: $data_path"
        return 1
    fi
    
    check_dependencies || return 1
    
    echo "Scanning for image sequences in: $data_path"
    
    local sequences
    sequences=($(find_image_sequences "$data_path"))
    
    if [ ${#sequences[@]} -eq 0 ]; then
        echo "No image sequences found"
        return 1
    fi
    
    echo "Found ${#sequences[@]} sequences to process"
    
    for seq_dir in "${sequences[@]}"; do
        if process_directory "$seq_dir" "$fwhm_sigma" "$star_sigma" "$round_sigma" "$no_filter" "$step"; then
            echo "SUCCESS: $seq_dir"
        else
            echo "FAILED: $seq_dir"
        fi
    done
}

# Main execution

PARAMS=()
STEP=1
NO_FILTER=false
FWHM_SIGMA=2.0
STAR_SIGMA=2.0
ROUND_SIGMA=1.5

while (($#)); do
  case "$1" in
    --fwhm-sigma)
      FWHM_SIGMA="$2"
      shift 2
      ;;
    --star-sigma)
      STAR_SIGMA="$2"
      shift 2
      ;;
    --round-sigma)
      ROUND_SIGMA="$2"
      shift 2
      ;;
    --no-filter)
      NO_FILTER=true
      shift
      ;;
    --step)
      STEP="$2"
      shift 2
      ;;
    -*)
      echo "Unsupported flag $1"
      exit 1
      ;;
    *)
      PARAMS+=("$1")
      shift
      ;;
  esac
done

set -- "${PARAMS[@]}"

case "${1:-}" in
    "batch")
        if [ -z "${2:-}" ]; then
            echo "ERROR: Data path required"
            show_usage
            exit 1
        fi
        batch_process "$2" "$FWHM_SIGMA" "$STAR_SIGMA" "$ROUND_SIGMA" "$NO_FILTER" "$STEP"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
