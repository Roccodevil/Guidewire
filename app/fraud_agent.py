import json
import os
import re
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from app.ml_engine import FraudNeuralNet


def _current_hour_decimal() -> float:
    now = datetime.now()
    return round(now.hour + (now.minute / 60), 2)


def _fallback_xai(fraud_prob: float, shap_importance: dict[str, float]) -> dict:
    status = "APPROVED" if fraud_prob < 0.5 else "FLAGGED"
    strongest_features = sorted(
        shap_importance.items(),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:2]

    if strongest_features:
        reasons = []
        for feature_name, weight in strongest_features:
            direction = "increased" if weight >= 0 else "reduced"
            reasons.append(f"{feature_name} {direction} the fraud score ({weight})")
        explanation = f"{status.title()} because " + " and ".join(reasons) + "."
    else:
        explanation = f"{status.title()} using the neural network fallback decision."

    return {
        "fraud_score": round(fraud_prob, 3),
        "status": status,
        "xai_explanation": explanation,
    }


def _parse_llm_json(content: str) -> dict | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def analyze_claim_validity(route_data: dict, suggested_action: str) -> dict:
    """
    Runs neural-network fraud inference and lets the LLM translate SHAP output into XAI.
    """
    live_speed = float(route_data.get("live_speed_kph", 12.0))
    route_deviation = float(route_data.get("route_deviation_km", 0.5))
    time_of_day = float(route_data.get("time_of_day_hours", _current_hour_decimal()))
    historical_speed = float(route_data.get("historical_avg_speed_kph", 35.0))

    nn = FraudNeuralNet()
    fraud_prob, shap_importance = nn.predict_and_explain(
        live_speed=live_speed,
        deviation=route_deviation,
        time_of_day=time_of_day,
        hist_speed=historical_speed,
    )

    fallback_result = _fallback_xai(fraud_prob, shap_importance)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return fallback_result

    llm = ChatGroq(
        temperature=0,
        model_name="llama3-8b-8192",
        groq_api_key=api_key,
    )

    prompt = PromptTemplate.from_template(
        """
    You are an XAI translator for a gig-worker insurance platform.
    A neural network just analyzed a parametric claim trigger.

    Raw Telemetry: {route_data}
    Trigger Event: {suggested_action}
    Neural Network Fraud Probability: {fraud_prob} (0.0 to 1.0)
    SHAP Feature Importance: {shap_importance}

    Task: Translate this into a 1-sentence human-readable audit log.
    Explain why the claim is valid or fraudulent based heavily on the SHAP feature importance.

    Provide your output strictly as a JSON object with three keys:
    1. "fraud_score": The exact float provided ({fraud_prob}).
    2. "status": "APPROVED" if score < 0.5, else "FLAGGED".
    3. "xai_explanation": Your 1-sentence translation of the neural network's logic.
    """
    )

    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "route_data": json.dumps(route_data),
                "suggested_action": suggested_action,
                "fraud_prob": round(fraud_prob, 3),
                "shap_importance": json.dumps(shap_importance),
            }
        )
        result = _parse_llm_json(response.content)
        if not result:
            return fallback_result

        result["fraud_score"] = round(fraud_prob, 3)
        result["status"] = "APPROVED" if fraud_prob < 0.5 else "FLAGGED"
        result.setdefault("xai_explanation", fallback_result["xai_explanation"])
        return result
    except Exception as error:
        print(f"LLM Error: {error}")
        return fallback_result