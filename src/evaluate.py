"""평가 지표: RMSE, PHM 비대칭 점수, 늦은 예측 비율.
채점은 상한을 씌우지 않은 실제 RUL로 하고, RUL<=115 구간만 본다 (D06 참고).
"""
import numpy as np


def cap_rul(rul, cap):
    """구간 선형 라벨: 상한 이상은 cap으로 자름. 학습 라벨 전용 — 평가에는 쓰지 않는다."""
    return np.minimum(rul, cap)


def phm_score(y_true, y_pred):
    """PHM08 비대칭 점수. 늦은 예측(d>0)에 더 큰 벌점. 낮을수록 좋음.
    늦은 예측 분모 10 / 이른 예측 분모 13 — Saxena 2008 본문·그림 9 기준
    (논문에 인쇄된 수식의 a1·a2는 뒤바뀌어 있어 따르지 않음, 03_의사결정로그 확인 사실).
    """
    d = np.asarray(y_pred) - np.asarray(y_true)
    return np.sum(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1))


def evaluate(y_true_raw, y_pred, eval_max=115):
    """실제 RUL(상한 없음) 기준으로, RUL<=eval_max 구간만 채점."""
    y_true_raw, y_pred = np.asarray(y_true_raw), np.asarray(y_pred)
    m = y_true_raw <= eval_max
    yt, yp = y_true_raw[m], y_pred[m]
    return {
        "rmse": np.sqrt(np.mean((yp - yt) ** 2)),
        "phm_mean": phm_score(yt, yp) / len(yt),
        "late_ratio": np.mean(yp > yt),
    }