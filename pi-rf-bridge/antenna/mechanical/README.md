# Mechanical Design

3D models and mounting hardware for antenna system.

## Contents
- `element_dimensions.py` - Critical manufacturing dimension calculator
- `MANUFACTURING_SPECS.md` - Complete build specifications and BOM
- Yagi antenna boom and element designs
- 2306 BLDC motor mounts and gimbal structure
- CEM40EC mount brackets and cable management
- Weatherproof housing and covers

## Requirements
- Center-fed Yagi for balanced weight distribution
- 2306 motor torque compatibility
- MMCX connector integration
- Coax routing through gimbal joints
- Fine balance adjustment capability on all axes

## Corrected Antenna Dimensions
**CRITICAL UPDATE**: Boom length requirements corrected after design verification.

**Final Antenna Envelope:**
- **2.4 GHz Yagi**: 89.3mm boom × 59mm element span
- **5.8 GHz Yagi**: 37.7mm boom × 25mm element span
- **Combined design**: ~109 × 69 × 6mm maximum envelope

## Build Approaches

### 3D Printed Boom Design (Recommended for Prototyping)
- **Square boom**: 6 × 6mm cross-section, 1.5mm wall thickness
- **Press-fit elements**: 2.0mm stainless steel spokes
- **No drill press required**: 3D printer under-sizing provides perfect interference fit
- **Tolerance strategy**: ±0.5mm hole positioning adequate with post-assembly trimming
- **Weight**: ~9g total (well within 2306 motor 521g capacity)
- **Materials**: PLA/PETG filament, bicycle spokes, basic hand tools

### PCB-Integrated Design (Recommended for Production)
- **Dual-sided PCB**: Both Yagi bands on single board
- **Dimensions**: 109 × 69 × 1.6mm
- **Mechanical advantage**: Precise element positioning, integrated matching
- **Weight**: ~15g with components
- **Mounting**: Standard PCB mounting holes for gimbal attachment

## Motor Integration Verification
- **2306 BLDC capacity**: 521g at antenna mounting radius
- **Antenna weight**: 9-15g depending on construction
- **Safety margin**: >97% capacity available
- **Torque authority**: Excellent for RSSI-based tracking precision