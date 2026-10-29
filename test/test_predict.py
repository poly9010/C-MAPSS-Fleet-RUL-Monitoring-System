from collections import deque

import numpy as np
import pandas as pd

from src.config import SENSORS, WINDOW_N
from src.features import make_features, feature_columns
from src.predict import predict_fleet


# class SumModel:
#     """특징 합을 돌려주는 가짜 모델. 엔진마다 값이 달라서, 엔진↔예측 매칭이 섞이면 바로 드러난다."""
#     def predict(self, X):
        


# def _rows(eid, n, seed):
#     """앱과 같은 조건: 문자열 열(role)이 섞인 DataFrame에서 iloc으로 꺼낸 행(Series)."""
    


# def test_fleet_matches_single_engine():
#     # 버퍼 길이가 서로 다른 엔진(1행, 덜 참, 가득 참)을 섞어서 넣는다
    

# def test_empty_returns_empty():
    
