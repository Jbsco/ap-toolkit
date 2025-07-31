# AP Toolkit

Observatory automation scripts for coordinated astrophotography nodes.

## Scripts

- `deploy.sh` - SSH setup and deployment to Raspberry Pi nodes
- `process.sh` - Batch processing with Siril and astrometry.net
- `control.sh` - Manual KStars/Ekos control via SSH

## Quick Start

```bash
# Deploy to a fresh Raspberry Pi
./deploy.sh test pi@192.168.1.100
./deploy.sh deploy pi@192.168.1.100

# Process captured data
./process.sh batch /mnt/nas/observatory/2025-07

# Manual control of node
./control.sh connect pi@192.168.1.100
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

## Complete Workflow Example

```bash
# 1. Deploy fresh Raspberry Pi node
./deploy.sh test pi@192.168.1.100
./deploy.sh deploy pi@192.168.1.100

# 2. Set up automated observing with KStars/Ekos:
#    - Launch KStars locally
#    - Open Ekos (Tools → Ekos)
#    - Connect to INDI server on pi@192.168.1.100:7624
#    - Create capture sequences and schedules in Scheduler tab
#    - Start automated observing

# 3. Monitor and process data
./process.sh batch /mnt/nas/observatory/
./process.sh solve /mnt/nas/observatory/processed/

# 4. Manual intervention if needed
./control.sh connect pi@192.168.1.100
```

## Dependencies

Nodes require: KStars/EKOS, INDI drivers, SSH access
Local processing requires: Siril, astrometry.net (optional)
