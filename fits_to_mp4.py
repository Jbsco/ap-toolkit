#!/usr/bin/env python3

import os
import sys
import glob
import cv2
import numpy as np
from astropy.io import fits
import subprocess
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Convert FITS files to MP4 timelapse')
parser.add_argument('directory', nargs='?', default='.', help='Directory containing FITS files (default: current directory)')
parser.add_argument('-t', '--test', action='store_true', help='Test GPU encoders before use')
parser.add_argument('--bmp', action='store_true', help='Convert frames to BMP format')
parser.add_argument('--png', action='store_true', help='Convert frames to PNG format (default: raw data)')
parser.add_argument('--prefix', help='Filter FITS files by prefix (e.g., r_, bkg_, pp_) - only includes numbered files ending in digits')
args = parser.parse_args()

# Set source and temp directories
source_dir = args.directory
temp_dir = os.path.join(source_dir, "temp_frames")
os.makedirs(temp_dir, exist_ok=True)

# Collect FITS files
if args.prefix:
    # Filter by prefix for Siril-style numbered files (prefix + digits + .fits)
    import re
    pattern = os.path.join(source_dir, f'{args.prefix}*.fits')
    all_files = glob.glob(pattern)
    # Filter to only include files ending in digits before .fits
    fits_files = []
    for f in all_files:
        basename = os.path.basename(f)
        # Check if filename matches pattern: prefix + any chars + digits + .fits
        if re.match(rf'^{re.escape(args.prefix)}.*\d+\.fits$', basename):
            fits_files.append(f)
    fits_files = sorted(fits_files)
    if fits_files:
        print(f'Found {len(fits_files)} FITS files with prefix "{args.prefix}" ending in digits')
    else:
        print(f'No FITS files found with prefix "{args.prefix}" ending in digits')
        sys.exit(1)
else:
    fits_files = sorted(glob.glob(os.path.join(source_dir, '*.fits')))

# Configure OpenCV for GPU acceleration if possible
try:
    cv2.ocl.setUseOpenCL(True)
    if cv2.ocl.useOpenCL():
        print('OpenCV-GPU acceleration enabled')
    else:
        print('OpenCV-GPU acceleration not available')
except:
    print('OpenCV-GPU acceleration not available')

# Process and create temporary image files
print(f'Processing {len(fits_files)} FITS files...')
for i, f in enumerate(fits_files):
    if (i + 1) % 50 == 0 or i == 0:
        print(f'Processing frame {i+1}/{len(fits_files)} ({f})')
    data = fits.getdata(f)
    
    # Handle 3D FITS files (RGB color data)
    if len(data.shape) == 3:
        # If 3D, transpose to get proper RGB order (channels last)
        if data.shape[0] == 3:  # Channels first
            data = np.transpose(data, (1, 2, 0))
        # Normalize each channel
        norm = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)
        # FITS RGB data is in RGB order - keep it as RGB since FFmpeg will handle it correctly
        rgb = norm
    else:
        # Handle 2D FITS files (grayscale)
        norm = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)
        rgb = cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)
    
    # Ensure dimensions are even for H.264 compatibility
    height, width = rgb.shape[:2]
    if height % 2 != 0:
        rgb = np.pad(rgb, ((0, 1), (0, 0), (0, 0)), mode='constant')
    if width % 2 != 0:
        rgb = np.pad(rgb, ((0, 0), (0, 1), (0, 0)), mode='constant')

    # Write raw data or convert to BMP/PNG
    if args.bmp:
        # Convert RGB to BGR for OpenCV imwrite
        bgr_data = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR) if len(rgb.shape) == 3 and rgb.shape[2] == 3 else rgb
        cv2.imwrite(os.path.join(temp_dir, f'frame_{i:04d}.bmp'), bgr_data)
    elif args.png:
        # Convert RGB to BGR for OpenCV imwrite
        bgr_data = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR) if len(rgb.shape) == 3 and rgb.shape[2] == 3 else rgb
        cv2.imwrite(os.path.join(temp_dir, f'frame_{i:04d}.png'), bgr_data)
    else:
        # Save raw data in RGB format
        np.save(os.path.join(temp_dir, f'frame_{i:04d}.npy'), rgb)

def test_encoder(encoder):
    """Test if an encoder actually works with a small test"""
    try:
        # Create a tiny test image
        test_cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-f', 'lavfi', '-i', 'testsrc=duration=0.1:size=64x64:rate=1',
            '-c:v', encoder, '-t', '0.1', '-f', 'null', '-'
        ]
        result = subprocess.run(test_cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False

def check_gpu_encoders(test_encoders=False):
    """Check available GPU encoders in order of preference"""
    encoders_to_try = [
        ('h264_vaapi', 'VAAPI (GPU)'),    # VAAPI works with AMD, Intel, and some NVIDIA
        ('h264_amf', 'AMD AMF'),          # AMD hardware encoding (requires driver)
        ('h264_nvenc', 'NVIDIA NVENC'),   # NVIDIA hardware encoding
        ('h264_videotoolbox', 'macOS VideoToolbox'), # macOS hardware encoding
    ]
    
    # First check if encoders are compiled into ffmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'], 
            capture_output=True, text=True, timeout=5
        )
        available_encoders = result.stdout
    except (subprocess.SubprocessError, subprocess.TimeoutExpired):
        return 'libx264', 'CPU (software)'
    
    # Default to CPU encoding unless testing confirms GPU encoder works
    if not test_encoders:
        print('Use --test flag to enable GPU encoder detection and testing')
        return 'libx264', 'CPU (software)'
    
    # Test each encoder that's available (only when --test flag is used)
    print('Testing GPU encoders...')
    for encoder, description in encoders_to_try:
        if encoder in available_encoders:
            print(f'Testing {description} ({encoder})...', end=' ', flush=True)
            if test_encoder(encoder):
                print('✓')
                return encoder, description
            else:
                print('✗')
    
    print('No working GPU encoders found, using CPU encoding')
    return 'libx264', 'CPU (software)'

# Create MP4 using FFmpeg with GPU acceleration fallback
output_file = os.path.join(source_dir, 'animation.mp4')
encoder, encoder_type = check_gpu_encoders(test_encoders=args.test)

print(f'Using {encoder_type} encoding ({encoder})')

# Determine input file pattern based on format
if args.bmp:
    input_pattern = os.path.join(temp_dir, 'frame_%04d.bmp')
    file_extension = '*.bmp'
elif args.png:
    input_pattern = os.path.join(temp_dir, 'frame_%04d.png')
    file_extension = '*.png'
else:
    # For raw numpy data, use different approaches based on encoder
    if encoder == 'h264_vaapi':
        # VAAPI works better with image sequence input, convert to BMP internally
        print('Converting raw data to BMP for VAAPI compatibility...')
        for i in range(len(fits_files)):
            frame_data = np.load(os.path.join(temp_dir, f'frame_{i:04d}.npy'))
            # Convert RGB to BGR for OpenCV imwrite
            bgr_data = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR) if len(frame_data.shape) == 3 and frame_data.shape[2] == 3 else frame_data
            cv2.imwrite(os.path.join(temp_dir, f'frame_{i:04d}.bmp'), bgr_data)
        
        input_pattern = os.path.join(temp_dir, 'frame_%04d.bmp')
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-framerate', '60',
            '-i', input_pattern,
            '-c:v', 'h264_vaapi', '-b:v', '8M',
            output_file
        ]
        file_extension = '*.npy'
        vaapi_temp_files = '*.bmp'
    else:
        # For other encoders, use raw video input
        import tempfile
        raw_frames = []
        for i in range(len(fits_files)):
            frame_data = np.load(os.path.join(temp_dir, f'frame_{i:04d}.npy'))
            raw_frames.append(frame_data)
        
        # Create a temporary raw video file
        raw_temp_file = os.path.join(temp_dir, 'raw_frames.rgb')
        with open(raw_temp_file, 'wb') as f:
            for frame in raw_frames:
                f.write(frame.tobytes())
        
        # Get dimensions from first frame
        height, width = raw_frames[0].shape[:2]
        
        # Build FFmpeg command for raw input
        base_cmd = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}', '-pix_fmt', 'rgb24',
            '-r', '60', '-i', raw_temp_file
        ]
        
        if encoder == 'libx264':
            ffmpeg_cmd = base_cmd + ['-c:v', encoder, '-pix_fmt', 'yuv420p', '-crf', '23', output_file]
        else:
            ffmpeg_cmd = base_cmd + ['-c:v', encoder, '-pix_fmt', 'yuv420p', '-b:v', '8M', output_file]
        
        file_extension = '*.npy'

# Build FFmpeg command for image sequence input (BMP/PNG)
if args.bmp or args.png:
    if encoder == 'libx264':
        # CPU encoding with CRF quality
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-framerate', '60', 
            '-i', input_pattern,
            '-c:v', encoder, '-pix_fmt', 'yuv420p', '-crf', '23', 
            output_file
        ]
    elif encoder == 'h264_vaapi':
        # VAAPI encoding with special handling
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-framerate', '60',
            '-hwaccel', 'vaapi', '-hwaccel_output_format', 'vaapi',
            '-i', input_pattern,
            '-c:v', 'h264_vaapi', '-b:v', '8M',
            output_file
        ]
    else:
        # Other GPU encoders - use bitrate for hardware compatibility
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-framerate', '60',
            '-i', input_pattern,
            '-c:v', encoder, '-pix_fmt', 'yuv420p', '-b:v', '8M',
            output_file
        ]

try:
    subprocess.run(ffmpeg_cmd, check=True)
except subprocess.CalledProcessError as e:
    if encoder != 'libx264':
        print(f'GPU encoding failed, falling back to CPU encoding...')
        # Fallback to CPU encoding
        if args.bmp or args.png or encoder == 'h264_vaapi':
            # Use image sequence input for fallback
            if encoder == 'h264_vaapi':
                # VAAPI created BMP files, use them for fallback
                fallback_input = os.path.join(temp_dir, 'frame_%04d.bmp')
            else:
                fallback_input = input_pattern
            
            fallback_cmd = [
                'ffmpeg', '-y', '-framerate', '60',
                '-i', fallback_input,
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23',
                output_file
            ]
        else:
            # Use raw video input for fallback
            fallback_cmd = [
                'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}', '-pix_fmt', 'rgb24',
                '-r', '60', '-i', raw_temp_file,
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23',
                output_file
            ]
        subprocess.run(fallback_cmd, check=True)
    else:
        raise e

# Clean up temporary files
del_temp_files = glob.glob(os.path.join(temp_dir, file_extension))
for f in del_temp_files:
    os.remove(f)

# Clean up VAAPI-generated BMP files if they exist
if not args.bmp and encoder == 'h264_vaapi':
    vaapi_bmp_files = glob.glob(os.path.join(temp_dir, '*.bmp'))
    for f in vaapi_bmp_files:
        os.remove(f)

# Clean up raw temp file if it exists
if not (args.bmp or args.png) and encoder != 'h264_vaapi':
    raw_temp_file = os.path.join(temp_dir, 'raw_frames.rgb')
    if os.path.exists(raw_temp_file):
        os.remove(raw_temp_file)

os.rmdir(temp_dir)

print(f'MP4 video created at {output_file}')
