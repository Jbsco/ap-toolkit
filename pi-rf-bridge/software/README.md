# Software

Pi-based control and monitoring for antenna tracking system.

## Contents
- `antenna_tracker.py` - Combined RSSI monitoring, BLDC control, and tracking
- `antenna_tracker.service` - Systemd service for standalone operation

## FOC Libraries to Research
- SimpleFOC for Pi GPIO BLDC control
- ODrive Python API for high-performance controllers
- VESC CAN/UART interface libraries

## Requirements
- Standalone Pi system service
- Pi 4/5 GPIO/SPI interface compatibility
- Silent operation during imaging sequences
- Real-time RSSI feedback and hill-climbing optimization
- Deployed via AP toolkit `node.sh` script
- Reusable on other Pi projects without modification