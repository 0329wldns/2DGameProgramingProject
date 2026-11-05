"""
play_scene.py
메인 전투 스테이지 씬. 플레이어 및 적, 수리검 렌더링과 업데이트가 일어나는 핵심 씬입니다.
"""

from typing import Any
import pico2d
from sdl2 import SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE, SDLK_F11
import game_framework
import game_world
from entities.player import Player
from entities.obstacle import Obstacle
from entities.shuriken import Shuriken
from entities.enemy import Enemy
from ui.cursor import Cursor

player: Player | None = None
cursor: Cursor | None = None
obstacles: list[Obstacle] = []
enemies: list[Enemy] = []


def init() -> None:
    """씬 초기화: 리소스 로드 및 초기 월드 세팅"""
    global player, cursor, obstacles, enemies
    game_world.clear()
    obstacles.clear()
    enemies.clear()

    # 시스템 기본 커서를 숨기고 인게임 크로스헤어로 대체
    pico2d.hide_cursor()

    # 인게임 커스텀 조준선 생성 (UI 레이어 등록)
    cursor = Cursor(x=640.0, y=360.0)
    game_world.add_object(cursor, game_world.LAYER_UI)

    # 플레이어 생성 (화면 좌측 중앙 부근 스폰)
    player = Player(x=250.0, y=360.0)
    game_world.add_object(player, game_world.LAYER_PLAYER)

    # 테스트용 기둥(장애물) 생성 (PRD 6.2절 사양: 중앙 기둥 배치)
    pillar = Obstacle(x=640.0, y=360.0, width=80.0, height=220.0)
    obstacles.append(pillar)
    game_world.add_object(pillar, game_world.LAYER_OBSTACLE)

    # 테스트용 적 생성 (PRD 6.2절 사양: 기둥 우측 배치, 초기 시선 좌측 [-1, 0])
    enemy = Enemy(x=900.0, y=360.0, dir_x=-1.0, dir_y=0.0, target=player)
    enemies.append(enemy)
    game_world.add_object(enemy, game_world.LAYER_ENEMY)


def finish() -> None:
    """씬 종료: 리소스 해제 및 객체 정리"""
    global player, cursor, obstacles, enemies
    pico2d.show_cursor()
    game_world.clear()
    obstacles.clear()
    enemies.clear()
    player = None
    cursor = None


def pause() -> None:
    """씬 일시정지 (서브 씬 푸시 등)"""
    pass


def resume() -> None:
    """씬 재개"""
    pass


def handle_events() -> None:
    """사용자 입력 이벤트 처리 (ESC 키, F11 전체화면 토글 및 플레이어 입력 전달)"""
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
    game_world.render()
    pico2d.update_canvas()

