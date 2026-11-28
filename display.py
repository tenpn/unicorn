from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
import math
import micropython

# typing isn't on the board; this block is only seen by type checkers.
# ptr32 is a viper built-in, so it only needs declaring for them
TYPE_CHECKING = False
if TYPE_CHECKING:
  def ptr32(buf: object) -> list[int]: ...

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# create our GalacticUnicorn object
gu = GalacticUnicorn()

gu.set_brightness(0.5)

# flipped mode turns the whole display 180°. B toggles it in the carousel
flipped = False

def toggle_flipped() -> None:
  global flipped
  flipped = not flipped

@micropython.viper
def _reverse_pixels(buf: object) -> object:
  # in row-major order, turning 180° is just reversing the pixels
  p = ptr32(buf)
  i = 0
  j = 53*11 - 1
  while i < j:
    t = p[i]
    p[i] = p[j]
    p[j] = t
    i += 1
    j -= 1

def show() -> None:
  """send the framebuffer to the LEDs, turned 180° in flipped mode. the
  framebuffer is put back afterwards, as some drawing builds on the last frame"""
  if flipped:
    _reverse_pixels(graphics)
    gu.update(graphics)
    _reverse_pixels(graphics)
  else:
    gu.update(graphics)

# pen colours to draw with
DARKER_GREY = graphics.create_pen(8,8,8)
DIM_BLUE = graphics.create_pen(5,5,16)
DARK_GREY = graphics.create_pen(15,15,15)
GREY = graphics.create_pen(50,50,50)
LIGHT_GREY = graphics.create_pen(150,150,150)
BLACK = graphics.create_pen(0, 0, 0)
YELLOW = graphics.create_pen(255, 255, 50)
LIGHT_PURPLE = graphics.create_pen(50, 0, 100)
PURPLE = graphics.create_pen(200, 50, 150)
RED = graphics.create_pen(255, 50, 50)
GREEN = graphics.create_pen(50, 255, 50)
ORANGE = graphics.create_pen(255, 127, 50)
LIGHT_BLUE = graphics.create_pen(100, 100, 255)
DARK_BLUE = graphics.create_pen(50, 50, 200)
BLUE = graphics.create_pen(50, 50, 255)

# a little lighter than DARK_GREY, for marks on a dim background
DARK_GREY_MARK = graphics.create_pen(35,35,35)
# a dim icy blue, for marking freezing point on a dim background
DIM_ICY_BLUE = graphics.create_pen(40,90,120)
# for the Christmas icons
WHITE = graphics.create_pen(255,255,255)
SKIN = graphics.create_pen(255,140,100)
BROWN = graphics.create_pen(110,50,15)
ANTLER = graphics.create_pen(170,120,60)

TEMPERATURE_COLOURS = [
  # below temp, pen
  [-3, graphics.create_pen(50,50,255)],
  [3, graphics.create_pen(50,125,255)],
  [10, graphics.create_pen(50,225,150)],
  [15, graphics.create_pen(50,255,50)],
  [25, graphics.create_pen(255,125,50)],
  [99, graphics.create_pen(255,50,50)],
]
def get_col_for_temp(temp: float) -> int:
  for (max_temp, col) in TEMPERATURE_COLOURS:
    if temp <= max_temp:
      return col
  return TEMPERATURE_COLOURS[-1][1]

graphics.set_font("bitmap6")

def lerp(a: float, b: float, t: float) -> float:
  return a*(1-t) + b*t

def ease_in_out(t: float) -> float:
  return (2*t*t) if t < 0.5 else (1 - (math.pow(-2*t+2, 2))*0.5)

def ease_out(t: float) -> float:
  return 1-(1-t)*(1-t)

def ease_in(t: float) -> float:
  return t*t
