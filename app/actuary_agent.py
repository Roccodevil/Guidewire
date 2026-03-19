from app.ml_engine import PricingAutoregressor
from app.services import get_weather_forecast


def calculate_weekly_premium(worker_zone_lat: float, worker_zone_lon: float) -> dict:
    """
    Actuary logic to dynamically price the insurance for the upcoming week.
    The autoregressive forecast sets the baseline and live weather adjusts it.
    """
    ar_model = PricingAutoregressor()
    base_premium = ar_model.forecast_next_week_risk()
    weather_data = get_weather_forecast(worker_zone_lat, worker_zone_lon)

    surcharge = 0.0
    if weather_data["risk_multiplier"] > 1.0:
        surcharge = base_premium * 0.4

    total_premium = round(base_premium + surcharge, 2)

    return {
        "base_premium": base_premium,
        "weather_surcharge": round(surcharge, 2),
        "total_premium": total_premium,
        "explanation": (
            f"Autoregressive Base: ₹{base_premium} + Weather Risk "
            f"({weather_data['forecast']}): ₹{round(surcharge, 2)}"
        ),
    }
