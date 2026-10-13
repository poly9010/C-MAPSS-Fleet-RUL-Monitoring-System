"""경로·상수 설정. 다른 모듈은 경로나 상수를 직접 적지 않고 여기서 가져온다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# D01.2에서 햄펠 필터는 적용하지 않기로 했으므로, 1차 전처리(센서 제거) 결과를 그대로 쓴다
DATA_PROCESSED = ROOT / "data" / "1차 전처리(센서 제거)" / "train1_sens_filter.csv"
SPLIT_PATH = ROOT / "data" / "split" / "engine_split.csv"
MODELS_DIR = ROOT / "models"

# D01.1 확정: 표준편차 0이라 제거한 센서
DROPPED_SENSORS = ["s1", "s5", "s6", "s10", "s16", "s18", "s19"]

# D07 (03_의사결정로그상 아직 "잠정" — 표에는 미확정으로 남아 있음)
SENSORS = ["s2", "s3", "s4", "s7", "s8", "s11", "s12", "s13", "s15", "s17", "s20", "s21"]
WINDOW_N = 30

# D06 (03_의사결정로그상 아직 "잠정")
RUL_CAP = 115

SEED = 42