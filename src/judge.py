# 알람 판단 : 예측한 RUL로 엔진별 알람 단계를 정함 (D09)
"""
④ 예측 결과(pred)가 있는 엔진만
   ↓
워밍업인가? (len(buffer) < WINDOW_N) → 예: 판단 안 함
   ↓ 아니오
이번 예측으로 단계 계산: 예측 ≤ 30 → 2, ≤ 40 → 1, 그 외 → 0
   ↓
래칭: 새 단계 = max(기존 단계, 이번 단계)   ← 내려가지 않음
   ↓
처음 1단계 이상이 된 순간이면 그 사이클을 기록 (우선순위 3번 기준) → 재생기.py에서 함
"""
from src.config import ALARM_T, ALARM_T2, WINDOW_N

ALARM_NAME = {0: '정상', 1: '정비 준비', 2: '긴급 : 정비 필요'} #단계별로 화면에 보여줄 이름


def alarm_stage(rul, t=ALARM_T, t2=ALARM_T2): #예측 RUL 하나만 보고 이번 단계를 계산
    if rul <= t2: #2단계 (30 이하)
        return 2
    elif rul <= t: #1단계 (40 이하)
        return 1
    else:
        return 0


# 예측이 나온 엔진만 매 틱마다 부름. old(기존 단계), rul(이번 예측), buffer_len(버퍼 길이)
def update_alarm(old, rul, buffer_len, n=WINDOW_N):
    if buffer_len < n: #워밍업 구간은 판단 안 하고 기존 단계 그대로 (D11)
        return old
    return max(old, alarm_stage(rul)) #래칭 : 한번 올라간 단계는 내려가지 않음
