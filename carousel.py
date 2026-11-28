from galactic import GalacticUnicorn
from display import graphics, gu, show, toggle_flipped, lerp, ease_in, BLACK, DARK_GREY
from screens import todays_screens, SCREEN_SCROLL_DURATION
from status import mem_used_y, draw_heap_status
from lifecycle import feed_watchdog
import time
import math
import gc

# how long each screen stays after sliding in. the volume up/sleep buttons change it
SCREEN_PAUSE_DURATION = 12

# last frame's button directions, so a press acts once rather than every frame it's held
brightness_btn_prev = 0
speed_btn_prev = 0
flip_btn_prev = False

def handle_buttons() -> None:
  """brightness up/down change brightness. volume up/sleep lengthen/shorten SCREEN_PAUSE_DURATION.
  B toggles flipped mode"""
  global SCREEN_PAUSE_DURATION, brightness_btn_prev, speed_btn_prev, flip_btn_prev

  brightness_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP) \
    else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN) \
    else 0
  if brightness_btn != brightness_btn_prev and brightness_btn != 0:
    gu.adjust_brightness(0.1 * brightness_btn)
  brightness_btn_prev = brightness_btn

  speed_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_VOLUME_UP) \
    else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_SLEEP) \
    else 0
  if speed_btn != speed_btn_prev and speed_btn != 0:
    SCREEN_PAUSE_DURATION = max(0, SCREEN_PAUSE_DURATION + speed_btn)
  speed_btn_prev = speed_btn

  flip_btn = gu.is_pressed(GalacticUnicorn.SWITCH_B)
  if flip_btn and not flip_btn_prev:
    toggle_flipped()
  flip_btn_prev = flip_btn

def show_screens(info: dict, duration_ms: int, heap_frag_y: int) -> None:
  """animate through the screens until duration_ms has passed (checked after each full cycle)"""
  start_tickms = time.ticks_ms()

  while time.ticks_diff(time.ticks_ms(), start_tickms) < duration_ms:
    current_screen = 0
    # checked once a cycle, so an occasional screen comes and goes between cycles
    screens = todays_screens()

    while current_screen < len(screens):

      screen_start_tickms = time.ticks_ms()
      # drawing churns out garbage, so without a collect the reading mostly
      # shows how long since the last automatic gc. collect then measure,
      # once per screen rather than every frame as both walk the heap
      gc.collect()
      mem_free = gc.mem_free()
      mem_alloc = gc.mem_alloc()
      mem_y = mem_used_y(mem_free, mem_alloc)
      print(f"screen {screens[current_screen].__name__} free {mem_free} alloc {mem_alloc} mem_y {mem_y}")

      while True:

        time_on_screen = time.ticks_diff(time.ticks_ms(), screen_start_tickms)/1000.0
        if time_on_screen > (SCREEN_SCROLL_DURATION + SCREEN_PAUSE_DURATION):
          current_screen +=1
          break

        graphics.set_pen(BLACK)
        graphics.clear()

        scroll_t = ease_in(min(1, time_on_screen/SCREEN_SCROLL_DURATION))

        prev_y = int(lerp(1, GalacticUnicorn.HEIGHT+1, scroll_t))
        current_y = int(lerp(-GalacticUnicorn.HEIGHT, 1, scroll_t))
        screens[current_screen-1](info, prev_y, time_on_screen)
        screens[current_screen](info, current_y, time_on_screen)

        # screen timer, counting down to the next screen
        graphics.set_pen(DARK_GREY)
        screen_t = (time_on_screen) / (SCREEN_PAUSE_DURATION+SCREEN_SCROLL_DURATION)
        progress_pixels = math.ceil(lerp(0, GalacticUnicorn.HEIGHT, (1-screen_t)))
        for progress_y in range(0, progress_pixels):
          graphics.pixel(GalacticUnicorn.WIDTH-1, (current_y - 1) + (GalacticUnicorn.HEIGHT - 1) - progress_y)
        draw_heap_status(mem_y, heap_frag_y)

        handle_buttons()

        # update the display
        show()
        feed_watchdog()

        time.sleep(0.02)
