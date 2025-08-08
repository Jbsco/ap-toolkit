#!/usr/bin/env python3

import argparse
import json
import sys
import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


@dataclass
class CameraSpec:
    sensor_width_mm: float
    sensor_height_mm: float
    resolution_x: int
    resolution_y: int
    pixel_size_um: float


@dataclass
class ScopeSetup:
    name: str
    focal_length_mm: float
    aperture_mm: float
    focal_ratio: float
    weight_lbs: float = 0.0  # Telescope weight in pounds


@dataclass
class ImageMetrics:
    scope_name: str
    focal_length_mm: float
    focal_ratio: float
    image_scale_arcsec_px: float
    fov_deg_x: float
    fov_deg_y: float
    is_oversampled: bool


class TargetType(Enum):
    GALAXY = "galaxy"
    NEBULA = "nebula"
    PLANETARY = "planetary"
    GLOBULAR_CLUSTER = "globular_cluster"
    OPEN_CLUSTER = "open_cluster"
    DOUBLE_STAR = "double_star"


class FilterType(Enum):
    LUMINANCE = "L"
    RED = "R"
    GREEN = "G"
    BLUE = "B"
    H_ALPHA = "Ha"
    O_III = "OIII"
    S_II = "SII"
    CLEAR = "Clear"
    L_PRO = "L-Pro"


@dataclass
class Target:
    name: str
    ra_hours: float
    dec_degrees: float
    magnitude: float
    target_type: TargetType
    size_arcmin: Optional[float] = None
    priority: int = 1


@dataclass
class FilterSequence:
    filter_type: FilterType
    exposure_seconds: int
    count: int
    binning: int = 1


@dataclass
class SequencePlan:
    target: Target
    filter_sequences: List[FilterSequence]
    total_time_minutes: float
    estimated_snr: float
    setup: ScopeSetup
    camera: CameraSpec


def calculate_image_scale(focal_length_mm: float, pixel_size_um: float) -> float:
    return (206.265 * pixel_size_um) / focal_length_mm


def calculate_fov_degrees(sensor_dim_mm: float, focal_length_mm: float) -> float:
    return (sensor_dim_mm * 57.296) / focal_length_mm


def calculate_exposure_time(target: Target, setup: ScopeSetup, camera: CameraSpec, 
                          filter_type: FilterType, target_snr: float = 100.0) -> int:
    """Calculate optimal exposure time based on target magnitude and setup"""
    # Base exposure calculation using magnitude and aperture
    # Formula: t = k * 10^(0.4 * (magnitude - reference_mag)) / (aperture^2)
    
    # Filter transmission factors (approximate)
    filter_factors = {
        FilterType.LUMINANCE: 1.0,
        FilterType.CLEAR: 1.0,
        FilterType.RED: 0.3,
        FilterType.GREEN: 0.3,
        FilterType.BLUE: 0.3,
        FilterType.H_ALPHA: 0.1,
        FilterType.O_III: 0.05,
        FilterType.S_II: 0.05,
        FilterType.L_PRO: 0.15  # Dual-band Ha+OIII, blocks light pollution
    }
    
    # Target type factors (relative brightness)
    type_factors = {
        TargetType.GALAXY: 1.5,
        TargetType.NEBULA: 1.0,
        TargetType.PLANETARY: 0.5,
        TargetType.GLOBULAR_CLUSTER: 0.8,
        TargetType.OPEN_CLUSTER: 0.6,
        TargetType.DOUBLE_STAR: 0.3
    }
    
    # Base exposure time calculation
    aperture_area = math.pi * (setup.aperture_mm / 2) ** 2
    magnitude_factor = 10 ** (0.4 * (target.magnitude - 10.0))  # Reference mag 10
    filter_factor = filter_factors.get(filter_type, 1.0)
    type_factor = type_factors.get(target.target_type, 1.0)
    
    # Calculate base exposure (seconds)
    base_exposure = 60 * magnitude_factor * type_factor / (aperture_area / 10000) / filter_factor
    
    # SNR adjustment
    snr_factor = (target_snr / 100.0) ** 2
    exposure_time = base_exposure * snr_factor
    
    # CEM40EC-specific adjustments for optimal guiding
    focal_length = setup.focal_length_mm
    if focal_length <= 200:  # Wide field (Rokinon 135mm)
        # Can use longer exposures with excellent tracking
        min_exposure = 60 if filter_type == FilterType.L_PRO else 45
        max_exposure = 300
    elif focal_length <= 600:  # Medium field (FC-76DP)
        min_exposure = 60
        max_exposure = 240
    else:  # Long focal length (Mewlon)
        min_exposure = 30
        max_exposure = 180
    
    # Clamp to mount-appropriate bounds
    exposure_time = max(min_exposure, min(max_exposure, exposure_time))
    
    # Round to nearest 30 seconds for consistency
    return int(round(exposure_time / 30) * 30)


def calculate_subframe_count(target: Target, setup: ScopeSetup, filter_type: FilterType,
                           total_time_minutes: int = 180) -> int:
    """Calculate optimal number of subframes based on target and total time"""
    exposure_time = calculate_exposure_time(target, setup, CameraSpec(23.5, 15.7, 6252, 4176, 3.76), filter_type)
    
    total_seconds = total_time_minutes * 60
    
    # KStars/Ekos overhead includes: image download, FITS save, dithering, PHD2 settling
    # Higher overhead for longer focal lengths due to more sensitive guiding
    focal_length = setup.focal_length_mm
    if focal_length <= 200:  # Wide field - less sensitive to dither settling
        overhead_per_frame = 25
        dither_frequency = 5  # Dither every 5 frames
    elif focal_length <= 600:  # Medium field
        overhead_per_frame = 30
        dither_frequency = 4  # More frequent dithering
    else:  # Long focal length - more sensitive
        overhead_per_frame = 35
        dither_frequency = 3
    
    # Add extra overhead for dithering cycles
    frames_between_dither = dither_frequency
    dither_overhead = 45  # PHD2 settling time after dither
    
    # Calculate effective time per frame including periodic dithering
    base_time_per_frame = exposure_time + overhead_per_frame
    dither_time_per_frame = dither_overhead / frames_between_dither
    effective_time_per_frame = base_time_per_frame + dither_time_per_frame
    
    max_frames = int(total_seconds // effective_time_per_frame)
    
    # Minimum frames for good statistics
    min_frames = 10
    
    return max(min_frames, max_frames)


def create_lrgb_sequence(target: Target, setup: ScopeSetup, camera: CameraSpec,
                        total_time_minutes: int = 300) -> SequencePlan:
    """Create a standard LRGB sequence plan"""
    # Time allocation: 50% L, 17% each for RGB
    l_time = int(total_time_minutes * 0.5)
    rgb_time = int(total_time_minutes * 0.17)
    
    sequences = []
    
    # Luminance
    l_exposure = calculate_exposure_time(target, setup, camera, FilterType.LUMINANCE)
    l_count = calculate_subframe_count(target, setup, FilterType.LUMINANCE, l_time)
    sequences.append(FilterSequence(FilterType.LUMINANCE, l_exposure, l_count))
    
    # RGB
    for filter_type in [FilterType.RED, FilterType.GREEN, FilterType.BLUE]:
        exposure = calculate_exposure_time(target, setup, camera, filter_type)
        count = calculate_subframe_count(target, setup, filter_type, rgb_time)
        sequences.append(FilterSequence(filter_type, exposure, count))
    
    # Calculate actual total time
    actual_time = sum(seq.exposure_seconds * seq.count for seq in sequences) / 60
    estimated_snr = 150.0  # Rough estimate for LRGB
    
    return SequencePlan(target, sequences, actual_time, estimated_snr, setup, camera)


def create_narrowband_sequence(target: Target, setup: ScopeSetup, camera: CameraSpec,
                             total_time_minutes: int = 600) -> SequencePlan:
    """Create a narrowband (Ha/OIII/SII) sequence plan"""
    # Equal time allocation for narrowband
    filter_time = total_time_minutes // 3
    
    sequences = []
    
    for filter_type in [FilterType.H_ALPHA, FilterType.O_III, FilterType.S_II]:
        exposure = calculate_exposure_time(target, setup, camera, filter_type)
        count = calculate_subframe_count(target, setup, filter_type, filter_time)
        sequences.append(FilterSequence(filter_type, exposure, count))
    
    # Calculate actual total time
    actual_time = sum(seq.exposure_seconds * seq.count for seq in sequences) / 60
    estimated_snr = 120.0  # Narrowband typically needs more time
    
    return SequencePlan(target, sequences, actual_time, estimated_snr, setup, camera)


def create_lpro_sequence(target: Target, setup: ScopeSetup, camera: CameraSpec,
                        total_time_minutes: int = 480) -> SequencePlan:
    """Create an L-Pro light pollution filter sequence plan"""
    sequences = []
    
    # L-Pro is a single filter that captures both Ha and OIII
    exposure = calculate_exposure_time(target, setup, camera, FilterType.L_PRO)
    count = calculate_subframe_count(target, setup, FilterType.L_PRO, total_time_minutes)
    sequences.append(FilterSequence(FilterType.L_PRO, exposure, count))
    
    # Calculate actual total time
    actual_time = sum(seq.exposure_seconds * seq.count for seq in sequences) / 60
    estimated_snr = 110.0  # L-Pro typically needs more time than broadband but less than narrowband
    
    return SequencePlan(target, sequences, actual_time, estimated_snr, setup, camera)


def analyze_setup(setup: ScopeSetup, camera: CameraSpec) -> ImageMetrics:
    scale = calculate_image_scale(setup.focal_length_mm, camera.pixel_size_um)
    fov_x = calculate_fov_degrees(camera.sensor_width_mm, setup.focal_length_mm)
    fov_y = calculate_fov_degrees(camera.sensor_height_mm, setup.focal_length_mm)
    
    return ImageMetrics(
        scope_name=setup.name,
        focal_length_mm=setup.focal_length_mm,
        focal_ratio=setup.focal_ratio,
        image_scale_arcsec_px=round(scale, 2),
        fov_deg_x=round(fov_x, 2),
        fov_deg_y=round(fov_y, 2),
        is_oversampled=scale < 1.0
    )


def get_default_camera() -> CameraSpec:
    return CameraSpec(
        sensor_width_mm=23.5,
        sensor_height_mm=15.7,
        resolution_x=6252,
        resolution_y=4176,
        pixel_size_um=3.76
    )


def get_default_setups() -> List[ScopeSetup]:
    return [
        ScopeSetup("Rokinon 135mm f/2", 135, 67.5, 2.0, 1.5),  # Lightweight lens
        ScopeSetup("Takahashi FC-76DP (native)", 570, 76, 7.5, 4.8),  # ~2.2kg
        ScopeSetup("Takahashi FC-76DP + 0.64x reducer", 365, 76, 4.8, 5.3),  # +reducer weight
        ScopeSetup("Takahashi Mewlon M210", 2415, 210, 11.5, 18.0)  # Heavy Dall-Kirkham
    ]


def format_table(metrics_list: List[ImageMetrics]) -> str:
    if not metrics_list:
        return "No data to display"
    
    headers = [
        "Scope/Lens", "FL (mm)", "f/", "Scale (\"/px)", 
        "FOV X (deg)", "FOV Y (deg)", "Oversampled"
    ]
    
    rows = []
    for m in metrics_list:
        rows.append([
            m.scope_name,
            str(m.focal_length_mm),
            str(m.focal_ratio),
            str(m.image_scale_arcsec_px),
            str(m.fov_deg_x),
            str(m.fov_deg_y),
            "Yes" if m.is_oversampled else "No"
        ])
    
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    
    def format_row(row):
        return " | ".join(str(item).ljust(col_widths[i]) for i, item in enumerate(row))
    
    separator = "-+-".join("-" * width for width in col_widths)
    
    output = []
    output.append(format_row(headers))
    output.append(separator)
    for row in rows:
        output.append(format_row(row))
    
    return "\n".join(output)


def check_mount_capacity(setup: ScopeSetup, camera: CameraSpec) -> str:
    """Check if payload exceeds CEM40EC capacity and return warning if needed"""
    camera_weight = 2.2  # Poseidon-C Pro weight in lbs
    guide_camera_weight = 0.3  # Typical guide camera
    accessories_weight = 2.0  # Rings, dovetail, cables, etc.
    
    total_payload = setup.weight_lbs + camera_weight + guide_camera_weight + accessories_weight
    cem40_capacity = 40.0  # lbs
    recommended_max = 30.0  # 75% of capacity for good tracking
    
    if total_payload > cem40_capacity:
        return f"⚠️  OVERLOAD: {total_payload:.1f}lbs exceeds CEM40EC capacity ({cem40_capacity}lbs)"
    elif total_payload > recommended_max:
        return f"⚠️  HEAVY: {total_payload:.1f}lbs approaches capacity limit (recommended <{recommended_max}lbs)"
    else:
        return f"✅ Payload: {total_payload:.1f}lbs (within safe limits)"


def format_sequence_plan(plan: SequencePlan) -> str:
    output = []
    output.append(f"Sequence Plan for {plan.target.name}")
    output.append("=" * (len(plan.target.name) + 17))
    output.append(f"Target: {plan.target.name} (Mag {plan.target.magnitude}, {plan.target.target_type.value})")
    output.append(f"Setup: {plan.setup.name}")
    output.append(f"Total Time: {plan.total_time_minutes:.1f} minutes")
    output.append(f"Estimated SNR: {plan.estimated_snr:.0f}")
    output.append(check_mount_capacity(plan.setup, plan.camera))
    
    # Session time warning for unattended operation
    if plan.total_time_minutes > 480:  # > 8 hours
        output.append("⚠️  Long session: Consider splitting across multiple nights")
    elif plan.total_time_minutes > 300:  # > 5 hours
        output.append("ℹ️  Extended session: Monitor weather and equipment")
    
    output.append("")
    
    headers = ["Filter", "Exposure (s)", "Count", "Total (min)", "Binning"]
    rows = []
    
    for seq in plan.filter_sequences:
        total_min = (seq.exposure_seconds * seq.count) / 60
        rows.append([
            seq.filter_type.value,
            str(seq.exposure_seconds),
            str(seq.count),
            f"{total_min:.1f}",
            f"{seq.binning}x{seq.binning}"
        ])
    
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    
    def format_row(row):
        return " | ".join(str(item).ljust(col_widths[i]) for i, item in enumerate(row))
    
    separator = "-+-".join("-" * width for width in col_widths)
    
    output.append(format_row(headers))
    output.append(separator)
    for row in rows:
        output.append(format_row(row))
    
    return "\n".join(output)


def load_config_file(filepath: str) -> Dict[str, Any]:
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Error loading config file {filepath}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Astrophotography setup analyzer and sequence planner"
    )
    parser.add_argument(
        "--config", 
        help="JSON config file with camera and scope specifications"
    )
    parser.add_argument(
        "--output", 
        choices=["table", "json"], 
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--camera-pixel-size", 
        type=float,
        help="Camera pixel size in microns (overrides default/config)"
    )
    parser.add_argument(
        "--camera-sensor-width", 
        type=float,
        help="Camera sensor width in mm (overrides default/config)"  
    )
    parser.add_argument(
        "--camera-sensor-height", 
        type=float,
        help="Camera sensor height in mm (overrides default/config)"
    )
    
    # Sequence planning arguments
    parser.add_argument(
        "--sequence",
        action="store_true",
        help="Generate sequence plans instead of setup analysis"
    )
    parser.add_argument(
        "--target-name",
        help="Target name for sequence planning"
    )
    parser.add_argument(
        "--target-magnitude",
        type=float,
        help="Target magnitude"
    )
    parser.add_argument(
        "--target-type",
        choices=["galaxy", "nebula", "planetary", "globular_cluster", "open_cluster", "double_star"],
        help="Target type"
    )
    parser.add_argument(
        "--sequence-type",
        choices=["lrgb", "narrowband", "lpro"],
        default="lpro",
        help="Sequence type (default: lpro)"
    )
    parser.add_argument(
        "--total-time",
        type=int,
        default=300,
        help="Total imaging time in minutes (default: 300)"
    )
    parser.add_argument(
        "--setup-name",
        help="Specific setup to use for sequence planning"
    )
    
    args = parser.parse_args()
    
    try:
        camera = get_default_camera()
        setups = get_default_setups()
        
        if args.config:
            config = load_config_file(args.config)
            if "camera" in config:
                cam_data = config["camera"]
                camera = CameraSpec(**cam_data)
            if "setups" in config:
                setups = [ScopeSetup(**setup) for setup in config["setups"]]
        
        if args.camera_pixel_size:
            camera.pixel_size_um = args.camera_pixel_size
        if args.camera_sensor_width:
            camera.sensor_width_mm = args.camera_sensor_width
        if args.camera_sensor_height:
            camera.sensor_height_mm = args.camera_sensor_height
        
        if args.sequence:
            # Sequence planning mode
            if not all([args.target_name, args.target_magnitude, args.target_type]):
                print("Error: --target-name, --target-magnitude, and --target-type are required for sequence planning", file=sys.stderr)
                sys.exit(1)
            
            target = Target(
                name=args.target_name,
                ra_hours=0.0,  # Not used in calculations
                dec_degrees=0.0,  # Not used in calculations
                magnitude=args.target_magnitude,
                target_type=TargetType(args.target_type)
            )
            
            # Select setup - default to Rokinon 135mm
            if args.setup_name:
                selected_setups = [s for s in setups if args.setup_name.lower() in s.name.lower()]
                if not selected_setups:
                    print(f"Error: Setup '{args.setup_name}' not found", file=sys.stderr)
                    sys.exit(1)
                setup = selected_setups[0]
            else:
                # Default to Rokinon 135mm f/2 (best for L-Pro wide field)
                rokinon_setups = [s for s in setups if "rokinon" in s.name.lower()]
                setup = rokinon_setups[0] if rokinon_setups else setups[0]
            
            # Generate sequence plan
            if args.sequence_type == "lrgb":
                plan = create_lrgb_sequence(target, setup, camera, args.total_time)
            elif args.sequence_type == "narrowband":
                plan = create_narrowband_sequence(target, setup, camera, args.total_time)
            else:  # lpro
                plan = create_lpro_sequence(target, setup, camera, args.total_time)
            
            if args.output == "json":
                output_data = {
                    "target": asdict(target),
                    "setup": asdict(setup),
                    "camera": asdict(camera),
                    "plan": asdict(plan)
                }
                print(json.dumps(output_data, indent=2, cls=EnumEncoder))
            else:
                print(format_sequence_plan(plan))
        else:
            # Setup analysis mode
            metrics = [analyze_setup(setup, camera) for setup in setups]
            
            if args.output == "json":
                output_data = {
                    "camera": asdict(camera),
                    "results": [asdict(m) for m in metrics]
                }
                print(json.dumps(output_data, indent=2))
            else:
                print("Astrophotography Setup Analysis")
                print("=" * 40)
                print(f"Camera: {camera.sensor_width_mm}x{camera.sensor_height_mm}mm, {camera.pixel_size_um}µm pixels")
                print()
                print(format_table(metrics))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()