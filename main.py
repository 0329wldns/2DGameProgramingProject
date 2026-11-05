"""
main.py
MARK STRIKE 게임 루프 진입점.
화면 해상도: 1280 x 720 (PRD 명세)
"""

import pico2d
import config
import game_framework
from scenes import play_scene


def main() -> None:
    pico2d.open_canvas(config.CANVAS_WIDTH, config.CANVAS_HEIGHT)
    try:
        game_framework.run(play_scene)
    finally:
        pico2d.close_canvas()


if __name__ == '__main__':
    main()