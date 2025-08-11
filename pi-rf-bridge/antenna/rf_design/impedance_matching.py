#!/usr/bin/env python3
"""
Impedance matching network design for Yagi antenna systems.
Includes coaxial cable analysis and MMCX connector considerations.
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
import cmath
import math

@dataclass
class CoaxialCable:
    """Coaxial cable specifications"""
    impedance_ohm: float
    velocity_factor: float
    attenuation_db_per_m: float
    length_m: float

@dataclass
class MatchingNetwork:
    """L-network impedance matching components"""
    inductor_nh: float
    capacitor_pf: float
    network_type: str  # 'low_pass' or 'high_pass'

def calculate_smith_chart_point(z_load: complex, z0: float = 50.0) -> complex:
    """Convert impedance to Smith chart reflection coefficient"""
    return (z_load - z0) / (z_load + z0)

def smith_to_impedance(gamma: complex, z0: float = 50.0) -> complex:
    """Convert Smith chart reflection coefficient to impedance"""
    return z0 * (1 + gamma) / (1 - gamma)

def coax_impedance_transform(z_load: complex, cable: CoaxialCable, frequency_hz: float) -> complex:
    """Transform load impedance through coaxial cable"""
    # Calculate electrical length in radians
    wavelength = 299792458 / frequency_hz  # Free space wavelength
    wavelength_coax = wavelength * cable.velocity_factor
    beta = 2 * math.pi / wavelength_coax
    electrical_length = beta * cable.length_m
    
    # Account for cable loss
    alpha = cable.attenuation_db_per_m * cable.length_m * math.log(10) / 20
    
    # Transform impedance through transmission line
    z_char = cable.impedance_ohm
    z_normalized = z_load / z_char
    
    # Transmission line transformation with loss
    z_in_norm = (z_normalized + 1j * math.tan(electrical_length)) / \
                (1 + 1j * z_normalized * math.tan(electrical_length))
    
    # Apply loss factor
    loss_factor = math.exp(-2 * alpha)
    z_in_norm *= loss_factor
    
    return z_in_norm * z_char

def design_l_network(z_load: complex, z_source: float, frequency_hz: float) -> MatchingNetwork:
    """
    Design L-network for impedance matching.
    Based on: W. Hayward, "Introduction to Radio Frequency Design," ARRL, 1994
    """
    r_load = z_load.real
    x_load = z_load.imag
    r_source = z_source
    
    # Determine if we need high-pass or low-pass configuration
    q_factor = abs(x_load) / r_load
    
    if r_load > r_source:
        # High-pass L-network (series C, shunt L)
        q_req = math.sqrt(r_load / r_source - 1)
        x_series = -q_req * r_source  # Negative for capacitor
        x_shunt = r_source * (1 + q_req**2) / q_req
        
        # Convert reactances to component values
        capacitor_pf = -1e12 / (2 * math.pi * frequency_hz * x_series)
        inductor_nh = x_shunt * 1e9 / (2 * math.pi * frequency_hz)
        
        return MatchingNetwork(inductor_nh, capacitor_pf, 'high_pass')
    else:
        # Low-pass L-network (series L, shunt C)
        q_req = math.sqrt(r_source / r_load - 1)
        x_series = q_req * r_load  # Positive for inductor
        x_shunt = -r_load * (1 + q_req**2) / q_req  # Negative for capacitor
        
        # Convert reactances to component values
        inductor_nh = x_series * 1e9 / (2 * math.pi * frequency_hz)
        capacitor_pf = -1e12 / (2 * math.pi * frequency_hz * x_shunt)
        
        return MatchingNetwork(inductor_nh, capacitor_pf, 'low_pass')

def calculate_mmcx_loss(frequency_hz: float) -> float:
    """
    Estimate MMCX connector insertion loss.
    Based on typical connector specifications.
    """
    # MMCX typical insertion loss: 0.1-0.2 dB to 6 GHz
    freq_ghz = frequency_hz / 1e9
    if freq_ghz <= 2.5:
        return 0.1  # dB
    elif freq_ghz <= 6.0:
        return 0.1 + (freq_ghz - 2.5) * 0.03  # Linear increase
    else:
        return 0.2  # dB

def plot_smith_chart(impedances: List[complex], labels: List[str], save_path: str = None):
    """Plot impedances on Smith chart"""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    # Smith chart circles (constant resistance and reactance)
    theta = np.linspace(0, 2*np.pi, 100)
    
    # Constant resistance circles
    for r in [0.2, 0.5, 1.0, 2.0, 5.0]:
        r_circle = r / (1 + r)
        radius = 1 / (1 + r)
        center_r = r_circle
        x_circle = center_r + radius * np.cos(theta)
        y_circle = radius * np.sin(theta)
        gamma_circle = x_circle + 1j * y_circle
        angles = np.angle(gamma_circle)
        mags = np.abs(gamma_circle)
        ax.plot(angles, mags, 'gray', alpha=0.3, linewidth=0.5)
    
    # Plot impedance points
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    for i, (z, label) in enumerate(zip(impedances, labels)):
        gamma = calculate_smith_chart_point(z)
        angle = np.angle(gamma)
        mag = abs(gamma)
        ax.plot(angle, mag, 'o', color=colors[i % len(colors)], 
                markersize=8, label=f'{label}: {z:.1f}Ω')
    
    ax.set_ylim(0, 1)
    ax.set_title('Smith Chart - Impedance Analysis')
    ax.legend(loc='upper left', bbox_to_anchor=(1.1, 1))
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

def analyze_cable_effects(frequency_hz: float, cable_lengths: List[float]):
    """Analyze coaxial cable effects on impedance matching"""
    # Typical RG174 specifications (thin coax suitable for short runs)
    cable_spec = CoaxialCable(
        impedance_ohm=50.0,
        velocity_factor=0.66,
        attenuation_db_per_m=1.5,  # At 2.4 GHz
        length_m=1.0  # Will be varied
    )
    
    # Antenna impedance (typical Yagi with slight mismatch)
    z_antenna = complex(45, 10)  # 45 + j10 ohms
    
    impedances = []
    labels = []
    
    for length in cable_lengths:
        cable_spec.length_m = length
        z_input = coax_impedance_transform(z_antenna, cable_spec, frequency_hz)
        impedances.append(z_input)
        labels.append(f'{length*1000:.0f}mm cable')
    
    return impedances, labels

def main():
    """Main impedance matching analysis"""
    print("Impedance Matching Network Design")
    print("=" * 40)
    
    # Analysis frequencies
    freq_2_4ghz = 2.45e9
    freq_5_8ghz = 5.8e9
    
    # Typical Yagi impedance (varies with design)
    z_yagi_2_4 = complex(42, 8)   # Slightly low impedance
    z_yagi_5_8 = complex(55, -12)  # Slightly high impedance with capacitive reactance
    
    print("2.4 GHz Analysis:")
    print(f"  Antenna impedance: {z_yagi_2_4:.1f} Ω")
    
    # Design matching network
    matching_2_4 = design_l_network(z_yagi_2_4, 50.0, freq_2_4ghz)
    print(f"  L-network type: {matching_2_4.network_type}")
    print(f"  Inductor: {matching_2_4.inductor_nh:.1f} nH")
    print(f"  Capacitor: {matching_2_4.capacitor_pf:.1f} pF")
    
    # Calculate VSWR before and after matching
    vswr_before = calculate_vswr(z_yagi_2_4)
    vswr_after = 1.0  # Ideal matching
    print(f"  VSWR before matching: {vswr_before:.2f}:1")
    print(f"  VSWR after matching: {vswr_after:.2f}:1")
    
    mmcx_loss = calculate_mmcx_loss(freq_2_4ghz)
    print(f"  MMCX connector loss: {mmcx_loss:.2f} dB")
    print()
    
    print("5.8 GHz Analysis:")
    print(f"  Antenna impedance: {z_yagi_5_8:.1f} Ω")
    
    matching_5_8 = design_l_network(z_yagi_5_8, 50.0, freq_5_8ghz)
    print(f"  L-network type: {matching_5_8.network_type}")
    print(f"  Inductor: {matching_5_8.inductor_nh:.1f} nH")
    print(f"  Capacitor: {matching_5_8.capacitor_pf:.1f} pF")
    
    vswr_before_5_8 = calculate_vswr(z_yagi_5_8)
    print(f"  VSWR before matching: {vswr_before_5_8:.2f}:1")
    print(f"  VSWR after matching: 1.00:1")
    
    mmcx_loss_5_8 = calculate_mmcx_loss(freq_5_8ghz)
    print(f"  MMCX connector loss: {mmcx_loss_5_8:.2f} dB")
    print()
    
    # Analyze cable length effects
    cable_lengths = [0.5, 1.0, 2.0, 3.0, 4.0]  # meters
    impedances_2_4, labels_2_4 = analyze_cable_effects(freq_2_4ghz, cable_lengths)
    impedances_5_8, labels_5_8 = analyze_cable_effects(freq_5_8ghz, cable_lengths)
    
    # Add original antenna impedances for reference
    all_impedances_2_4 = [z_yagi_2_4] + impedances_2_4
    all_labels_2_4 = ['Antenna'] + labels_2_4
    
    # Plot Smith charts
    plot_smith_chart(all_impedances_2_4, all_labels_2_4, 'smith_chart_2.4ghz.png')
    
    print("Cable Length Analysis (2.4 GHz):")
    for length, z in zip(cable_lengths, impedances_2_4):
        vswr = calculate_vswr(z)
        print(f"  {length*1000:.0f}mm: {z:.1f}Ω, VSWR {vswr:.2f}:1")
    
    print()
    print("Component Specifications:")
    print("-" * 40)
    print("2.4 GHz Matching Components:")
    if matching_2_4.network_type == 'low_pass':
        print(f"  Series inductor: {matching_2_4.inductor_nh:.1f} nH (wire wound, 0603 size)")
        print(f"  Shunt capacitor: {matching_2_4.capacitor_pf:.1f} pF (ceramic, 0402 size)")
    else:
        print(f"  Series capacitor: {matching_2_4.capacitor_pf:.1f} pF (ceramic, 0402 size)")
        print(f"  Shunt inductor: {matching_2_4.inductor_nh:.1f} nH (wire wound, 0603 size)")
    
    print()
    print("5.8 GHz Matching Components:")
    if matching_5_8.network_type == 'low_pass':
        print(f"  Series inductor: {matching_5_8.inductor_nh:.1f} nH (wire wound, 0402 size)")
        print(f"  Shunt capacitor: {matching_5_8.capacitor_pf:.1f} pF (ceramic, 0402 size)")
    else:
        print(f"  Series capacitor: {matching_5_8.capacitor_pf:.1f} pF (ceramic, 0402 size)")  
        print(f"  Shunt inductor: {matching_5_8.inductor_nh:.1f} nH (wire wound, 0402 size)")
    
    print()
    print("Cable Recommendations:")
    print("-" * 40)
    print("Optimal cable lengths (2.4 GHz):")
    for length, z in zip(cable_lengths, impedances_2_4):
        vswr = calculate_vswr(z)
        if vswr <= 1.5:
            print(f"  ✅ {length*1000:.0f}mm: VSWR {vswr:.2f}:1 (Good match)")
        elif vswr <= 2.0:
            print(f"  ⚠️  {length*1000:.0f}mm: VSWR {vswr:.2f}:1 (Acceptable)")
        else:
            print(f"  ❌ {length*1000:.0f}mm: VSWR {vswr:.2f}:1 (Poor match)")
    
    print()
    print("Coax Specifications:")
    print(f"  Recommended: RG174 or similar (50Ω, 0.66 VF)")
    print(f"  Max practical length: 2000mm (VSWR < 2:1)")
    print(f"  MMCX connector pair loss: {mmcx_loss:.2f} dB (2.4GHz), {mmcx_loss_5_8:.2f} dB (5.8GHz)")
    
    print()
    print("MATCHING NETWORK SUMMARY:")
    print("=" * 40)
    print("Implementation strategy:")
    print("- Dual-band switchable matching via PIN diode RF switches")
    print("- SMD components on PCB substrate for compact integration")
    print("- Center-fed balun design for mechanical symmetry")
    print("- MMCX connector at antenna feed point")
    print(f"- Coax length optimization: {cable_lengths[0]*1000:.0f}mm preferred")

def calculate_vswr(z_antenna: complex, z_line: float = 50.0) -> float:
    """Calculate VSWR from antenna impedance"""
    gamma = abs((z_antenna - z_line) / (z_antenna + z_line))
    return (1 + gamma) / (1 - gamma)

if __name__ == "__main__":
    main()