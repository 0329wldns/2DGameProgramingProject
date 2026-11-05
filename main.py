"""
main.py
MARK STRIKE 게임 루프 진입점.
화면 해상도: 1280 x 720 (PRD 명세)
"""

import pico2d
import game_framework
from scenes import play_scene

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


def main() -> None:
    pico2d.open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    try:
        game_framework.run(play_scene)
    finally:
        pico2d.close_canvas()


if __name__ == '__main__':
    main()
