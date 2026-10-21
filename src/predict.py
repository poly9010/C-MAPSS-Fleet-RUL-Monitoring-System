"""실시간 RUL 예측. 학습과 같은 make_features를 쓰고, 마지막 행(현재 사이클)만 예측한다.
Streamlit에 의존하지 않으므로 9주차 MQTT 수신 쪽에서도 그대로 재사용한다."""
import pandas as pd

from src.features import make_features, feature_columns


def predict_fleet(model, buffers, cols=None):
    """
    buffers: {engine_id: 품질검사를 통과한 최근 N행이 담긴 deque}  (이번 틱에 예측할 엔진만)
    반환:    {engine_id: 예측 RUL(float)}
    여러 엔진을 한 DataFrame으로 묶어 make_features·predict를 한 번씩만 호출한다.
    make_features는 engine_id별로 따로 rolling하므로 엔진끼리 섞이지 않는다.
    """
    if not buffers:
        return {}

    cols = cols or feature_columns()
    hist = pd.concat([pd.DataFrame(list(b)) for b in buffers.values()], ignore_index=True)
    last = make_features(hist).groupby("engine_id", sort=False).tail(1)  # 버퍼 30개를 요약한 특징의 가장 최근 특징
    preds = model.predict(last[cols])
    return {int(e): float(p) for e, p in zip(last["engine_id"], preds)} #return {엔진아이디 : 예측한 RUL}
