"""
enemy.py
적(Enemy) 베이스 클래스 모듈.
PRD 3.2절 및 4절 명세에 따른 시선 벡터(F) 회전 제한, 수리검 피격 내적(F·V) 판정,
일반 스택 누적 및 배후 일격사(처형 가능 상태) 활성화를 담당합니다.
"""

import math
from typing import Any
import pico2d
import game_world
from entities.shuriken import STATE_FLYING, STATE_EMBEDDED


class Enemy:
    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float = -1.0,
        dir_y: float = 0.0,
        target: Any = None,
    ) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = 20.0

        # 체력 및 피격 데미지 설정
        self.max_hp: float = 100.0
        self.hp: float = 100.0
        self.shuriken_hit_damage: float = 10.0

        # 시선 단위 벡터 F = (dir_x, dir_y) 정규화 초기화
        length = math.hypot(dir_x, dir_y)
        if length > 0.0:
            self.dir_x: float = dir_x / length
            self.dir_y: float = dir_y / length
        else:
            self.dir_x = -1.0
            self.dir_y = 0.0

        # 회전 속도 제한 (rad/s) - PRD 4절: 반사 수리검이 배후를 노릴 수 있도록 딜레이 부여
        self.turn_rate: float = 2.0
        self.target: Any = target

        # 스택 및 처형 상태 (PRD 3.2절)
        self.stack_count: int = 0
        self.is_executable: bool = False
        self.embedded_shurikens: list[Any] = []
        # 귀속된 수리검의 적 중심 기준 상대 오프셋 리스트 [(offset_x, offset_y), ...]
        self._embedded_offsets: list[tuple[float, float]] = []

    def update_facing(self, dt: float) -> None:
        """
        타겟(플레이어) 방향으로 시선 벡터 F를 회전하되,
        초당 최대 회전각(turn_rate * dt)으로 회전 속도를 제한합니다.
        """
        if self.target is None:
            return

        to_x = self.target.x - self.x
        to_y = self.target.y - self.y
        if math.hypot(to_x, to_y) <= 1e-5:
            return

        current_angle = math.atan2(self.dir_y, self.dir_x)
        target_angle = math.atan2(to_y, to_x)

        # 최단 회전 각도 차이 계산 (-pi ~ +pi)
        diff = (target_angle - current_angle + math.pi) % (2.0 * math.pi) - math.pi
        max_step = self.turn_rate * dt

        if abs(diff) <= max_step:
            new_angle = target_angle
        else:
            new_angle = current_angle + (max_step if diff > 0.0 else -max_step)

        self.dir_x = math.cos(new_angle)
        self.dir_y = math.sin(new_angle)

    def attach_shuriken(self, shuriken: Any) -> None:
        """수리검을 적에게 귀속(STATE_EMBEDDED)시키고 상대 위치 오프셋을 기록합니다."""
        shuriken.state = STATE_EMBEDDED
        self.embedded_shurikens.append(shuriken)
        self._embedded_offsets.append((shuriken.x - self.x, shuriken.y - self.y))

    def retrieve_all_shurikens(self) -> int:
        """
        적에게 박힌 모든 수리검을 회수하여 플레이어 탄창으로 반환하고 월드에서 제거합니다.
        반환값: 회수된 수리검 개수
        """
        count = len(self.embedded_shurikens)
        for shuriken in self.embedded_shurikens:
            if shuriken.owner is not None:
                shuriken.owner.current_ammo = min(
                    shuriken.owner.max_ammo,
                    shuriken.owner.current_ammo + 1,
                )
            game_world.remove_object(shuriken)
        self.embedded_shurikens.clear()
        self._embedded_offsets.clear()
        self.stack_count = 0
        return count

    def resolve_shuriken_collision(self, shuriken: Any) -> bool:
        """
        # TODO(Copilot): 수리검 피격 충돌 검사 및 배후 내적(Dot Product) 판정 구현
        # PRD 3.1절 및 3.2절 명세:
        # 1. shuriken.state != STATE_FLYING 이거나 self.hp <= 0.0 이면 False 반환
        # 2. 원형 충돌 판정:
        #    - 적 중심(self.x, self.y)과 수리검 중심(shuriken.x, shuriken.y)의 거리(math.hypot) 계산
        #    - 거리가 (self.radius + shuriken.radius) 보다 크면 충돌하지 않았으므로 False 반환
        # 3. 배후 타격 판정을 위한 벡터 내적(Dot Product) 계산:
        #    - 공식: dot = self.dir_x * shuriken.dir_x + self.dir_y * shuriken.dir_y
        # 4. 내적 결과에 따른 분기 처리:
        #    - 배후 타격 (dot > 0.0):
        #        * 등 뒤 180도 이내 피격이므로 1회 적중 즉시 처형 가능 상태 활성화:
        #          self.is_executable = True
        #        * 기본 투사체 피해 적용: self.hp = max(0.0, self.hp - self.shuriken_hit_damage)
        #    - 정면 타격 (dot <= 0.0):
        #        * 일반 스택 1개 누적: self.stack_count += 1
        #        * 기본 투사체 피해 적용: self.hp = max(0.0, self.hp - self.shuriken_hit_damage)
        # 5. 수리검 귀속 처리:
        #    - self.attach_shuriken(shuriken) 호출하여 STATE_EMBEDDED 전환 및 적에게 귀속
        # 6. 충돌 처리 완료 후 True 반환
        """
        if shuriken.state != STATE_FLYING or self.hp <= 0.0:
            return False

        distance = math.hypot(shuriken.x - self.x, shuriken.y - self.y)
        if distance > self.radius + shuriken.radius:
            return False

        dot = self.dir_x * shuriken.dir_x + self.dir_y * shuriken.dir_y
        if dot > 0.0:
            self.is_executable = True
        else:
            self.stack_count += 1

        self.hp = max(0.0, self.hp - self.shuriken_hit_damage)
        self.attach_shuriken(shuriken)
        return True

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """적 상태 업데이트 (시선 회전 및 귀속된 수리검 위치 동기화)"""
        self.update_facing(scaled_dt)

        # 적 이동 시 박혀있는 수리검들의 위치도 함께 이동하도록 동기화
        for idx, shuriken in enumerate(self.embedded_shurikens):
            ox, oy = self._embedded_offsets[idx]
            shuriken.x = self.x + ox
            shuriken.y = self.y + oy

    def _draw_diamond_marker(self, cx: float, cy: float, size: float) -> None:
        """처형 가능 상태(is_executable)일 때 체력바 상단에 표시할 다이아몬드 마커"""
        ix, iy, isize = int(cx), int(cy), int(size)
        pico2d.draw_line(ix, iy + isize, ix + isize, iy)
        pico2d.draw_line(ix + isize, iy, ix, iy - isize)
        pico2d.draw_line(ix, iy - isize, ix - isize, iy)
        pico2d.draw_line(ix - isize, iy, ix, iy + isize)

    def draw(self) -> None:
        """적 본체, 시선 방향선, 체력바, 스택 및 처형 마커 렌더링"""
        # 1. 적 본체 히트박스
        left = int(self.x - self.radius)
        bottom = int(self.y - self.radius)
        right = int(self.x + self.radius)
        top = int(self.y + self.radius)
        pico2d.draw_rectangle(left, bottom, right, top)

        # 2. 시선 방향 벡터(F) 표시선 (정면이 어디인지 명확히 시각화)
        look_x = int(self.x + self.dir_x * (self.radius + 14.0))
        look_y = int(self.y + self.dir_y * (self.radius + 14.0))
        pico2d.draw_line(int(self.x), int(self.y), look_x, look_y)

        # 3. 상단 체력바 표시
        bar_w = 40.0
        bar_h = 5.0
        bar_left = int(self.x - bar_w / 2.0)
        bar_bottom = int(self.y + self.radius + 8.0)
        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        fill_right = int(bar_left + bar_w * hp_ratio)
        pico2d.draw_rectangle(bar_left, bar_bottom, fill_right, int(bar_bottom + bar_h))

        # 4. 일반 스택 표시 (체력바 위 작은 사각형들)
        stack_y = bar_bottom + bar_h + 6.0
        for i in range(self.stack_count):
            sx = int(self.x - 10.0 + i * 10.0)
            pico2d.draw_rectangle(sx - 3, int(stack_y - 3), sx + 3, int(stack_y + 3))

        # 5. 처형 가능 상태(is_executable) 다이아몬드 마커 (PRD 5.2절 명세)
        if self.is_executable:
            marker_y = bar_bottom + bar_h + 18.0
            self._draw_diamond_marker(self.x, marker_y, 8.0)
