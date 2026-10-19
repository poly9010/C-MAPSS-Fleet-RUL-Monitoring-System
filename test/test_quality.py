"""품질검사 결함 주입 테스트. 실행: 프로젝트 루트에서  pytest test/test_quality.py -v"""
from collections import deque

import numpy as np
import pandas as pd

from src.quality import check_row, load_json, update_qc_status
from src.config import SENSORS,WINDOW_N, QC_ESCALATE_M 

QC = load_json()          # 파일 맨 위에서 한 번만 읽음 (모든 테스트가 공유)

def make_normal_row(cycle=50):
    # 모든 센서를 dev 범위의 정중앙 값으로 채운 정상 행 = 대조군 설정
    # 실제CSV파일에서 한 행만 바꾸는 방법보다 이미 만들어진 json을 이용해 작성하는게 더 빠르고 데이터가 변동되지 않음.
    values = {s: (QC["sensors"][s]["dev_min"] + QC["sensors"][s]["dev_max"]) / 2
              for s in SENSORS}
    values["cycle"] = cycle
    return pd.Series(values)


def test_normal_row_passes(): #정상행 탐지
    row = make_normal_row()
    assert check_row(row, row["cycle"] - 1, deque(), QC) == []


def test_nan_is_missing(): #nan값 탐지
    row = make_normal_row()
    row["s2"] = np.nan
    assert check_row(row, row["cycle"] - 1, deque(), QC) == ["s2:missing"]

def test_9999_is_range(): #이상치 탐지
    row = make_normal_row()
    row['s2'] = 9999
    assert check_row(row,row['cycle']-1,deque(),QC) == ["s2:range"]

def test_cycle_gap(): #연속된 사이클 여부
    row = make_normal_row()
    original_cycle = row['cycle']
    row['cycle'] =  original_cycle + 1
    assert check_row(row,original_cycle-1,deque(),QC) == ['cycle']

def test_first_row_no_cycle_check(): #이전 행의 사이클이 none일 경우
    row = make_normal_row()
    assert check_row(row,None,deque(),QC) == []
    
def test_not_stuck_below_k(): #경계값 테스트(21에서 걸리지 않는지)
    k = QC["sensors"]["s17"]["k_stuck"]           # s17에서 가장 중복이 많은 값의 길이 : 22
    row = make_normal_row()
    row["s17"] = 393

    recent = deque(maxlen=WINDOW_N)
    for i in range(k - 2):                         # 20개 → 새 행까지 21번
        prev = make_normal_row(cycle=row["cycle"] - (k - 2) + i)
        prev["s17"] = 393                          # s17만 고정
        for s in SENSORS:
            if s != "s17":
                prev[s] += (i + 1) * 0.001         # 나머지 센서는 행마다 조금씩 다르게
        recent.append(prev)

    assert check_row(row, row["cycle"] - 1, recent, QC) == []

def test_stuck_at_k(): #경계값 테스트(22에서 걸리는지)
    k = QC["sensors"]["s17"]["k_stuck"]           # s17에서 가장 중복이 많은 값의 길이 : 22
    row = make_normal_row()
    row["s17"] = 393

    recent = deque(maxlen=WINDOW_N)
    for i in range(k - 1):                         # 20개 → 새 행까지 21번
        prev = make_normal_row(cycle=row["cycle"] - (k - 2) + i)
        prev["s17"] = 393                          # s17만 고정
        for s in SENSORS:
            if s != "s17":
                prev[s] += (i + 1) * 0.001         # 나머지 센서는 행마다 조금씩 다르게
        recent.append(prev)

    assert check_row(row, row["cycle"] - 1, recent, QC) == ['s17:stuck']

def test_fail_streak_passes(): #정상인 행이 들어올 시 통과
    row = make_normal_row()
    fail_streak = 0
    fails = check_row(row,row['cycle']-1,deque(), QC)

    assert update_qc_status(fails,fail_streak) == (0,'정상')
    
def test_fail_streak(): #품질경고 테스트
    row = make_normal_row()
    fail_streak = 0
    results = []
    for i in range(3): # range 값은 m값 기준
        row['s2'] = 9999
        fails = check_row(row,row['cycle']-1,deque(), QC)
        fail_streak,result = update_qc_status(fails, fail_streak)
        results.append(result)

    assert results == ['품질 경고','품질 경고','센서 점검 필요']
    
        