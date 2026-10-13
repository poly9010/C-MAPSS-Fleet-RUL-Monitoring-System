"""학습과 실시간 추론이 공유하는 특징 계산. 과거(현재 시점까지)만 사용한다."""
import numpy as np

from src.config import SENSORS, WINDOW_N


def make_features(hist, N=WINDOW_N, sensors=SENSORS):
    """
    hist: engine_id, cycle, 센서 열을 가진 DataFrame (한 엔진 또는 여러 엔진)
    반환: 각 행마다 '그 시점까지의 최근 N사이클'로만 계산한 특징 (과거만 사용)
      - {s}_mean : 최근 N사이클 평균
      - {s}_slope: 최근 N사이클 기울기 (사이클당 변화량)

    학습 시 전체 이력을 통째로 넣는 것과, 실시간에 최근 N줄짜리 버퍼만 넣는 것이
    같은 결과를 내야 한다 (이 파일 아래 tests/test_features.py에서 검증).
    """
    hist = hist.sort_values(["engine_id", "cycle"])
    t = hist["cycle"].astype(float)

    def rmean(s):
        return s.groupby(hist["engine_id"], sort=False) \
                 .transform(lambda x: x.rolling(N, min_periods=1).mean())

    mt, mtt = rmean(t), rmean(t * t)
    var_t = mtt - mt ** 2

    out = hist[["engine_id", "cycle"]].copy()
    for s in sensors:
        x = hist[s].astype(float)
        mx, mtx = rmean(x), rmean(t * x)
        out[f"{s}_mean"] = mx
        out[f"{s}_slope"] = np.where(
            var_t > 1e-9, (mtx - mt * mx) / var_t.where(var_t > 1e-9, 1), 0.0
        )
    return out


def feature_columns(sensors=SENSORS):
    """make_features가 만드는 특징 열 이름. train.py와 실시간 추론에서 X_cols로 똑같이 쓴다."""
    cols = []
    for s in sensors:
        cols += [f"{s}_mean", f"{s}_slope"]
    return cols