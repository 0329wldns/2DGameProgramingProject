"""
play_scene.py
메인 전투 스테이지 씬. 플레이어 및 적, 수리검 렌더링과 업데이트가 일어나는 핵심 씬입니다.
"""

from typing import Any
import pico2d
from sdl2 import SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE
import game_framework
import game_world
from entities.player import Player

player: Player | None = None


def init() -> None:
    """씬 초기화: 리소스 로드 및 초기 월드 세팅"""
    global player
    game_world.clear()
    player = Player(x=640.0, y=360.0)
    game_world.add_object(player, game_world.LAYER_PLAYER)


def finish() -> None:
    """씬 종료: 리소스 해제 및 객체 정리"""
    global player
    game_world.clear()
    player = None


def pause() -> None:
    """씬 일시정지 (서브 씬 푸시 등)"""
    pass


def resume() -> None:
    """씬 재개"""
    pass


def handle_events() -> None:
    """사용자 입력 이벤트 처리 (ESC 키 및 플레이어 입력 전달)"""
    global player
    events = pico2d.get_events()
    for event in events:
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.quit()
        else:
            if player:
                player.handle_event(event)


def update(scaled_dt: float, unscaled_dt: float) -> None:
    """월드 엔티티 상태 갱신"""
    game_world.update(scaled_dt, unscaled_dt)


def draw() -> None:
    """씬 렌더링"""
    pico2d.clear_canvas()
    game_world.render()
    pico2d.update_canvas()

