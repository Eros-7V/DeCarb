import math


def linear_ramp(start_year: int, duration_years: int, year: float) -> float:
    """Compute linear ramp commitment fraction [0, 1] for a given year."""
    if duration_years <= 0:
        return 1.0 if year >= start_year else 0.0
    if year < start_year:
        return 0.0
    if year >= start_year + duration_years:
        return 1.0
    return (year - start_year) / duration_years


def s_curve_ramp(start_year: int, duration_years: int, year: float) -> float:
    """Compute S-curve ramp commitment fraction [0, 1] using sigmoid approximation."""
    if duration_years <= 0:
        return 1.0 if year >= start_year else 0.0
    if year < start_year:
        return 0.0
    if year >= start_year + duration_years:
        return 1.0
    t = (year - start_year) / duration_years
    return 1.0 / (1.0 + math.exp(-12.0 * (t - 0.5)))


def get_ramp_commitment(
    lever: dict,
    year: float,
    start_year_override: int | None = None,
    duration_override: int | None = None,
) -> float:
    """Get commitment fraction for a lever in a given year."""
    ramp = lever.get("ramp", {})
    start_year = start_year_override if start_year_override is not None else ramp.get("default_start_year", 0)
    duration_years = (
        duration_override if duration_override is not None else ramp.get("default_duration_years", 0)
    )
    curve = ramp.get("curve", "linear")
    if curve == "s_curve":
        return s_curve_ramp(start_year, duration_years, year)
    return linear_ramp(start_year, duration_years, year)
