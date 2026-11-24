"""Fake PicoGraphics for the simulator, ported from pimoroni-pico (commit 5ed5cb4):
libraries/pico_graphics/pico_graphics.cpp, libraries/bitmap_fonts/bitmap_fonts.cpp
and micropython/modules/picographics/picographics.cpp.

Only what the project uses is here. Where it's cheap it fails like the board
does: int-only coordinates, str-only text, known font names.
"""
from sim.bitmap_fonts import FONTS

DISPLAY_GALACTIC_UNICORN = 13  # the value doesn't matter, only that it's passed
PEN_RGB888 = 7

WIDTH = 53
HEIGHT = 11

# what the C side uses when wordwrap is left out
NO_WRAP = 2**31 - 1


def _int(name: str, value: object) -> int:
  # MP_ARG_INT rejects floats (and anything else that isn't an int)
  if not isinstance(value, int):
    raise TypeError(f"{name}: can't convert {type(value).__name__} to int")
  return value


def _scale(scale: object) -> int:
  """bitmap fonts: float scale, clamped to at least 1, then truncated to uint8"""
  if scale is None:
    return 2
  if not isinstance(scale, (int, float)):
    raise TypeError(f"scale: can't convert {type(scale).__name__} to float")
  return int(max(1.0, float(scale))) & 0xff


def _cdiv(a: int, b: int) -> int:
  """C integer division, which truncates towards zero"""
  q = abs(a) // abs(b)
  return q if (a < 0) == (b < 0) else -q


class _Rect:
  def __init__(self, x: int, y: int, w: int, h: int) -> None:
    self.x, self.y, self.w, self.h = x, y, w, h

  def intersection(self, r: "_Rect") -> "_Rect":
    x = max(self.x, r.x)
    y = max(self.y, r.y)
    return _Rect(x, y, min(self.x + self.w, r.x + r.w) - x, min(self.y + self.h, r.y + r.h) - y)

  def empty(self) -> bool:
    return self.w <= 0 or self.h <= 0

  def contains(self, x: int, y: int) -> bool:
    return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h


class PicoGraphics:
  def __init__(self, display: int, pen_type: int = PEN_RGB888) -> None:
    self.width = WIDTH
    self.height = HEIGHT
    self.bounds = _Rect(0, 0, WIDTH, HEIGHT)
    self.clip = _Rect(0, 0, WIDTH, HEIGHT)
    self.pen = 0
    # RGB888 ints, row by row
    self.framebuffer: list[int] = [0] * (WIDTH * HEIGHT)
    self.font = FONTS["bitmap6"]

  # pens and state

  def create_pen(self, r: int, g: int, b: int) -> int:
    r, g, b = _int("r", r) & 0xff, _int("g", g) & 0xff, _int("b", b) & 0xff
    return (r << 16) | (g << 8) | b

  def set_pen(self, pen: int) -> None:
    self.pen = _int("pen", pen)

  def set_font(self, font: str) -> None:
    if font not in FONTS:
      # the board raises for fonts it doesn't know about, too
      raise ValueError(f"unknown font {font!r}, the simulator knows {sorted(FONTS)}")
    self.font = FONTS[font]

  def get_bounds(self) -> tuple[int, int]:
    return (WIDTH, HEIGHT)

  def set_clip(self, x: int, y: int, w: int, h: int) -> None:
    self.clip = self.bounds.intersection(_Rect(_int("x", x), _int("y", y), _int("w", w), _int("h", h)))

  def remove_clip(self) -> None:
    self.clip = _Rect(0, 0, WIDTH, HEIGHT)

  # drawing

  def _set_pixel(self, x: int, y: int) -> None:
    self.framebuffer[y * WIDTH + x] = self.pen & 0xffffff

  def _rect(self, r: _Rect) -> None:
    clipped = r.intersection(self.clip)
    if clipped.empty():
      return
    for y in range(clipped.y, clipped.y + clipped.h):
      for x in range(clipped.x, clipped.x + clipped.w):
        self._set_pixel(x, y)

  def _pixel(self, x: int, y: int) -> None:
    if self.clip.contains(x, y):
      self._set_pixel(x, y)

  def clear(self) -> None:
    self._rect(self.clip)

  def pixel(self, x: int, y: int) -> None:
    self._pixel(_int("x", x), _int("y", y))

  def rectangle(self, x: int, y: int, w: int, h: int) -> None:
    self._rect(_Rect(_int("x", x), _int("y", y), _int("w", w), _int("h", h)))

  def line(self, x1: int, y1: int, x2: int, y2: int, thickness: int | None = None) -> None:
    x1, y1, x2, y2 = _int("x1", x1), _int("y1", y1), _int("x2", x2), _int("y2", y2)
    if thickness is not None and _int("thickness", thickness) != 1:
      raise NotImplementedError("the simulator only draws 1px lines")
    if y1 == y2:
      for x in range(min(x1, x2), max(x1, x2) + 1):
        self._pixel(x, y1)
      return
    if x1 == x2:
      for y in range(min(y1, y2), max(y1, y2) + 1):
        self._pixel(x1, y)
      return
    # general case, 16:16 fixed point stepping like the C
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) > abs(dy):
      s = abs(dx)
      sx = -1 if dx < 0 else 1
      sy = _cdiv(dy << 16, s)
      x, y = x1, y1 << 16
      for _ in range(s):
        self._pixel(x, y >> 16)
        y += sy
        x += sx
    else:
      s = abs(dy)
      sy = -1 if dy < 0 else 1
      sx = _cdiv(dx << 16, s)
      y, x = y1, x1 << 16
      for _ in range(s):
        self._pixel(x >> 16, y)
        y += sy
        x += sx
    self._pixel(x2, y2)

  # text, bitmap fonts only

  def _char_width(self, c: int, scale: int, fixed_width: bool) -> int:
    _, widths, glyphs = self.font
    if c < 32 or c > 127:
      # the board remaps some latin-1 accented letters. we don't, they measure 0
      return 0
    if fixed_width:
      return len(glyphs[0]) * scale
    return widths[c - 32] * scale

  def _char(self, c: int, x: int, y: int, scale: int) -> None:
    _, widths, glyphs = self.font
    if c < 32 or c > 127:
      return
    glyph = glyphs[c - 32]
    for cx in range(widths[c - 32]):
      column = glyph[cx]
      for cy in range(8):
        if column & (1 << cy):
          self._rect(_Rect(x + cx * scale, y + cy * scale, scale, scale))

  @staticmethod
  def _bytes(text: object) -> bytes:
    if isinstance(text, bytes):
      return text
    if not isinstance(text, str):
      raise TypeError("text: string required")
    # the C walks the utf-8 bytes. 0xc2/0xc3 are codepage markers it skips
    return bytes(b for b in text.encode("utf-8") if b not in (0xc2, 0xc3))

  def measure_text(self, text: str, scale: float | None = None, spacing: int = 1, fixed_width: bool = False) -> int:
    t = self._bytes(text)
    s = _scale(scale)
    spacing = _int("spacing", spacing)
    width = 0
    for c in t:
      width += self._char_width(c, s, fixed_width) + spacing * s
    if width > 0:
      width -= spacing * s
    return width

  def text(self, text: str, x1: int, y1: int, wordwrap: int = NO_WRAP, scale: float | None = None,
           angle: int = 0, spacing: int = 1, fixed_width: bool = False) -> None:
    t = self._bytes(text)
    x, y = _int("x1", x1), _int("y1", y1)
    wrap = _int("wordwrap", wordwrap)
    s = _scale(scale)
    spacing = _int("spacing", spacing)
    if _int("angle", angle) % 360 != 0:
      raise NotImplementedError("the simulator only draws unrotated text")
    height = self.font[0]

    char_offset = 0
    line_offset = 0
    space_width = self._char_width(ord(" "), s, fixed_width) + spacing * s
    i = 0
    n = len(t)
    while i < n:
      next_space = t.find(b" ", i + 1)
      next_space = n if next_space == -1 else next_space
      next_linebreak = t.find(b"\n", i + 1)
      next_linebreak = n if next_linebreak == -1 else next_linebreak
      next_break = min(next_space, next_linebreak)

      # uint16 in the C
      word_width = sum(self._char_width(t[j], s, fixed_width) + spacing * s for j in range(i, next_break)) & 0xffff
      if char_offset != 0 and char_offset + word_width > wrap:
        char_offset = 0
        line_offset += (height + 1) * s

      for j in range(i, min(next_break + 1, n)):
        c = t[j]
        if c == ord("\n"):
          line_offset += (height + 1) * s
          char_offset = 0
        elif c == ord(" "):
          char_offset += space_width
        else:
          self._char(c, x + char_offset, y + line_offset, s)
          char_offset += self._char_width(c, s, fixed_width) + spacing * s
      i = next_break + 1
