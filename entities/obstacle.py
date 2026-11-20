"""
obstacle.py
아레나 내부 장애물(기둥/벽) 엔티티 모듈.
AABB 충돌 판정 및 수리검 반사 물리, 플레이어 이동 차단(밀어내기)을 담당합니다.
"""

import math
from typing import Any
import pico2d
from entities.shuriken import STATE_FLYING, STATE_RETURNING


class Obstacle:
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        """
        x, y: 기둥의 중심 좌표
        width, height: 기둥의 너비와 높이
        """
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height

        self.half_w: float = width / 2.0
        self.half_h: float = height / 2.0

    @property
    def left(self) -> float:
        return self.x - self.half_w

    @property
    def right(self) -> float:
        return self.x + self.half_w

    @property
    def bottom(self) -> float:
        return self.y - self.half_h

    @property
    def top(self) -> float:
        return self.y + self.half_h

    def resolve_entity_collision(self, entity: Any) -> None:
        """
        엔티티(플레이어/적)와 기둥 간 AABB-원형 충돌 감지 및 밀어내기 (Sliding)
        """
        closest_x = max(self.left, min(entity.x, self.right))
        closest_y = max(self.bottom, min(entity.y, self.top))

        diff_x = entity.x - closest_x
        diff_y = entity.y - closest_y
        dist = math.hypot(diff_x, diff_y)

        if dist < entity.radius:
            if dist > 0.0:
                overlap = entity.radius - dist
                entity.x += (diff_x / dist) * overlap
                entity.y += (diff_y / dist) * overlap
            else:
                overlap_left = entity.x - self.left + entity.radius
                overlap_right = self.right - entity.x + entity.radius
                overlap_bottom = entity.y - self.bottom + entity.radius
                overlap_top = self.top - entity.y + entity.radius
                min_overlap = min(overlap_left, overlap_right, overlap_bottom, overlap_top)
                if min_overlap == overlap_left:
                    entity.x = self.left - entity.radius
                elif min_overlap == overlap_right:
                    entity.x = self.right + entity.radius
                elif min_overlap == overlap_bottom:
                    entity.y = self.bottom - entity.radius
                else:
                    entity.y = self.top + entity.radius

    def resolve_player_collision(self, player: Any) -> None:
        """기존 호환성 유지를 위한 별칭 메서드"""
        self.resolve_entity_collision(player)

    def resolve_shuriken_collision(self, shuriken: Any) -> bool:
        """
        # TODO(Copilot): 수리검과 기둥 간 AABB 충돌 감지 및 법선 벡터 반사 구현
        # PRD 3.1절 명세:
        # 공식: V_reflect = V_in - 2 * (V_in · n) * n
        #
        # 세부 구현 가이드:
        # 1. 수리검이 STATE_FLYING 상태가 아니면 충돌 검사 무시 (False 반환)
        # 2. 기둥 AABB와 수리검 중심(shuriken.x, shuriken.y, shuriken.radius) 간의 접촉 검사
        # 3. 충돌 면 판정 (4개 면 중 침범 깊이가 가장 얕은 면의 법선 벡터 n 결정):
        #    - 좌측면: n = (-1.0, 0.0) -> 수리검을 self.left - radius 로 위치 보정
        #    - 우측면: n = (1.0, 0.0)  -> 수리검을 self.right + radius 로 위치 보정
        #    - 하단면: n = (0.0, -1.0) -> 수리검을 self.bottom - radius 로 위치 보정
        #    - 상단면: n = (0.0, 1.0)  -> 수리검을 self.top + radius 로 위치 보정
        # 4. 반사 벡터 공식 적용:
        #    dot = shuriken.dir_x * nx + shuriken.dir_y * ny
        #    shuriken.dir_x -= 2 * dot * nx
        #    shuriken.dir_y -= 2 * dot * ny
        #    (정규화 확인)
        # 5. shuriken.bounce_count += 1 증가
        #    - 만약 shuriken.bounce_count >= shuriken.max_bounce 이면:
        #        shuriken.state = STATE_RETURNING 전이
        # 6. 충돌 성공 시 True 반환
        """
        if shuriken.state != STATE_FLYING:
            return False

        closest_x = max(self.left, min(shuriken.x, self.right))
        closest_y = max(self.bottom, min(shuriken.y, self.top))
        distance_x = shuriken.x - closest_x
        distance_y = shuriken.y - closest_y

        if math.hypot(distance_x, distance_y) > shuriken.radius:
            return False

        penetrations = (
            (shuriken.x + shuriken.radius - self.left, (-1.0, 0.0)),
            (self.right - shuriken.x + shuriken.radius, (1.0, 0.0)),
            (shuriken.y + shuriken.radius - self.bottom, (0.0, -1.0)),
            (self.top - shuriken.y + shuriken.radius, (0.0, 1.0)),
        )
        _, (nx, ny) = min(penetrations, key=lambda item: item[0])

        if nx < 0.0:
            shuriken.x = self.left - shuriken.radius
        elif nx > 0.0:
            shuriken.x = self.right + shuriken.radius
        elif ny < 0.0:
            shuriken.y = self.bottom - shuriken.radius
        else:
            shuriken.y = self.top + shuriken.radius

        dot = shuriken.dir_x * nx + shuriken.dir_y * ny
        shuriken.dir_x -= 2 * dot * nx
        shuriken.dir_y -= 2 * dot * ny

        shuriken.bounce_count += 1
        if shuriken.bounce_count >= shuriken.max_bounce:
            shuriken.state = STATE_RETURNING

        return True

    def draw(self) -> None:
        """기둥 렌더링 (아레나 내 사각 기둥)"""
        l = int(self.left)
        b = int(self.bottom)
        r = int(self.right)
        t = int(self.top)
        pico2d.draw_rectangle(l, b, r, t)
