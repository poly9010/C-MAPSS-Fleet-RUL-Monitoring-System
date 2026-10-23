# 해당 엔진의 현재 예측한 RUL이 T값보다 아래인지 
"""
④ 예측 결과(pred)가 있는 엔진만
   ↓
워밍업인가? (len(buffer) < WINDOW_N) → 예: 판단 안 함
   ↓ 아니오
이번 예측으로 단계 계산: 예측 ≤ 30 → 2, ≤ 40 → 1, 그 외 → 0
   ↓
래칭: 새 단계 = max(기존 단계, 이번 단계)   ← 내려가지 않음
   ↓
처음 1단계 이상이 된 순간이면 그 사이클을 기록 (우선순위 3번 기준)
"""
from src.config import ALARM_L, ALARM_T

def alarm(pred,pred_cycle):
    if pred_cycle < 30: #워밍업구간 판단
        return 

    engine_cols = pred.keys() #엔진아이디 추출
    alarm_true = {eid: 0 for eid in engine_cols} #엔진별로 알람에 해당되는지
    
    for eid in engine_cols:
        if pred[eid] <= ALARM_T-10: 
            #알람2단계
            alarm_true[eid] = 2 

        if pred[eid] <= ALARM_T and alarm_true[eid] == 0: #RUL이 T보다 작고 알람이 울린적이 없다면
            #알람1단계 
            alarm_true[eid] = 1

        
            


