# RF Design

Antenna modeling and impedance matching networks.

## Contents
- `yagi_design.py` - Antenna element calculations and analysis
- `impedance_matching.py` - Matching network design and coax analysis
- Yagi element spacing and dimensions
- Impedance matching circuit designs
- MMCX connector integration
- Coax cable specifications and routing

## Requirements  
- Dual-band 2.4/5GHz operation
- 50-ohm impedance matching
- 10+ dBi gain target
- Center feed design for optimal balance
- Minimize connector losses in 2-4ft cable run

## Analysis Results

### Antenna Design (from yagi_design.py)

**2.4 GHz Band:**
- Boom length: 58.7mm
- Element range: 50.2 - 59.0mm
- Estimated weight: 7.9g (84% weight margin for 2306 motor)
- Bandwidth: 490 MHz (-3dB), covers 2.4-2.5 GHz WiFi

**5.8 GHz Band:**
- Boom length: 24.8mm  
- Element range: 21.2 - 24.9mm
- Estimated weight: 5.5g (96% weight margin for 2306 motor)
- Bandwidth: 1160 MHz (-3dB), covers 5.1-6.4 GHz WiFi

**Manufacturing Specifications:**
- Wire diameter: 1-2mm (2.4GHz), 0.5-1mm (5.8GHz)
- Tolerance: ±0.5mm (2.4GHz), ±0.2mm (5.8GHz)
- Construction: Aluminum rod or PCB trace feasible
- Feed point: Center-fed design for mechanical balance

### Impedance Matching (from impedance_matching.py)

**2.4 GHz Network:**
- Type: Low-pass L-network
- Series inductor: 1.2 nH (0603 size)
- Shunt capacitor: 0.6 pF (0402 size)
- VSWR improvement: 1.28:1 → 1.00:1

**5.8 GHz Network:**
- Type: High-pass L-network  
- Series capacitor: 1.7 pF (0402 size)
- Shunt inductor: 4.8 nH (0402 size)
- VSWR improvement: 1.28:1 → 1.00:1

**Cable Analysis:**
- Optimal length: 500mm (VSWR 1.12:1)
- Maximum practical: 2000mm (VSWR 2.01:1)
- MMCX connector loss: 0.1 dB (2.4GHz), 0.2 dB (5.8GHz)
- Recommended coax: RG174 (50Ω, 0.66 VF)

## Design Proposal

**Primary Recommendation: Dual-Band Switchable Yagi**

1. **Mechanical Design:**
   - Center-fed Yagi with 5 elements per band
   - Lightweight aluminum construction (<8g total)
   - Compact form factor (59mm max boom length)
   - Compatible with 2306 BLDC motor limits

2. **RF Implementation:**
   - PIN diode RF switches for band selection
   - SMD matching components on PCB substrate
   - MMCX connector at feed point
   - 500mm coax run to Pi transceiver

3. **Performance Targets:**
   - Gain: 9+ dBi both bands
   - Range: 1km+ line-of-sight capability
   - VSWR: <2:1 across WiFi bands
   - Bandwidth: Full WiFi spectrum coverage

4. **Integration Strategy:**
   - 5.8 GHz primary (higher bandwidth, less congestion)
   - 2.4 GHz fallback (better penetration)
   - Software-controlled band switching
   - RSSI feedback for tracking optimization

**Next Steps:**
- Mechanical CAD design and 3D printing
- PCB layout for matching networks
- Prototype fabrication and NanoVNA testing
- Integration with BLDC tracking system