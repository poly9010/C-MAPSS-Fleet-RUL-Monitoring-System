"""dev 80대의 교차검증 예측(OOF)을 만든다. D09(알람 기준) 분석용.

저장된 최종 모델(rul_model.pkl)은 쓰지 않는다. dev 80대 전체로 학습했기 때문에
dev 엔진을 예측하면 이미 본 데이터를 맞히는 셈(누수)이라 알람 기준이 낙관적으로 잡힌다.
대신 train.py와 같은 설정으로 폴드마다 새 모델을 학습하고,
학습에서 뺀 폴드의 엔진만 예측한다. → 모든 dev 행이 '처음 보는 엔진'으로 예측됨.
replay 20대는 쓰지 않는다 (시연용, 알람 기준을 맞추면 시연 성능이 부풀려짐).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.config import ROOT, DATA_PROCESSED, SPLIT_PATH, WINDOW_N, RUL_CAP, SEED
from src.evaluate import cap_rul, evaluate
from src.features import make_features, feature_columns

OOF_PATH = ROOT / "data" / "oof" / "oof_dev.csv"


def make_oof():
    df = pd.read_csv(DATA_PROCESSED, index_col=0)
    split = pd.read_csv(SPLIT_PATH)

    # 특징은 엔진별로 과거만 써서 계산하므로, 폴드를 나누기 전에 한 번에 계산해도 누수가 없다
    feats = make_features(df)
    feats = feats.merge(df[["engine_id", "cycle", "RUL"]], on=["engine_id", "cycle"])
    feats = feats.merge(split, on="engine_id")
    dev = feats.query("role == 'dev'").reset_index(drop=True)

    X_cols = feature_columns()
    dev["pred"] = np.nan

    for k in sorted(dev["fold"].unique()):
        tr = dev["fold"] != k          # 학습: 나머지 폴드 (엔진 단위로 나뉨)
        va = dev["fold"] == k          # 예측: 이번 폴드
        model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=SEED)
        model.fit(dev.loc[tr, X_cols], cap_rul(dev.loc[tr, "RUL"], RUL_CAP))
        dev.loc[va, "pred"] = model.predict(dev.loc[va, X_cols])

        r = evaluate(dev.loc[va, "RUL"], dev.loc[va, "pred"])
        print(f"fold {int(k)}: 엔진 {dev.loc[va, 'engine_id'].nunique()}대, "
              f"RMSE {r['rmse']:.2f}, PHM {r['phm_mean']:.2f}, 늦은 예측 {r['late_ratio']:.0%}")

    # 워밍업 여부: 저장 데이터에는 결측·결함이 없으므로 버퍼 길이 = min(cycle, N)
    dev["warmup"] = dev["cycle"] < WINDOW_N

    out = dev[["engine_id", "fold", "cycle", "RUL", "pred", "warmup"]]
    OOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OOF_PATH, index=False)
    print(f"저장: {OOF_PATH.relative_to(ROOT)}  ({len(out)}행, 엔진 {out['engine_id'].nunique()}대)")
    return out


if __name__ == "__main__":
    make_oof()