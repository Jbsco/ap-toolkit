#!/bin/bash

plate_solve_annotate() {
    local input_path="$1"
    local hd_flag="$2"
    
    if [ -z "$input_path" ]; then
        echo "Usage: plate_solve_annotate <image_path> [--hd]"
        echo "  image_path: Path to the image file to solve"
        echo "  --hd:       Optional flag to include HD catalog annotations"
        return 1
    fi
    
    # Extract the directory and filename components
    local input_dir=$(dirname "$input_path")
    local filename=$(basename "$input_path")
    local basename="${filename%.*}"
    
    # Create output directory name
    local output_dir="${basename} Solved"
    
    # Build the paths
    local wcs_file="${output_dir}/${basename}.wcs"
    local annotations_file="${output_dir}/annotations.png"
    
    # Prepare HD catalog arguments if requested
    local hd_args=""
    if [ "$hd_flag" = "--hd" ]; then
        hd_args="-D -d /usr/share/astrometry/data/hd.fits"
    fi
    
    echo "Running plate solving on: $input_path"
    echo "Output directory: $output_dir"
    echo "WCS file: $wcs_file"
    echo "Annotations file: $annotations_file"
    
    # Run solve-field
    echo "Step 1: Running solve-field..."
    if ! solve-field "$input_path" --downsample 2 --objs 1000 --tag-all -D "$output_dir"; then
        echo "Error: solve-field failed"
        return 1
    fi
    
    # Check if WCS file was created
    if [ ! -f "$wcs_file" ]; then
        echo "Error: WCS file not found at $wcs_file"
        return 1
    fi
    
    # Run plot-constellations
    echo "Step 2: Running plot-constellations..."
    if ! plot-constellations -w "$wcs_file" -N -C -B $hd_args -o "$annotations_file"; then
        echo "Error: plot-constellations failed"
        return 1
    fi
    
    echo "Success! Files created:"
    echo "  - Solved files in: $output_dir"
    echo "  - Annotations: $annotations_file"
}

# If script is executed directly (not sourced), call the function with arguments
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    plate_solve_annotate "$@"
fi