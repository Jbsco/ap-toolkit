#!/usr/bin/env python3
"""
RF measurement analysis and data processing for antenna characterization.
Supports NanoVNA, TinySA, and SDR measurement data.
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import csv
import json
import math

@dataclass
class S11Measurement:
    """S11 (reflection) measurement data"""
    frequency_hz: np.ndarray
    s11_magnitude: np.ndarray
    s11_phase_deg: np.ndarray
    
    def to_complex(self) -> np.ndarray:
        """Convert to complex S11 values"""
        return self.s11_magnitude * np.exp(1j * np.deg2rad(self.s11_phase_deg))

@dataclass
class AntennaPattern:
    """Antenna radiation pattern measurement"""
    angle_deg: np.ndarray
    gain_dbi: np.ndarray
    frequency_hz: float
    pattern_type: str  # 'azimuth' or 'elevation'

@dataclass
class FieldStrengthMeasurement:
    """Field strength vs distance measurement"""
    distance_m: np.ndarray
    rssi_dbm: np.ndarray
    frequency_hz: float
    tx_power_dbm: float

def load_nanovna_s11(filename: str) -> S11Measurement:
    """Load S11 data from NanoVNA CSV export"""
    # NanoVNA CSV format: Frequency,S11_real,S11_imag
    data = np.loadtxt(filename, delimiter=',', skiprows=1)
    
    frequency_hz = data[:, 0]
    s11_real = data[:, 1]
    s11_imag = data[:, 2]
    
    s11_complex = s11_real + 1j * s11_imag
    s11_magnitude = np.abs(s11_complex)
    s11_phase_deg = np.rad2deg(np.angle(s11_complex))
    
    return S11Measurement(frequency_hz, s11_magnitude, s11_phase_deg)

def calculate_vswr_from_s11(s11_complex: np.ndarray) -> np.ndarray:
    """Calculate VSWR from complex S11 measurements"""
    gamma = np.abs(s11_complex)
    return (1 + gamma) / (1 - gamma)

def calculate_return_loss_from_s11(s11_complex: np.ndarray) -> np.ndarray:
    """Calculate return loss in dB from S11"""
    s11_mag = np.abs(s11_complex)
    # Avoid log(0) by setting minimum value
    s11_mag = np.maximum(s11_mag, 1e-10)
    return -20 * np.log10(s11_mag)

def smith_chart_coordinates(s11_complex: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Convert S11 to Smith chart coordinates"""
    gamma = s11_complex
    return gamma.real, gamma.imag

def plot_s11_analysis(measurement: S11Measurement, save_path: str = None):
    """Plot comprehensive S11 analysis"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    freq_ghz = measurement.frequency_hz / 1e9
    s11_complex = measurement.to_complex()
    
    # S11 magnitude
    s11_mag_safe = np.maximum(measurement.s11_magnitude, 1e-10)
    ax1.plot(freq_ghz, 20*np.log10(s11_mag_safe), 'b-', linewidth=2)
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('S11 Magnitude (dB)')
    ax1.set_title('Return Loss')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=-10, color='r', linestyle='--', alpha=0.7, label='VSWR 2:1')
    ax1.legend()
    
    # VSWR
    vswr = calculate_vswr_from_s11(s11_complex)
    ax2.plot(freq_ghz, vswr, 'r-', linewidth=2)
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('VSWR')
    ax2.set_title('Voltage Standing Wave Ratio')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=2.0, color='orange', linestyle='--', alpha=0.7, label='VSWR = 2:1')
    ax2.set_ylim(1, min(10, np.max(vswr)))
    ax2.legend()
    
    # Smith chart
    real_part, imag_part = smith_chart_coordinates(s11_complex)
    ax3.plot(real_part, imag_part, 'g-', linewidth=2, alpha=0.7)
    ax3.scatter(real_part[0], imag_part[0], color='red', s=50, label='Start', zorder=5)
    ax3.scatter(real_part[-1], imag_part[-1], color='blue', s=50, label='End', zorder=5)
    
    # Add Smith chart grid
    theta = np.linspace(0, 2*np.pi, 100)
    ax3.plot(np.cos(theta), np.sin(theta), 'k-', alpha=0.3)  # Unit circle
    
    # Constant resistance circles
    for r in [0.5, 1.0, 2.0]:
        r_norm = r
        center = r_norm / (1 + r_norm)
        radius = 1 / (1 + r_norm)
        circle = center + radius * np.exp(1j * theta)
        ax3.plot(circle.real, circle.imag, 'gray', alpha=0.3, linewidth=0.5)
    
    ax3.set_xlim(-1.1, 1.1)
    ax3.set_ylim(-1.1, 1.1)
    ax3.set_aspect('equal')
    ax3.set_title('Smith Chart')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Phase
    ax4.plot(freq_ghz, measurement.s11_phase_deg, 'm-', linewidth=2)
    ax4.set_xlabel('Frequency (GHz)')
    ax4.set_ylabel('S11 Phase (degrees)')
    ax4.set_title('Reflection Phase')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

def friis_transmission_formula(distance_m: float, frequency_hz: float, 
                              tx_gain_dbi: float = 0, rx_gain_dbi: float = 0) -> float:
    """
    Calculate path loss using Friis transmission equation.
    
    Friis formula: Pr/Pt = Gt * Gr * (λ/(4πR))²
    Where: λ = c/f, R = distance
    
    Returns path loss in dB.
    """
    c = 299792458  # Speed of light
    wavelength = c / frequency_hz
    
    # Free space path loss
    fspl_db = 20 * math.log10(4 * math.pi * distance_m / wavelength)
    
    # Total path loss including antenna gains
    path_loss_db = fspl_db - tx_gain_dbi - rx_gain_dbi
    
    return path_loss_db

def analyze_field_strength(measurement: FieldStrengthMeasurement, 
                          antenna_gain_dbi: float = 0) -> Dict:
    """Analyze field strength measurement against theory"""
    
    # Calculate theoretical path loss
    theoretical_loss = []
    for distance in measurement.distance_m:
        loss = friis_transmission_formula(distance, measurement.frequency_hz, 
                                        antenna_gain_dbi, antenna_gain_dbi)
        theoretical_loss.append(loss)
    
    theoretical_loss = np.array(theoretical_loss)
    
    # Calculate received power from RSSI
    rx_power_dbm = measurement.rssi_dbm
    
    # Calculate actual path loss
    actual_loss = measurement.tx_power_dbm - rx_power_dbm
    
    # Compare with theory
    loss_difference = actual_loss - theoretical_loss
    
    return {
        'theoretical_loss_db': theoretical_loss,
        'actual_loss_db': actual_loss,
        'difference_db': loss_difference,
        'mean_difference': np.mean(loss_difference),
        'std_difference': np.std(loss_difference)
    }

def plot_range_analysis(measurement: FieldStrengthMeasurement, 
                       antenna_gain_dbi: float, save_path: str = None):
    """Plot range analysis with theoretical comparison"""
    analysis = analyze_field_strength(measurement, antenna_gain_dbi)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Path loss comparison
    ax1.semilogx(measurement.distance_m, analysis['actual_loss_db'], 
                'ro-', label='Measured', linewidth=2)
    ax1.semilogx(measurement.distance_m, analysis['theoretical_loss_db'], 
                'b--', label='Friis Formula', linewidth=2)
    ax1.set_xlabel('Distance (m)')
    ax1.set_ylabel('Path Loss (dB)')
    ax1.set_title(f'Path Loss Analysis - {measurement.frequency_hz/1e9:.1f} GHz')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # RSSI vs distance
    ax2.semilogx(measurement.distance_m, measurement.rssi_dbm, 
                'go-', linewidth=2, label='Measured RSSI')
    
    # Add sensitivity threshold lines
    ax2.axhline(y=-70, color='orange', linestyle='--', alpha=0.7, 
               label='Good Signal (-70 dBm)')
    ax2.axhline(y=-90, color='red', linestyle='--', alpha=0.7, 
               label='Poor Signal (-90 dBm)')
    
    ax2.set_xlabel('Distance (m)')
    ax2.set_ylabel('RSSI (dBm)')
    ax2.set_title('Received Signal Strength')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print analysis results
    print(f"Range Analysis Summary:")
    print(f"  Mean path loss difference: {analysis['mean_difference']:.1f} dB")
    print(f"  Standard deviation: {analysis['std_difference']:.1f} dB")
    
    if analysis['mean_difference'] > 5:
        print(f"  ⚠️  Higher than expected path loss - check for obstacles")
    elif analysis['mean_difference'] < -5:
        print(f"  ⚠️  Lower than expected path loss - possible multipath enhancement")
    else:
        print(f"  ✅ Path loss matches theoretical expectations")
    
    # Calculate link budget
    print()
    print("Link Budget Analysis:")
    print("-" * 30)
    max_range_idx = len(measurement.distance_m) - 1
    max_range = measurement.distance_m[max_range_idx]
    final_rssi = measurement.rssi_dbm[max_range_idx]
    
    print(f"Test conditions:")
    print(f"  TX power: {measurement.tx_power_dbm:.0f} dBm")
    print(f"  Antenna gain: {antenna_gain_dbi:.1f} dBi (each end)")
    print(f"  Maximum test range: {max_range:.0f} m")
    print(f"  Final RSSI: {final_rssi:.0f} dBm")
    
    # Extrapolate to target ranges
    target_ranges = [500, 1000, 2000, 5000]  # meters
    print()
    print("Projected performance:")
    for target_range in target_ranges:
        path_loss = friis_transmission_formula(target_range, measurement.frequency_hz, 
                                             antenna_gain_dbi, antenna_gain_dbi)
        projected_rssi = measurement.tx_power_dbm - path_loss
        
        # Account for measured vs theoretical difference
        projected_rssi += analysis['mean_difference']
        
        if projected_rssi >= -70:
            status = "Excellent"
        elif projected_rssi >= -80:
            status = "Good"
        elif projected_rssi >= -90:
            status = "Marginal"
        else:
            status = "Insufficient"
            
        print(f"  {target_range:4.0f}m: {projected_rssi:5.1f} dBm ({status})")
    
    return analysis

def generate_test_data():
    """Generate synthetic test data for demonstration"""
    # Synthetic S11 data (slightly mismatched antenna)
    frequencies = np.linspace(2.4e9, 2.5e9, 201)
    
    # Model a slightly detuned antenna
    f0 = 2.45e9  # Resonant frequency
    q = 20       # Quality factor
    
    s11_complex = []
    for f in frequencies:
        # Simple resonant circuit model
        delta_f = (f - f0) / f0
        z_antenna = 50 * (1 + 1j * 2 * q * delta_f)  # Approximate impedance
        gamma = (z_antenna - 50) / (z_antenna + 50)
        s11_complex.append(gamma)
    
    s11_complex = np.array(s11_complex)
    s11_mag = np.abs(s11_complex)
    s11_phase = np.rad2deg(np.angle(s11_complex))
    
    s11_measurement = S11Measurement(frequencies, s11_mag, s11_phase)
    
    # Synthetic field strength data
    distances = np.array([10, 50, 100, 200, 500, 1000, 2000])  # meters
    tx_power = 20  # dBm
    frequency = 2.45e9
    antenna_gain = 9  # dBi
    
    # Add some measurement noise and environmental effects
    rssi_values = []
    for dist in distances:
        path_loss = friis_transmission_formula(dist, frequency, antenna_gain, antenna_gain)
        rx_power = tx_power - path_loss
        # Add realistic noise and fading (±3dB variation)
        noise = np.random.normal(0, 3)
        rssi_values.append(rx_power + noise)
    
    field_measurement = FieldStrengthMeasurement(distances, np.array(rssi_values), 
                                               frequency, tx_power)
    
    return s11_measurement, field_measurement

def main():
    """Main measurement analysis function"""
    print("RF Measurement Analysis")
    print("=" * 40)
    
    # Generate test data (replace with real measurements)
    s11_data, field_data = generate_test_data()
    
    print("S11 Analysis:")
    s11_complex = s11_data.to_complex()
    vswr = calculate_vswr_from_s11(s11_complex)
    return_loss = calculate_return_loss_from_s11(s11_complex)
    
    print(f"  Frequency range: {s11_data.frequency_hz[0]/1e9:.2f} - {s11_data.frequency_hz[-1]/1e9:.2f} GHz")
    print(f"  Best VSWR: {np.min(vswr):.2f}:1")
    print(f"  Best return loss: {np.max(return_loss):.1f} dB")
    print()
    
    # Plot S11 analysis
    plot_s11_analysis(s11_data, 'antenna_s11_analysis.png')
    
    # Analyze field strength
    antenna_gain = 9.0  # dBi estimated gain
    analysis = plot_range_analysis(field_data, antenna_gain, 'range_analysis.png')
    
    print()
    print("MEASUREMENT ANALYSIS SUMMARY:")
    print("=" * 50)
    print("Antenna characterization approach:")
    print("1. S11 measurements with NanoVNA (impedance/VSWR)")
    print("2. Field strength testing with calibrated equipment")
    print("3. Spectrum analysis with TinySA (interference/harmonics)")
    print("4. Time domain analysis with Siglent 1204X-E (transients)")
    print()
    print("Expected measurement accuracy:")
    print(f"- VSWR: ±0.1 (NanoVNA calibrated)")
    print(f"- RSSI: ±2 dB (calibrated reference)")  
    print(f"- Pattern: ±1 dB (controlled environment)")
    print(f"- Range: ±10% (environmental factors)")
    print()
    print("Critical validation points:")
    print("- Impedance match across WiFi bands")
    print("- Gain pattern symmetry (center-fed design)")
    print("- Cross-polarization discrimination >15 dB")
    print("- Front-to-back ratio >15 dB")
    print(f"- 1km link budget margin >10 dB")

if __name__ == "__main__":
    main()