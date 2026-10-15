import json 
from datetime import datetime
import pandas as pd
from src.config import (DATA_PROCESSED, SPLIT_PATH, SENSORS, 
                        QC_STATS_PATH,  QC_SIGMA_K, QC_STUCK_MIN)


#build_qc_stats 검사 기준 설정(dev 80개 기준)
#기준설정 후 train의 80대 엔진에 적용 -> 각 센서별 기준 정보를 담은 json 파일 생성


def max_run_length(values):
    # 1차원 값 배열에서 같은 값이 연속으로 나온 최대 길이.
    max_len = 1
    max_val = 0
    count = 1
    for i in range(len(values)-1):
        if values[i]==values[i+1]:
            count+=1
            if max_len < count:
                max_val = values[i]
                max_len = count
        else:
            count = 1
    
    return max_len

def load_data(path1,path2):
    return pd.read_csv(path1, index_col=0),pd.read_csv(path2)


def main():
    
    df, split = load_data(DATA_PROCESSED,SPLIT_PATH)
    
    # role=dev인 엔진들만 가져옴
    dev = df.merge(split[split['role']=='dev'],on = 'engine_id')

    stats = {}
    for s in SENSORS: # 센서 루프 (s2,s3...)
        x = dev[s] # 모든 엔진의 센서 값
        mn, mx, sd = x.min(), x.max(), x.std() # 센서값의 최소, 최대, 표준편차

        # ③: 엔진별로 max_run_length를 구한 뒤 그중 최댓값 
        # 엔진별 센서별 최대 중복길이
        # 엔진별로 구분하지 않으면 만약 엔진1마지막행 = 엔진2첫번째행일 때 연속이라 판단할 수 있음
        dev_max_run = dev.groupby('engine_id')[s].apply(lambda x:max_run_length(x.tolist())).max()

        stats[s] = {
            # TODO ④: 허용 하한·상한, 고착 기준 K (공식은 앞에서 정한 것)
            "lo": float(mn - QC_SIGMA_K*sd), #min - 5σ보다 작으면 탈락
            "hi": float(mx + QC_SIGMA_K*sd), #max + 5σ보다 크면 탈락
            "k_stuck": int(max(2*dev_max_run,QC_STUCK_MIN)), #고착기준k
            # 추적용 원본 값 (나중에 "왜 이 기준이냐" 물으면 근거가 됨)
            "dev_min": float(mn), "dev_max": float(mx), "dev_std": float(sd), "dev_max_run": int(dev_max_run),
        }

    out = {
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "source_data": str(DATA_PROCESSED),
        "n_dev_engines": int(dev["engine_id"].nunique()),
        "sigma_k": QC_SIGMA_K,
        "stuck_min": QC_STUCK_MIN,
        "sensors": stats,
    }

    # TODO ⑤: QC_STATS_PATH에 json으로 저장 (ensure_ascii=False, indent=2)
    with open(QC_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {QC_STATS_PATH}")

if __name__ == "__main__":
    main()