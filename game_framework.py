"""
game_framework.py
씬(Scene) 스택 관리, 프레임별 델타 타임(Scaled / Unscaled) 관리 및 가상 해상도/전체화면 제어 모듈.
"""

import time
from typing import Any
import pico2d.pico2d as _pico2d_internal
from sdl2 import (
    SDL_SetWindowFullscreen,
    SDL_WINDOW_FULLSCREEN_DESKTOP,
    SDL_RenderSetLogicalSize
)

# 게임 루프 상태
running: bool = True
stack: list[Any] = []

# 시간 관리 (PRD 3.4절 불릿타임 지원을 위한 타임스케일)
time_scale: float = 1.0
target_fps: int = 120
frame_time_limit: float = 1.0 / target_fps

# 가상 논리 해상도 및 전체화면 상태 (PRD 1절: 1280x720 16:9 고정)
logical_width: int = 1280
logical_height: int = 720
is_fullscreen: bool = False


def init_display_scaling(width: int = 1280, height: int = 720) -> None:
    """
    가상 논리 해상도를 설정하여 모니터 해상도(노트북, FHD, QHD, 4K 등)와 무관하게
    화면 비율(16:9)을 유지하며 GPU 하드웨어 자동 스케일링 및 마우스 좌표 역보정을 적용합니다.
    """
    global logical_width, logical_height
    logical_width, logical_height = width, height
    if hasattr(_pico2d_internal, 'renderer') and _pico2d_internal.renderer is not None:
        SDL_RenderSetLogicalSize(_pico2d_internal.renderer, logical_width, logical_height)


def toggle_fullscreen() -> None:
    """
    F11 입력 시 창 모드와 전체화면(모니터 해상도 자동 맞춤)을 토글합니다.
    어떤 모니터에서도 화면 밖으로 삐져나가지 않고 16:9 레터박스/스케일링을 유지합니다.
    """
    global is_fullscreen
    if not hasattr(_pico2d_internal, 'window') or _pico2d_internal.window is None:
        return

    is_fullscreen = not is_fullscreen
    flags = SDL_WINDOW_FULLSCREEN_DESKTOP if is_fullscreen else 0
    SDL_SetWindowFullscreen(_pico2d_internal.window, flags)

    # 전체화면 전환 후에도 가상 논리 해상도 비율 유지 보장
    if hasattr(_pico2d_internal, 'renderer') and _pico2d_internal.renderer is not None:
        SDL_RenderSetLogicalSize(_pico2d_internal.renderer, logical_width, logical_height)


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

    # 가상 해상도 스케일러 자동 초기화
    init_display_scaling(logical_width, logical_height)

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

