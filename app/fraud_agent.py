import os
import json
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.ml_engine import FraudNeuralNet


# 1. Define strict output schema for the LLM
class FraudAudit(BaseModel):
    fraud_score: float = Field(description="The exact float probability provided by the NN")
    status: str = Field(description="'APPROVED' if score < 0.5, else 'FLAGGED'")
    xai_explanation: str = Field(description="A 1-sentence translation explaining the SHAP feature importance")


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


def analyze_claim_validity(route_data: dict, suggested_action: str) -> dict:
    """
    Runs neural-network fraud inference and lets the LLM translate SHAP output into XAI.
    Utilizes Pydantic for strict output parsing.
    """
    # 2. Extract telemetry for the Neural Network
    live_speed = float(route_data.get("live_speed_kph", 12.0))
    route_deviation = float(route_data.get("route_deviation_km", 0.5))
    time_of_day = float(route_data.get("time_of_day_hours", _current_hour_decimal()))
    historical_speed = float(route_data.get("historical_avg_speed_kph", 35.0))

    # 3. Run Inference & SHAP Extraction
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

    # 4. Set up Pydantic Parser and LLM
    parser = PydanticOutputParser(pydantic_object=FraudAudit)
    
    llm = ChatGroq(
        temperature=0.0,
        model_name="llama-3.1-8b-instant",
        groq_api_key=api_key,
    )

    # 5. Inject format instructions into the prompt
    prompt = PromptTemplate(
        template="""
        You are an XAI translator for a gig-worker insurance platform.
        A neural network just analyzed a parametric claim trigger.

        Raw Telemetry: {route_data}
        Trigger Event: {suggested_action}
        Neural Network Fraud Probability: {fraud_prob} (0.0 to 1.0)
        SHAP Feature Importance: {shap_importance}

        Task: Translate this into a 1-sentence human-readable audit log.
        Explain why the claim is valid or fraudulent based heavily on the SHAP feature importance.

        {format_instructions}
        """,
        input_variables=["route_data", "suggested_action", "fraud_prob", "shap_importance"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    # 6. Chain components together
    chain = prompt | llm | parser

    try:
        # Execute chain. Pydantic guarantees a FraudAudit object is returned.
        result = chain.invoke(
            {
                "route_data": json.dumps(route_data),
                "suggested_action": suggested_action,
                "fraud_prob": round(fraud_prob, 3),
                "shap_importance": json.dumps(shap_importance),
            }
        )
        
        # Convert Pydantic object to dictionary
        final_dict = result.dict()
        
        # Security check: Ensure the LLM didn't hallucinate a different fraud score
        final_dict["fraud_score"] = round(fraud_prob, 3)
        final_dict["status"] = "APPROVED" if fraud_prob < 0.5 else "FLAGGED"
        
        return final_dict
        
    except Exception as error:
        print(f"LLM Pydantic Error: {error}")
        return fallback_result