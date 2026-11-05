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

    def resolve_player_collision(self, player: Any) -> None:
        """
        플레이어와 기둥 간 AABB-원형 충돌 감지 및 밀어내기 (Sliding)
        """
        # 기둥 AABB 상에서 플레이어 중심과 가장 가까운 점 (Closest Point)
        closest_x = max(self.left, min(player.x, self.right))
        closest_y = max(self.bottom, min(player.y, self.top))

        diff_x = player.x - closest_x
        diff_y = player.y - closest_y
        dist = math.hypot(diff_x, diff_y)

        # 충돌 발생 시
        if dist < player.radius:
            if dist > 0.0:
                # 겹친 깊이만큼 플레이어를 바깥으로 밀어냄
                overlap = player.radius - dist
                player.x += (diff_x / dist) * overlap
                player.y += (diff_y / dist) * overlap
            else:
                # 플레이어가 완전히 기둥 중심에 파묻힌 예외 케이스 처리
                overlap_left = player.x - self.left + player.radius
                overlap_right = self.right - player.x + player.radius
                overlap_bottom = player.y - self.bottom + player.radius
                overlap_top = self.top - player.y + player.radius
                min_overlap = min(overlap_left, overlap_right, overlap_bottom, overlap_top)
                if min_overlap == overlap_left:
                    player.x = self.left - player.radius
                elif min_overlap == overlap_right:
                    player.x = self.right + player.radius
                elif min_overlap == overlap_bottom:
                    player.y = self.bottom - player.radius
                else:
                    player.y = self.top + player.radius

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
        pass

    def draw(self) -> None:
        """기둥 렌더링 (아레나 내 사각 기둥)"""
        l = int(self.left)
        b = int(self.bottom)
        r = int(self.right)
        t = int(self.top)
        pico2d.draw_rectangle(l, b, r, t)
