import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

def generate_policy_tiers(ar_baseline_risk: float, weather_forecast: str) -> list:
    """
    Uses Groq LLM to generate 3 policy tiers (Basic, Standard, Premium) 
    with XAI descriptions justifying the price based on AR data and weather.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        # Hackathon Fallback
        return [
            {"tier": "Basic", "premium": 25, "coverage": 1000, "xai": f"Low cost cover based on {weather_forecast}."},
            {"tier": "Standard", "premium": 35, "coverage": 2500, "xai": f"Recommended. Accounts for AR risk score of {ar_baseline_risk}."},
            {"tier": "Premium", "premium": 50, "coverage": 5000, "xai": "Max protection for severe disruption zones."}
        ]

    llm = ChatGroq(temperature=0.2, model_name="llama3-8b-8192", groq_api_key=api_key)
    
    prompt = PromptTemplate.from_template("""
    You are an Actuary AI for a gig-worker insurance platform.
    Current Base Risk Score (from Autoregressor): {ar_risk}
    Upcoming Weather: {weather}
    
    Generate exactly 3 policy tiers (Basic, Standard, Premium).
    For each, calculate a weekly premium (in ₹), a coverage limit, and a 1-sentence "xai_description" 
    explaining WHY this price is fair given the risk and weather.
    
    Output strictly as a JSON array of 3 objects with keys: "tier", "premium", "coverage", "xai".
    """)

    chain = prompt | llm
    try:
        response = chain.invoke({"ar_risk": ar_baseline_risk, "weather": weather_forecast})
        return json.loads(response.content)
    except:
        return [{"tier": "Standard", "premium": 35, "coverage": 2500, "xai": "Default policy generated due to LLM timeout."}]

def recommend_best_policy(wallet_balance: float, tiers: list) -> str:
    """Simple expert system to recommend a policy to the worker."""
    if wallet_balance > 1500:
        return "Premium"
    elif wallet_balance > 500:
        return "Standard"
    return "Basic"

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