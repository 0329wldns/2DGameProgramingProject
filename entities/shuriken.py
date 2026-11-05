"""
shuriken.py
혼령 수리검(Soul Shuriken) 투사체 엔티티 및 FSM 모듈.
PRD 3.1절 명세에 따른 상태 머신(FLYING, RETURNING, EMBEDDED) 및 반사/복귀 로직.
"""

import math
from typing import Any
import pico2d
import game_world

# 수리검 상태 상수
STATE_FLYING: int = 0
STATE_RETURNING: int = 1
STATE_EMBEDDED: int = 2

# 화면 크기 상수
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


class Shuriken:
    def __init__(self, x: float, y: float, dir_x: float, dir_y: float, owner: Any) -> None:
        self.x: float = x
        self.y: float = y
        self.dir_x: float = dir_x
        self.dir_y: float = dir_y
        self.owner: Any = owner

        self.radius: float = 8.0
        self.speed: float = 1300.0         # 비행 속도 (px/s) - 하이템포 튜닝
        self.return_speed: float = 1600.0  # 플레이어 복귀 추적 속도 (px/s)

        self.bounce_count: int = 0
        self.max_bounce: int = 3           # 최대 반사 횟수 (PRD 3.1)
        self.state: int = STATE_FLYING

    def update_flying(self, dt: float) -> None:
        """
        # TODO(Copilot): 비행 이동 및 외벽 반사 물리 구현
        # PRD 3.1절 명세:
        # 1. dir_x, dir_y 방향으로 self.speed * dt 만큼 self.x, self.y 전진
        # 2. 4면 외벽 충돌 검사 (반경 self.radius 고려):
        #    - 좌측 벽 (x - radius <= 0) or 우측 벽 (x + radius >= CANVAS_WIDTH):
        #        dir_x 반전 (-dir_x), 위치를 경계 내부로 보정, bounce_count += 1
        #    - 하단 벽 (y - radius <= 0) or 상단 벽 (y + radius >= CANVAS_HEIGHT):
        #        dir_y 반전 (-dir_y), 위치를 경계 내부로 보정, bounce_count += 1
        # 3. bounce_count >= self.max_bounce 도달 시:
        #    - self.state = STATE_RETURNING 전이
        """
        # 기본 전진
        self.x += self.dir_x * self.speed * dt
        self.y += self.dir_y * self.speed * dt

        # 외벽 충돌 및 반사 처리 (Copilot 구현 영역)
        hit_wall = False
        if self.x - self.radius <= 0:
            self.x = self.radius
            self.dir_x = -self.dir_x
            hit_wall = True
        elif self.x + self.radius >= CANVAS_WIDTH:
            self.x = CANVAS_WIDTH - self.radius
            self.dir_x = -self.dir_x
            hit_wall = True

        if self.y - self.radius <= 0:
            self.y = self.radius
            self.dir_y = -self.dir_y
            hit_wall = True
        elif self.y + self.radius >= CANVAS_HEIGHT:
            self.y = CANVAS_HEIGHT - self.radius
            self.dir_y = -self.dir_y
            hit_wall = True

        if hit_wall:
            self.bounce_count += 1
            if self.bounce_count >= self.max_bounce:
                self.state = STATE_RETURNING

    def update_returning(self, dt: float) -> None:
        """
        # TODO(Copilot): 플레이어(owner) 추적 복귀 및 회수 처리
        # PRD 3.1절 명세:
        # 1. 플레이어 위치(owner.x, owner.y)를 향하는 방향 벡터(to_player_x, to_player_y) 계산
        # 2. 방향 벡터 정규화 후 return_speed * dt 속도로 플레이어를 향해 고속 추적 이동
        # 3. 플레이어와의 거리(math.hypot)가 (self.radius + owner.radius) 이하로 좁혀지거나,
        #    이번 프레임 이동 거리가 남은 거리 이상일 때(오버슈트 방지):
        #    - owner.current_ammo = min(owner.max_ammo, owner.current_ammo + 1)
        #    - game_world.remove_object(self) 호출로 수리검 소멸
        """
        to_x = self.owner.x - self.x
        to_y = self.owner.y - self.y
        dist = math.hypot(to_x, to_y)
        catch_dist = self.radius + self.owner.radius
        move_step = self.return_speed * dt

        # 플레이어 회수 거리 도달 또는 오버슈트 방지 즉시 회수
        if dist <= catch_dist or move_step >= dist:
            self.owner.current_ammo = min(self.owner.max_ammo, self.owner.current_ammo + 1)
            game_world.remove_object(self)
            return

        if dist > 0.0:
            self.x += (to_x / dist) * move_step
            self.y += (to_y / dist) * move_step

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """수리검 상태에 따른 물리 업데이트 (scaled_dt 기준)"""
        if self.state == STATE_FLYING:
            self.update_flying(scaled_dt)
        elif self.state == STATE_RETURNING:
            self.update_returning(scaled_dt)
        elif self.state == STATE_EMBEDDED:
            pass  # 적에게 귀속된 상태 (추후 적 update에서 관리)

    def draw(self) -> None:
        """수리검 시각화 (형광 청록/Cyan 다이아몬드 히트박스)"""
        left = int(self.x - self.radius)
        bottom = int(self.y - self.radius)
        right = int(self.x + self.radius)
        top = int(self.y + self.radius)
        pico2d.draw_rectangle(left, bottom, right, top)
