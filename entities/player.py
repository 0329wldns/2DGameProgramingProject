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

# 플레이어 상태 머신(FSM) 상수
STATE_NORMAL: int = 0
STATE_ROLL: int = 1
STATE_DASH: int = 2
STATE_BULLET_TIME: int = 3

# 화면 크기 상수
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


class Player:
    def __init__(self, x: float = 640.0, y: float = 360.0) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = 16.0
        self.move_speed: float = 300.0  # 초당 300 픽셀 이동

        # 플레이어 FSM 상태
        self.state: int = STATE_NORMAL

        # 구르기(Roll) 파라미터 (PRD 2절: 순간 가속 포지셔닝, I-Frame 없음, 쿨다운 존재)
        self.roll_speed: float = 650.0          # 구르기 순간 속도
        self.roll_duration: float = 0.22        # 구르기 지속 시간 (초)
        self.roll_cooldown: float = 0.6         # 구르기 재사용 대기시간 (초)
        self.roll_timer: float = 0.0            # 구르기 잔여 시간 타이머
        self.roll_cooldown_timer: float = 0.0   # 쿨다운 타이머
        self.roll_dir_x: float = 1.0            # 구르기 진행 방향
        self.roll_dir_y: float = 0.0
        self.last_move_dir: tuple[float, float] = (1.0, 0.0)  # 마지막 이동 방향 기록

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
            elif event.key == SDLK_SPACE:
                self.start_roll()
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

    def start_roll(self) -> None:
        """
        # TODO(Copilot): 구르기(Roll) 시작 처리
        # PRD 2절 명세:
        # 1. self.state == STATE_NORMAL 이고 self.roll_cooldown_timer <= 0.0 일 때만 발동
        # 2. 구르기 방향 벡터(dx, dy) 결정:
        #    - 현재 WASD 입력(dx = right - left, dy = up - down) 확인
        #    - 만약 이동 키가 눌려있다면 정규화하여 self.roll_dir_x, self.roll_dir_y 설정
        #    - 이동 키가 눌려있지 않다면(정지 상태):
        #      self.last_move_dir 또는 마우스 방향(mouse_x - x, mouse_y - y)을 정규화하여 구르기 방향으로 설정
        # 3. 상태 및 타이머 설정:
        #    - self.state = STATE_ROLL
        #    - self.roll_timer = self.roll_duration
        #    - self.roll_cooldown_timer = self.roll_cooldown
        """
        pass

    def update_roll(self, dt: float) -> None:
        """
        # TODO(Copilot): 구르기 물리 이동 및 상태 전이
        # PRD 2절 명세:
        # 1. self.roll_timer -= dt
        # 2. 구르기 속도로 순간 가속 이동:
        #    - self.x += self.roll_dir_x * self.roll_speed * dt
        #    - self.y += self.roll_dir_y * self.roll_speed * dt
        # 3. 화면 경계(CANVAS_WIDTH, CANVAS_HEIGHT) 클램핑
        # 4. self.roll_timer <= 0.0 이 되면:
        #    - self.state = STATE_NORMAL 상태 복귀
        """
        pass

    def update_movement(self, dt: float) -> None:
        """8방향 등속 이동 및 대각선 벡터 정규화"""
        dx = int(self.key_right) - int(self.key_left)
        dy = int(self.key_up) - int(self.key_down)

        direction_length = math.hypot(dx, dy)
        if direction_length > 0.0:
            dx /= direction_length
            dy /= direction_length
            self.last_move_dir = (dx, dy)
            self.x += dx * self.move_speed * dt
            self.y += dy * self.move_speed * dt

        self.x = max(self.radius, min(CANVAS_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(CANVAS_HEIGHT - self.radius, self.y))

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """프레임 업데이트 (FSM 상태별 처리 및 쿨다운 차감)"""
        # 쿨다운 타이머 갱신 (scaled_dt 기준)
        if self.roll_cooldown_timer > 0.0:
            self.roll_cooldown_timer = max(0.0, self.roll_cooldown_timer - scaled_dt)

        # FSM 상태별 이동 처리
        if self.state == STATE_ROLL:
            self.update_roll(scaled_dt)
        else:
            self.update_movement(scaled_dt)

    def draw(self) -> None:
        """플레이어 임시 렌더링 (사각 히트박스 시각화 및 머리 위 탄창 표시)"""
        # 구르기 상태일 때는 순간적으로 납작/축소되는 시각적 피드백 제공
        rx = self.radius * 0.7 if self.state == STATE_ROLL else self.radius
        ry = self.radius * 0.7 if self.state == STATE_ROLL else self.radius

        left = int(self.x - rx)
        bottom = int(self.y - ry)
        right = int(self.x + rx)
        top = int(self.y + ry)
        pico2d.draw_rectangle(left, bottom, right, top)

        # 잔여 탄창 시각화 (플레이어 머리 위에 3개 표시)
        start_x = self.x - 12.0
        ammo_y = self.y + self.radius + 8.0
        for i in range(self.max_ammo):
            bx = start_x + i * 12.0
            if i < self.current_ammo:
                pico2d.draw_rectangle(int(bx - 4), int(ammo_y - 4), int(bx + 4), int(ammo_y + 4))
