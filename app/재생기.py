# def check_row(row, last_cycle, recent, qc_stats, sensors=SENSORS)
# def update_qc_status(fails, fail_streak, m = QC_ESCALATE_M)
# def predict_fleet(model, buffers)
# def update_alarm(old, rul, buffer_len)
# 실행 : 프로젝트 루트에서  PYTHONPATH=. python -m streamlit run app/재생기.py

import time
import joblib
import streamlit as st
import pandas as pd
from collections import deque

from src.config import DATA_PROCESSED, SPLIT_PATH, WINDOW_N, MODEL_PATH, TICK_SEC
from src.quality import load_json, check_row, update_qc_status
from src.predict import predict_fleet
from src.judge import update_alarm, ALARM_NAME

st.set_page_config(page_title="엔진 플릿 모니터링", layout="wide") #화면을 넓게 써서 20대를 한번에 보이게 함. st 명령 중에 제일 먼저 와야함

@st.cache_resource
def model_load():
    return joblib.load(MODEL_PATH)
model = model_load()

@st.cache_data
def load_to_json():
    return load_json()
qc_stats = load_to_json()

# 재생기는 데이터가 들어오면 한줄씩 꺼내서 넘겨주고, 데이터가 더이상 들어오지 않는 센서는 종료 알림을 전달한다.
@st.cache_data
def load_data(path1, path2):
    return pd.read_csv(path1,index_col = 0), pd.read_csv(path2)
train,train_split = load_data(DATA_PROCESSED,SPLIT_PATH) #데이터 불러오기

@st.cache_data
def merge(df1,df2):
   return df1.merge(df2[df2['role']=='replay'], on='engine_id')
stream_20 = merge(train, train_split) #replay데이터만 엔진 아이디 기준으로 합치기
engine_cols = sorted(stream_20['engine_id'].unique().tolist()) #엔진id (화면에 번호순으로 보이게 정렬)

replay_data = {}
for x in stream_20['engine_id'].unique(): #딕셔너리로 만듬
    replay_data[x] = stream_20[stream_20['engine_id']==x].sort_values('cycle').reset_index(drop=True)

# [시연용] 결함 주입 : 엔진 8의 사이클 3~5에 s2 이상치. 시연할 때만 주석 풀기
# replay_data[8].loc[replay_data[8]['cycle'].between(3, 5), 's2'] = 9999

# 초기화는 한번만 수행해야 하므로 session_state 선언
if 'cursor' not in st.session_state:
    st.session_state['cursor'] = {eid: 0 for eid in engine_cols} # 딕셔너리{8(엔진아이디):0(사이클),9:2} : 재생기가 다음에 읽을 행 위치
if 'buffer' not in st.session_state:
    st.session_state['buffer'] = {eid: deque(maxlen=WINDOW_N) for eid in engine_cols}
if 'finished' not in st.session_state:
    st.session_state['finished'] = {eid: False for eid in engine_cols} #엔진별 종료여부
if 'life' not in st.session_state:
    st.session_state['life'] = {eid: replay_data[eid]['cycle'].max() for eid in engine_cols} # 엔진별 최대 수명
if 'last_cycle' not in st.session_state: #엔진별 마지막 사이클 저장
    st.session_state['last_cycle'] = {eid: None for eid in engine_cols}
if 'fail_streak' not in st.session_state:
    st.session_state['fail_streak'] = {eid:0 for eid in engine_cols}
if 'last_fails' not in st.session_state:
    st.session_state['last_fails'] = {eid:[] for eid in engine_cols}
if 'qc_status' not in st.session_state:
    st.session_state['qc_status'] = {eid: '정상' for eid in engine_cols}
if 'pred' not in st.session_state: #최근 예측한 행의 RUL을 모아두는 딕셔너리
    st.session_state['pred'] = {eid: None for eid in engine_cols}
if 'pred_cycle' not in st.session_state:#pred는 RUL을 저장, pred_cycle은 RUL을 계산한 cycle을 저장
    st.session_state['pred_cycle'] = {eid: None for eid in engine_cols}
if 'alarm' not in st.session_state: #엔진별 알람 단계 0:정상 1:정비 준비 2:긴급
    st.session_state['alarm'] = {eid: 0 for eid in engine_cols}
if 'alarm_cycle' not in st.session_state: #1단계 이상 알람이 처음 울린 사이클 (우선순위 3번 기준)
    st.session_state['alarm_cycle'] = {eid: None for eid in engine_cols}
if 'running' not in st.session_state: #자동 재생 중인지
    st.session_state['running'] = False
if 'step' not in st.session_state: #정지 상태에서 한 사이클만 진행할지
    st.session_state['step'] = False

cursor = st.session_state['cursor']
buffer = st.session_state['buffer']
finished = st.session_state['finished']
life = st.session_state['life']
last_cycle = st.session_state['last_cycle']
fail_streak = st.session_state['fail_streak']
last_fails = st.session_state['last_fails']
qc_status = st.session_state['qc_status']
pred = st.session_state['pred']
pred_cycle = st.session_state['pred_cycle']
alarm = st.session_state['alarm']
alarm_cycle = st.session_state['alarm_cycle']

# 버튼 콜백 : 버튼을 누르면 스크립트가 다시 실행되기 "전에" 먼저 실행됨
def play(): #재생 <-> 정지
    st.session_state['running'] = not st.session_state['running']

def one_step(): #한 사이클만 진행
    st.session_state['step'] = True

def reset(): #session_state를 다 지우면 다시 실행될 때 위에서 처음 상태로 초기화됨
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# 이번 실행에서 한 사이클 진행할지. 재생 중이거나 한 사이클 버튼을 눌렀을 때만 진행
# (이게 없으면 버튼만 눌러도 사이클이 넘어감)
tick = st.session_state['running'] or st.session_state['step']
st.session_state['step'] = False

new_alarm = [] #이번 틱에 단계가 올라간 엔진 (알림 띄우는 용도)

if tick:
    new_row = {}

    # ①재생기 ②품질검사 : 한 틱에 엔진별로 행 하나씩 들어옴
    for eid in engine_cols:
        # 엔진별 종료 여부
        if finished[eid] == True:
            continue
        else:
            row = replay_data[eid].iloc[cursor[eid]] #품질검사를 위한 행
            last_fails[eid] = check_row(row,last_cycle[eid],buffer[eid],qc_stats) #품질검사
            fail_streak[eid], qc_status[eid] = update_qc_status(last_fails[eid],fail_streak[eid]) #연속실패검사
            last_cycle[eid] = row['cycle']

            if qc_status[eid] == '정상' : #정상 행이라면
                buffer[eid].append(row) #버퍼에 추가
                #매 틱마다 정상인 행들만 모델 예측을 해야하기 때문에 따로 모아놈.
                new_row[eid] = buffer[eid]

            if cursor[eid] == life[eid]-1: #엔진의 현재 수명이 최대수명인지
                finished[eid] = True         # 맞으면 finished을 True로 변경
            else:
                cursor[eid] += 1 #아니면 해당 엔진의 행 +1

    # ③특징계산 ④예측 : 이번 틱에 정상 행이 들어온 엔진만
    result = predict_fleet(model,new_row)
    for engine_id,rul in zip(result.keys(),result.values()):
        pred[engine_id] = rul
        pred_cycle[engine_id] = buffer[engine_id][-1]['cycle'] #RUL을 예측한 사이클을 저장

        # ⑤알람 판단 : 예측이 새로 나온 엔진만. 품질검사 실패한 엔진은 예측이 그대로라 판단도 그대로
        old = alarm[engine_id]
        alarm[engine_id] = update_alarm(old, rul, len(buffer[engine_id])) #워밍업이면 기존 단계 그대로
        if alarm[engine_id] > old: #단계가 올라갔을 때만 알람 (래칭이라 단계마다 한번씩만 울림)
            new_alarm.append(engine_id)
            if alarm_cycle[engine_id] is None: #0에서 바로 2단계로 가도 첫 알람 사이클은 기록
                alarm_cycle[engine_id] = pred_cycle[engine_id]

# 엔진이 전부 끝나면 자동 재생 멈춤
all_done = all(finished.values())
if all_done:
    st.session_state['running'] = False


# ⑦화면 ---------------------------------------------------------------

# 알람 : 단계가 올라간 엔진은 오른쪽 아래에 알림을 띄움 (몇 초 뒤 사라짐, 카드 색은 계속 유지)
for eid in new_alarm:
    icon = "🚨" if alarm[eid] == 2 else "⚠️"
    st.toast(f"엔진 {eid} : {ALARM_NAME[alarm[eid]]} (예측 RUL {pred[eid]:.1f})", icon=icon)

st.title("엔진 플릿 실시간 모니터링")
st.caption(f"저장된 데이터를 {TICK_SEC}초에 한 사이클씩 재생 · 엔진 {len(engine_cols)}대 · 1단계 예측 RUL ≤ 40 / 2단계 ≤ 30")

# 조작 버튼
b1, b2, b3, _ = st.columns([1, 1, 1, 6])
b1.button("정지" if st.session_state['running'] else "재생", on_click=play, key='play', disabled=all_done)
b2.button("한 사이클", on_click=one_step, key='step_btn', disabled=st.session_state['running'] or all_done)
b3.button("처음부터", on_click=reset, key='reset')

# 상단 요약 : 끝난 엔진은 알람 개수에서 뺌
alive = [eid for eid in engine_cols if not finished[eid]]
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("운행 중", len(alive))
m2.metric("정비 준비 (1단계)", sum(alarm[eid] == 1 for eid in alive))
m3.metric("긴급 (2단계)", sum(alarm[eid] == 2 for eid in alive))
m4.metric("품질 이상", sum(qc_status[eid] != '정상' for eid in alive))
m5.metric("재생 종료", len(engine_cols) - len(alive))

# 정비 우선순위 : 단계 높은 순 → 예측 RUL 낮은 순 → 첫 알람이 빠른 순
st.subheader("정비 우선순위")
alarm_list = []
for eid in alive:
    if alarm[eid] >= 1:
        alarm_list.append({'엔진': eid,
                           '단계': ALARM_NAME[alarm[eid]],
                           '예측 RUL': round(pred[eid], 1),
                           '첫 알람 사이클': int(alarm_cycle[eid]),
                           '현재 사이클': int(last_cycle[eid]),
                           'stage': alarm[eid]}) #정렬용, 화면엔 안 보임
if alarm_list:
    alarm_df = pd.DataFrame(alarm_list).sort_values(['stage', '예측 RUL', '첫 알람 사이클'], ascending=[False, True, True])
    st.dataframe(alarm_df.drop(columns='stage'), hide_index=True)
else:
    st.write("알람이 울린 엔진 없음")

# 엔진 카드 색 (배경, 테두리, 글자)
CARD_COLOR = {0: ('#FFFFFF', '#D0D0D0', '#222222'),  #정상
              1: ('#FFE0B2', '#FB8C00', '#222222'),  #1단계 : 주황
              2: ('#C62828', '#8E0000', '#FFFFFF')}  #2단계 : 같은 계열 진한 빨강
END_COLOR = ('#EEEEEE', '#9E9E9E', '#616161')        #재생 끝난 엔진 : 회색

def engine_card(eid): #엔진 하나의 상태를 html 카드로 만듬
    cyc = '-' if last_cycle[eid] is None else int(last_cycle[eid])
    rul = '-' if pred[eid] is None else f"{pred[eid]:.1f}"  #첫 행부터 품질검사 실패하면 None일 수 있음

    note = "" #품질검사 실패로 예측이 멈춰있으면 몇 사이클 전 값인지 표시
    if pred_cycle[eid] is not None and last_cycle[eid] - pred_cycle[eid] > 0:
        note = f" ({int(last_cycle[eid] - pred_cycle[eid])}사이클 전 예측)"

    if finished[eid]: #재생 끝난 엔진 = 고장. 첫 알람이 고장 몇 사이클 전에 울렸는지 보여줌
        bg, line, text = END_COLOR
        if alarm_cycle[eid] is None:
            state = "고장 · 알람 없이 고장"
        else:
            state = f"고장 · {int(life[eid] - alarm_cycle[eid])}사이클 전 첫 알람"
    else:
        bg, line, text = CARD_COLOR[alarm[eid]]
        state = ALARM_NAME[alarm[eid]]
        if len(buffer[eid]) < WINDOW_N: #워밍업이면 알람 판단 전이라고 표시
            state = f"워밍업 ({len(buffer[eid])}/{WINDOW_N})"

    qc = qc_status[eid]
    if qc != '정상': #품질 이상이면 실패 사유도 같이
        qc = f"{qc} {', '.join(last_fails[eid])}"

    # 줄 앞에 공백이 있으면 markdown이 코드블록으로 인식해서 한 줄씩 붙여서 만듬
    return (f'<div style="background:{bg}; border:2px solid {line}; color:{text}; border-radius:8px; padding:10px 12px; margin-bottom:12px; min-height:165px;">'
            f'<div style="font-size:17px; font-weight:700;">엔진 {eid}</div>'
            f'<div style="font-size:12px;">사이클 {cyc}</div>'
            f'<div style="font-size:28px; font-weight:700; line-height:1.3;">{rul}</div>'
            f'<div style="font-size:12px;">예측 RUL{note}</div>'
            f'<div style="font-size:14px; font-weight:700; margin-top:6px;">{state}</div>'
            f'<div style="font-size:12px;">품질 : {qc}</div>'
            f'</div>')

# 엔진 20대 카드 : 한 줄에 5대씩 4줄
st.subheader("엔진별 상태")
N_COL = 5
for i in range(0, len(engine_cols), N_COL):
    cols = st.columns(N_COL)
    for col, eid in zip(cols, engine_cols[i:i+N_COL]):
        col.markdown(engine_card(eid), unsafe_allow_html=True)

if all_done:
    st.success("모든 엔진 재생 끝")

# 자동 재생 : 2초 기다렸다가 스크립트를 다시 실행 = 다음 사이클
# 맨 마지막에 둬야 화면을 다 그리고 나서 기다림
if st.session_state['running']:
    time.sleep(TICK_SEC)
    st.rerun()
