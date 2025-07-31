# AP Toolkit

Observatory automation scripts for coordinated astrophotography nodes.

## Scripts

- `node.sh` - Node deployment, hardware setup, camera testing, NFS setup, and file transfer management
- `process.sh` - Batch processing with Siril and astrometry.net

## Quick Start

```bash
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

# Process captured data
./process.sh batch /mnt/nas/observatory/2025-07
```

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

## Hardware Setup

The deployment script automatically configures:
- **USB permissions** for cameras and telescope mounts
- **INDI drivers** for Canon/Nikon cameras, FTDI serial devices, USB-to-serial adapters
- **System services** for NTP time synchronization
- **Directory structure** for capture storage and NFS sharing
- **Hardware detection** via udev rules for plug-and-play device access

Supported hardware includes Canon/Nikon DSLR cameras, FTDI-based telescope mounts, and USB-to-serial adapters commonly used with astronomical equipment.

## Complete Workflow Example

```bash
# 1. Deploy fresh Raspberry Pi node with connected hardware
./node.sh test pi@192.168.1.100
./node.sh deploy pi@192.168.1.100
./node.sh test-camera pi@192.168.1.100  # Verify camera detection
./node.sh setup-nfs pi@192.168.1.100

# 2. Set up automated observing with KStars/Ekos:
#    - Launch KStars locally
#    - Open Ekos (Tools → Ekos)
#    - Connect to INDI server on pi@192.168.1.100:7624
#    - Create capture sequences and schedules in Scheduler tab
#    - Start automated observing

# 3. Monitor and process data
./process.sh batch /mnt/nas/observatory/
./process.sh solve /mnt/nas/observatory/processed/
```

## Dependencies

**Nodes require:** KStars/EKOS, INDI drivers, gphoto2, SSH access, hardware permissions

**Local processing requires:** Siril, astrometry.net (optional)
