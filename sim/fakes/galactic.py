"""Fake GalacticUnicorn for the simulator. Buttons are never pressed and
update() does nothing: the simulator reads the framebuffer itself."""
import math

# typing isn't on the board, but this file only runs on the Mac
from typing import Any


class GalacticUnicorn:
  WIDTH = 53
  HEIGHT = 11

  SWITCH_A = 0
  SWITCH_B = 1
  SWITCH_C = 3
  SWITCH_D = 6
  SWITCH_SLEEP = 27
  SWITCH_VOLUME_UP = 7
  SWITCH_VOLUME_DOWN = 8
  SWITCH_BRIGHTNESS_UP = 21
  SWITCH_BRIGHTNESS_DOWN = 26

  def __init__(self) -> None:
    # 0..256, as galactic_unicorn.cpp stores it. 256 is full brightness
    self.brightness = 256

  def set_brightness(self, value: float) -> None:
    self.brightness = math.floor(max(0.0, min(1.0, value)) * 256.0)

  def get_brightness(self) -> float:
    return self.brightness / 256.0

  def adjust_brightness(self, delta: float) -> None:
    self.set_brightness(self.get_brightness() + delta)

  def is_pressed(self, switch: int) -> bool:
    return False

  def update(self, graphics: Any) -> None:
    pass
