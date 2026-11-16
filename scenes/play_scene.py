"""
play_scene.py
메인 전투 스테이지 씬. 플레이어 및 적, 수리검 렌더링과 업데이트가 일어나는 핵심 씬입니다.
"""

from typing import Any
import pico2d
from sdl2 import SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE, SDLK_F11, SDLK_F1
import game_framework
import game_world
from entities.player import Player
from entities.obstacle import Obstacle
from entities.shuriken import Shuriken
from entities.enemy import Enemy
from ui.cursor import Cursor
from ui.trajectory import TrajectoryGuide
import config

player: Player | None = None
cursor: Cursor | None = None
trajectory_guide: TrajectoryGuide | None = None
obstacles: list[Obstacle] = []
enemies: list[Enemy] = []


def init() -> None:
    """씬 초기화: 리소스 로드 및 초기 월드 세팅"""
    global player, cursor, trajectory_guide, obstacles, enemies
    game_world.clear()
    obstacles.clear()
    enemies.clear()
    game_framework.set_time_scale(1.0)

    # 시스템 기본 커서를 숨기고 인게임 크로스헤어로 대체
    pico2d.hide_cursor()

    # 인게임 커스텀 조준선 생성 (UI 레이어 등록)
    cursor = Cursor(x=960.0, y=540.0)
    game_world.add_object(cursor, game_world.LAYER_UI)

    # 수리검 투척 및 반사 궤적 가이드 생성
    trajectory_guide = TrajectoryGuide(max_bounces=config.SHURIKEN_MAX_BOUNCE)

    # 플레이어 생성 (화면 좌측 중앙 부근 스폰)
    player = Player(x=300.0, y=540.0)
    game_world.add_object(player, game_world.LAYER_PLAYER)

    # 엔티티 스폰 헬퍼
    def spawn_obstacle(x: float, y: float, w: float, h: float) -> Obstacle:
        obs = Obstacle(x=x, y=y, width=w, height=h)
        obstacles.append(obs)
        game_world.add_object(obs, game_world.LAYER_OBSTACLE)
        return obs

    def spawn_enemy(x: float, y: float, hp: float = 100.0, dir_x: float = -1.0, dir_y: float = 0.0) -> Enemy:
        e = Enemy(x=x, y=y, dir_x=dir_x, dir_y=dir_y, target=player, max_hp=hp)
        enemies.append(e)
        game_world.add_object(e, game_world.LAYER_ENEMY)
        return e

    # 1. 전술적 반사용 기둥(장애물) 배치
    spawn_obstacle(x=750.0, y=540.0, w=80.0, h=340.0)   # 중앙 좌측 기둥 (적 전방 엄폐)
    spawn_obstacle(x=1450.0, y=540.0, w=80.0, h=240.0)  # 중앙 우측 기둥 (외곽 반사 지원)

    # 2. 연쇄 돌진(Chain Dash) 콤보 테스트용 적 배치 (이동거리 250px 최적화)
    # [적 1] 기둥 뒤 메인 타겟: 배후 반사타격으로 처형 시동 (HP 100)
    spawn_enemy(x=950.0, y=540.0, hp=100.0, dir_x=-1.0, dir_y=0.0)

    # [적 2] 1차 관통 궤적 테스트: 적 1 처형 돌진 경로상에서 휩쓸려 사망 (HP 50)
    spawn_enemy(x=1100.0, y=540.0, hp=50.0, dir_x=-1.0, dir_y=0.0)

    # [적 3] 2차 연쇄 돌진 (우상단 징검다리, HP 50)
    spawn_enemy(x=1300.0, y=780.0, hp=50.0, dir_x=-1.0, dir_y=-0.5)

    # [적 4] 3차 연쇄 돌진 (우측 외곽 징검다리, HP 50)
    spawn_enemy(x=1650.0, y=540.0, hp=50.0, dir_x=-1.0, dir_y=0.0)

    # [적 5] 4차 연쇄 돌진 (우하단 징검다리, HP 50)
    spawn_enemy(x=1300.0, y=300.0, hp=50.0, dir_x=-1.0, dir_y=0.5)


def finish() -> None:
    """씬 종료: 리소스 해제 및 객체 정리"""
    global player, cursor, trajectory_guide, obstacles, enemies
    game_framework.reset_visual_effects()
    pico2d.show_cursor()
    game_world.clear()
    obstacles.clear()
    enemies.clear()
    player = None
    cursor = None
    trajectory_guide = None


def restart() -> None:
    """F1 키 입력 시 씬을 완전히 초기 상태로 리셋합니다."""
    finish()
    game_framework.set_time_scale(1.0)
    game_framework.reset_visual_effects()
    init()


def pause() -> None:
    """씬 일시정지 (서브 씬 푸시 등)"""
    pass


def resume() -> None:
    """씬 재개"""
    pass


def handle_events() -> None:
    """사용자 입력 이벤트 처리 (ESC 종료, F11 전체화면, F1 리셋 및 플레이어 입력 전달)"""
    global player, cursor
    events = pico2d.get_events()
    for event in events:
        if event.type == SDL_QUIT:
            game_framework.quit()
            continue

        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                game_framework.quit()
                continue
            elif event.key == SDLK_F11:
                game_framework.toggle_fullscreen()
                continue
            elif event.key == SDLK_F1:
                restart()
                continue

        # 커서 위치 갱신
        if cursor:
            cursor.handle_event(event)

        # 시스템 단에서 가로채지 않은 모든 이벤트(WASD, SPACE, 마우스 등)는 플레이어에게 전달
        if player:
            player.handle_event(event)


def update(scaled_dt: float, unscaled_dt: float) -> None:
    """월드 엔티티 상태 갱신 및 충돌 처리"""
    # 1. 모든 엔티티 위치 및 상태 갱신
    game_world.update(scaled_dt, unscaled_dt)

    # 2. 커서 타겟 호버(Hover) 검사 (적 위에 커서가 올라갔을 때 조준선 강조)
    if cursor:
        is_hover = False
        for enemy in enemies:
            import math
            dist = math.hypot(cursor.x - enemy.x, cursor.y - enemy.y)
            if dist <= enemy.radius:
                is_hover = True
                break
        cursor.is_hovering_target = is_hover

    # 2. 플레이어 vs 장애물 충돌 보정 (Sliding)
    if player:
        for obs in obstacles:
            obs.resolve_player_collision(player)

    # 3. 수리검 vs 장애물 반사 및 적 피격 충돌 판정
    shurikens = game_world.world[game_world.LAYER_PROJECTILE]
    for obj in list(shurikens):
        if isinstance(obj, Shuriken):
            for obs in obstacles:
                obs.resolve_shuriken_collision(obj)
            for enemy in enemies:
                if enemy.resolve_shuriken_collision(obj):
                    break


def draw() -> None:
    """씬 렌더링"""
    pico2d.clear_canvas()

    # 1. 수리검 투척 및 반사 예상 궤적 가이드 렌더링 (바닥에 점선 표시)
    if trajectory_guide and player:
        trajectory_guide.render(player, obstacles)

    # 2. 게임 월드 객체 렌더링 (장애물, 플레이어, 적, 수리검, UI)
    game_world.render()
    pico2d.update_canvas()

