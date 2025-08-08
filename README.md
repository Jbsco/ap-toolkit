# AP Toolkit
<img width="1023" height="184" alt="image" src="https://github.com/user-attachments/assets/30686937-5d7e-4f97-99aa-d04c38dbb27a" />

Deployment and processing scripts for Raspberry Pi nodes controlled by KStars/Ekos. Simplifies setup of Pi-based astrophotography nodes and automates data processing workflows.

## What it does

The AP Toolkit assists with:
- **Deploying** KStars/Ekos and INDI software on Raspberry Pi nodes
- **Configuring** hardware permissions and system settings for astrophotography equipment
- **Testing** camera connectivity and basic hardware functionality
- **Processing** captured image data with automated calibration and stacking
- **Managing** file transfers and network storage between nodes

## Scripts

- `node.sh` - Raspberry Pi deployment, hardware setup, camera testing, NFS setup, and file transfer management
- `process.sh` - Batch processing with Siril and astrometry.net
- `ref_binder_gen.py` - Astrophotography sequence planning and telescope setup analysis

## Quick Start

```bash
# Create custom SD card image and flash
./node.sh flash-image config.json /dev/sdX

# Deploy to a fresh Raspberry Pi with astrophotography hardware
./node.sh test pi@192.168.1.100
./node.sh deploy pi@192.168.1.100

# Test camera connectivity (local or remote)
./node.sh test-camera                    # Test local camera
./node.sh test-camera pi@192.168.1.100  # Test remote camera

# Setup file sharing
./node.sh setup-nfs pi@192.168.1.100  # Enable NFS server
./node.sh mount-nfs pi@192.168.1.100   # Mount NFS locally
./node.sh transfer pi@192.168.1.100    # SSH transfer to ./captures/

# Plan astrophotography sequences
python3 ref_binder_gen.py --sequence --target-name "Orion Nebula" --target-magnitude 4.0 --target-type nebula --total-time 300

# Process captured data
./process.sh batch ./captures
```

### Processing Script Workflow

The `process.sh` script automates the processing of astrophotography data using Siril.

**Steps:**
1. **Stack darks, flats**: Stacks dark and flat frames for calibration.
2. **Calibrate lights**: Applies dark and flat calibration to light frames.
3. **Apply background extraction**: Removes background gradients from light frames.
4. **Register stars**: Aligns frames using stars; uses the middle frame as a reference.
5. **Exclude frames outside thresholds**: Filters frames based on focus (FWHM < mean+2σ), star count (> mean-2σ), and roundness (> mean-1.5σ).
6. **Stack selected frames**: Combines frames using winsorized sigma filter with FWHM weighting.
7. **Output**: Processed images saved in `process_*` directory as `result.fit`.


If [Astrometry.net](https://github.com/dstndstn/astrometry.net) is installed locally, and the [appropriate catalogues](https://data.astrometry.net/) are present, then the image may be plate-solved and annotated:

```
solve-field process_captures/result.fit -D output_directory
plot-constellations -w output_directory/result.wcs -C -B -D -d /usr/share/astrometry/data/hd.fits -o result_annotated.png
```

![vega_annotated](https://github.com/user-attachments/assets/ad95bc30-6890-4387-aa52-e76f42f8c2a6)

The python scriopt `fits_to_mp4.py` may also be used to produce a video sequence of the collected data. This is similar to Siril's ability to output a sequence to video (generally the Siril function is recommended), but the script allows specifying prefixes to filter from existing *.fit files in a directory, as well as the intermediate file format used by OpenCV:

```
fits_to_mp4.py . --prefix bkg_pp_ --bmp
```

https://github.com/user-attachments/assets/963f8cfa-f93b-4940-aa53-6ca9eeeef182

This script may also be used to produce video of other timelapse subjects.

https://github.com/user-attachments/assets/b77f7ed9-9470-4317-9149-bb0a43b25c80

### Observation Scheduling

Use **KStars/Ekos Scheduler** for automated observation planning:

- **Scheduler Guide**: [Official KStars Ekos Scheduler Documentation](https://docs.kde.org/trunk5/en/kstars/kstars/ekos-scheduler.html)
- **Complete Ekos Guide**: [KStars Ekos Module Documentation](https://docs.kde.org/trunk5/en/kstars/kstars/ekos.html)
- **INDI Setup**: [Equipment Profile Configuration](https://docs.kde.org/trunk5/en/kstars/kstars/ekos-profile-wizard.html)
- **Getting Started**: Launch `kstars`, open Ekos (Tools → Ekos), and use the Scheduler tab
- **Multi-Node Support**: Connect to multiple INDI servers simultaneously (each Pi runs its own server on port 7624)
- **Remote Control**: Switch between nodes or coordinate multiple telescopes from a single Ekos instance

**Why use KStars/Ekos instead of custom scheduling scripts?**
- Complete GUI-based scheduling with constraints, priorities, and automated equipment control
- Built-in INDI driver support for all major astronomical equipment
- Automated alignment, focusing, guiding, and imaging sequences
- Weather monitoring, meridian flip handling, and safety shutdown
- Remote observatory control over network connections
- Extensive documentation and active community support

## Raspberry Pi Node Deployment

The `node.sh` script prepares Raspberry Pi systems for KStars/Ekos control by configuring:

### System Configuration
- **Software installation**: KStars/Ekos, INDI drivers, gphoto2, system utilities
- **USB permissions**: Adds users to plugdev, tty, dialout groups for hardware access
- **Udev rules**: Automatic device detection for cameras, mounts, and serial adapters
- **System services**: NTP synchronization, SSH access, directory structure
- **Network setup**: INDI server configuration for remote KStars/Ekos connections

### Hardware Support
Configures access for common astrophotography equipment:
- **Cameras**: Canon/Nikon DSLR cameras via USB
- **Mounts**: FTDI-based telescope mounts and USB-to-serial adapters
- **Accessories**: Focusers, filter wheels, guide cameras

### KStars/Ekos Integration
Each deployed Pi node:
- Runs INDI server (port 7624) for equipment drivers
- Accepts remote connections from KStars/Ekos control systems
- Provides local storage with optional NFS sharing for captured images
- Operates as part of a multi-node observatory network controlled by KStars/Ekos

## Dependencies

**Nodes require:** KStars/EKOS, INDI drivers, gphoto2, SSH access, hardware permissions

**Local processing requires:** Siril, Astrometry.net (optional)
