"""
trajectory.py
수리검 투척 및 벽/기둥 반사 예상 궤적(Trajectory Prediction) 시각화 가이드 모듈.
PRD 5.2절 조준 가이드라인 명세에 따라, 플레이어가 조준 중일 때
실제 수리검 물리(AABB 기둥 및 4면 외벽 반사)와 100% 동일한 경로를 점선(Dashed Line)으로 사전 렌더링합니다.
"""

import math
from typing import Any
import pico2d
import config


class TrajectoryGuide:
    def __init__(self, max_bounces: int = 3, dash_len: float = 8.0, gap_len: float = 6.0) -> None:
        self.max_bounces: int = max_bounces
        self.dash_len: float = dash_len
        self.gap_len: float = gap_len
        self.step: float = dash_len + gap_len

    def _raycast_closest_hit(
        self,
        x: float,
        y: float,
        dx: float,
        dy: float,
        obstacles: list[Any],
        radius: float = config.SHURIKEN_RADIUS,
    ) -> tuple[tuple[float, float] | None, tuple[float, float]]:
        """단일 광선에 대해 가장 먼저 충돌하는 외벽 또는 기둥 면을 탐색합니다."""
        best_t: float = float('inf')
        best_normal: tuple[float, float] = (0.0, 0.0)

        # 1. 4면 외벽 검사
        if dx < 0.0:
            t = (radius - x) / dx
            if 0.0 < t < best_t:
                best_t = t
                best_normal = (1.0, 0.0)
        elif dx > 0.0:
            t = (config.CANVAS_WIDTH - radius - x) / dx
            if 0.0 < t < best_t:
                best_t = t
                best_normal = (-1.0, 0.0)

        if dy < 0.0:
            t = (radius - y) / dy
            if 0.0 < t < best_t:
                best_t = t
                best_normal = (0.0, 1.0)
        elif dy > 0.0:
            t = (config.CANVAS_HEIGHT - radius - y) / dy
            if 0.0 < t < best_t:
                best_t = t
                best_normal = (0.0, -1.0)

        # 2. 기둥(Obstacle) AABB 확장 검사 (Minkowski Sum)
        for obs in obstacles:
            l = obs.left - radius
            r = obs.right + radius
            b = obs.bottom - radius
            top = obs.top + radius

            # X축 슬랩 검사
            if abs(dx) > 1e-6:
                tx1 = (l - x) / dx
                tx2 = (r - x) / dx
                tnear_x = min(tx1, tx2)
                tfar_x = max(tx1, tx2)
                nx = -1.0 if dx > 0.0 else 1.0
            else:
                if x < l or x > r:
                    continue
                tnear_x = -float('inf')
                tfar_x = float('inf')
                nx = 0.0

            # Y축 슬랩 검사
            if abs(dy) > 1e-6:
                ty1 = (b - y) / dy
                ty2 = (top - y) / dy
                tnear_y = min(ty1, ty2)
                tfar_y = max(ty1, ty2)
                ny = -1.0 if dy > 0.0 else 1.0
            else:
                if y < b or y > top:
                    continue
                tnear_y = -float('inf')
                tfar_y = float('inf')
                ny = 0.0

            t_enter = max(tnear_x, tnear_y)
            t_exit = min(tfar_x, ty_exit := tfar_y)

            if t_enter <= t_exit and t_exit > 1e-4:
                hit_t = t_enter if t_enter > 1e-4 else t_exit
                if 1e-4 < hit_t < best_t:
                    best_t = hit_t
                    best_normal = (nx, 0.0) if tnear_x > tnear_y else (0.0, ny)

        if math.isinf(best_t):
            return None, (0.0, 0.0)

        hit_x = x + dx * best_t
        hit_y = y + dy * best_t
        return (hit_x, hit_y), best_normal

    def calculate_path(
        self,
        start_x: float,
        start_y: float,
        dir_x: float,
        dir_y: float,
        obstacles: list[Any],
    ) -> list[tuple[float, float]]:
        """시작점에서 반사 횟수만큼의 궤적 좌표 리스트를 계산합니다."""
        points: list[tuple[float, float]] = [(start_x, start_y)]
        curr_x, curr_y = start_x, start_y
        curr_dx, curr_dy = dir_x, dir_y

        for _ in range(self.max_bounces):
            hit_pos, normal = self._raycast_closest_hit(curr_x, curr_y, curr_dx, curr_dy, obstacles)
            if hit_pos is None:
                break
            points.append(hit_pos)
            curr_x, curr_y = hit_pos
            nx, ny = normal
            dot = curr_dx * nx + curr_dy * ny
            curr_dx -= 2.0 * dot * nx
            curr_dy -= 2.0 * dot * ny
            # 자기 자신 재충돌 방지 미세 오프셋
            curr_x += curr_dx * 0.1
            curr_y += curr_dy * 0.1

        return points

    def draw_dashed_segment(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """두 점 사이에 점선(Dashed Line)을 렌더링합니다."""
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist <= 1e-3:
            return

        dx = (x2 - x1) / dist
        dy = (y2 - y1) / dist

        curr = 0.0
        while curr < dist:
            seg_start = curr
            seg_end = min(dist, curr + self.dash_len)
            sx = int(x1 + dx * seg_start)
            sy = int(y1 + dy * seg_start)
            ex = int(x1 + dx * seg_end)
            ey = int(y1 + dy * seg_end)
            pico2d.draw_line(sx, sy, ex, ey)
            curr += self.step

    def render(self, player: Any, obstacles: list[Any]) -> None:
        """플레이어가 조준 중이고 탄창이 있을 때 예상 점선 궤적 렌더링"""
        # 탄창이 없거나 구르기/돌진 중일 때는 궤적을 표시하지 않음
        if getattr(player, 'current_ammo', 0) <= 0 or getattr(player, 'state', 0) != 0:
            return

        to_x = player.mouse_x - player.x
        to_y = player.mouse_y - player.y
        dist = math.hypot(to_x, to_y)
        if dist <= 1e-4:
            return

        dir_x = to_x / dist
        dir_y = to_y / dist

        # 플레이어 히트박스 바깥에서 시작
        spawn_x = player.x + dir_x * (player.radius + 5.0)
        spawn_y = player.y + dir_y * (player.radius + 5.0)

        path_points = self.calculate_path(spawn_x, spawn_y, dir_x, dir_y, obstacles)

        # 궤적 점선 및 반사 포인트 마커 렌더링
        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i + 1]
            self.draw_dashed_segment(p1[0], p1[1], p2[0], p2[1])

            # 반사 지점에 작은 다이아몬드 앵커 표시
            hit_x, hit_y = int(p2[0]), int(p2[1])
            pico2d.draw_rectangle(hit_x - 2, hit_y - 2, hit_x + 2, hit_y + 2)
