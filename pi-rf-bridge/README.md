# Pi RF Bridge - Development Plan

Raspberry Pi-based directional antenna system for robust observatory networking.

## Must-Have Features

### Static Yagi Antenna Design
- **Frequency**: 2.4GHz or 5GHz operation
- **Cable**: 2-4ft coax with impedance matching 
- **Connectors**: MMCX preferred, minimize connections
- **Integration**: CEM40EC mount compatibility
- **Performance**: 10+ dBi gain, weatherproof housing

### RSSI-Based Tracking System  
- **Motors**: BLDC 2306 stators with FOC speed controllers
- **Control**: Quiet, efficient operation during imaging
- **Protocol**: Critical assessment of communication method
- **Safety**: Position limits, collision detection
- **Integration**: Pi GPIO/SPI control interface

### Pi Integration
- **Hardware**: Pi 4/5 compatibility
- **Libraries**: Existing RF/antenna control projects
- **Services**: Integration with existing AP toolkit
- **Network**: Maintain SSH/INDI/NFS functionality

## Design Decisions

### Motor Control Protocol
**Options Assessment:**
- CAN bus: Industrial standard, noise immunity
- I2C: Simple, Pi native, distance limited
- SPI: High speed, reliable for FOC controllers
- UART: Universal, moderate complexity
- PWM: Simplest but limited control

**Recommendation**: SPI for FOC controller communication
- Native Pi support via HAT interface
- High bandwidth for real-time FOC updates
- Deterministic timing for motor synchronization
- Noise immunity better than I2C at cable distances

### Antenna Design
**2.4GHz vs 5GHz Trade-offs:**
- 2.4GHz: Better penetration, more interference
- 5GHz: Higher bandwidth, cleaner spectrum
- **FITS File Considerations**: RGB/mono FITS files 60MB+ per exposure
  - 2.4GHz: ~150 Mbps theoretical, ~50-80 Mbps real-world
  - 5GHz: ~866 Mbps theoretical, ~200-400 Mbps real-world
  - **Impact**: 60MB file transfer time: 2.4GHz ~8-12 seconds, 5GHz ~2-3 seconds
  - **Session throughput**: 100+ files/night favors 5GHz for bulk transfers
- **Decision**: Dual-band Yagi for flexibility, 5GHz primary for data transfer

## Implementation Phases

### Phase 1: Static Antenna System
- Yagi antenna mechanical design and 3D models
- Impedance matching network design
- MMCX connector integration
- Mount bracket for CEM40EC compatibility

### Phase 2: RSSI Measurement
- Pi WiFi RSSI monitoring library
- Signal strength logging and analysis
- Antenna pattern characterization
- Link quality metrics

### Phase 3: Motor Control Integration
- BLDC controller interface development
- FOC parameter tuning for quiet operation
- Position feedback and safety systems
- Integration with Pi GPIO/SPI

### Phase 4: Tracking Algorithm
- RSSI-based hill climbing algorithm
- Predictive tracking using mount position
- Multi-point optimization capabilities
- Performance optimization and field testing

## External Resources

### Existing Pi RF Libraries
- **rpyc-wifi**: Python WiFi control and monitoring
- **iwlib**: Python iwconfig wrapper for signal strength
- **scapy**: RF analysis and packet monitoring
- **GNU Radio**: SDR integration if advanced RF needed

### BLDC Control Projects
- **SimpleFOC**: Arduino FOC library, Pi port available
- **ODrive**: High-performance BLDC controller with Python API
- **VESC**: Open ESC project with CAN/UART interface
- **pi-bldc**: Direct Pi GPIO BLDC control library

### Antenna Design Resources
- **4nec2**: NEC-based antenna modeling software
- **MMANA-GAL**: Yagi antenna design calculator
- **Saturn PCB Design**: RF PCB layout tools for matching networks

## File Structure
```
pi-rf-bridge/
├── README.md               # This development plan
├── antenna/
│   ├── mechanical/         # 3D models, mounting brackets
│   ├── rf_design/          # Impedance matching, simulations
│   └── test_data/          # Field measurements, patterns
├── software/
│   ├── rssi_monitor.py     # WiFi signal monitoring
│   ├── motor_control.py    # BLDC interface
│   ├── antenna_tracker.py  # Main tracking algorithm
│   └── integration.py      # AP toolkit integration
└── hardware/
    ├── schematics/         # PCB designs, wiring
    ├── bom.md              # Bill of materials
    └── assembly.md         # Build instructions
```

## Success Criteria
- 20+ dBi effective antenna gain at 1km+ range
- Sub-1 degree pointing accuracy with RSSI feedback
- Silent operation during 5-minute imaging exposures
- Seamless integration with existing AP toolkit workflow
- Field-deployable with CEM40EC mount system
