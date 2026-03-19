from typing import TypedDict


class ClaimState(TypedDict):
    worker_id: int
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    route_data: dict
    parametric_triggered: bool
    fraud_score: float
    fraud_status: str
    xai_explanation: str
    suggested_action: str
