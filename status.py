from galactic import GalacticUnicorn
from display import graphics, gu, BLACK, YELLOW, RED, GREEN, ORANGE, DARKER_GREY, DIM_BLUE
from lifecycle import feed_watchdog
import time
import gc

# connection status: column 0 is wifi, column 1 is fetch attempts.
# the fetch column is split into MAX_FETCH_FAILURES sections, one per attempt
FETCH_STATUS_X = 1
MAX_FETCH_FAILURES = 3

def status_handler(mode: str, status: bool | None, ip: str) -> None:
  # reports wifi connection status. called ~1/sec while connecting
  feed_watchdog()
  print(mode, status, ip)
  print('Connecting to wifi...')

  graphics.clear()

  graphics.set_pen(YELLOW)
  # flash while connecting
  for i in range(GalacticUnicorn.HEIGHT):
    graphics.line(0,0,0,i)
    gu.update(graphics)
    time.sleep(0.02)

  graphics.set_pen(BLACK)
  graphics.clear()
  gu.update(graphics)

  if status is not None:
    if status:
      print('Wifi connection successful!')
      graphics.set_pen(GREEN)
      graphics.rectangle(0, 0, 1, GalacticUnicorn.HEIGHT)
      gu.update(graphics)
    else:
      print('Wifi connection failed!')
      graphics.set_pen(RED)
      graphics.line(0,0,0,GalacticUnicorn.HEIGHT)
      gu.update(graphics)

def draw_fetch_status(failures: int, pen: int) -> None:
  """show fetch progress in the status column, a third of its height per attempt.
  earlier failed attempts stay orange, the current attempt uses pen.
  also redraws the wifi column green, as we only fetch once connected"""
  graphics.set_pen(GREEN)
  graphics.rectangle(0, 0, 1, GalacticUnicorn.HEIGHT)
  graphics.set_pen(BLACK)
  graphics.rectangle(FETCH_STATUS_X, 0, 1, GalacticUnicorn.HEIGHT)
  for attempt in range(failures+1):
    top = attempt * GalacticUnicorn.HEIGHT // MAX_FETCH_FAILURES
    bottom = (attempt+1) * GalacticUnicorn.HEIGHT // MAX_FETCH_FAILURES
    graphics.set_pen(pen if attempt == failures else ORANGE)
    graphics.rectangle(FETCH_STATUS_X, top, 1, bottom-top)
  gu.update(graphics)

def mem_used_y(free: int, used: int) -> int:
  """y for the memory pixel: bottom row is 0% of the heap used, top row is 100%"""
  used_frac = used / (free + used)
  return round((GalacticUnicorn.HEIGHT - 1) * (1 - used_frac))

def largest_free_block() -> int:
  """biggest single allocation the heap can satisfy right now, in bytes.
  micropython.mem_info() only prints this, so binary search with real
  allocations instead. ~18 tries, each failure costs a gc, so call sparingly"""
  gc.collect()
  lo = 0
  hi = gc.mem_free()
  while lo < hi:
    mid = (lo + hi + 1) // 2
    try:
      block = bytearray(mid)
      del block
      lo = mid
    except MemoryError:
      hi = mid - 1
  gc.collect()
  return lo

def frag_y(largest: int, boot_largest: int) -> int:
  """y for the fragmentation pixel: bottom row when the largest free block is
  as big as at boot, top row when it has shrunk to nothing. relative to boot
  because even a fresh heap's largest block is only ~1/3 of free memory"""
  frac = min(1, largest / boot_largest) if boot_largest > 0 else 0
  return round((GalacticUnicorn.HEIGHT - 1) * frac)

def draw_heap_status(mem_y: int, heap_frag_y: int) -> None:
  """heap status pixels in the right column. draw after the screen timer so
  they show over it"""
  # memory used
  graphics.set_pen(DARKER_GREY)
  graphics.pixel(GalacticUnicorn.WIDTH-1, mem_y)
  # fragmentation, measured after each fetch. drawn last, so it wins if
  # it lands on the same pixel as memory used
  graphics.set_pen(DIM_BLUE)
  graphics.pixel(GalacticUnicorn.WIDTH-1, heap_frag_y)
