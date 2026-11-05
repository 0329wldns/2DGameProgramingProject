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
    SDLK_SPACE,
    SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN,
    SDL_BUTTON_LEFT, SDL_BUTTON_RIGHT
)
import game_world
from entities.shuriken import Shuriken

# 화면 크기 상수
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


class Player:
    def __init__(self, x: float = 640.0, y: float = 360.0) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = 16.0
        self.move_speed: float = 300.0  # 초당 300 픽셀 이동

        # 탄창 자원 관리 (PRD 3.1 명세: 최대 3개)
        self.max_ammo: int = 3
        self.current_ammo: int = 3

        # 키보드 입력 상태 플래그
        self.key_up: bool = False
        self.key_down: bool = False
        self.key_left: bool = False
        self.key_right: bool = False

        # 바라보는 방향 및 마우스 위치 (캔버스 좌표계 기준)
        self.mouse_x: float = x
        self.mouse_y: float = y

    def shoot_shuriken(self) -> None:
        """
        혼령 수리검 발사 로직
        - 탄창이 있을 때만 발사
        - 플레이어 위치 -> 마우스 좌표 방향 벡터 정규화 후 수리검 투척
        """
        if self.current_ammo <= 0:
            return

        to_x = self.mouse_x - self.x
        to_y = self.mouse_y - self.y
        dist = math.hypot(to_x, to_y)

        # 마우스와 완전히 겹쳐있는 경우 기본 오른쪽 방향
        if dist > 0.0:
            dir_x = to_x / dist
            dir_y = to_y / dist
        else:
            dir_x, dir_y = 1.0, 0.0

        # 약간 앞에서 발사되도록 오프셋 적용
        spawn_x = self.x + dir_x * (self.radius + 5.0)
        spawn_y = self.y + dir_y * (self.radius + 5.0)

        shuriken = Shuriken(spawn_x, spawn_y, dir_x, dir_y, owner=self)
        game_world.add_object(shuriken, game_world.LAYER_PROJECTILE)

        self.current_ammo -= 1

    def handle_event(self, event: Any) -> None:
        """키보드 및 마우스 입력 이벤트 처리"""
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
        elif event.type == SDL_MOUSEMOTION:
            # SDL 마우스 y좌표(상단 0)를 pico2d 데카르트 좌표계(하단 0)로 반전 변환
            self.mouse_x = float(event.x)
            self.mouse_y = float(CANVAS_HEIGHT - 1 - event.y)
        elif event.type == SDL_MOUSEBUTTONDOWN:
            if event.button == SDL_BUTTON_LEFT:
                # 마우스 좌표 동기화 후 수리검 발사
                self.mouse_x = float(event.x)
                self.mouse_y = float(CANVAS_HEIGHT - 1 - event.y)
                self.shoot_shuriken()

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
        """플레이어 임시 렌더링 (사각 히트박스 시각화 및 머리 위 탄창 표시)"""
        left = int(self.x - self.radius)
        bottom = int(self.y - self.radius)
        right = int(self.x + self.radius)
        top = int(self.y + self.radius)
        pico2d.draw_rectangle(left, bottom, right, top)

        # 잔여 탄창 시각화 (플레이어 머리 위에 3개 표시)
        start_x = self.x - 12.0
        ammo_y = self.y + self.radius + 8.0
        for i in range(self.max_ammo):
            bx = start_x + i * 12.0
            if i < self.current_ammo:
                pico2d.draw_rectangle(int(bx - 4), int(ammo_y - 4), int(bx + 4), int(ammo_y + 4))
