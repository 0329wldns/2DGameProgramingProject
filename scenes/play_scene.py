"""
play_scene.py
메인 전투 스테이지 씬. 플레이어 및 적, 수리검 렌더링과 업데이트가 일어나는 핵심 씬입니다.
"""

from typing import Any
import pico2d
from sdl2 import SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE, SDLK_F11, SDLK_F1, SDLK_F2
import game_framework
import game_world
from entities.player import Player, STATE_BULLET_TIME
from entities.obstacle import Obstacle
from entities.shuriken import Shuriken
from entities.enemy import Enemy, Shielder
from ui.cursor import Cursor
from ui.trajectory import TrajectoryGuide
import config

player: Player | None = None
cursor: Cursor | None = None
trajectory_guide: TrajectoryGuide | None = None
obstacles: list[Obstacle] = []
enemies: list[Enemy] = []
show_trajectory: bool = False


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

    def spawn_shielder(x: float, y: float, dir_x: float = -1.0, dir_y: float = 0.0) -> Shielder:
        s = Shielder(x=x, y=y, dir_x=dir_x, dir_y=dir_y, target=player)
        enemies.append(s)
        game_world.add_object(s, game_world.LAYER_ENEMY)
        return s

    # 1. 전술적 반사용 기둥(장애물) 배치
    spawn_obstacle(x=750.0, y=540.0, w=80.0, h=340.0)   # 중앙 좌측 기둥 (적 전방 엄폐)
    spawn_obstacle(x=1450.0, y=540.0, w=80.0, h=240.0)  # 중앙 우측 기둥 (외곽 반사 지원)

    # 2. 연쇄 돌진(Chain Dash) 콤보 테스트용 적 배치 (이동거리 400px 최적화)
    # [적 1] 기둥 뒤 메인 타겟: 전방 가드 방패병(Shielder) -> 외벽/기둥 배후 반사타격으로 처형 시동 (HP 140)
    spawn_shielder(x=950.0, y=540.0, dir_x=-1.0, dir_y=0.0)

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
    """사용자 입력 이벤트 처리 (ESC 종료, F11 전체화면, F1 리셋, F2 궤적 표시 토글 및 플레이어 입력 전달)"""
    global player, cursor, show_trajectory
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
            elif event.key == SDLK_F2:
                show_trajectory = not show_trajectory
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

    # 2. 적 호버(Hover) 검사 (커서가 적 위에 올라갔을 때 해당 적 타겟 하이라이트 활성화)
    best_enemy = None
    min_dist = float('inf')
    for enemy in enemies:
        enemy.is_hovered = False
        if cursor and not enemy.is_dead and enemy.hp > 0.0:
            import math
            dist = math.hypot(cursor.x - enemy.x, cursor.y - enemy.y)
            # 플레이어 돌진 타겟팅 인식 반경(radius + 18.0)과 동일하게 판정
            if dist <= (enemy.radius + 18.0) and dist < min_dist:
                min_dist = dist
                best_enemy = enemy

    if best_enemy is not None:
        best_enemy.is_hovered = True

    # 2. 플레이어 및 적 vs 장애물 충돌 보정 (Sliding)
    for obs in obstacles:
        if player:
            obs.resolve_player_collision(player)
        for enemy in enemies:
            if not enemy.is_dead:
                obs.resolve_entity_collision(enemy)

    # 3. 수리검 vs 장애물 반사 및 적 피격 충돌 판정
    shurikens = game_world.world[game_world.LAYER_PROJECTILE]
    for obj in list(shurikens):
        if isinstance(obj, Shuriken):
            for obs in obstacles:
                obs.resolve_shuriken_collision(obj)
            for enemy in enemies:
                if enemy.resolve_shuriken_collision(obj):
                    break


def _draw_bullet_time_hud(p: Player) -> None:
    """불릿타임 진입 시 화면 상단 중앙에 표시되는 시네마틱 타이머 바 HUD (PRD 3.4절)"""
    if p.bullet_time_duration <= 0.0:
        return

    ratio = max(0.0, min(1.0, p.bullet_time_timer / p.bullet_time_duration))
    cx = config.CANVAS_WIDTH / 2.0
    cy = config.CANVAS_HEIGHT - 36.0
    bar_w = 340.0
    bar_h = 8.0

    left = int(cx - bar_w / 2.0)
    right = int(cx + bar_w / 2.0)
    bottom = int(cy - bar_h / 2.0)
    top = int(cy + bar_h / 2.0)

    # 1. 배경 바 (Dark Slate)
    pico2d.draw_rectangle(left, bottom, right, top, r=15, g=25, b=38)

    # 2. 잔여 시간 채움 바 (25% 미만 잔여 시 경고 주황색 플래시, 평상시 형광 청록색)
    fill_w = bar_w * ratio
    if fill_w > 0:
        if ratio > 0.25:
            r, g, b = 0, 255, 255
        else:
            r, g, b = 255, 170, 30
        pico2d.draw_rectangle(left, bottom, int(left + fill_w), top, r=r, g=g, b=b, filled=True)

    # 3. 네온 발광 테두리
    pico2d.draw_rectangle(left - 2, bottom - 2, right + 2, top + 2, r=0, g=200, b=240)

    # 4. 좌우 날개 브래킷 < [   ] >
    pico2d.draw_line(left - 12, int(cy), left - 5, int(cy + 6), r=0, g=255, b=255)
    pico2d.draw_line(left - 12, int(cy), left - 5, int(cy - 6), r=0, g=255, b=255)
    pico2d.draw_line(right + 12, int(cy), right + 5, int(cy + 6), r=0, g=255, b=255)
    pico2d.draw_line(right + 12, int(cy), right + 5, int(cy - 6), r=0, g=255, b=255)

    # 5. 하단 중앙 다이아몬드 포인트
    pico2d.draw_rectangle(int(cx - 3), bottom - 6, int(cx + 3), bottom, r=0, g=255, b=255, filled=True)


def draw() -> None:
    """씬 렌더링"""
    pico2d.clear_canvas()

    # 1. 수리검 투척 및 반사 예상 궤적 가이드 렌더링 (F2 키로 토글 가능)
    if show_trajectory and trajectory_guide and player:
        trajectory_guide.render(player, obstacles)

    # 2. 게임 월드 객체 렌더링 (장애물, 플레이어, 적, 수리검, UI)
    game_world.render()

    # 3. 불릿타임 상단 전역 타이머 바 HUD 렌더링 (PRD 3.4절)
    if player and getattr(player, 'state', None) == STATE_BULLET_TIME:
        _draw_bullet_time_hud(player)

    pico2d.update_canvas()

