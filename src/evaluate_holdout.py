"""최종 hold-out 평가 (replay 20대, 1회용).

- 저장된 최종 모델(models/rul_model.pkl, dev 80대로 학습)을 그대로 쓴다. 재학습·튜닝 없음.
- replay 20대는 학습·CV·알람 기준 결정 어디에도 쓰지 않은 엔진 → '처음 보는 엔진' 성능.
- 채점 기준은 CV와 동일: 상한 없는 실제 RUL <= 115 구간 (src/evaluate.py).
- 알람 규칙도 dev OOF로 정한 값(T=40, L=20)을 그대로 적용해 놓침·리드타임을 확인한다.

train.py의 'test 평가 최대 2회' 규칙 때문에, 결과 파일이 이미 있으면 실행을 멈춘다.
정말 다시 돌려야 할 때만 --force (2회차로 기록됨).

실행: 프로젝트 루트에서  python -m src.evaluate_holdout
"""
import json
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from src.config import ROOT, DATA_PROCESSED, SPLIT_PATH, MODEL_PATH, WINDOW_N, ALARM_T
from src.evaluate import evaluate
from src.features import make_features, feature_columns
from src.alarm_analysis import engine_alarms

ALARM_L = 20                      # config에는 AMARM_L(오타)로 되어 있어 여기서 명시
OUT_DIR = ROOT / "reports" / "holdout"
RESULT_PATH = OUT_DIR / "holdout_result.json"
PRED_PATH = OUT_DIR / "holdout_pred.csv"
LOG_PATH = OUT_DIR / "holdout_runs.log"


def main(force=False):
    if RESULT_PATH.exists() and not force:
        print(f"이미 평가 결과가 있습니다: {RESULT_PATH.relative_to(ROOT)}")
        print("다시 평가하면 hold-out 사용 횟수가 늘어납니다. 꼭 필요할 때만 --force")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_run = (len(LOG_PATH.read_text().splitlines()) if LOG_PATH.exists() else 0) + 1

    df = pd.read_csv(DATA_PROCESSED, index_col=0)
    split = pd.read_csv(SPLIT_PATH)
    replay_ids = split.loc[split["role"] == "replay", "engine_id"]

    model = joblib.load(MODEL_PATH)
    meta = json.loads((ROOT / "models" / "rul_model_meta.json").read_text(encoding="utf-8"))
    leak = set(replay_ids) & set(meta["train_engine_ids"])
    assert not leak, f"replay 엔진이 학습에 포함됨(누수): {sorted(leak)}"

    rep = df[df["engine_id"].isin(replay_ids)]
    feats = make_features(rep).merge(rep[["engine_id", "cycle", "RUL"]], on=["engine_id", "cycle"])
    feats["pred"] = model.predict(feats[feature_columns()])
    feats["warmup"] = feats["cycle"] < WINDOW_N
    feats["fold"] = 0

    # 1) 예측 성능 (CV와 같은 기준)
    overall = evaluate(feats["RUL"], feats["pred"])
    near = feats[feats["RUL"] <= 20]
    near_rmse = float(np.sqrt(np.mean((near["pred"] - near["RUL"]) ** 2)))

    bins = [-1, 10, 20, 30, 40, 60, 80, 100, 115]
    sub = feats[feats["RUL"] <= 115].copy()
    sub["err"] = sub["pred"] - sub["RUL"]
    sub["bin"] = pd.cut(sub["RUL"], bins).astype(str)
    by_bin = sub.groupby("bin", sort=False)["err"].agg(
        n="count", bias="mean", rmse=lambda e: float(np.sqrt(np.mean(e ** 2))),
        late_ratio=lambda e: float(np.mean(e > 0))).reset_index()

    # 2) 알람 규칙 (T=40, L=20, dev OOF로 정한 값 그대로)
    eng = engine_alarms(feats, ALARM_T)
    missed = eng["lead"].isna() | (eng["lead"] < ALARM_L)
    ok = eng.loc[~missed, "lead"]

    result = {
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "run_no": n_run,
        "n_engines": int(feats["engine_id"].nunique()),
        "n_rows_scored": int((feats["RUL"] <= 115).sum()),
        "rmse": float(overall["rmse"]),
        "phm_mean": float(overall["phm_mean"]),
        "late_ratio": float(overall["late_ratio"]),
        "rmse_rul_le_20": near_rmse,
        "alarm": {
            "T": ALARM_T, "L": ALARM_L,
            "missed_engines": int(missed.sum()),
            "missed_ids": eng.loc[missed, "engine_id"].astype(int).tolist(),
            "lead_min": float(eng["lead"].min()),
            "lead_median": float(eng["lead"].median()),
            "mean_wasted_life": float((ok - ALARM_L).mean()) if len(ok) else None,
            "flicker_engines": int((eng["flicker"] > 0).sum()),
        },
        "by_rul_bin": by_bin.to_dict(orient="records"),
        "model_trained_at": meta["trained_at"],
    }

    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    feats[["engine_id", "cycle", "RUL", "pred", "warmup"]].to_csv(PRED_PATH, index=False)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{result['evaluated_at']} run {n_run}\n")

    print(f"[hold-out {n_run}회차] 엔진 {result['n_engines']}대")
    print(f"RMSE {result['rmse']:.2f} | PHM {result['phm_mean']:.2f} | 늦은 예측 {result['late_ratio']:.0%}"
          f" | 고장 직전(RUL<=20) RMSE {near_rmse:.2f}")
    a = result["alarm"]
    print(f"알람 T={a['T']}, L={a['L']}: 놓친 엔진 {a['missed_engines']}대 {a['missed_ids']}, "
          f"리드타임 최소 {a['lead_min']:.0f} / 중앙값 {a['lead_median']:.0f}, 평균 낭비 수명 {a['mean_wasted_life']}")
    print(by_bin.round(2).to_string(index=False))
    print(f"저장: {RESULT_PATH.relative_to(ROOT)}, {PRED_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
