## 1. 데이터 정보

| 항목 | 내용 |
|---|---|
| 데이터명 | Turbofan Engine Degradation Simulation Data Set (C-MAPSS) |
| 제공 | NASA Prognostics Center of Excellence (PCoE) |
| 구성 | 하위셋 4종(FD001~FD004) × 파일 3개 + 설명 문서 |
| 형식 | 공백 구분 텍스트(.txt), 헤더 없음 |

다운로드: NASA PCoE 데이터 저장소 또는 Kaggle의 미러 데이터셋

### 어떤 작업에서 나온 데이터인가?
실제 항공기에서 수집된 데이터는 아니다. NASA가 만든 물리 기반 시뮬레이터(c-mapss)에서 나온 가상의 데이터이다. c-mapss는 90,000lb 추력급 대형 상용 터보팬 엔진"의 열역학적 동작을 컴퓨터로 모사하는 시뮬레이션 소프트웨어이며, 실제 엔진을 고장낼 수 없으니 이 시뮬레이터에 13개의 건강 파라미터(Fan, HPC, HPT, LPT 각 부품의 효율·유량·압력비)를 서서히 나쁘게 만들어가며 가상의 열화 과정을 만든 것이다.

### Cycle의 의미
사이클 1회의 의미는 비행 1회에 해당된다. 해당 사이클마다 특정 비행 조건을 다르게한 뒤 시뮬레이터를 돌려서 데이터를 쌓고,해당 사이클의 열화 상태를 살짝 진행시킨다. 해당 과정을 반복하다보면 정해진 열화의 실패 기준을 넘게되고 해당 센서의 이력이 끝난다.

---

## 2. 폴더 구조

```
data/
├── README.md
├── raw/                      # 원본 (git 제외)
│   ├── train_FD001.txt
│   ├── test_FD001.txt
│   ├── RUL_FD001.txt
│   ├── ... (FD002 ~ FD004)
│   └── readme.txt            # 원 제공 설명 문서
└── processed/                # 가공 결과 (git 제외)
    └── cmapss.parquet
```

---

## 3. 파일 구조

| 파일 | 내용 |
|---|---|
| `train_FD00X.txt` | 엔진별로 고장까지의 전체 운전 이력. 정상 상태에서 시작해서 고장 나는 순간까지 사이클(비행 1회 단위)별 센서값이 다 들어있음 |
| `test_FD00X.txt` | 같은 형식이지만, 각 엔진 이력이 고장 나기 전 임의 시점에서 잘려 있음. "지금까지의 데이터로 남은 수명을 맞혀봐"가 이 파일의 역할 |
| `RUL_FD00X.txt` | test 각 엔진의 정답 하나씩. test 파일이 끊긴 그 마지막 시점에서 실제로 몇 사이클을 더 버텼는지(잔여수명, RUL) — 한 줄에 정수 하나 |

### 컬럼 (26열, 헤더 없음)

| 순서 | 컬럼 | 설명 |
|---|---|---|
| 1 | `engine_id` | 엔진 번호 |
| 2 | `cycle` | 운전 사이클 번호 (1부터 증가) |
| 3~5 | `op1`, `op2`, `op3` | 운전조건 설정값 |
| 6~26 | `s1` ~ `s21` | 센서 측정값 |

### 로드 예시
```python
import pandas as pd

cols = ["engine_id", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
train = pd.read_csv("data/raw/train_FD001.txt", sep=r"\s+", header=None, names=cols)
```

---

## 4. 하위셋 특성 [공식 문서 기준 — 직접 확인 필요]

| 셋 | 운전조건 | 고장모드 | train 엔진 | test 엔진 |
|---|---|---|---|---|
| FD001 | 1 | 1 (HPC 열화) | 100 | 100 |
| FD002 | 6 | 1 | 260 | 259 |
| FD003 | 1 | 2 (HPC, Fan) | 100 | 100 |
| FD004 | 6 | 2 | 249 | 248 |

> ⚠️ 공식 설명 문서와 실제 파일의 엔진 수가 다른 사례가 보고되어 있습니다.
> 아래 명령으로 **직접 확인한 뒤 이 표를 갱신**하세요.
> ```python
> train.engine_id.nunique(), test.engine_id.nunique(), len(open("RUL_FD001.txt").readlines())
> ```

---

## 5. 통합 테이블 생성

```bash
python src/load.py
```

결과: `data/processed/cmapss.parquet`

| 컬럼 | 설명 |
|---|---|
| `subset` | FD001 ~ FD004 |
| `split` | train / test |
| `engine_id`, `cycle` | 엔진 번호, 사이클 |
| `op1`~`op3`, `s1`~`s21` | 운전조건, 센서값 |
| `RUL` | train에만 계산해 부여 (라벨링 방식은 `src/labeling.py`) |

---

## 6. 사용 규칙
- **학습은 train, 실시간 재생 시연은 test** 데이터를 사용합니다.
- train 내부에서 검증셋을 나눌 때는 **엔진 단위**로 나눕니다. 같은 엔진의 사이클이 학습과 검증에 섞이면 성능이 과대평가됩니다.
- test 정답은 각 엔진의 **마지막 시점 RUL 하나**뿐입니다. 중간 사이클의 정답은 없으므로, 재생 중 예측값 평가는 마지막 시점 기준으로 합니다.
- `data/raw`, `data/processed`는 `.gitignore`에 등록되어 커밋되지 않습니다.

---

## 출처
A. Saxena and K. Goebel (2008). *Turbofan Engine Degradation Simulation Data Set*, NASA Prognostics Center of Excellence (PCoE) Data Set Repository, NASA Ames Research Center.
