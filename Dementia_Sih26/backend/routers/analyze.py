"""
analyze.py — NeuroAid V5
Unified routing wrapper aligning analyze.py with analyze_api.py.
"""

from routers.analyze_api import (
    router,
    analyze,
    get_my_results,
    get_patient_results,
    _compute_composite_risk,
    _compute_risk_drivers,
    DISCLAIMER,
)

__all__ = [
    "router",
    "analyze",
    "get_my_results",
    "get_patient_results",
    "_compute_composite_risk",
    "_compute_risk_drivers",
    "DISCLAIMER",
]
