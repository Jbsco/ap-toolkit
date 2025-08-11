#!/usr/bin/env python3
"""
Critical element dimensions and layout for Yagi antenna construction.
Generates manufacturing specifications for both 3D printed boom and PCB designs.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rf_design'))

import yagi_design
import math

def generate_manufacturing_specs():
    """Generate critical manufacturing dimensions for both design approaches"""
    
    # Design both bands
    freq_2_4ghz = 2.45e9
    freq_5_8ghz = 5.8e9
    
    design_2_4 = yagi_design.design_yagi_5element(freq_2_4ghz)
    design_5_8 = yagi_design.design_yagi_5element(freq_5_8ghz)
    
    wavelength_2_4_mm = yagi_design.wavelength_m(freq_2_4ghz) * 1000
    wavelength_5_8_mm = yagi_design.wavelength_m(freq_5_8ghz) * 1000
    
    print("CRITICAL MANUFACTURING DIMENSIONS")
    print("=" * 60)
    print()
    
    # 3D PRINTED BOOM + SPOKE DESIGN
    print("3D PRINTED BOOM + STAINLESS SPOKE DESIGN")
    print("-" * 45)
    print()
    
    print("2.4 GHz Band Elements (Stainless Steel Spokes):")
    print("Element    Position    Length    Hole Location")
    print("           from center  (mm)     from boom end")
    print("-" * 50)
    
    positions_2_4 = []
    lengths_2_4 = []
    for i, element in enumerate(design_2_4.elements):
        pos_mm = element.position_lambda * wavelength_2_4_mm
        length_mm = element.length_lambda * wavelength_2_4_mm
        positions_2_4.append(pos_mm)
        lengths_2_4.append(length_mm)
        
        # Calculate hole position from boom end (reflector end = 0)
        boom_length = max(positions_2_4) - min(positions_2_4)
        hole_from_end = pos_mm - min(positions_2_4)
        
        print(f"{element.element_type:>9}  {pos_mm:+8.1f}mm  {length_mm:6.1f}mm  {hole_from_end:8.1f}mm")
    
    boom_2_4 = max(positions_2_4) - min(positions_2_4)
    print(f"\nTotal boom length required: {boom_2_4:.1f}mm")
    print(f"Boom cross-section: 6.0 × 6.0mm square, 1.5mm wall")
    print(f"Element holes: 2.0mm diameter (for 2.0mm spokes)")
    print()
    
    print("5.8 GHz Band Elements:")
    print("Element    Position    Length    Hole Location") 
    print("           from center  (mm)     from boom end")
    print("-" * 50)
    
    positions_5_8 = []
    for i, element in enumerate(design_5_8.elements):
        pos_mm = element.position_lambda * wavelength_5_8_mm
        length_mm = element.length_lambda * wavelength_5_8_mm
        positions_5_8.append(pos_mm)
        
        hole_from_end = pos_mm - min(positions_5_8)
        print(f"{element.element_type:>9}  {pos_mm:+8.1f}mm  {length_mm:6.1f}mm  {hole_from_end:8.1f}mm")
    
    boom_5_8 = max(positions_5_8) - min(positions_5_8)
    print(f"\nTotal boom length required: {boom_5_8:.1f}mm")
    print()
    
    # Feed point specifications
    print("FEED POINT SPECIFICATIONS:")
    print("-" * 30)
    print("2.4 GHz driven element:")
    driven_2_4_length = design_2_4.elements[1].length_lambda * wavelength_2_4_mm  # Driven element is index 1
    print(f"  Total length: {driven_2_4_length:.1f}mm")
    print(f"  Feed point: {driven_2_4_length/2:.1f}mm from each end (center)")
    print(f"  Center tap: Solder coax center conductor")
    print(f"  Ground: Solder coax shield to reflector element")
    print()
    
    print("5.8 GHz driven element:")
    driven_5_8_length = design_5_8.elements[1].length_lambda * wavelength_5_8_mm
    print(f"  Total length: {driven_5_8_length:.1f}mm")
    print(f"  Feed point: {driven_5_8_length/2:.1f}mm from each end (center)")
    print()
    
    # PCB DESIGN SPECIFICATIONS
    print()
    print("DUAL-SIDED PCB DESIGN SPECIFICATIONS")
    print("-" * 40)
    print()
    
    # Calculate PCB dimensions needed
    max_element_2_4 = max(lengths_2_4)
    max_element_5_8 = max([e.length_lambda * wavelength_5_8_mm for e in design_5_8.elements])
    
    pcb_length = boom_2_4 + 20  # +20mm for connectors and matching circuits
    pcb_width = max_element_2_4 + 10  # +10mm clearance
    
    print(f"PCB Dimensions: {pcb_length:.0f} × {pcb_width:.0f} × 1.6mm")
    print("4-layer stackup: Top copper / Ground / Ground / Bottom copper")
    print()
    
    print("TOP LAYER (2.4 GHz Elements):")
    print("Element    X-Position   Y-Position   Trace Width")
    print("           (mm)         (mm)         (mm)")
    print("-" * 50)
    
    # PCB coordinate system: center of board = (0,0)
    pcb_center_x = pcb_length / 2
    pcb_center_y = pcb_width / 2
    
    for i, element in enumerate(design_2_4.elements):
        pos_mm = element.position_lambda * wavelength_2_4_mm
        length_mm = element.length_lambda * wavelength_2_4_mm
        
        # X position relative to PCB center
        x_pos = pos_mm + pcb_center_x
        # Y position: center of element at board center
        y_start = pcb_center_y - length_mm/2
        y_end = pcb_center_y + length_mm/2
        
        # Trace width for 50 ohm impedance on FR4
        trace_width = 0.8 if element.element_type == 'driven' else 0.6
        
        print(f"{element.element_type:>9}  {x_pos:8.1f}    {y_start:.1f}-{y_end:.1f}  {trace_width:.1f}")
    
    print()
    print("BOTTOM LAYER (5.8 GHz Elements - Rotated 90°):")
    print("Element    X-Position   Y-Position   Trace Width")
    print("           (mm)         (mm)         (mm)")
    print("-" * 50)
    
    for i, element in enumerate(design_5_8.elements):
        pos_mm = element.position_lambda * wavelength_5_8_mm  
        length_mm = element.length_lambda * wavelength_5_8_mm
        
        # For 5.8 GHz, elements run along Y-axis (rotated 90°)
        # Y position relative to PCB center
        y_pos = pos_mm + pcb_center_y
        # X position: center of element at board center  
        x_start = pcb_center_x - length_mm/2
        x_end = pcb_center_x + length_mm/2
        
        trace_width = 0.5 if element.element_type == 'driven' else 0.4
        
        print(f"{element.element_type:>9}  {x_start:.1f}-{x_end:.1f}  {y_pos:8.1f}    {trace_width:.1f}")
    
    print()
    print("PCB FEED POINT:")
    print(f"Location: ({pcb_center_x:.1f}, {pcb_center_y:.1f}) - center of PCB")
    print("Via: Plated through-hole, connects both driven elements")
    print("MMCX connector: Edge-mount at feed point location")
    print()
    
    print("COMPONENT PLACEMENT:")
    print("- L-network components: Near feed point")
    print("- PIN diodes: Between driven elements and feed via")
    print("- Band select line: Routed to PCB edge")
    print("- Ground plane: Unbroken except at feed via")
    print()
    
    # Critical tolerances
    print("MANUFACTURING TOLERANCES:")
    print("-" * 25)
    print("3D Printed Boom:")
    print(f"  Element hole position: ±0.5mm (adequate)")
    print(f"  Hole diameter: 2.0mm ±0.1mm (press-fit)")
    print(f"  Spoke length: ±0.2mm (trim to final length)")
    print()
    print("PCB Design:")
    print(f"  Trace position: ±0.1mm (PCB fab standard)")
    print(f"  Trace width: ±0.05mm (controlled impedance)")
    print(f"  Via placement: ±0.05mm (professional fab)")
    print()
    
    # Weight breakdown
    print("WEIGHT BREAKDOWN:")
    print("-" * 17)
    
    # 3D print weight
    boom_volume_mm3 = (6*6 - 3*3) * boom_2_4  # Hollow square tube
    pla_density = 1.24e-6  # kg/mm³
    boom_weight_g = boom_volume_mm3 * pla_density * 1000
    
    steel_volume_mm3 = sum(lengths_2_4) * math.pi * 1.0**2  # 2mm diameter spokes
    steel_density = 7.8e-6  # kg/mm³  
    spokes_weight_g = steel_volume_mm3 * steel_density * 1000
    
    print(f"3D Print Option:")
    print(f"  Boom: {boom_weight_g:.1f}g")
    print(f"  Spokes: {spokes_weight_g:.1f}g")
    print(f"  Total: {boom_weight_g + spokes_weight_g:.1f}g")
    print()
    
    # PCB weight
    pcb_volume_mm3 = pcb_length * pcb_width * 1.6
    fr4_density = 1.85e-6  # kg/mm³
    pcb_weight_g = pcb_volume_mm3 * fr4_density * 1000
    components_weight_g = 5  # Estimated
    
    print(f"PCB Option:")
    print(f"  Substrate: {pcb_weight_g:.1f}g")
    print(f"  Components: {components_weight_g:.1f}g")
    print(f"  Total: {pcb_weight_g + components_weight_g:.1f}g")

if __name__ == "__main__":
    generate_manufacturing_specs()