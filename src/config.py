"""경로·상수 설정. 다른 모듈은 경로나 상수를 직접 적지 않고 여기서 가져온다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# D01.2에서 햄펠 필터는 적용하지 않기로 했으므로, 1차 전처리(센서 제거) 결과 그대로 사용
DATA_PROCESSED = ROOT / "data" / "1차 전처리(센서 제거)" / "train1_sens_filter.csv"
SPLIT_PATH = ROOT / "data" / "split" / "engine_split.csv"
MODELS_DIR = ROOT / "models"
MODEL_PATH = ROOT/ "models/rul_model.pkl"

# D01.1 확정: 표준편차 0이라 제거한 센서
DROPPED_SENSORS = ["s1", "s5", "s6", "s10", "s16", "s18", "s19"]

# D07 학습 사용 센서 및 윈도우 범위
SENSORS = ["s2", "s3", "s4", "s7", "s8", "s11", "s12", "s13", "s15", "s17", "s20", "s21"]
WINDOW_N = 30

# D06 RUL 상한
RUL_CAP = 115

# 시드 
SEED = 42

# 품질검사 (D10 후보, 값은 [가정] → 결함 주입 테스트로 확정)
QC_STATS_PATH = MODELS_DIR / "qc_stats.json"
QC_SIGMA_K = 5      # 범위 여유 폭: dev_min - kσ ~ dev_max + kσ
QC_STUCK_MIN = 5      # 고착 기준 K의 하한

QC_ESCALATE_M = 3 #[가정]

ALARM_T = 40
AMARM_L = 20 #기본값 20