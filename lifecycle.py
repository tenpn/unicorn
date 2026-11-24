from galactic import GalacticUnicorn
from display import graphics, gu, RED
import machine
import time
import gc
import os
import sys

# unexpected exceptions get appended here, so we can see what killed it.
# capped so a boot loop doesn't wear out the flash
CRASH_LOG = "crash.txt"
CRASH_LOG_MAX_BYTES = 8*1024

# hardware watchdog resets the board if we hang or crash without feeding it
watchdog: machine.WDT | None = None

def start_watchdog(timeout_ms: int) -> None:
  global watchdog
  watchdog = machine.WDT(timeout=timeout_ms)

def watchdog_running() -> bool:
  return watchdog is not None

def feed_watchdog() -> None:
  if watchdog is not None:
    watchdog.feed()

def sleep_ms_fed(ms: int) -> None:
  """sleep without letting the watchdog fire"""
  end = time.ticks_add(time.ticks_ms(), ms)
  while time.ticks_diff(end, time.ticks_ms()) > 0:
    feed_watchdog()
    time.sleep_ms(100)

def log_crash(e: Exception) -> None:
  try:
    gc.collect()
    try:
      size = os.stat(CRASH_LOG)[6]
    except OSError:
      size = 0
    if size >= CRASH_LOG_MAX_BYTES:
      print("crash log full, not writing")
      return
    with open(CRASH_LOG, "a") as f:
      f.write(f"--- localtime {time.localtime()} uptime {time.ticks_ms()}ms mem {gc.mem_free()}\n")
      sys.print_exception(e, f)
  except Exception as log_e:
    print(f"couldn't write crash log: {log_e}")

def reset_after(ms: int, reason: str) -> None:
  print(f"resetting in {ms}ms: {reason}")
  try:
    graphics.set_pen(RED)
    graphics.line(0, 0, 0, GalacticUnicorn.HEIGHT)
    gu.update(graphics)
  except Exception:
    pass
  sleep_ms_fed(ms)
  # shutting the wifi chip down first may help it come back cleanly after reset
  try:
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)
  except Exception:
    pass
  # give usb a moment to send the print above before the port disappears
  time.sleep_ms(100)
  # if this hangs, the watchdog (no longer fed) will reset us anyway
  machine.reset()
