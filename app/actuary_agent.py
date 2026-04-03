import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List

# Import YOUR custom ML engine
from app.ml_engine import PricingAutoregressor 

class PolicyTier(BaseModel):
    tier: str = Field(description="Name of the tier (e.g., 'Monsoon Shield')")
    premium: float = Field(description="Calculated weekly premium in INR")
    coverage: float = Field(description="Maximum payout limit in INR")
    profit_margin_pct: float = Field(description="Projected platform profit margin % (e.g., 15.5)")
    xai_actuarial_reasoning: str = Field(description="Underwriter justification: Explain the math. Mention the AR risk score, the weather multiplier, and why this premium guarantees platform liquidity.")
    terms: str = Field(description="Strict legal Terms & Conditions (e.g., 'Subject to a 30-min parametric deductible. Payouts capped at coverage limit.')")
    rules: str = Field(description="Algorithmic execution rules (e.g., 'Trigger fires only if TomTom API confirms route deviation > 1km or delay > 30m.')")

class PolicyList(BaseModel):
    policies: List[PolicyTier] = Field(description="List of exactly 2 policy options")

def generate_policy_tiers(ar_baseline_risk: float, weather_forecast: str) -> list:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return [{"tier": "Fallback", "premium": 35, "coverage": 2500, "profit_margin_pct": 20.0, "xai_actuarial_reasoning": "API Key Missing", "terms": "Standard", "rules": "Standard"}]

    parser = PydanticOutputParser(pydantic_object=PolicyList)
    llm = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=api_key)
    
    prompt = PromptTemplate(
        template="""
        You are the Chief Actuary for an Indian gig-worker insurance platform.
        Your goal is to price parametric insurance policies that protect worker income while ensuring the platform remains profitable.
        
        DATA:
        - ML Autoregressive Risk Score: {ar_risk}/100 (Historical claim frequency)
        - Live Weather Forecast: {weather}
        - Target Loss Ratio: 75% (Aim to pay out 75% of premiums collected, keep 25% as gross profit).
        
        TASK:
        Generate exactly 2 targeted insurance policies. 
        For 'xai_actuarial_reasoning', explicitly explain your pricing math to the board of directors. Mention the Target Loss Ratio and the exact weather risks.
        For 'terms' and 'rules', write strict, professional insurance underwriting conditions.
        
        {format_instructions}
        """,
        input_variables=["ar_risk", "weather"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser
    try:
        result = chain.invoke({"ar_risk": ar_baseline_risk, "weather": weather_forecast})
        return [policy.dict() for policy in result.policies]
    except Exception as e:
        print(f"Actuary AI Error: {e}")
        return [{"tier": "LLM Error", "premium": 40, "coverage": 3000, "profit_margin_pct": 20.0, "xai_actuarial_reasoning": "Format failed.", "terms": "Error", "rules": "Error"}]
def run_autonomous_actuary() -> list:
    """Master function triggered by the Admin Dashboard."""
    # 1. Instantiate YOUR Autoregressor
    ar_model = PricingAutoregressor()
    predicted_ar_risk = ar_model.forecast_next_week_risk()
    
    # 2. Fetch Live Weather Data
    from app.services import get_weather_forecast
    live_weather = get_weather_forecast(28.6139, 77.2090)
    
    print(f"--- ACTUARY RUN ---")
    print(f"Predicted ML Risk: {predicted_ar_risk}")
    print(f"Weather Forecast: {live_weather['forecast']}")
    
    # 3. Pass to LLM
    new_policies = generate_policy_tiers(predicted_ar_risk, live_weather['forecast'])
    return new_policies

def recommend_best_policy(wallet_balance: float, tiers: list) -> str:
    affordable = [t for t in tiers if wallet_balance >= (t.premium * 3)] 
    if affordable:
        return max(affordable, key=lambda x: x.coverage_limit).tier
    return tiers[0].tier if tiers else None