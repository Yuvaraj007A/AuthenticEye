from detectors.registry import get_registry, DetectorRegistry

# Import all detectors
from detectors.efficientnet_dfdc import EfficientNetDFDC
from detectors.xception_ffpp import XceptionFFPP
from detectors.synthid import SynthIDDetector
from detectors.frequency_forensics import FrequencyForensics
from detectors.metadata_analyzer import MetadataAnalyzer
from detectors.temporal_video import TemporalVideoAnalyzer
from detectors.c2pa_detector import C2PADetector

# Get global registry instance
registry = get_registry()

# Register all 7 detectors
registry.register("EfficientNetDFDC", EfficientNetDFDC)
registry.register("XceptionFFPP", XceptionFFPP)
registry.register("SynthIDDetector", SynthIDDetector)
registry.register("FrequencyForensics", FrequencyForensics)
registry.register("MetadataAnalyzer", MetadataAnalyzer)
registry.register("TemporalVideoAnalyzer", TemporalVideoAnalyzer)
registry.register("C2PADetector", C2PADetector)


# Export registry
__all__ = ["registry", "DetectorRegistry"]
