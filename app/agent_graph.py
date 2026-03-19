from langgraph.graph import END, StateGraph

from app.fraud_agent import analyze_claim_validity
from app.agent_state import ClaimState
from app.services import get_tomtom_route_data


def ingest_data_node(state: ClaimState):
    route_data = get_tomtom_route_data(
        state["origin_lat"],
        state["origin_lon"],
        state["dest_lat"],
        state["dest_lon"],
    )
    return {"route_data": route_data}


def route_analysis_node(state: ClaimState):
    route = state.get("route_data", {})
    if route.get("status") == "NO_ROUTE_FOUND" or route.get("delay_mins", 0) > 45:
        return {
            "parametric_triggered": True,
            "suggested_action": "Severe Gridlock. Automated Claim Initiated.",
        }
    if route.get("is_severely_disrupted") and route.get("has_better_alternative"):
        return {
            "parametric_triggered": False,
            "suggested_action": "Traffic ahead. Rerouting to protect earnings.",
        }
    if route.get("is_severely_disrupted"):
        return {
            "parametric_triggered": True,
            "suggested_action": "Unavoidable delay detected. Micro-claim initiated.",
        }
    return {"parametric_triggered": False, "suggested_action": "Route Clear."}


def fraud_check_node(state: ClaimState):
    """Passes the claim to the NN + LLM stack for XAI verification."""
    print("Initiating neuro-symbolic fraud analysis...")
    analysis = analyze_claim_validity(
        route_data=state.get("route_data", {}),
        suggested_action=state.get("suggested_action", ""),
    )

    updated_action = (
        f"{state['suggested_action']} | XAI Audit: {analysis['xai_explanation']}"
    )

    return {
        "fraud_score": analysis["fraud_score"],
        "fraud_status": analysis["status"],
        "xai_explanation": analysis["xai_explanation"],
        "suggested_action": updated_action,
    }


def check_trigger_routing(state: ClaimState):
    if state["parametric_triggered"]:
        return "fraud_check"
    return END


workflow = StateGraph(ClaimState)
workflow.add_node("ingest_data", ingest_data_node)
workflow.add_node("route_analysis", route_analysis_node)
workflow.add_node("fraud_check", fraud_check_node)
workflow.set_entry_point("ingest_data")
workflow.add_edge("ingest_data", "route_analysis")
workflow.add_conditional_edges(
    "route_analysis",
    check_trigger_routing,
    {"fraud_check": "fraud_check", END: END},
)
workflow.add_edge("fraud_check", END)

insurance_graph = workflow.compile()
