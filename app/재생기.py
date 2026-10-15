import streamlit as st
import pandas as pd
import numpy as np
from collections import deque

from src.config import ROOT, DATA_PROCESSED, SPLIT_PATH, MODELS_DIR, SENSORS, WINDOW_N, RUL_CAP, SEED
N = 30

# 재생기는 데이터가 들어오면 한줄씩 꺼내서 넘겨주고, 데이터가 더이상 들어오지 않는 센서는 종료 알림을 전달한다.
@st.cache_data
def load_data(path1, path2):
    return pd.read_csv(path1,index_col = 0), pd.read_csv(path2)

@st.cache_data
def merge(df1,df2):
   return df1.merge(df2[df2['role']=='replay'], on='engine_id')
    
train,train_split = load_data(DATA_PROCESSED,SPLIT_PATH) #데이터 불러오기
stream_20 = merge(train, train_split) #replay데이터만 엔진 아이디 기준으로 합치기
engine_cols = stream_20['engine_id'].unique().tolist() #엔진별 최대 수명

replay_data = {}
for x in stream_20['engine_id'].unique(): #딕셔너리로 만듬
    replay_data[x] = stream_20[stream_20['engine_id']==x].sort_values('cycle').reset_index(drop=True)

# 초기화는 한번만 수행해야 하므로 session_state 선언
if 'cursor' not in st.session_state:
    st.session_state['cursor'] = {eid: 0 for eid in engine_cols} #딕셔너리{8(엔진아이디):0(사이클),9:2}
if 'buffer' not in st.session_state:
    st.session_state['buffer'] = {eid: deque(maxlen=N) for eid in engine_cols}
if 'finished' not in st.session_state:
    st.session_state['finished'] = {eid: False for eid in engine_cols} #엔진별 종료여부
if 'life' not in st.session_state:
    st.session_state['life'] = dict(zip([eid for eid in engine_cols], stream_20.groupby('engine_id')['cycle'].max().tolist())) # 엔진별 최대 수명

cursor = st.session_state['cursor'] 
buffer = st.session_state['buffer']
finished = st.session_state['finished']
life = st.session_state['life']

for eid in engine_cols:
    # 엔진별 종료 여부
    if finished[eid] == True:
        continue
    else:
        buffer[eid].append(replay_data[eid].iloc[cursor[eid]])
        # buffer[eid].append(replay_data[eid].iloc[max(0,cursor[eid]-N+1):cursor[eid]+1])
        if cursor[eid] == life[eid]-1: #엔진의 현재 수명이 최대수명인지
            finished[eid] = True         # 맞으면 finished을 True로 변경
        else: 
            cursor[eid] += 1 #아니면 해당 엔진의 사이클 +1

st.header(f'엔진아이디 8 현재 사이클 : {cursor[8]}')
    # print('현재 엔진 ID : ',buffer[0]['engine_id'],"현재 사이클 : ", buffer[0]['cycle'])
# PYTHONPATH=. python app/test.py 

