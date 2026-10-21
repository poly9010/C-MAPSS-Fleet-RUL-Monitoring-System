"""최종 모델 학습·저장. 이미 CV로 정한 설정(N=30, 상한 115, HistGradientBoosting)을
dev 80대 전체(폴드 나누지 않고 전부)로 학습해서 models/에 저장한다.

주의: 이 스크립트는 test 데이터를 전혀 쓰지 않는다. test 평가는 따로, 최대 2회 규칙을 지켜서 한다.
다시 실행하면 기존 모델 파일을 덮어쓴다.
"""
import json
from datetime import datetime

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.config import ROOT, DATA_PROCESSED, SPLIT_PATH, MODELS_DIR, SENSORS, WINDOW_N, RUL_CAP, SEED
from src.evaluate import cap_rul
from src.features import make_features, feature_columns


def load_dev_data():
    df = pd.read_csv(DATA_PROCESSED, index_col=0)
    split = pd.read_csv(SPLIT_PATH)

    feats = make_features(df, N=WINDOW_N, sensors=SENSORS)
    feats = feats.merge(df[["engine_id", "cycle", "RUL"]], on=["engine_id", "cycle"])
    feats = feats.merge(split, on="engine_id")
    return feats.query("role == 'dev'").reset_index(drop=True)


def train_final_model():
    dev = load_dev_data()
    X_cols = feature_columns(SENSORS)

    X = dev[X_cols]
    y = cap_rul(dev["RUL"], RUL_CAP)   # 학습 라벨만 상한 적용

    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=SEED)
    model.fit(X, y)

    MODELS_DIR.mkdir(exist_ok=True)
    model_path = MODELS_DIR / "rul_model.pkl"
    joblib.dump(model, model_path)

    meta = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "window_n": WINDOW_N,
        "rul_cap": RUL_CAP,
        "sensors": SENSORS,
        "feature_columns": X_cols,
        "model_type": type(model).__name__,
        "model_params": {"max_iter": 300, "learning_rate": 0.05, "random_state": SEED},
        "train_engine_ids": sorted(dev["engine_id"].unique().tolist()),
        "n_train_rows": len(dev),
        "source_data": str(DATA_PROCESSED.relative_to(ROOT)),
    }
    meta_path = MODELS_DIR / "rul_model_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"모델 저장: {model_path}")
    print(f"설정 저장: {meta_path}")
    print(f"학습 엔진 수: {len(meta['train_engine_ids'])} / 행 수: {meta['n_train_rows']}")
    return model, meta


if __name__ == "__main__":
    train_final_model()