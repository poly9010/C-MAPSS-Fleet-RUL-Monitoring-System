"""알람 판단 테스트. 실행: 프로젝트 루트에서  pytest test/test_judge.py -v"""
from src.judge import alarm_stage, update_alarm
from src.config import WINDOW_N

FULL = WINDOW_N #버퍼가 가득 찬 상태 (워밍업 아님)


def test_stage_boundary(): #경계값 : 40, 30 '이하'일 때 울리는지
    assert alarm_stage(40.1) == 0
    assert alarm_stage(40) == 1
    assert alarm_stage(30.1) == 1
    assert alarm_stage(30) == 2


def test_latch_not_down(): #래칭 : 45 → 38 → 42 로 움직여도 1단계 유지
    stage = 0
    for rul in [45, 38, 42]:
        stage = update_alarm(stage, rul, FULL)
    assert stage == 1


def test_jump_to_stage2(): #45에서 바로 28로 떨어지면 1단계를 건너뛰고 2단계
    stage = update_alarm(0, 45, FULL)
    stage = update_alarm(stage, 28, FULL)
    assert stage == 2


def test_warmup_ignored(): #워밍업 중에는 예측이 25여도 알람 안 울림
    assert update_alarm(0, 25, FULL - 1) == 0


def test_warmup_keeps_old(): #워밍업이면 기존 단계를 그대로 돌려줌 (내려가지도 않음)
    assert update_alarm(1, 80, FULL - 1) == 1
