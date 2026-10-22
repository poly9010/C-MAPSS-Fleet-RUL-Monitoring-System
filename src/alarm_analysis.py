"""D09 알람 기준 분석: T(알람 임계값) 후보별로 놓침·리드타임·낭비 수명·깜빡임을 계산한다.
입력은 make_oof.py가 만든 dev 80대 OOF 예측 (replay·test는 쓰지 않음).

정의
- 알람     : 워밍업이 아니고 예측 RUL <= T 인 상태가 k번 연속된 첫 사이클 (기본 k=1)
- 리드타임 : 첫 알람 시점의 실제 RUL. 끝까지 알람이 없으면 NaN
- 놓침     : 알람이 없거나 리드타임 < L
- 낭비 수명: 놓치지 않은 엔진의 (리드타임 - L). 준비가 끝나자마자 정비한다고 가정
- 깜빡임   : 첫 알람 이후 알람이 꺼진(켜짐→꺼짐) 횟수
"""
import numpy as np
import pandas as pd

from src.config import ROOT

OOF_PATH = ROOT / "data" / "oof" / "oof_dev.csv"
T_LIST = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
L_LIST = [10, 20, 30]


def engine_alarms(oof, T, k=1):
    """엔진별 첫 알람의 리드타임과 깜빡임 횟수. L과 무관한 값만 계산한다."""
    rows = []
    for eid, g in oof.sort_values(["engine_id", "cycle"]).groupby("engine_id"):
        life = g["cycle"].max()
        g = g[~g["warmup"]]                                   # 워밍업 구간은 알람 판단 제외 (D11)
        below = pd.Series((g["pred"] <= T).to_numpy())
        streak = below.groupby((~below).cumsum()).cumsum()    # 연속으로 T 이하인 횟수
        alarm = (streak >= k).to_numpy()

        idx = np.flatnonzero(alarm)
        if len(idx):
            first = idx[0]
            lead = g["RUL"].iloc[first]
            after = alarm[first:]
            flicker = int(np.sum(after[:-1] & ~after[1:]))    # 켜짐 → 꺼짐 전환
        else:
            lead, flicker = np.nan, 0

        rows.append({"engine_id": eid, "fold": g["fold"].iloc[0], "life": life,
                     "lead": lead, "flicker": flicker})
    return pd.DataFrame(rows)


def summarize(eng, L):
    """engine_alarms 결과를 L 기준으로 요약해서 표의 한 줄로 만든다."""
    missed = eng["lead"].isna() | (eng["lead"] < L)
    ok_lead = eng.loc[~missed, "lead"]
    return {
        "놓친엔진수": int(missed.sum()),
        "폴드별최대놓침": int(missed.groupby(eng["fold"]).sum().max()),
        "리드_min": eng["lead"].min(),
        "리드_p10": eng["lead"].quantile(0.10),
        "리드_중앙값": eng["lead"].median(),
        "평균낭비수명": round((ok_lead - L).mean(), 1),
        "깜빡임_엔진수": int((eng["flicker"] > 0).sum()),
        "깜빡임_최대": int(eng["flicker"].max()),
    }


def missed_engines(eng, L):
    """놓친 엔진 목록 (수명과 함께 보면 어떤 엔진이 놓치는지 알 수 있음)."""
    missed = eng["lead"].isna() | (eng["lead"] < L)
    return eng[missed].sort_values("lead")


def run(k=1):
    oof = pd.read_csv(OOF_PATH)
    per_T = {T: engine_alarms(oof, T, k) for T in T_LIST}   # L과 무관하므로 T마다 한 번만 계산
    tables = {}
    for L in L_LIST:
        table = pd.DataFrame([{"T": T, **summarize(per_T[T], L)} for T in T_LIST]).set_index("T")
        tables[L] = table
        print(f"\n===== L = {L} (k = {k}) =====")
        print(table.to_string())
        print(missed_engines())

    return tables, per_T


if __name__ == "__main__":
    run()