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
import game_framework
import config
from entities.shuriken import Shuriken

# 플레이어 상태 머신(FSM) 상수
STATE_NORMAL: int = 0
STATE_ROLL: int = 1
STATE_DASH: int = 2
STATE_BULLET_TIME: int = 3


class Player:
    def __init__(self, x: float = 640.0, y: float = 360.0) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = config.PLAYER_RADIUS
        self.move_speed: float = config.PLAYER_MOVE_SPEED

        # 플레이어 체력 및 피격 파라미터
        self.max_hp: float = config.PLAYER_MAX_HP
        self.hp: float = self.max_hp
        self.damage_flash_timer: float = 0.0

        # 플레이어 FSM 상태
        self.state: int = STATE_NORMAL

        # 구르기(Roll) 파라미터 (PRD 2절: 순간 가속 포지셔닝, I-Frame 없음, 쿨다운 존재)
        self.roll_speed: float = config.PLAYER_ROLL_SPEED
        self.roll_duration: float = config.PLAYER_ROLL_DURATION
        self.roll_cooldown: float = config.PLAYER_ROLL_COOLDOWN
        self.roll_timer: float = 0.0            # 구르기 잔여 시간 타이머
        self.roll_cooldown_timer: float = 0.0   # 쿨다운 타이머
        self.roll_dir_x: float = 1.0            # 구르기 진행 방향
        self.roll_dir_y: float = 0.0
        self.last_move_dir: tuple[float, float] = (1.0, 0.0)  # 마지막 이동 방향 기록

        # 돌진 일섬(Dash) 파라미터 (PRD 3.3절: 관성 계승 일섬, 텔레포트 및 50% 관통 데미지)
        self.dash_speed: float = config.PLAYER_DASH_SPEED
        self.dash_distance: float = config.PLAYER_DASH_DISTANCE
        self.dash_duration: float = self.dash_distance / self.dash_speed
        self.dash_timer: float = 0.0
        self.dash_dir_x: float = 1.0
        self.dash_dir_y: float = 0.0
        self.dash_base_damage: float = 0.0      # 최초 타겟에게 가해진 데미지 (관통 50% 계산 기준)
        self.dash_hit_enemies: set[int] = set() # 관통 궤적 상 이미 타격된 적 id 집합

        # 불릿타임 및 연쇄 돌진 파라미터 (PRD 3.4절)
        self.bullet_time_duration: float = config.BULLET_TIME_DURATION
        self.bullet_time_timer: float = 0.0
        self.dash_killed_any: bool = False      # 이번 돌진(최초/연쇄)에서 적 처치 여부
        self.in_bullet_time_dash: bool = False  # 불릿타임 중 연쇄 돌진 진행 중 플래그
        self.chain_kill_count: int = 0          # 불릿타임 내 누적 처치 수

        # 청록색 궤적 잔상 관리 (PRD 5.2절)
        # 각 잔상: [x, y, timer, max_timer, dir_x, dir_y]
        self.afterimages: list[list[float]] = []
        self.afterimage_spawn_timer: float = 0.0

        # 탄창 자원 관리 (config.PLAYER_MAX_AMMO)
        self.max_ammo: int = config.PLAYER_MAX_AMMO
        self.current_ammo: int = self.max_ammo

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
            self.mouse_y = float(config.CANVAS_HEIGHT - 1 - event.y)
        elif event.type == SDL_MOUSEBUTTONDOWN:
            if event.button == SDL_BUTTON_LEFT:
                # 마우스 좌표 동기화 후 수리검 발사
                self.mouse_x = float(event.x)
                self.mouse_y = float(config.CANVAS_HEIGHT - 1 - event.y)
                self.shoot_shuriken()
            elif event.button == SDL_BUTTON_RIGHT:
                # 마우스 좌표 동기화 후 우클릭 타겟 돌진 또는 연쇄 돌진 발동 시도
                self.mouse_x = float(event.x)
                self.mouse_y = float(config.CANVAS_HEIGHT - 1 - event.y)
                if self.state == STATE_BULLET_TIME:
                    self.start_chain_dash()
                else:
                    self.try_trigger_dash()

    def find_aim_assist_target(self, allow_all_alive: bool = False) -> Any:
        """
        마우스 커서 위치(mouse_x, mouse_y)를 기준으로 가장 가까운 유효 돌진 타겟을 탐색 (스마트 에임 어시스트).
        - allow_all_alive == False (일반 상태): 수리검이 꽂혀있거나 배후 처형 가능(is_dash_target == True)한 적만 탐색.
        - allow_all_alive == True (불릿타임 상태): 생존해 있는 모든 적(not is_dead and hp > 0)을 연쇄 처형 대상으로 탐색.
        - 반환값: 유효 반경(config.PLAYER_AIM_ASSIST_RADIUS) 내 최단 거리 적 엔티티 (없으면 None).
        """
        enemies = game_world.world[game_world.LAYER_ENEMY]
        best_target = None
        min_dist = float('inf')
        assist_radius = getattr(config, 'PLAYER_AIM_ASSIST_RADIUS', 160.0)

        for enemy in enemies:
            if getattr(enemy, 'is_dead', False) or getattr(enemy, 'hp', 0.0) <= 0.0:
                continue

            # 일반 상태에서는 수리검 표식 또는 처형 상태인 적만 유효
            if not allow_all_alive and not getattr(enemy, 'is_dash_target', False):
                continue

            dist = math.hypot(self.mouse_x - enemy.x, self.mouse_y - enemy.y)
            if dist <= (enemy.radius + assist_radius) and dist < min_dist:
                min_dist = dist
                best_target = enemy

        return best_target

    def try_trigger_dash(self) -> bool:
        """
        우클릭 시 스마트 에임 어시스트로 표식 적을 찾아 최초 돌진(일섬) 발동
        """
        if self.state in (STATE_DASH, STATE_ROLL):
            return False

        target = self.find_aim_assist_target(allow_all_alive=False)
        if target is not None:
            self.start_dash(target)
            return True
        return False

    def start_dash(self, target: Any) -> None:
        """
        최초 돌진 (텔레포트 & 관성 계승 일섬 발동)
        PRD 3.3절 명세:
        1. 발동 시점의 'Player -> Target' 방향 벡터 정규화 -> 관성 방향(dash_dir) 저장
        2. 타겟 위치로 텔레포트
        3. 타겟의 수리검 전량 회수 (탄창 복구)
        4. 데미지 계산 및 적용:
           - is_executable == True: target.max_hp (100% 즉사 처형)
           - 일반 상태: max(1, retrieved) * 40.0
        5. dash_base_damage 기록 및 dash_hit_enemies 초기화
        6. STATE_DASH FSM 전이
        """
        to_x = target.x - self.x
        to_y = target.y - self.y
        dist = math.hypot(to_x, to_y)
        if dist > 0.0:
            self.dash_dir_x = to_x / dist
            self.dash_dir_y = to_y / dist
        else:
            self.dash_dir_x, self.dash_dir_y = 1.0, 0.0

        # 타겟 위치로 텔레포트
        self.x = target.x
        self.y = target.y

        # 박힌 수리검 일괄 회수
        retrieved = target.retrieve_all_shurikens()

        # 타겟 데미지 계산
        if getattr(target, 'is_executable', False):
            damage = target.max_hp
        else:
            damage = retrieved * config.PLAYER_DASH_STACK_DAMAGE

        target.hp = max(0.0, target.hp - damage)
        self.dash_base_damage = damage
        self.dash_hit_enemies = {id(target)}

        # 타격감 연출: Hit-Stop 0.08초, Screen Shake, 잔상 및 타겟 섬광 (PRD 5.2절)
        game_framework.start_hit_stop(config.HIT_STOP_DURATION)
        game_framework.start_screen_shake(config.SCREEN_SHAKE_INTENSITY, config.SCREEN_SHAKE_DURATION)
        if hasattr(target, 'hit_flash_timer'):
            target.hit_flash_timer = 0.16
        self.afterimages.append([self.x, self.y, config.AFTERIMAGE_LIFETIME, config.AFTERIMAGE_LIFETIME, self.dash_dir_x, self.dash_dir_y])

        # 처치 판정 및 플래그 초기화
        self.dash_killed_any = False
        if target.hp <= 0.0:
            target.is_dead = True
            self.dash_killed_any = True

        # FSM 상태 전이
        self.state = STATE_DASH
        self.dash_timer = self.dash_duration
        self.afterimage_spawn_timer = 0.0

    def update_dash(self, dt: float) -> None:
        prev_x = self.x
        prev_y = self.y

        move_dt = min(dt, max(0.0, self.dash_timer))
        self.dash_timer -= dt
        self.x += self.dash_dir_x * self.dash_speed * move_dt
        self.y += self.dash_dir_y * self.dash_speed * move_dt

        self.x = max(self.radius, min(config.CANVAS_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(config.CANVAS_HEIGHT - self.radius, self.y))

        # 이동 중 청록색 잔상 생성 (주기적 샘플링)
        self.afterimage_spawn_timer += dt
        if self.afterimage_spawn_timer >= 0.015:
            self.afterimage_spawn_timer = 0.0
            self.afterimages.append([self.x, self.y, config.AFTERIMAGE_LIFETIME, config.AFTERIMAGE_LIFETIME, self.dash_dir_x, self.dash_dir_y])

        # 이번 프레임의 이동 선분 (prev_x, prev_y) -> (self.x, self.y)
        seg_dx = self.x - prev_x
        seg_dy = self.y - prev_y
        seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy

        penetrate_damage = self.dash_base_damage * config.PLAYER_DASH_PENETRATE_RATIO
        for enemy in game_world.world[game_world.LAYER_ENEMY]:
            enemy_id = id(enemy)
            if (
                getattr(enemy, 'is_dead', False)
                or getattr(enemy, 'hp', 0.0) <= 0.0
                or enemy_id in self.dash_hit_enemies
            ):
                continue

            # 선분 vs 원 최단 거리 계산 (터널링 방지 궤적 판정)
            hit_dist = self.radius + enemy.radius
            if seg_len_sq > 0.0:
                t = ((enemy.x - prev_x) * seg_dx + (enemy.y - prev_y) * seg_dy) / seg_len_sq
                t_clamped = max(0.0, min(1.0, t))
                closest_x = prev_x + t_clamped * seg_dx
                closest_y = prev_y + t_clamped * seg_dy
                dist = math.hypot(enemy.x - closest_x, enemy.y - closest_y)
            else:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)

            if dist <= hit_dist:
                enemy.hp = max(0.0, enemy.hp - penetrate_damage)
                if hasattr(enemy, 'hit_flash_timer'):
                    enemy.hit_flash_timer = 0.14
                self.dash_hit_enemies.add(enemy_id)
                # 관통 타격 시 경쾌한 히트스탑 및 카메라 진동
                game_framework.start_hit_stop(0.05)
                game_framework.start_screen_shake(10.0, 0.12)
                if enemy.hp <= 0.0:
                    enemy.is_dead = True
                    self.dash_killed_any = True
                    if hasattr(enemy, 'release_embedded_shurikens'):
                        enemy.release_embedded_shurikens()

        if self.dash_timer <= 0.0:
            if getattr(self, 'in_bullet_time_dash', False):
                # 불릿타임 중 연쇄 돌진 완료: 불릿타임 시간 남아있으면 불릿타임 복귀!
                if self.bullet_time_timer > 0.0:
                    self.state = STATE_BULLET_TIME
                    game_framework.set_time_scale(config.BULLET_TIME_SCALE)
                else:
                    self.exit_bullet_time()
                self.in_bullet_time_dash = False
            elif self.dash_killed_any:
                self.enter_bullet_time()
            else:
                self.state = STATE_NORMAL

    def enter_bullet_time(self) -> None:
        """
        처치 리셋 발동 및 불릿타임 상태 진입 (PRD 3.4절)
        - FSM 상태를 STATE_BULLET_TIME으로 전이
        - 전역 시간 배율을 BULLET_TIME_SCALE (0.1)로 감속
        - 현실 시간(Unscaled Time) 기준 타이머를 BULLET_TIME_DURATION으로 설정
        - dash_killed_any 초기화 및 체인 킬 카운트 1 시작
        """
        self.state = STATE_BULLET_TIME
        self.bullet_time_timer = self.bullet_time_duration
        self.dash_killed_any = False
        self.chain_kill_count = 1
        game_framework.set_time_scale(config.BULLET_TIME_SCALE)

    def exit_bullet_time(self) -> None:
        """불릿타임 만료 시 일반 상태 복귀 및 시간 배율 정상화(1.0)"""
        self.state = STATE_NORMAL
        self.bullet_time_timer = 0.0
        self.in_bullet_time_dash = False
        game_framework.set_time_scale(1.0)

    def update_bullet_time(self, unscaled_dt: float) -> None:
        """불릿타임 실제 시간 타이머 차감 및 만료 처리"""
        self.bullet_time_timer -= unscaled_dt
        if self.bullet_time_timer <= 0.0:
            self.exit_bullet_time()

    def start_chain_dash(self) -> None:
        """
        불릿타임 중 연쇄 돌진/처형 (Hyper Chain Execution) 발동.
        1. 스마트 에임 어시스트로 마우스 커서 부근(160px)의 살아있는 적을 자동 락온 타겟팅.
        2. 타겟 적이 존재하는 경우:
           - 플레이어 -> 타겟 방향 벡터 및 관성 방향 설정
           - 해당 적으로 즉시 순간이동
           - 방패병 정면 가드 판정 (정면이면 가드 방어, 배후면 처형)
           - 일반 적(추격병, 저격병 등): 즉시 100% 일격 처형! (hp = 0, is_dead = True)
           - 적에 꽂혀있던 수리검 전량 회수 (탄창 복구)
           - 불릿타임 타이머 연장 (+1.2초) 및 0.1배속 유지
           - 짧은 일섬 관통 이동(STATE_DASH) 후 불릿타임 복귀
        3. 타겟이 없는 빈 공간 클릭 시:
           - 커서 방향으로 맹목 돌진하며 불릿타임 해제(정상 시간 1.0 복귀)
        """
        target = self.find_aim_assist_target(allow_all_alive=True)

        if target is not None:
            to_x = target.x - self.x
            to_y = target.y - self.y
            dist = math.hypot(to_x, to_y)
            if dist > 0.0:
                self.dash_dir_x = to_x / dist
                self.dash_dir_y = to_y / dist
            else:
                self.dash_dir_x, self.dash_dir_y = 1.0, 0.0

            # 방패병 정면 방어 판정
            is_shielder = getattr(target, 'enemy_type', '') == 'shielder'
            guarded = False
            if is_shielder:
                dot = target.dir_x * self.dash_dir_x + target.dir_y * self.dash_dir_y
                if dot <= 0.0:
                    guarded = True

            if guarded:
                # 방패병 정면에 막힘: 데미지 0, 튕김 이펙트, 불릿타임 유지
                target.shield_flash_timer = 0.2
                game_framework.start_hit_stop(0.08)
                game_framework.start_screen_shake(8.0, 0.1)
                self.x = target.x - self.dash_dir_x * (target.radius + self.radius + 6.0)
                self.y = target.y - self.dash_dir_y * (target.radius + self.radius + 6.0)
                self.dash_killed_any = False
            else:
                # 순간이동 및 일격 처형
                self.x = target.x
                self.y = target.y

                target.retrieve_all_shurikens()
                target.hp = 0.0
                target.is_dead = True
                self.dash_killed_any = True
                self.chain_kill_count += 1

                # 불릿타임 시간 충전
                reward_time = getattr(config, 'CHAIN_DASH_KILL_REWARD_TIME', 1.2)
                self.bullet_time_timer = min(self.bullet_time_duration, self.bullet_time_timer + reward_time)

                # 타격감 연출
                game_framework.start_hit_stop(config.HIT_STOP_DURATION)
                game_framework.start_screen_shake(config.SCREEN_SHAKE_INTENSITY, config.SCREEN_SHAKE_DURATION)
                if hasattr(target, 'hit_flash_timer'):
                    target.hit_flash_timer = 0.16

            self.dash_base_damage = getattr(config, 'CHAIN_DASH_DAMAGE', 200.0)
            self.dash_hit_enemies = {id(target)}
            self.in_bullet_time_dash = True
            self.dash_timer = self.dash_duration
            self.state = STATE_DASH
            self.afterimage_spawn_timer = 0.0
            self.afterimages.append([self.x, self.y, config.AFTERIMAGE_LIFETIME, config.AFTERIMAGE_LIFETIME, self.dash_dir_x, self.dash_dir_y])

        else:
            # 빈 공간 우클릭: 커서 방향으로 돌진하며 불릿타임 탈출
            self.exit_bullet_time()

            to_x = self.mouse_x - self.x
            to_y = self.mouse_y - self.y
            dist = math.hypot(to_x, to_y)
            if dist > 0.0:
                self.dash_dir_x = to_x / dist
                self.dash_dir_y = to_y / dist
            else:
                self.dash_dir_x, self.dash_dir_y = 1.0, 0.0

            self.state = STATE_DASH
            self.dash_timer = self.dash_duration
            self.dash_hit_enemies.clear()
            self.dash_killed_any = False
            self.in_bullet_time_dash = False
            self.afterimage_spawn_timer = 0.0
            self.afterimages.append([self.x, self.y, config.AFTERIMAGE_LIFETIME, config.AFTERIMAGE_LIFETIME, self.dash_dir_x, self.dash_dir_y])
            if self.dash_base_damage <= 0.0:
                self.dash_base_damage = config.ENEMY_BASE_MAX_HP

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
        if self.state != STATE_NORMAL or self.roll_cooldown_timer > 0.0:
            return

        dx = int(self.key_right) - int(self.key_left)
        dy = int(self.key_up) - int(self.key_down)
        direction_length = math.hypot(dx, dy)

        if direction_length > 0.0:
            self.roll_dir_x = dx / direction_length
            self.roll_dir_y = dy / direction_length
        else:
            last_dir_x, last_dir_y = self.last_move_dir
            last_direction_length = math.hypot(last_dir_x, last_dir_y)
            if last_direction_length > 0.0:
                self.roll_dir_x = last_dir_x / last_direction_length
                self.roll_dir_y = last_dir_y / last_direction_length
            else:
                mouse_dir_x = self.mouse_x - self.x
                mouse_dir_y = self.mouse_y - self.y
                mouse_direction_length = math.hypot(mouse_dir_x, mouse_dir_y)
                if mouse_direction_length > 0.0:
                    self.roll_dir_x = mouse_dir_x / mouse_direction_length
                    self.roll_dir_y = mouse_dir_y / mouse_direction_length
                else:
                    self.roll_dir_x, self.roll_dir_y = 1.0, 0.0

        self.state = STATE_ROLL
        self.roll_timer = self.roll_duration
        self.roll_cooldown_timer = self.roll_cooldown

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
        self.roll_timer -= dt
        self.x += self.roll_dir_x * self.roll_speed * dt
        self.y += self.roll_dir_y * self.roll_speed * dt

        self.x = max(self.radius, min(config.CANVAS_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(config.CANVAS_HEIGHT - self.radius, self.y))

        if self.roll_timer <= 0.0:
            self.state = STATE_NORMAL

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

        self.x = max(self.radius, min(config.CANVAS_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(config.CANVAS_HEIGHT - self.radius, self.y))

    def take_damage(self, amount: float) -> None:
        """
        플레이어 피격 데미지 처리.
        - 주의(기획 규칙): 구르기(STATE_ROLL) 상태라도 I-Frame(무적)이 없으므로 회피 불가, 그대로 피해를 입음!
        - 순간 카메라 진동 및 피격 섬광 활성화
        """
        self.hp = max(0.0, self.hp - amount)
        self.damage_flash_timer = 0.15
        game_framework.start_screen_shake(8.0, 0.12)

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """프레임 업데이트 (FSM 상태별 처리 및 쿨다운/잔상 차감)"""
        # 피격 섬광 타이머 차감
        if self.damage_flash_timer > 0.0:
            self.damage_flash_timer = max(0.0, self.damage_flash_timer - unscaled_dt)

        # 잔상 타이머 갱신 (unscaled_dt 기준 감쇄)
        for img in self.afterimages:
            img[2] -= unscaled_dt
        self.afterimages = [img for img in self.afterimages if img[2] > 0.0]

        # 쿨다운 타이머 갱신 (scaled_dt 기준)
        if self.roll_cooldown_timer > 0.0:
            self.roll_cooldown_timer = max(0.0, self.roll_cooldown_timer - scaled_dt)

        # FSM 상태별 이동 처리
        if self.state == STATE_DASH:
            # 불릿타임 중 연쇄 일섬은 적들이 0.1배속인 상태에서 플레이어는 실시간 속도로 베고 지나가도록 unscaled_dt 적용
            dash_dt = unscaled_dt if getattr(self, 'in_bullet_time_dash', False) else scaled_dt
            self.update_dash(dash_dt)
        elif self.state == STATE_ROLL:
            self.update_roll(scaled_dt)
        elif self.state == STATE_BULLET_TIME:
            self.update_bullet_time(unscaled_dt)
        else:
            self.update_movement(scaled_dt)

    def draw(self) -> None:
        """플레이어 임시 렌더링 (사각 히트박스 시각화, 청록 잔상, 일섬 궤적, 불릿타임 조준선 및 머리 위 탄창 표시)"""
        # 1. 청록색 궤적 잔상(Afterimage) 렌더링 (PRD 5.2절)
        for img in self.afterimages:
            ix, iy, timer, max_timer, dir_x, dir_y = img
            progress = max(0.0, min(1.0, timer / max_timer))
            alpha = int(220 * progress)
            rx = int(self.radius * (0.7 + 0.3 * progress))
            ry = int(self.radius * (0.7 + 0.3 * progress))
            pico2d.draw_rectangle(int(ix - rx), int(iy - ry), int(ix + rx), int(iy + ry), r=0, g=255, b=255, a=alpha)
            pico2d.draw_line(int(ix - dir_x * 30.0 * progress), int(iy - dir_y * 30.0 * progress), int(ix), int(iy), r=0, g=255, b=255, a=alpha)

        # 2. 불릿타임 스마트 락온 조준선 및 착지 지점 시각화 (PRD 3.4 & 5.2절)
        if self.state == STATE_BULLET_TIME:
            target = self.find_aim_assist_target(allow_all_alive=True)
            if target is not None:
                # 스마트 락온된 연쇄 처형 대상 표시선 (Bright Neon Cyan -> Gold)
                pico2d.draw_line(int(self.x), int(self.y), int(target.x), int(target.y), r=255, g=220, b=50)
                # 타겟 주변 네온 다이아몬드 락온 브래킷
                tr = int(target.radius + 10.0)
                pico2d.draw_rectangle(int(target.x - tr), int(target.y - tr), int(target.x + tr), int(target.y + tr), r=255, g=220, b=50)
                pico2d.draw_line(int(target.x - tr - 4), int(target.y), int(target.x + tr + 4), int(target.y), r=255, g=220, b=50)
                pico2d.draw_line(int(target.x), int(target.y - tr - 4), int(target.x), int(target.y + tr + 4), r=255, g=220, b=50)
            else:
                to_x = self.mouse_x - self.x
                to_y = self.mouse_y - self.y
                dist = math.hypot(to_x, to_y)
                if dist > 0.0:
                    dir_x = to_x / dist
                    dir_y = to_y / dist
                else:
                    dir_x, dir_y = 1.0, 0.0

                end_x = int(self.x + dir_x * self.dash_distance)
                end_y = int(self.y + dir_y * self.dash_distance)
                pico2d.draw_line(int(self.x), int(self.y), end_x, end_y, r=0, g=255, b=255)
                pico2d.draw_rectangle(end_x - 4, end_y - 4, end_x + 4, end_y + 4, r=0, g=255, b=255, filled=True)
        elif self.state == STATE_DASH:
            # 일섬 관통 궤적 연출 (청록색 발광 삼중선)
            tail_x = int(self.x - self.dash_dir_x * 70.0)
            tail_y = int(self.y - self.dash_dir_y * 70.0)
            pico2d.draw_line(tail_x, tail_y, int(self.x), int(self.y), r=0, g=255, b=255)
            pico2d.draw_line(tail_x, tail_y + 1, int(self.x), int(self.y) + 1, r=0, g=255, b=255)
            pico2d.draw_line(tail_x, tail_y - 1, int(self.x), int(self.y) - 1, r=0, g=255, b=255)

        # 3. 본체 렌더링 (피격 섬광 및 구르기 축소 피드백)
        rx = self.radius * 0.7 if self.state == STATE_ROLL else self.radius
        ry = self.radius * 0.7 if self.state == STATE_ROLL else self.radius

        left = int(self.x - rx)
        bottom = int(self.y - ry)
        right = int(self.x + rx)
        top = int(self.y + ry)

        if self.damage_flash_timer > 0.0:
            pico2d.draw_rectangle(left - 2, bottom - 2, right + 2, top + 2, r=255, g=60, b=60, filled=True)
            pico2d.draw_rectangle(left, bottom, right, top, r=255, g=255, b=255)
        else:
            pico2d.draw_rectangle(left, bottom, right, top, r=0, g=255, b=255)

        # 4. 플레이어 체력바 (본체 하단 표시)
        hp_bar_w = 36.0
        hp_bar_h = 4.0
        hp_bar_left = int(self.x - hp_bar_w / 2.0)
        hp_bar_bottom = int(self.y - self.radius - 8.0)
        pico2d.draw_rectangle(hp_bar_left, hp_bar_bottom, int(hp_bar_left + hp_bar_w), int(hp_bar_bottom + hp_bar_h), r=70, g=20, b=20)
        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        if hp_ratio > 0.0:
            pico2d.draw_rectangle(hp_bar_left, hp_bar_bottom, int(hp_bar_left + hp_bar_w * hp_ratio), int(hp_bar_bottom + hp_bar_h), r=0, g=230, b=120, filled=True)

        # 5. 잔여 탄창 시각화 (청록색 네온 탄창 도트)
        spacing = 11.0
        total_span = (self.max_ammo - 1) * spacing if self.max_ammo > 1 else 0.0
        start_x = self.x - total_span / 2.0
        ammo_y = self.y + self.radius + 10.0
        for i in range(self.max_ammo):
            bx = start_x + i * spacing
            if i < self.current_ammo:
                pico2d.draw_rectangle(int(bx - 3), int(ammo_y - 3), int(bx + 3), int(ammo_y + 3), r=0, g=255, b=255, filled=True)
            else:
                pico2d.draw_rectangle(int(bx - 1), int(ammo_y - 1), int(bx + 1), int(ammo_y + 1), r=0, g=90, b=90)
