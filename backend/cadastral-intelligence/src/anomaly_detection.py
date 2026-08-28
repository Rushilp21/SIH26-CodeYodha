"""Anomaly detection stubs. Types: boundary_shift, overlap, encroachment, topology_break."""

ANOMALY_TYPES = ("boundary_shift", "overlap", "encroachment", "topology_break")


def detect_anomalies(parcels: list[dict]) -> list[dict]:
    """TODO(dev3): implement detectors. Returns list of {parcel_id, type, magnitude}."""
    return []
