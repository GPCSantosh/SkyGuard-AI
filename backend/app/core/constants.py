"""Core physical meteorological constants and bounds."""

# Temperature physical bounds (°C)
TEMP_PHYSICAL_MIN_C: float = -50.0
TEMP_PHYSICAL_MAX_C: float = 60.0

# Barometric pressure physical bounds (hPa)
PRESSURE_PHYSICAL_MIN_HPA: float = 500.0
PRESSURE_PHYSICAL_MAX_HPA: float = 1080.0

# Relative humidity physical bounds (%)
HUMIDITY_PHYSICAL_MIN_PCT: float = 0.0
HUMIDITY_PHYSICAL_MAX_PCT: float = 100.0

# Default sampling cadence in seconds (5 minutes)
DEFAULT_SAMPLING_INTERVAL_SECONDS: int = 300

# Earth mean radius in kilometers for Haversine geodesic calculations
EARTH_RADIUS_KM: float = 6371.0088
