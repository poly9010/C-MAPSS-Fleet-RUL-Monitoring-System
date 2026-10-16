# 품질검사 : 들어온 행이 기준에 맞는지 확인.
""" json 형식
"computed_at": "2026-10-16T04:43:06",
  "source_data": "/Users/gimminjeong/Downloads/예지보전프로젝트/data/1차 전처리(센서 제거)/train1_sens_filter.csv",
  "n_dev_engines": 80,
  "sigma_k": 5,
  "stuck_min": 5,
  "sensors": {
    "s2": {
      "lo": 638.6958899850324,
      "hi": 647.0441100149676,
      "k_stuck": 5,
      "dev_min": 641.21,
      "dev_max": 644.53,
      "dev_std": 0.5028220029935321,
      "dev_max_run": 2
    }
"""

import json
import pandas as pd
from src.config import SENSORS, QC_STATS_PATH

def load_json():
    with open(QC_STATS_PATH,'r',encoding='utf-8') as f:
        return json.load(f) 

# 매 행마다 불림. row(들어온 행), last_cycle(마지막 사이클번호), recent(버퍼),qc_stats(기준값json)
def check_row(row, last_cycle, recent, qc_stats, sensors=SENSORS):
    
    fails = [] #실패사유 리스트. 비어있으면 통과

    # 1. 결측치 확인, 3.이상치 확인 4. 고착
    for s in sensors:
        sens = qc_stats['sensors'][s]
        if pd.isna(row[s]): # 결측확인
            fails.append(s + ':' + 'missing') 
            continue
        if row[s] < sens['lo'] or row[s] > sens['hi']: # 이상치 확인
            fails.append(s + ':' + 'range')
        
        run = 1
        for prev in reversed(recent): # 버퍼값 역순으로 반복
            if prev[s] == row[s]:
                run+=1
            else:
                break
        if run >= sens['k_stuck']:
            fails.append(s + ':' + 'stuck')
                
    # 2. 사이클 연속 확인
    if last_cycle is not None and row['cycle'] != last_cycle+1: #사이클이 연속으로 들어왔는가
        fails.append('cycle')
    
    return fails

 