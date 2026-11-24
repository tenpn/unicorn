"""The simulator: draws screens from screens.py in a window on the Mac, using
fake galactic/picographics modules so the device code runs unchanged.

Run it with `.venv/bin/python tools.py sim`. See the readme for keys.
"""
import argparse
import datetime
import os
import sys
import time
import traceback
from pathlib import Path
from types import ModuleType

from sim import fixtures

# typing isn't on the board, but this file only runs on the Mac
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  import pygame

PROJECT_DIR = Path(__file__).resolve().parent.parent
FAKES_DIR = Path(__file__).resolve().parent / "fakes"
# device modules the simulator imports, and reloads when they change
DEVICE_MODULES = ["display", "icons", "screens"]

WIDTH = 53
HEIGHT = 11
PIXEL_SIZE = 16
FPS = 50
FRAME_S = 1 / FPS
WATCH_INTERVAL_S = 0.25

# the LED view lifts dim values, because on the panel a pen like (8,8,8) is
# clearly lit but on a monitor it's black. eyeballed, not measured: tune it
# against the real board. 1.0 is no lift
LED_LIFT = 0.6
UNLIT_LED = (10, 10, 10)


class SimClock:
  """the wall clock the screens see. starts at the fixture's "at" (or --at)
  and only moves while the simulator is playing"""

  def __init__(self, at: str) -> None:
    self.reset(at)

  def reset(self, at: str) -> None:
    h, m = fixtures.parse_at(at)
    start = datetime.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    self.start_epoch = start.timestamp()
    self.elapsed = 0.0

  def epoch(self) -> float:
    return self.start_epoch + self.elapsed


TICKS_PERIOD = 1 << 30


def install_time_shim(clock: SimClock) -> None:
  """make the CPython time module look like MicroPython's, on the sim clock.
  the simulator itself only uses time.perf_counter, which isn't touched"""
  real_localtime = time.localtime

  def localtime(secs: float | None = None) -> tuple[int, ...]:
    # MicroPython returns 8 fields: no tm_isdst
    return tuple(real_localtime(clock.epoch() if secs is None else secs))[:8]

  def ticks_ms() -> int:
    return int(clock.elapsed * 1000) % TICKS_PERIOD

  def ticks_diff(a: int, b: int) -> int:
    return ((a - b + TICKS_PERIOD // 2) % TICKS_PERIOD) - TICKS_PERIOD // 2

  def ticks_add(a: int, delta: int) -> int:
    return (a + delta) % TICKS_PERIOD

  def sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000)

  shim = time  # setattr, so pyright doesn't complain about assigning to the module
  setattr(shim, "time", lambda: int(clock.epoch()))
  setattr(shim, "localtime", localtime)
  setattr(shim, "ticks_ms", ticks_ms)
  setattr(shim, "ticks_diff", ticks_diff)
  setattr(shim, "ticks_add", ticks_add)
  setattr(shim, "sleep_ms", sleep_ms)


def import_device_modules() -> tuple[ModuleType, ModuleType]:
  """(re)import display, icons and screens. if that throws, the previous
  modules are put back and the exception propagates"""
  for p in (str(PROJECT_DIR), str(FAKES_DIR)):
    if p in sys.path:
      sys.path.remove(p)
  # fakes first, so `import galactic` finds ours
  sys.path[0:0] = [str(FAKES_DIR), str(PROJECT_DIR)]

  old = {name: sys.modules.pop(name) for name in DEVICE_MODULES if name in sys.modules}
  try:
    import display
    import screens
  except BaseException:
    for name in DEVICE_MODULES:
      sys.modules.pop(name, None)
    sys.modules.update(old)
    raise
  return display, screens


def screen_names(screens: ModuleType) -> list[str]:
  return [fn.__name__.removeprefix("draw_") for fn in screens.SCREENS]


def screen_order(screens: ModuleType, chosen: str) -> list[str]:
  """the carousel's order, plus the chosen screen at the end if it isn't in it"""
  order = screen_names(screens)
  return order if chosen in order else order + [chosen]


def draw_function(screens: ModuleType, name: str) -> object:
  fn = getattr(screens, f"draw_{name}", None)
  if fn is None:
    available = sorted(n.removeprefix("draw_") for n in dir(screens) if n.startswith("draw_"))
    raise LookupError(f"no draw_{name} in screens.py (screens: {', '.join(available)})")
  return fn


def draw_frame(display: ModuleType, screens: ModuleType, name: str, info: dict, t: float) -> list[int]:
  """one frame of a screen at rest, where the carousel leaves it after sliding in.
  no slide, screen timer or status indicators"""
  graphics = display.graphics
  graphics.remove_clip()
  graphics.set_font("bitmap6")
  graphics.set_pen(display.BLACK)
  graphics.clear()
  draw_function(screens, name)(info, 1, t)  # type: ignore[operator]
  return list(graphics.framebuffer)


def led_colour(pen: int, brightness: int) -> tuple[int, int, int] | None:
  """what an LED looks like on a monitor, or None if it's off.
  brightness is applied like galactic_unicorn.cpp (multiply, >>8), then
  normalised so a full pen is full white whatever the brightness, then lifted"""
  full = (255 * brightness) >> 8
  if full == 0:
    return None
  out = []
  for shift in (16, 8, 0):
    v = (((pen >> shift) & 0xff) * brightness) >> 8
    out.append(round(255 * (v / full) ** LED_LIFT))
  return None if out == [0, 0, 0] else (out[0], out[1], out[2])


def render(surface: "pygame.Surface", framebuffer: list[int], brightness: int, led: bool) -> None:
  import pygame
  surface.fill((0, 0, 0))
  for y in range(HEIGHT):
    for x in range(WIDTH):
      pen = framebuffer[y * WIDTH + x]
      if led:
        colour = led_colour(pen, brightness)
        centre = (x * PIXEL_SIZE + PIXEL_SIZE // 2, y * PIXEL_SIZE + PIXEL_SIZE // 2)
        pygame.draw.circle(surface, colour or UNLIT_LED, centre, PIXEL_SIZE * 0.4)
      else:
        surface.fill(((pen >> 16) & 0xff, (pen >> 8) & 0xff, pen & 0xff),
                     (x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE))


def init_pygame(headless: bool) -> None:
  os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
  if headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
  import pygame
  pygame.init()


def choose_fixture(args: argparse.Namespace) -> fixtures.Fixture:
  path = fixtures.fetch_and_save() if args.live else fixtures.find(args.fixture)
  if path is None:
    print(f"no fixtures in {fixtures.FIXTURES_DIR}, fetching one")
    path = fixtures.fetch_and_save()
  return fixtures.load(path)


def save_png(args: argparse.Namespace, fixture: fixtures.Fixture, clock: SimClock) -> None:
  init_pygame(headless=True)
  import pygame
  display, screens = import_device_modules()
  name = args.screen or screen_names(screens)[0]
  clock.elapsed = args.t
  framebuffer = draw_frame(display, screens, name, fixture.info, args.t)
  surface = pygame.Surface((WIDTH * PIXEL_SIZE, HEIGHT * PIXEL_SIZE))
  render(surface, framebuffer, display.gu.brightness, led=not args.raw)
  pygame.image.save(surface, args.png)
  print(f"saved {name} at t={args.t:.2f}s ({fixture.path.name}) to {args.png}")


def mtimes(paths: list[Path]) -> list[float]:
  return [p.stat().st_mtime if p.exists() else 0.0 for p in paths]


def run_window(args: argparse.Namespace, fixture: fixtures.Fixture, clock: SimClock) -> None:
  init_pygame(headless=False)
  import pygame

  watched = [PROJECT_DIR / f"{m}.py" for m in DEVICE_MODULES] + [fixture.path]
  last_mtimes = mtimes(watched)
  display, screens = import_device_modules()
  name: str = args.screen or screen_names(screens)[0]
  draw_function(screens, name)  # fail now on a bad --screen
  info = fixture.info

  window = pygame.display.set_mode((WIDTH * PIXEL_SIZE, HEIGHT * PIXEL_SIZE))
  led = not args.raw
  paused = False
  t = 0.0
  framebuffer = [0] * (WIDTH * HEIGHT)
  # after an exception, stop drawing (keeping the last good frame) until a file changes
  broken = False
  last_watch = time.perf_counter()
  last_frame = time.perf_counter()
  pygame_clock = pygame.time.Clock()

  def step(dt: float) -> None:
    nonlocal t
    t = max(0.0, t + dt)
    clock.elapsed = max(0.0, clock.elapsed + dt)

  print("space pause, ,/. step frame, r restart, l LED/raw, left/right change screen, q quit")
  while True:
    now = time.perf_counter()
    dt = now - last_frame
    last_frame = now
    order = screen_order(screens, name)
    index = order.index(name)

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        return
      if event.type != pygame.KEYDOWN:
        continue
      if event.key in (pygame.K_q, pygame.K_ESCAPE):
        return
      elif event.key == pygame.K_SPACE:
        paused = not paused
      elif event.key == pygame.K_PERIOD and paused:
        step(FRAME_S)
      elif event.key == pygame.K_COMMA and paused:
        step(-FRAME_S)
      elif event.key == pygame.K_r:
        t = 0.0
      elif event.key == pygame.K_l:
        led = not led
      elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
        index = (index + (1 if event.key == pygame.K_RIGHT else -1)) % len(order)
        name = order[index]
        t = 0.0
        broken = False

    if now - last_watch >= WATCH_INTERVAL_S:
      last_watch = now
      current_mtimes = mtimes(watched)
      if current_mtimes != last_mtimes:
        fixture_changed = current_mtimes[-1] != last_mtimes[-1]
        last_mtimes = current_mtimes
        try:
          if fixture_changed:
            new_fixture = fixtures.load(fixture.path)
            if new_fixture.at != fixture.at and args.at is None:
              clock.reset(new_fixture.at)
            fixture = new_fixture
            info = fixture.info
          display, screens = import_device_modules()
          draw_function(screens, name)
          print(f"reloaded at {datetime.datetime.now():%H:%M:%S}")
          broken = False
          t = 0.0
        except Exception:
          traceback.print_exc()
          broken = True

    if not broken:
      if not paused:
        step(dt)
      try:
        framebuffer = draw_frame(display, screens, name, info, t)
      except Exception:
        traceback.print_exc()
        print("drawing failed, showing the last good frame until a file changes")
        broken = True

    render(window, framebuffer, display.gu.brightness, led)
    shown = f"{datetime.datetime.fromtimestamp(clock.epoch()):%H:%M:%S}"
    state = " broken" if broken else " paused" if paused else ""
    pygame.display.set_caption(f"{name}  t={t:5.2f}s  {shown}  {'LED' if led else 'raw'}{state}  [{fixture.path.stem}]")
    pygame.display.flip()
    pygame_clock.tick(FPS)


def add_arguments(parser: argparse.ArgumentParser) -> None:
  parser.add_argument("--screen", help="screen to show, eg trains for draw_trains. default: the first in SCREENS")
  parser.add_argument("--fixture", help="sim/fixtures/NAME.json. default: the most recently modified one")
  parser.add_argument("--live", action="store_true", help="fetch info now, save it as a fixture and show it")
  parser.add_argument("--at", help="HH:MM the clock starts at. default: the fixture's")
  parser.add_argument("--png", help="render one frame to this file and exit, no window")
  parser.add_argument("--t", type=float, default=3.0, help="with --png: the screen's time_on_screen, in seconds")
  parser.add_argument("--raw", action="store_true", help="show the framebuffer colours rather than LEDs")


def run(args: argparse.Namespace) -> None:
  try:
    fixture = choose_fixture(args)
    if args.at is not None:
      fixtures.parse_at(args.at)
  except Exception as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)
  clock = SimClock(args.at or fixture.at)
  install_time_shim(clock)
  if args.png:
    save_png(args, fixture, clock)
  else:
    run_window(args, fixture, clock)
