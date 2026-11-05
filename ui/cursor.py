"""
cursor.py
인게임 커스텀 조준선(크로스헤어, Crosshair) UI 모듈.
전체화면 및 창 모드에서 정밀한 마우스 조준점을 항상 시각화하며,
수리검 투척 및 타겟팅 상태에 따라 조준선 형태를 제공합니다.
"""

from typing import Any
import pico2d
from sdl2 import SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP
import config


class Cursor:
    def __init__(self, x: float = 640.0, y: float = 360.0) -> None:
        self.x: float = x
        self.y: float = y
        self.size: float = 12.0       # 십자선 길이
        self.gap: float = 4.0         # 중심 여백
        self.is_hovering_target: bool = False  # 적 호버 시 조준선 강조

    def handle_event(self, event: Any) -> None:
        """마우스 이동 이벤트 수신 시 좌표를 캔버스 데카르트 좌표계로 갱신"""
        if event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP):
            self.x = float(event.x)
            self.y = float(config.CANVAS_HEIGHT - 1 - event.y)

    def update(self, scaled_dt: float, unscaled_dt: float) -> None:
        """커서 애니메이션 또는 상태 업데이트"""
        pass

    def draw(self) -> None:
        """형광 네온 테마의 정밀 십자선(Crosshair) 렌더링"""
        ix, iy = int(self.x), int(self.y)
        gap = int(self.gap * (1.5 if self.is_hovering_target else 1.0))
        size = int(self.size * (1.3 if self.is_hovering_target else 1.0))

        # 1. 중심 점 (Center Dot)
        pico2d.draw_rectangle(ix - 1, iy - 1, ix + 1, iy + 1)

        # 2. 상하좌우 십자선 (Crosshair Lines)
        # 좌측 선
        pico2d.draw_line(ix - gap - size, iy, ix - gap, iy)
        # 우측 선
        pico2d.draw_line(ix + gap, iy, ix + gap + size, iy)
        # 하단 선
        pico2d.draw_line(ix, iy - gap - size, ix, iy - gap)
        # 상단 선
        pico2d.draw_line(ix, iy + gap, ix, iy + gap + size)

        # 3. 타겟 호버 중일 때 보조 조준 박스 (Target Lock Reticle)
        if self.is_hovering_target:
            box_r = gap + size
            pico2d.draw_rectangle(ix - box_r, iy - box_r, ix + box_r, iy + box_r)

