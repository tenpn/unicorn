from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
import time

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# create our GalacticUnicorn object
gu = GalacticUnicorn()

# start position for scrolling (off the side of the display)
scroll = float(-GalacticUnicorn.WIDTH)

# message to scroll
rows = [
  "Min 3, max 13",
  "Cloudy",
  "Paignton",
  "Next train: 3.35pm",
  "Really long long long text here"
]

# pen colours to draw with
BLACK = graphics.create_pen(0, 0, 0)
YELLOW = graphics.create_pen(255, 255, 0)

SCROLL_DURATION = 1
PAUSE_DURATION = 10
SCROLL_PADDING = 4

graphics.set_font("bitmap6")

current_row = 0
row_start_tickms = time.ticks_ms()
prev_scroll = 0
current_scroll = 0

def lerp(a: float, b: float, t: float):
  return a*(1-t) + b*t

while True:
  now = time.ticks_ms()
  time_on_row = time.ticks_diff(time.ticks_ms(), row_start_tickms)/1000.0

  graphics.set_pen(BLACK)
  graphics.clear()

  scroll_t = min(1, time_on_row/SCROLL_DURATION)

  prev_y = int(lerp(2, GalacticUnicorn.HEIGHT, scroll_t))
  current_y = int(lerp(-GalacticUnicorn.HEIGHT, 2, scroll_t))
  
  current_width = graphics.measure_text(rows[current_row], 1)
  if time_on_row > SCROLL_DURATION and current_width > GalacticUnicorn.WIDTH:
    current_scroll += 0.4
    while current_scroll >= (current_width + SCROLL_PADDING):
      current_scroll -= (current_width + SCROLL_PADDING)

  graphics.set_pen(YELLOW)
  graphics.text(rows[current_row-1], round(2 - prev_scroll), prev_y, -1, 0.5);    
  if prev_scroll > 0:
    prev_width = graphics.measure_text(rows[current_row-1], 1)
    graphics.text(rows[current_row-1], round(2 - prev_scroll) + prev_width + SCROLL_PADDING, prev_y, -1, 0.5);    
    
  graphics.text(rows[current_row], round(2 - current_scroll), current_y, -1, 0.5);
  if current_scroll > 0:
    graphics.text(rows[current_row], round(2 - current_scroll) + current_width + SCROLL_PADDING, current_y, -1, 0.5);

  if time_on_row > (SCROLL_DURATION + PAUSE_DURATION):
    current_row = (current_row + 1) % len(rows)
    row_start_tickms = now
    prev_scroll = current_scroll
    current_scroll = 0

  # update the display
  gu.update(graphics)

  time.sleep(0.02)