"""Mechanics calculations for a vertical squat jump."""
import math

G = 9.81


def calculate_metrics(flight_time_s, mass_kg, push_off_distance_m):
    """Return idealised estimates; inputs must be positive and flight time > 0."""
    T = float(flight_time_s)
    m = float(mass_kg)
    d = float(push_off_distance_m)
    if not (math.isfinite(T) and T > 0 and math.isfinite(m) and m > 0
            and math.isfinite(d) and d > 0):
        raise ValueError("Flight time, mass and push-off distance must be positive finite values.")

    h = G * T * T / 8.0
    v_takeoff = G * T / 2.0
    mean_force = m * G * (1.0 + h / d)
    mean_velocity = v_takeoff / 2.0
    mean_power = mean_force * mean_velocity
    return {
        "flight_time_s": T,
        "jump_height_m": h,
        "jump_height_cm": h * 100.0,
        "takeoff_velocity_m_s": v_takeoff,
        "mean_push_force_N": mean_force,
        "mean_push_velocity_m_s": mean_velocity,
        "mean_push_power_W": mean_power,
        "mean_push_power_W_kg": mean_power / m,
        "assumed_gravity_m_s2": G,
        "model_assumptions": [
            "Vertical ballistic flight with negligible air resistance",
            "COM height at take-off equals COM height at landing",
            "COM starts push-off from rest",
            "Constant vertical COM acceleration during push-off for mean velocity",
            "Mean force estimated using body mass, jump height and push-off distance",
            "No direct force-plate measurement",
        ],
    }
