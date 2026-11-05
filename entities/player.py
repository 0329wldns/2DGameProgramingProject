"""
player.py
플레이어 엔티티 모듈.
WASD 8방향 정규화 이동 및 향후 구르기, 돌진 FSM의 기초가 되는 엔티티입니다.
"""

import math
from typing import Any
import pico2d
from sdl2 import (
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_w, SDLK_a, SDLK_s, SDLK_d,
    SDLK_SPACE
)

# 화면 크기 상수
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


class Player:
    def __init__(self, x: float = 640.0, y: float = 360.0) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = 16.0
        self.move_speed: float = 300.0  # 초당 300 픽셀 이동

        # 키보드 입력 상태 플래그
        self.key_up: bool = False
        self.key_down: bool = False
        self.key_left: bool = False
        self.key_right: bool = False

        # 바라보는 방향 및 마우스 위치
        self.facing_dir: tuple[float, float] = (1.0, 0.0)
        self.mouse_x: float = x
        self.mouse_y: float = y

    def handle_event(self, event: Any) -> None:
        """키보드 입력 이벤트 처리"""
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_w:
                self.key_up = True
            elif event.key == SDLK_s:
                self.key_down = True
            elif event.key == SDLK_a:
                self.key_left = True
            elif event.key == SDLK_d:
                self.key_right = True
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_w:
                self.key_up = False
            elif event.key == SDLK_s:
                self.key_down = False
            elif event.key == SDLK_a:
                self.key_left = False
            elif event.key == SDLK_d:
                self.key_right = False

    def update_movement(self, dt: float) -> None:
        """
        # TODO(Copilot): 8방향 등속 이동 및 대각선 벡터 정규화 구현
        # PRD 2절 명세:
        # 1. 입력 플래그(key_up, key_down, key_left, key_right)를 조합하여 dx, dy 방향 벡터 계산
        #    - W: +y, S: -y, A: -x, D: +x
        # 2. 이동 벡터의 크기가 0보다 클 경우, 정규화(Normalize, ||v|| = 1) 필수 적용
        #    - 대각선 이동 시에도 동일한 move_speed가 유지되어야 함
        # 3. dt(델타 타임)와 move_speed를 곱하여 self.x, self.y 좌표 갱신
        # 4. 화면 경계(0 + radius ~ CANVAS_WIDTH - radius, 0 + radius ~ CANVAS_HEIGHT - radius) 이탈 방지 클램핑
        """
        dx = int(self.key_right) - int(self.key_left)
        dy = int(self.key_up) - int(self.key_down)

        direction_length = math.hypot(dx, dy)
        if direction_length > 0.0:
            dx /= direction_length
            dy /= direction_length
            self.x += dx * self.move_speed * dt
            self.y += dy * self.move_speed * dt

        self.x = max(self.radius, min(CANVAS_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(CANVAS_HEIGHT - self.radius, self.y))

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """프레임 업데이트 (물리 이동은 scaled_dt 기준)"""
        self.update_movement(scaled_dt)

    def draw(self) -> None:
        """플레이어 임시 렌더링 (사각 히트박스 시각화)"""
        # 임시 디버그 렌더링: 플레이어 중심 기준 사각형 드로우
        left = int(self.x - self.radius)
        bottom = int(self.y - self.radius)
        right = int(self.x + self.radius)
        top = int(self.y + self.radius)
        pico2d.draw_rectangle(left, bottom, right, top)
