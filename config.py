"""
config.py
MARK STRIKE 게임 전역 설정 및 밸런스 상수 모듈 (Single Source of Truth).
화면 해상도, 플레이어 기동 수치, 수리검 물리 및 전투 데미지 공식을 한곳에서 관리합니다.
"""

# ==========================================
# 1. 화면 및 프레임워크 설정 (PRD 1절)
# ==========================================
CANVAS_WIDTH: int = 1280
CANVAS_HEIGHT: int = 720
TARGET_FPS: int = 120

# ==========================================
# 2. 플레이어(Player) 기동 및 자원 설정 (PRD 2절, 3.1절)
# ==========================================
PLAYER_RADIUS: float = 16.0
PLAYER_MOVE_SPEED: float = 460.0        # 기본 8방향 이동 속도 (px/s)
PLAYER_MAX_AMMO: int = 3                # 최대 수리검 소지 탄창 수 (밸런스 조정 가능)

# 구르기(Roll) 파라미터 (I-Frame 없음, 순간 가속 기동)
PLAYER_ROLL_SPEED: float = 950.0        # 구르기 순간 속도 (px/s)
PLAYER_ROLL_DURATION: float = 0.18      # 구르기 지속 시간 (초)
PLAYER_ROLL_COOLDOWN: float = 0.35      # 구르기 재사용 대기시간 (초)

# 최초 돌진 및 일섬(Dash) 파라미터 (PRD 3.3절)
PLAYER_DASH_SPEED: float = 2400.0       # 일섬 관통 이동 속도 (px/s)
PLAYER_DASH_DISTANCE: float = 180.0     # 일섬 관통 고정 거리 (px)
PLAYER_DASH_STACK_DAMAGE: float = 40.0  # 일반 스택 소모 시 1스택당 데미지
PLAYER_DASH_PENETRATE_RATIO: float = 0.5 # 관통 궤적 적들에 대한 데미지 비율 (50%)

# ==========================================
# 3. 혼령 수리검(Shuriken) 설정 (PRD 3.1절)
# ==========================================
SHURIKEN_RADIUS: float = 8.0
SHURIKEN_FLY_SPEED: float = 1300.0      # 비행 속도 (px/s)
SHURIKEN_RETURN_SPEED: float = 1600.0   # 플레이어 추적 복귀 속도 (px/s)
SHURIKEN_MAX_BOUNCE: int = 3            # 최대 반사 횟수 후 복귀
SHURIKEN_HIT_DAMAGE: float = 10.0       # 수리검 기본 투사체 적중 피해

# ==========================================
# 4. 적(Enemy) 베이스 설정 (PRD 3.2절, 4절)
# ==========================================
ENEMY_BASE_RADIUS: float = 20.0
ENEMY_BASE_MAX_HP: float = 100.0
ENEMY_BASE_TURN_RATE: float = 2.0       # 시선 회전 속도 제한 (rad/s)

# ==========================================
# 5. 불릿타임 및 처치 리셋 설정 (PRD 3.4절)
# ==========================================
BULLET_TIME_SCALE: float = 0.1          # 시간 감속 배율 (10% 속도)
BULLET_TIME_DURATION: float = 0.8       # 실제 현실 시간(Unscaled Time) 기준 지속 시간 (초)
