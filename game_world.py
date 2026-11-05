"""
game_world.py
게임 내 모든 엔티티의 레이어별 등록, 업데이트, 렌더링 및 충돌 관리를 담당하는 모듈.
"""

from typing import Any

# 레이어 정의 (숫자가 클수록 나중에 렌더링됨)
LAYER_BACKGROUND: int = 0
LAYER_OBSTACLE: int = 1
LAYER_ENEMY: int = 2
LAYER_PLAYER: int = 3
LAYER_PROJECTILE: int = 4
LAYER_UI: int = 5
LAYER_COUNT: int = 6

# 월드 내 객체 레이어 리스트
world: list[list[Any]] = [[] for _ in range(LAYER_COUNT)]


def add_object(obj: Any, layer: int) -> None:
    """지정된 레이어에 게임 객체를 추가합니다."""
    if 0 <= layer < LAYER_COUNT:
        world[layer].append(obj)


def remove_object(obj: Any) -> None:
    """월드에서 해당 객체를 제거합니다."""
    for layer in world:
        if obj in layer:
            layer.remove(obj)
            return


def clear() -> None:
    """월드의 모든 객체를 비웁니다."""
    for layer in world:
        layer.clear()


def update(scaled_dt: float, unscaled_dt: float) -> None:
    """월드의 모든 객체를 업데이트합니다."""
    for layer in world:
        for obj in layer:
            if hasattr(obj, 'update'):
                obj.update(scaled_dt, unscaled_dt)


def render() -> None:
    """레이어 순서대로 모든 객체를 렌더링합니다."""
    for layer in world:
        for obj in layer:
            if hasattr(obj, 'draw'):
                obj.draw()

