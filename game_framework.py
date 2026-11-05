"""
game_framework.py
씬(Scene) 스택 관리 및 프레임별 델타 타임(Scaled / Unscaled) 관리 모듈.
"""

import time
from typing import Any

# 게임 루프 상태
running: bool = True
stack: list[Any] = []

# 시간 관리 (PRD 3.4절 불릿타임 지원을 위한 타임스케일)
time_scale: float = 1.0
target_fps: int = 120
frame_time_limit: float = 1.0 / target_fps


def set_time_scale(scale: float) -> None:
    """전역 시간 배율을 설정합니다. (불릿타임 시 0.1 등)"""
    global time_scale
    time_scale = max(0.0, scale)


def get_time_scale() -> float:
    """현재 전역 시간 배율을 반환합니다."""
    return time_scale


def change_scene(scene: Any) -> None:
    """현재 씬을 종료하고 새로운 씬으로 전환합니다."""
    global stack
    if stack:
        stack[-1].finish()
        stack.pop()
    stack.append(scene)
    scene.init()


def push_scene(scene: Any) -> None:
    """현재 씬을 일시정지하고 새 씬을 스택 위에 올립니다."""
    global stack
    if stack:
        stack[-1].pause()
    stack.append(scene)
    scene.init()


def pop_scene() -> None:
    """현재 씬을 종료하고 이전 씬을 재개합니다."""
    global stack
    if stack:
        stack[-1].finish()
        stack.pop()
    if stack:
        stack[-1].resume()


def quit() -> None:
    """전체 게임 루프를 종료합니다."""
    global running
    running = False


def run(start_scene: Any) -> None:
    """게임 메인 루프를 실행합니다."""
    global running, stack
    running = True
    stack = [start_scene]
    start_scene.init()

    last_time = time.time()

    while running:
        current_time = time.time()
        unscaled_dt = current_time - last_time
        last_time = current_time

        # 비정상적인 프레임 스파이크 방지 (최대 0.1초로 캡핑)
        if unscaled_dt > 0.1:
            unscaled_dt = 0.1

        scaled_dt = unscaled_dt * time_scale

        # 활성화된 씬 처리
        current_scene = stack[-1]
        current_scene.handle_events()
        current_scene.update(scaled_dt, unscaled_dt)
        current_scene.draw()

        # 프레임 제한을 위한 미세 딜레이
        elapsed = time.time() - current_time
        if elapsed < frame_time_limit:
            time.sleep(frame_time_limit - elapsed)

    # 루프 종료 후 남은 씬 정리
    while stack:
        stack[-1].finish()
        stack.pop()
