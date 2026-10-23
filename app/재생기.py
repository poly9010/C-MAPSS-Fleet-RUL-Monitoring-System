# def check_row(row, last_cycle, recent, qc_stats, sensors=SENSORS)
# def update_qc_status(fails, fail_streak, m = QC_ESCALATE_M)

import joblib
import streamlit as st
import pandas as pd
import numpy as np
from collections import deque

from src.config import ROOT, DATA_PROCESSED, SPLIT_PATH, MODELS_DIR, SENSORS, WINDOW_N, RUL_CAP, SEED, QC_STATS_PATH, MODEL_PATH
from src.quality import load_json, check_row, update_qc_status
from src.predict import predict_fleet

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
engine_cols = stream_20['engine_id'].unique().tolist() #엔진id

replay_data = {}
for x in stream_20['engine_id'].unique(): #딕셔너리로 만듬
    replay_data[x] = stream_20[stream_20['engine_id']==x].sort_values('cycle').reset_index(drop=True)

replay_data[8]['s2'].iloc[2:5] = replay_data[8]['s2'].iloc[2:5].apply(lambda x:x+9000) ## 결함 주입줄

# 초기화는 한번만 수행해야 하므로 session_state 선언
if 'cursor' not in st.session_state: 
    st.session_state['cursor'] = {eid: 0 for eid in engine_cols} # 딕셔너리{8(엔진아이디):0(사이클),9:2} : 재생기가 다음에 읽을 행 위치
if 'buffer' not in st.session_state:
    st.session_state['buffer'] = {eid: deque(maxlen=WINDOW_N) for eid in engine_cols}
if 'finished' not in st.session_state:
    st.session_state['finished'] = {eid: False for eid in engine_cols} #엔진별 종료여부
if 'life' not in st.session_state:
    st.session_state['life'] = dict(zip([eid for eid in engine_cols], stream_20.groupby('engine_id')['cycle'].max().tolist())) # 엔진별 최대 수명
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

new_row = {}

# 한 틱에 하나의 행을 검사 (한 틱에 엔진별로 행 하나씩 들어옴)
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

    
# 예측
result = predict_fleet(model,new_row)
for engine_id,rul in zip(result.keys(),result.values()):
    pred[engine_id] = rul
    pred_cycle[engine_id] = buffer[engine_id][-1]['cycle'] #RUL을 예측한 사이클을 저장
    
#알람
#인자는 result
for eid in engine_cols:
    
    st.subheader(f"엔진 {eid} : 방금 처리한 사이클: {last_cycle[eid]}")
    st.subheader(f'RUL : {pred[eid]:.1f}')
    
    note1 = "(워밍업)" if len(buffer[eid]) < WINDOW_N else ""
    st.subheader(note1)
    gap = last_cycle[eid] - pred_cycle[eid]
    note2 = "" if gap == 0 else f"{gap} 사이클 전 예측"
    st.subheader(note2)


# col1, col2, col3 = st.columns(3)
# col1.metric("품질 상태", qc_status[eid])
# col2.metric("연속 실패", fail_streak[eid])
# col3.metric("버퍼 길이", len(buffer[eid]))

# st.write("실패 사유:", last_fails[eid])
# if len(buffer[eid]) > 0:
#     st.write("버퍼 s2 평균:", round(sum(r['s2'] for r in buffer[eid]) / len(buffer[eid]), 3))

st.button("다음 사이클")  # 누르면 스크립트가 다시 실행되면서 한 틱 진행

# [임시] 품질검사 확인용 화면 (⑦화면 단계에서 정리)



