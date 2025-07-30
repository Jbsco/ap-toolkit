# AP Toolkit

Observatory automation scripts for coordinated astrophotography nodes.

## Scripts

- `deploy.sh` - SSH setup and deployment to Raspberry Pi nodes
- `schedule.sh` - Generate YAML observation schedules 
- `process.sh` - Batch processing with Siril and astrometry.net
- `control.sh` - Manual KStars/Ekos control via SSH

## Quick Start

```bash
# Deploy to a fresh Raspberry Pi
./deploy.sh test pi@192.168.1.100
./deploy.sh deploy pi@192.168.1.100

# Create observation schedule
./schedule.sh create targets.yaml

# Process captured data
./process.sh batch /mnt/nas/observatory/2025-07

# Manual control of node
./control.sh connect pi@192.168.1.100
```

## Complete Workflow Example

```bash
# 1. Deploy fresh Raspberry Pi node
./deploy.sh test pi@192.168.1.100
./deploy.sh deploy pi@192.168.1.100

# 2. Create observation schedule
./schedule.sh create tonight.yaml
./schedule.sh send tonight.yaml pi@192.168.1.100

# 3. Monitor and process data
./process.sh batch /mnt/nas/observatory/
./process.sh solve /mnt/nas/observatory/processed/

# 4. Manual intervention if needed
./control.sh connect pi@192.168.1.100
```

## Dependencies

Nodes require: KStars/EKOS, INDI drivers, SSH access
Local processing requires: Siril, astrometry.net (optional)
