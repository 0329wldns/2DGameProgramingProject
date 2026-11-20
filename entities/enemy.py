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
import game_framework
import config
from entities.shuriken import STATE_FLYING, STATE_RETURNING, STATE_EMBEDDED


class Enemy:
    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float = -1.0,
        dir_y: float = 0.0,
        target: Any = None,
        max_hp: float = config.ENEMY_BASE_MAX_HP,
    ) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = config.ENEMY_BASE_RADIUS

        # 체력 및 피격 데미지 설정
        self.max_hp: float = max_hp
        self.hp: float = self.max_hp
        self.shuriken_hit_damage: float = config.SHURIKEN_HIT_DAMAGE

        # 시선 단위 벡터 F = (dir_x, dir_y) 정규화 초기화
        length = math.hypot(dir_x, dir_y)
        if length > 0.0:
            self.dir_x: float = dir_x / length
            self.dir_y: float = dir_y / length
        else:
            self.dir_x = -1.0
            self.dir_y = 0.0

        # 회전 속도 제한 (rad/s)
        self.turn_rate: float = config.ENEMY_BASE_TURN_RATE
        self.target: Any = target

        # 스택 및 처형 상태 (PRD 3.2절)
        self.stack_count: int = 0
        self.is_executable: bool = False
        self.is_dead: bool = False
        self.is_hovered: bool = False           # 마우스 커서 호버 여부
        self.hit_flash_timer: float = 0.0       # 피격 시 순간 섬광 타이머
        self.embedded_shurikens: list[Any] = []
        # 귀속된 수리검의 적 중심 기준 상대 오프셋 리스트 [(offset_x, offset_y), ...]
        self._embedded_offsets: list[tuple[float, float]] = []

    @property
    def is_executable_by_dash(self) -> bool:
        """
        수리검 표식이 박혀 있고, 해당 스택으로 인한 돌진 피해량으로 일격 처치 가능한 상태인지 확인.
        1. 사망했거나 체력이 0 이하인 경우 False
        2. 배후 타격으로 처형 활성화(is_executable == True)된 경우 True
        3. 반드시 수리검 표식이 박혀 있어야 함 (len(embedded_shurikens) > 0)
        4. 적의 잔여 체력이 (박힌 수리검 수 * 스택당 돌진 피해량) 이하인 경우 True
        """
        if self.is_dead or self.hp <= 0.0:
            return False
        if self.is_executable:
            return True
        shuriken_count = len(self.embedded_shurikens)
        if shuriken_count <= 0:
            return False
        dash_damage = shuriken_count * config.PLAYER_DASH_STACK_DAMAGE
        return self.hp <= dash_damage

    @property
    def is_dash_target(self) -> bool:
        """돌진(Dash)이 가능한 상태(수리검 표식이 꽂혀 있거나 배후 처형 가능 상태)인지 확인"""
        return (len(self.embedded_shurikens) > 0 or self.is_executable) and not self.is_dead and self.hp > 0.0

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
        적에게 박힌 모든 수리검을 즉시 회수하여 플레이어 탄창으로 반환하고 월드에서 제거합니다.
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

    def release_embedded_shurikens(self) -> int:
        """
        적 사망 시 박혀있던 모든 수리검의 상태를 STATE_RETURNING으로 전환하여
        벽을 통과해 플레이어에게 날아가 자동 회수되도록 방출합니다.
        반환값: 방출된 수리검 개수
        """
        count = len(self.embedded_shurikens)
        for shuriken in self.embedded_shurikens:
            shuriken.state = STATE_RETURNING
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
        if self.is_dead or shuriken.state != STATE_FLYING or self.hp <= 0.0:
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
        self.hit_flash_timer = 0.12
        self.attach_shuriken(shuriken)

        # 적이 이번 피격으로 사망한 경우 박힌 모든 수리검을 즉시 복귀 상태로 전환하여 회수
        if self.hp <= 0.0:
            self.is_dead = True
            self.release_embedded_shurikens()

        return True

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """적 상태 업데이트 (시선 회전 및 귀속된 수리검 위치 동기화)"""
        if self.hit_flash_timer > 0.0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - unscaled_dt)

        if self.is_dead:
            return

        self.update_facing(scaled_dt)

        # 적 이동 시 박혀있는 수리검들의 위치도 함께 이동하도록 동기화
        for idx, shuriken in enumerate(self.embedded_shurikens):
            ox, oy = self._embedded_offsets[idx]
            shuriken.x = self.x + ox
            shuriken.y = self.y + oy

    def _draw_execution_marker(self, cx: float, cy: float) -> None:
        """
        처형 가능(일격사 확정) 상태일 때 머리 위에 표시되는 발광 처형 마커.
        동적 맥동(Pulse), 상하 부유(Bobbing), 이중 네온 테두리, 내부 단도 슬릿 및 하단 유도 화살표(▼) 포함.
        """
        import time
        t = time.time()
        bob = math.sin(t * 6.0) * 3.5
        pulse = 1.0 + 0.16 * math.sin(t * 8.0)

        ix = int(cx)
        iy = int(cy + bob)
        base_size = 14.0 * pulse
        isize = max(6, int(base_size))

        # 1. 외곽 발광 다이아몬드 (이중 네온 청록 테두리)
        pico2d.draw_line(ix, iy + isize, ix + isize, iy, r=0, g=255, b=255)
        pico2d.draw_line(ix + isize, iy, ix, iy - isize, r=0, g=255, b=255)
        pico2d.draw_line(ix, iy - isize, ix - isize, iy, r=0, g=255, b=255)
        pico2d.draw_line(ix - isize, iy, ix, iy + isize, r=0, g=255, b=255)

        # 2. 내부 채움 그라데이션 및 백색 코어 (Luminous Core)
        for s in range(1, isize):
            ratio = s / isize
            if ratio < 0.4:
                r, g, b = 255, 255, 255
            else:
                r = int(50 * (1.0 - ratio))
                g = 255
                b = 255
            pico2d.draw_line(ix, iy + s, ix + s, iy, r=r, g=g, b=b)
            pico2d.draw_line(ix + s, iy, ix, iy - s, r=r, g=g, b=b)
            pico2d.draw_line(ix, iy - s, ix - s, iy, r=r, g=g, b=b)
            pico2d.draw_line(ix - s, iy, ix, iy + s, r=r, g=g, b=b)

        # 3. 중앙 단도 슬릿 (어두운 실루엣 크로스 슬래시)
        slit_h = max(3, isize - 4)
        pico2d.draw_line(ix, iy - slit_h, ix, iy + slit_h, r=15, g=30, b=45)
        pico2d.draw_line(ix - 1, iy - slit_h + 1, ix - 1, iy + slit_h - 1, r=15, g=30, b=45)
        pico2d.draw_line(ix - 4, iy + 1, ix + 4, iy + 1, r=15, g=30, b=45)

        # 4. 하단 유도 화살표 / 셰브론 (▼) - 적 머리를 직접 가리킴
        arrow_y = iy - isize - 3
        pico2d.draw_line(ix - 5, arrow_y, ix, arrow_y - 5, r=0, g=255, b=255)
        pico2d.draw_line(ix + 5, arrow_y, ix, arrow_y - 5, r=0, g=255, b=255)
        pico2d.draw_line(ix - 5, arrow_y + 1, ix, arrow_y - 4, r=0, g=255, b=255)
        pico2d.draw_line(ix + 5, arrow_y + 1, ix, arrow_y - 4, r=0, g=255, b=255)

        # 5. 좌우 날개 브래킷 ( < ◆ > )
        wing_dist = isize + 5
        pico2d.draw_line(ix - wing_dist - 4, iy, ix - wing_dist, iy + 4, r=0, g=255, b=255)
        pico2d.draw_line(ix - wing_dist - 4, iy, ix - wing_dist, iy - 4, r=0, g=255, b=255)
        pico2d.draw_line(ix + wing_dist + 4, iy, ix + wing_dist, iy + 4, r=0, g=255, b=255)
        pico2d.draw_line(ix + wing_dist + 4, iy, ix + wing_dist, iy - 4, r=0, g=255, b=255)

    def _draw_targeting_brackets(self, cx: float, cy: float, offset: int, blen: int, r: int, g: int, b: int) -> None:
        """타겟팅 코너 브래킷 [ ] 렌더링"""
        ix, iy = int(cx), int(cy)
        # Top-Left [
        pico2d.draw_line(ix - offset, iy + offset - blen, ix - offset, iy + offset, r=r, g=g, b=b)
        pico2d.draw_line(ix - offset, iy + offset, ix - offset + blen, iy + offset, r=r, g=g, b=b)
        # Top-Right ]
        pico2d.draw_line(ix + offset - blen, iy + offset, ix + offset, iy + offset, r=r, g=g, b=b)
        pico2d.draw_line(ix + offset, iy + offset, ix + offset, iy + offset - blen, r=r, g=g, b=b)
        # Bottom-Left [
        pico2d.draw_line(ix - offset, iy - offset + blen, ix - offset, iy - offset, r=r, g=g, b=b)
        pico2d.draw_line(ix - offset, iy - offset, ix - offset + blen, iy - offset, r=r, g=g, b=b)
        # Bottom-Right ]
        pico2d.draw_line(ix + offset - blen, iy - offset, ix + offset, iy - offset, r=r, g=g, b=b)
        pico2d.draw_line(ix + offset, iy - offset, ix + offset, iy - offset + blen, r=r, g=g, b=b)

    def _draw_dash_aim_preview(self) -> None:
        """돌진 타겟 호버 시 돌진 진입 및 관통 예상 궤적 Ray Line 시각화 (PRD 5.2절)"""
        if self.target is None or getattr(self.target, 'is_dead', False):
            return

        to_x = self.x - self.target.x
        to_y = self.y - self.target.y
        dist = math.hypot(to_x, to_y)
        if dist <= 1e-4:
            return

        dash_dir_x = to_x / dist
        dash_dir_y = to_y / dist
        dash_dist = getattr(self.target, 'dash_distance', config.PLAYER_DASH_DISTANCE)

        # 1. 플레이어 -> 적 진입 접근선 (Cyan/White)
        pico2d.draw_line(int(self.target.x), int(self.target.y), int(self.x), int(self.y), r=0, g=180, b=220)

        # 2. 적 -> 관통 도착 지점 일섬 궤적 Ray Line (Bright Cyan)
        dest_x = int(self.x + dash_dir_x * dash_dist)
        dest_y = int(self.y + dash_dir_y * dash_dist)
        pico2d.draw_line(int(self.x), int(self.y), dest_x, dest_y, r=0, g=255, b=255)

        # 3. 도착 지점 랜딩 마커 (청록색 사각형)
        pico2d.draw_rectangle(dest_x - 4, dest_y - 4, dest_x + 4, dest_y + 4, r=0, g=255, b=255, filled=True)

    def draw(self) -> None:
        """적 본체, 시선 방향선, 체력바, 스택 및 처형 마커 렌더링"""
        if self.is_dead:
            # 사망한 적 시각화 (어두운 회색 X 표시 히트박스)
            ix, iy, ir = int(self.x), int(self.y), int(self.radius)
            pico2d.draw_rectangle(ix - ir, iy - ir, ix + ir, iy + ir, r=70, g=70, b=80)
            pico2d.draw_line(ix - ir, iy - ir, ix + ir, iy + ir, r=70, g=70, b=80)
            pico2d.draw_line(ix - ir, iy + ir, ix + ir, iy - ir, r=70, g=70, b=80)
            return

        # 1. 적 본체 히트박스 (붉은색 네온)
        left = int(self.x - self.radius)
        bottom = int(self.y - self.radius)
        right = int(self.x + self.radius)
        top = int(self.y + self.radius)
        pico2d.draw_rectangle(left, bottom, right, top, r=230, g=65, b=65)

        # 2. 마우스 커서 호버 시 타겟 하이라이트 (PRD 5.2절)
        if self.is_hovered:
            if self.is_dash_target:
                # 돌진 가능 타겟: 청록색 발광 이중 테두리 + 코너 브래킷 [ ] + 관통 Ray Line
                pico2d.draw_rectangle(left - 2, bottom - 2, right + 2, top + 2, r=0, g=255, b=255)
                self._draw_targeting_brackets(self.x, self.y, offset=int(self.radius + 7.0), blen=8, r=0, g=255, b=255)
                pico2d.draw_rectangle(left - 7, bottom - 7, right + 7, top + 7, r=0, g=255, b=255)
                self._draw_dash_aim_preview()
            else:
                # 돌진 불가능(수리검 미부착): 은은한 백색/회색 타겟 브래킷 (조준 호버 인지 피드백)
                self._draw_targeting_brackets(self.x, self.y, offset=int(self.radius + 5.0), blen=6, r=200, g=200, b=200)
                pico2d.draw_rectangle(left - 5, bottom - 5, right + 5, top + 5, r=160, g=160, b=160)

        # 3. 피격 섬광/베기 이펙트 (Hit Flash)
        if self.hit_flash_timer > 0.0:
            flash_r = int(self.radius + 6.0)
            pico2d.draw_line(int(self.x - flash_r), int(self.y - flash_r), int(self.x + flash_r), int(self.y + flash_r), r=0, g=255, b=255)
            pico2d.draw_line(int(self.x - flash_r), int(self.y + flash_r), int(self.x + flash_r), int(self.y - flash_r), r=0, g=255, b=255)

        # 4. 시선 방향 벡터(F) 표시선 (정면 황색 시각화)
        look_x = int(self.x + self.dir_x * (self.radius + 14.0))
        look_y = int(self.y + self.dir_y * (self.radius + 14.0))
        pico2d.draw_line(int(self.x), int(self.y), look_x, look_y, r=255, g=190, b=60)

        # 5. 상단 체력바 표시 (배경 및 잔여 체력)
        bar_w = 40.0
        bar_h = 5.0
        bar_left = int(self.x - bar_w / 2.0)
        bar_bottom = int(self.y + self.radius + 8.0)
        pico2d.draw_rectangle(bar_left, bar_bottom, int(bar_left + bar_w), int(bar_bottom + bar_h), r=100, g=30, b=30)
        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        fill_right = int(bar_left + bar_w * hp_ratio)
        pico2d.draw_rectangle(bar_left, bar_bottom, fill_right, int(bar_bottom + bar_h), r=255, g=50, b=50, filled=True)

        # 6. 일반 스택 표시 (누적된 stack_count 개수에 맞춘 동적 중앙 정렬)
        if self.stack_count > 0:
            stack_y = bar_bottom + bar_h + 6.0
            stack_spacing = 9.0
            stack_span = (self.stack_count - 1) * stack_spacing
            stack_start_x = self.x - stack_span / 2.0
            for i in range(self.stack_count):
                sx = int(stack_start_x + i * stack_spacing)
                pico2d.draw_rectangle(sx - 2, int(stack_y - 2), sx + 2, int(stack_y + 2), r=255, g=220, b=50, filled=True)

        # 7. 처형 가능 상태 마커 렌더링 (PRD 5.2절 명세: 배후 처형 확정 또는 돌진 처치 체력 도달 시)
        if self.is_executable_by_dash:
            marker_y = bar_bottom + bar_h + (24.0 if self.stack_count > 0 else 18.0)
            self._draw_execution_marker(self.x, marker_y)


class Shielder(Enemy):
    """
    방패병 (Shielder) 아키타입 클래스 (PRD 4절, 5주차).
    - 전방(시선 방향 180도)으로 견고한 물리 방패를 들고 있는 중갑 탱커 몬스터.
    - 정면(F · V <= 0)에서 날아오는 수리검을 100% 가드하며 도탄(반사)시킴 (피해 0, 탄창 미귀속).
    - 수리검이 3회 반사를 모두 채우면 즉시 플레이어에게 복귀.
    - 오직 벽이나 기둥을 이용한 반사 투척으로 배후(F · V > 0)를 노려야만 일격 처형 마커가 점등됨.
    - 플레이어를 향해 묵직하게 전진(SHIELDER_MOVE_SPEED)하며 압박함.
    """
    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float = -1.0,
        dir_y: float = 0.0,
        target: Any = None,
        max_hp: float = config.SHIELDER_MAX_HP,
    ) -> None:
        super().__init__(x=x, y=y, dir_x=dir_x, dir_y=dir_y, target=target, max_hp=max_hp)
        self.radius: float = config.SHIELDER_RADIUS
        self.move_speed: float = config.SHIELDER_MOVE_SPEED
        self.turn_rate: float = config.SHIELDER_TURN_RATE
        self.shield_flash_timer: float = 0.0
        self.enemy_type: str = "shielder"

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """방패병 상태 업데이트: 시선 회전, 플레이어 추적 전진, 방패 섬광 타이머 감쇄"""
        if self.shield_flash_timer > 0.0:
            self.shield_flash_timer = max(0.0, self.shield_flash_timer - unscaled_dt)

        super().update(scaled_dt, unscaled_dt)

        if self.is_dead:
            return

        # 플레이어 추적 이동 (전진 AI)
        if self.target is not None and not getattr(self.target, 'is_dead', False):
            to_x = self.target.x - self.x
            to_y = self.target.y - self.y
            dist = math.hypot(to_x, to_y)
            # 플레이어와 일정 근접 거리 유지 (완전히 겹치지 않도록 정지선 확보)
            min_stop_dist = self.radius + getattr(self.target, 'radius', 20.0) + 10.0
            if dist > min_stop_dist:
                self.x += self.dir_x * self.move_speed * scaled_dt
                self.y += self.dir_y * self.move_speed * scaled_dt

                # 화면 경계 이탈 방지
                self.x = max(self.radius, min(config.CANVAS_WIDTH - self.radius, self.x))
                self.y = max(self.radius, min(config.CANVAS_HEIGHT - self.radius, self.y))

    def resolve_shuriken_collision(self, shuriken: Any) -> bool:
        """
        방패병 전용 수리검 충돌 및 방패 방어/도탄 판정 (PRD 4절).
        1. 배후 피격 (dot > 0.0):
           - 방패를 우회하여 등 뒤를 찌름 -> 처형 확정(is_executable = True) 및 수리검 귀속.
        2. 정면 피격 (dot <= 0.0):
           - 방패에 적중 -> 데미지 0 무효화, 수리검 미귀속, 방패 법선 기준 수리검 반사(도탄)!
           - 반사 카운트 증가 및 3회 누적 시 자동 복귀.
        """
        if self.is_dead or shuriken.state != STATE_FLYING or self.hp <= 0.0:
            return False

        distance = math.hypot(shuriken.x - self.x, shuriken.y - self.y)
        if distance > self.radius + shuriken.radius:
            return False

        dot = self.dir_x * shuriken.dir_x + self.dir_y * shuriken.dir_y

        if dot > 0.0:
            # === 배후 피격: 방패를 뚫고 등 뒤 적중 (처형 활성화) ===
            self.is_executable = True
            self.hp = max(0.0, self.hp - self.shuriken_hit_damage)
            self.hit_flash_timer = 0.12
            self.attach_shuriken(shuriken)

            if self.hp <= 0.0:
                self.is_dead = True
                self.release_embedded_shurikens()

            return True

        else:
            # === 정면 피격: 방패 가드 및 도탄 반사 (Shield Ricochet) ===
            # 방패 표면 법선 벡터 n = (self.dir_x, self.dir_y)
            # 입사각 = 반사각 반사 벡터: V_reflect = V - 2 * (V · n) * n
            new_vx = shuriken.dir_x - 2.0 * dot * self.dir_x
            new_vy = shuriken.dir_y - 2.0 * dot * self.dir_y
            v_len = math.hypot(new_vx, new_vy)
            if v_len > 0.0:
                shuriken.dir_x = new_vx / v_len
                shuriken.dir_y = new_vy / v_len

            # 수리검이 방패 안쪽으로 파고들지 않도록 방패 앞쪽으로 위치 보정
            push_dist = self.radius + shuriken.radius + 4.0
            shuriken.x = self.x + self.dir_x * push_dist
            shuriken.y = self.y + self.dir_y * push_dist

            # 도탄 카운트 증가 및 상한 도달 시 복귀 처리
            shuriken.bounce_count += 1
            if shuriken.bounce_count >= shuriken.max_bounce:
                shuriken.state = STATE_RETURNING

            # 방패 피격 이펙트 (황금색/백색 불꽃 섬광 및 약한 화면 진동)
            self.shield_flash_timer = 0.15
            game_framework.start_screen_shake(4.0, 0.08)

            return True

    def draw(self) -> None:
        """방패병 렌더링: 본체 히트박스 + 전방 거대 방패(Tower Shield) 시각화"""
        super().draw()

        if self.is_dead:
            return

        # 전방 방패 (Convex Tower Shield) 렌더링
        shield_offset = self.radius + 4.0
        sx = self.x + self.dir_x * shield_offset
        sy = self.y + self.dir_y * shield_offset

        # 방패 접선(Tangent) 단위 벡터
        tx = -self.dir_y
        ty = self.dir_x

        half_w = self.radius * 1.25  # 방패 날개 길이 (총 폭 약 60px)
        curv = 5.0                   # 중앙 돌출 곡률

        # 방패 3개 정점: 좌측 팁, 중앙 크레스트, 우측 팁
        p_left_x = int(sx - tx * half_w - self.dir_x * curv)
        p_left_y = int(sy - ty * half_w - self.dir_y * curv)
        p_mid_x  = int(sx + self.dir_x * curv)
        p_mid_y  = int(sy + self.dir_y * curv)
        p_right_x = int(sx + tx * half_w - self.dir_x * curv)
        p_right_y = int(sy + ty * half_w - self.dir_y * curv)

        # 색상 설정 (방패 가드 시 황금색 섬광, 평상시 묵직한 청록/스틸)
        if self.shield_flash_timer > 0.0:
            sr, sg, sb = 255, 240, 100
        else:
            sr, sg, sb = 0, 220, 255

        # 1. 방패 메인 전면 라인 (두껍게 다중 라인 드로우)
        for offset in (-1, 0, 1):
            ox = int(self.dir_x * offset)
            oy = int(self.dir_y * offset)
            pico2d.draw_line(p_left_x + ox, p_left_y + oy, p_mid_x + ox, p_mid_y + oy, r=sr, g=sg, b=sb)
            pico2d.draw_line(p_mid_x + ox, p_mid_y + oy, p_right_x + ox, p_right_y + oy, r=sr, g=sg, b=sb)

        # 2. 방패 양 끝단 가드 브래킷
        pico2d.draw_rectangle(p_left_x - 2, p_left_y - 2, p_left_x + 2, p_left_y + 2, r=sr, g=sg, b=sb, filled=True)
        pico2d.draw_rectangle(p_right_x - 2, p_right_y - 2, p_right_x + 2, p_right_y + 2, r=sr, g=sg, b=sb, filled=True)

        # 3. 방패 중앙 보강 코어 리벳
        pico2d.draw_rectangle(p_mid_x - 2, p_mid_y - 2, p_mid_x + 2, p_mid_y + 2, r=255, g=255, b=255, filled=True)
