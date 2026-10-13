"""make_features가 '전체 이력을 한 번에 계산'과 '최근 N줄 버퍼로 매번 계산'에서
같은 결과를 내는지 확인한다 (학습·실시간 같은 함수 — 작업 규칙 6).
notebooks/(3)베이스라인.ipynb 코드 9를 그대로 옮긴 것.
"""
import numpy as np
import pandas as pd

from src.config import DATA_PROCESSED, WINDOW_N
from src.features import make_features


def test_stream_matches_batch():
    df = pd.read_csv(DATA_PROCESSED, index_col=0)
    N = WINDOW_N

    batch = make_features(df, N=N)
    e1 = df[df.engine_id == 1].sort_values("cycle")
    stream = pd.concat([
        make_features(e1.iloc[max(0, i - N + 1): i + 1], N=N).tail(1)
        for i in range(len(e1))
    ])

    feat_cols = [c for c in batch.columns if c.endswith(("_mean", "_slope"))]
    b1 = batch[batch.engine_id == 1][feat_cols].to_numpy()
    diff = np.abs(b1 - stream[feat_cols].to_numpy()).max()
    assert diff < 1e-9, f"배치·스트림 불일치: 최대 차이 {diff}"


if __name__ == "__main__":
    test_stream_matches_batch()
    print("배치와 스트림 계산이 일치합니다.")