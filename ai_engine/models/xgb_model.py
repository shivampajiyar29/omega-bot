"""XGBoost classifier model — predicts UP/DOWN."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_PATH  = Path(__file__).parent / "saved" / "xgb_model.json"
SCALER_PATH = Path(__file__).parent / "saved" / "xgb_scaler.pkl"


class XGBoostPredictor:
    def __init__(self):
        self.model  = None
        self.scaler = None
        self._ready = False

    def load_or_train(self, feature_cols: List[str], force: bool = False):
        if not force and MODEL_PATH.exists() and SCALER_PATH.exists():
            self._load()
        else:
            logger.info("XGBoost: training on synthetic data…")
            self._train(feature_cols)

    def _load(self):
        try:
            import xgboost as xgb, joblib
            self.model  = xgb.XGBClassifier()
            self.model.load_model(str(MODEL_PATH))
            self.scaler = joblib.load(str(SCALER_PATH))
            self._ready = True
            logger.info("XGBoost loaded from disk")
        except Exception as e:
            logger.warning(f"XGBoost load failed ({e}), retraining…")
            from ai_engine.core.features import get_feature_columns
            self._train(get_feature_columns())

    def _train(self, feature_cols: List[str]):
        try:
            import xgboost as xgb, joblib
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import train_test_split
            from ai_engine.data.generator import generate_synthetic_ohlcv
            from ai_engine.core.features import build_features, create_labels

            ohlcv  = generate_synthetic_ohlcv(2500, seed=42)
            df     = build_features(ohlcv)
            labels = create_labels(df)

            used = [c for c in feature_cols if c in df.columns]
            X = df[used].values
            y = labels.values[:len(X)]
            valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X, y = X[valid], y[valid].astype(int)

            self.scaler = StandardScaler()
            Xs = self.scaler.fit_transform(X)
            Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, shuffle=False)

            self.model = xgb.XGBClassifier(
                n_estimators=300, max_depth=5, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                use_label_encoder=False, eval_metric="logloss",
                random_state=42, n_jobs=-1,
            )
            self.model.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)

            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(str(MODEL_PATH))
            joblib.dump(self.scaler, str(SCALER_PATH))
            self._ready = True

            from sklearn.metrics import accuracy_score
            acc = accuracy_score(yte, self.model.predict(Xte))
            logger.info(f"XGBoost trained — test accuracy: {acc:.3f}")
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")

    def predict(self, features_df: pd.DataFrame, feature_cols: List[str]) -> Tuple[int, float]:
        if not self._ready:
            return 1, 0.5   # default: weakly bullish
        used = [c for c in feature_cols if c in features_df.columns]
        X = features_df[used].iloc[[-1]].values
        Xs = self.scaler.transform(X)
        proba = self.model.predict_proba(Xs)[0]
        pred = int(np.argmax(proba))
        return pred, float(proba[pred])

    @property
    def is_ready(self) -> bool:
        return self._ready
