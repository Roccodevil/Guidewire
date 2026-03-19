import json

from app.ml_engine import FraudNeuralNet


def main():
    nn = FraudNeuralNet()
    scenarios = {
        "expected_valid": {
            "live_speed": 12.0,
            "deviation": 0.5,
            "time_of_day": 17.5,
            "hist_speed": 35.0,
        },
        "expected_flagged": {
            "live_speed": 45.0,
            "deviation": 12.0,
            "time_of_day": 2.0,
            "hist_speed": 30.0,
        },
    }

    output = {}
    for scenario_name, features in scenarios.items():
        fraud_prob, shap_values = nn.predict_and_explain(**features)
        output[scenario_name] = {
            "features": features,
            "fraud_probability": fraud_prob,
            "shap_importance": shap_values,
        }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()