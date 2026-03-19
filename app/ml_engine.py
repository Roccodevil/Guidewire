from __future__ import annotations

from typing import Any

import numpy as np

try:
    import shap
except ImportError:
    shap = None

try:
    from sklearn.neural_network import MLPClassifier
except ImportError:
    MLPClassifier = None

try:
    from statsmodels.tsa.ar_model import AutoReg
except ImportError:
    AutoReg = None


class PricingAutoregressor:
    def __init__(self):
        # Mock weekly historical baseline risk. In production, load this from a feature store.
        self.historical_risk_scores = np.array(
            [20, 22, 19, 25, 30, 45, 50, 40, 35, 20],
            dtype=float,
        )

    def forecast_next_week_risk(self) -> float:
        """Uses an autoregressive model to predict next week's baseline risk."""
        try:
            if AutoReg is None:
                raise ImportError

            model = AutoReg(self.historical_risk_scores, lags=1, old_names=False)
            model_fit = model.fit()
            prediction = model_fit.predict(
                start=len(self.historical_risk_scores),
                end=len(self.historical_risk_scores),
            )
            next_risk = float(np.asarray(prediction).ravel()[0])
        except Exception:
            recent_scores = self.historical_risk_scores[-5:]
            weights = np.linspace(1.0, 2.0, len(recent_scores))
            next_risk = float(np.average(recent_scores, weights=weights))

        return round(max(next_risk, 0.0), 2)


class FraudNeuralNet:
    def __init__(self):
        self.feature_names = [
            "Live Speed",
            "Route Deviation",
            "Time of Day",
            "Historical Speed",
        ]

        self.background = np.array(
            [
                [35.0, 0.5, 14.0, 34.0],
                [5.0, 0.1, 18.0, 10.0],
                [45.0, 12.0, 2.0, 30.0],
                [0.0, 0.0, 15.0, 35.0],
                [12.0, 0.8, 17.5, 35.0],
                [28.0, 0.3, 11.0, 30.0],
            ],
            dtype=float,
        )
        y_train = np.array([0, 0, 1, 1, 0, 0], dtype=int)

        self.model = None
        if MLPClassifier is not None:
            self.model = MLPClassifier(
                hidden_layer_sizes=(16, 8),
                max_iter=1000,
                random_state=42,
            )
            self.model.fit(self.background, y_train)

        self._explainer: Any | None = None

    def _get_explainer(self) -> Any | None:
        if shap is None or self.model is None:
            return None

        if self._explainer is None:
            self._explainer = shap.KernelExplainer(
                self.model.predict_proba,
                self.background,
            )
        return self._explainer

    def _extract_positive_class_values(self, shap_values: Any) -> np.ndarray:
        if isinstance(shap_values, list):
            return np.asarray(shap_values[1])[0]

        values = np.asarray(shap_values)
        if values.ndim == 3:
            if values.shape[0] == 1:
                return values[0, :, -1]
            if values.shape[-1] == 1:
                return values[0, :, 0]
        if values.ndim == 2:
            return values[0]

        raise ValueError("Unexpected SHAP output shape.")

    def _heuristic_importance(self, features: np.ndarray) -> np.ndarray:
        baseline = self.background.mean(axis=0)
        scale = np.where(np.abs(baseline) < 1.0, 1.0, np.abs(baseline))
        return (features[0] - baseline) / scale

    def _predict_fraud_probability(self, features: np.ndarray) -> float:
        if self.model is not None:
            return float(self.model.predict_proba(features)[0][1])

        live_speed, deviation, time_of_day, hist_speed = features[0]
        speed_gap = max(hist_speed - live_speed, 0.0) / max(hist_speed, 1.0)
        deviation_factor = min(deviation / 10.0, 1.5)
        odd_hour_factor = 1.0 if time_of_day < 5.0 or time_of_day > 22.0 else 0.0
        fraud_score = (0.45 * speed_gap) + (0.35 * deviation_factor) + (0.20 * odd_hour_factor)
        return float(np.clip(fraud_score, 0.0, 1.0))

    def predict_and_explain(
        self,
        live_speed: float,
        deviation: float,
        time_of_day: float,
        hist_speed: float,
    ) -> tuple[float, dict[str, float]]:
        """Runs inference and generates SHAP feature importance for explainability."""
        features = np.array([[live_speed, deviation, time_of_day, hist_speed]], dtype=float)

        fraud_prob = self._predict_fraud_probability(features)

        try:
            explainer = self._get_explainer()
            if explainer is None:
                raise RuntimeError

            shap_values = explainer.shap_values(features, nsamples=100)
            importance_vector = self._extract_positive_class_values(shap_values)
        except Exception:
            importance_vector = self._heuristic_importance(features)

        importance = {
            self.feature_names[index]: round(float(value), 3)
            for index, value in enumerate(importance_vector)
        }

        return round(fraud_prob, 3), importance