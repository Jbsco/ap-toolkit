# Manufacturing Specifications

Critical dimensions and layouts for dual-band Yagi antenna construction.

## 3D Printed Boom + Stainless Spoke Design

### Boom Specifications
- **Cross-section**: 6.0 × 6.0mm square (hollow)
- **Wall thickness**: 1.5mm
- **Total length**: 100mm (89.3mm required + 10mm margin)
- **Material**: PLA or PETG filament
- **Print settings**: 0.2mm layers, 3 perimeters, 50% infill

### Element Hole Positions (2.4 GHz Band)
```
Element     Distance from boom end    Hole diameter
Reflector   0.0mm                     2.0mm
Driven      30.6mm                    2.0mm  
Director 1  48.9mm                    2.0mm
Director 2  67.3mm                    2.0mm
Director 3  89.3mm                    2.0mm
```

### Element Lengths (Stainless Steel Spokes)
```
2.4 GHz Band:
- Reflector:  59.0mm (cut from 2.0mm spoke)
- Driven:     56.9mm (center feed at 28.4mm)
- Director 1: 53.8mm
- Director 2: 52.0mm  
- Director 3: 50.2mm

5.8 GHz Band:
- Reflector:  24.9mm (cut from 2.0mm spoke)
- Driven:     24.0mm (center feed at 12.0mm)
- Director 1: 22.7mm
- Director 2: 22.0mm
- Director 3: 21.2mm
```

### Assembly Process
1. 3D print boom with holes at specified positions
2. Cut stainless spokes to element lengths ±0.2mm
3. Press-fit elements into holes (hand pressure sufficient)
4. Solder center conductor to driven element center
5. Solder shield to reflector element
6. Test with NanoVNA, trim elements if needed

## Dual-Sided PCB Design

### PCB Specifications
- **Dimensions**: 109 × 69 × 1.6mm
- **Layer count**: 4 layers
- **Stackup**: Top / Ground / Ground / Bottom
- **Material**: Standard FR4, 1oz copper
- **Via specification**: 0.2mm drill, plated through

### Top Layer (2.4 GHz Elements)
```
Element     X-Position   Y-Start   Y-End     Trace Width
Reflector   24.1mm      5.0mm     64.0mm    0.6mm
Driven      54.7mm      6.0mm     62.9mm    0.8mm
Director 1  73.0mm      7.6mm     61.4mm    0.6mm
Director 2  91.4mm      8.5mm     60.5mm    0.6mm
Director 3  113.4mm     9.4mm     59.6mm    0.6mm
```

### Bottom Layer (5.8 GHz Elements - Rotated 90°)
```
Element     X-Start   X-End     Y-Position   Trace Width
Reflector   42.2mm    67.1mm    21.6mm      0.4mm
Driven      42.6mm    66.7mm    34.5mm      0.5mm
Director 1  43.3mm    66.0mm    42.2mm      0.4mm
Director 2  43.7mm    65.6mm    50.0mm      0.4mm
Director 3  44.1mm    65.3mm    59.3mm      0.4mm
```

### Feed Point and Components
- **Feed location**: (54.7, 34.5)mm from PCB corner
- **Feed via**: 0.4mm diameter, connects top/bottom driven elements
- **MMCX connector**: Edge-mount at feed point
- **L-network**: 0402/0603 SMD components near feed
- **PIN diodes**: BAP65-02 or equivalent, between elements and feed

### Ground Plane Design
- **Layer 2**: Solid copper ground plane
- **Layer 3**: Solid copper ground plane
- **Via stitching**: Every 10mm around perimeter
- **Keepout**: 2mm clearance around antenna elements

## Manufacturing Tolerances

### 3D Printed Version
- **Hole position**: ±0.5mm (adequate for RF performance)
- **Hole diameter**: 2.0mm ±0.1mm (printer under-sizing provides press-fit)
- **Element length**: ±0.2mm (trim after assembly)

### PCB Version
- **Trace position**: ±0.1mm (standard PCB fabrication)
- **Trace width**: ±0.05mm (controlled impedance requirement)
- **Via placement**: ±0.05mm (professional fabrication)

## Bill of Materials

### 3D Printed Version (~$20 total)
- PLA/PETG filament: ~50g (~$2)
- Stainless steel spokes: 2.0mm × 300mm (~$5)
- RG174 coax: 500mm (~$3)
- MMCX connector: 1 piece (~$8)
- Hardware: screws, mounting (~$2)

### PCB Version (~$65 total)
- PCB fabrication: 109×69mm, 4-layer (~$40)
- Components: MMCX, PIN diodes, L-network (~$15)
- Assembly hardware: mounting, coax (~$10)

## Weight Comparison
- **3D Print + Spokes**: 9.7g total
- **PCB Version**: 27.3g total
- **2306 Motor Capacity**: 521g (both well within limits)

## Performance Validation
- **VSWR target**: <2:1 across WiFi bands
- **Gain target**: 9+ dBi both bands
- **Bandwidth**: 2.4-2.5 GHz, 5.1-5.9 GHz
- **Isolation**: >30 dB between bands (PCB version)