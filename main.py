import machine

# "overclock" from the sample code???
# set before display.py creates the PicoGraphics framebuffer, as it used to be
machine.freq(200000000)

from galactic import GalacticUnicorn
from network_manager import NetworkManager
from display import gu, BLUE, RED, GREEN, ORANGE
from lifecycle import start_watchdog, watchdog_running, feed_watchdog, sleep_ms_fed, log_crash, reset_after
from status import status_handler, draw_fetch_status, largest_free_block, frag_y, MAX_FETCH_FAILURES
from carousel import show_screens
import proj_secrets
import time
import uasyncio
import requests
import ntp_time
import gc
import sys

REQUEST_INTERVAL = 9*60*1000
# retry sooner if a fetch fails, and reset after MAX_FETCH_FAILURES in a row
FETCH_RETRY_INTERVAL = 60*1000
# per socket operation, so must stay under WATCHDOG_TIMEOUT_MS
FETCH_TIMEOUT_S = 5
FETCH_STATUS_HOLD_MS = 500
# reset every hour regardless, to clear out heap fragmentation
RESET_INTERVAL = 60*60*1000

# hardware watchdog resets the board if we hang or crash without feeding it.
# rp2040 max timeout is ~8.3s. hold A at boot to disable it (eg for REPL work)
WATCHDOG_ENABLED = False
WATCHDOG_TIMEOUT_MS = 8000

# wait before resetting after a crash, so a boot loop doesn't hammer the server
CRASH_RESET_DELAY_MS = 30*1000
WIFI_FAIL_RESET_DELAY_MS = 10*1000

def set_time_with_retries(attempts: int = 3) -> None:
  for attempt in range(attempts):
    feed_watchdog()
    try:
      ntp_time.set_time()
      return
    except Exception as e:
      print(f"ntp failed ({attempt+1}/{attempts}): {e}")
      if attempt == attempts-1:
        raise
      sleep_ms_fed(2000)

def fetch_info(url: str) -> dict:
  gc.collect()
  print(f"starting request with mem {gc.mem_free()}")
  feed_watchdog()
  info_req = requests.get(url, timeout=FETCH_TIMEOUT_S)
  try:
    feed_watchdog()
    if info_req.status_code != 200:
      raise OSError(f"HTTP {info_req.status_code}")
    # can't stream into json.load: .raw is a python BodyStream, and json.load
    # needs a native stream. the body is only ~500 bytes anyway
    return info_req.json()
  finally:
    info_req.close()
    feed_watchdog()

def main() -> None:
  if WATCHDOG_ENABLED and not gu.is_pressed(GalacticUnicorn.SWITCH_A):
    start_watchdog(WATCHDOG_TIMEOUT_MS)
  else:
    print("watchdog and scheduled reset disabled")

  try:
    network_manager = NetworkManager(proj_secrets.WIFI_COUNTRY, status_handler=status_handler)
    uasyncio.get_event_loop().run_until_complete(network_manager.client(proj_secrets.WIFI_SSID, proj_secrets.WIFI_PSK))
  except Exception as e:
    print(f'Wifi connection failed! {e}')
    reset_after(WIFI_FAIL_RESET_DELAY_MS, "no wifi")

  set_time_with_retries()

  info_url = f"https://trainledazure.vercel.app/api/localinfo?code={proj_secrets.WEB_AUTH}&trainFrom={proj_secrets.TRAINS_FROM}&trainTo={proj_secrets.TRAINS_TO}&weather={proj_secrets.WEATHER_POSTCODE}"

  boot_time = time.ticks_ms()
  info: dict | None = None
  fetch_failures = 0
  boot_largest = largest_free_block()
  print(f"largest free block at boot {boot_largest}")

  while True:
    # unverified: it seemed to run out of memory after a few hours. a soak
    # test showed no fragmentation or leak, but reset after a while anyway.
    # not in dev mode (watchdog off), so long runs from tools.py aren't cut off
    if watchdog_running() and time.ticks_diff(time.ticks_ms(), boot_time) >= RESET_INTERVAL:
      reset_after(0, "scheduled reset")

    draw_fetch_status(fetch_failures, BLUE)
    try:
      # on failure, info keeps the previous data so we carry on showing it
      info = fetch_info(info_url)
    except Exception as e:
      fetch_failures += 1
      print(f"fetch failed ({fetch_failures}/{MAX_FETCH_FAILURES}): {e}")
      if fetch_failures >= MAX_FETCH_FAILURES:
        draw_fetch_status(fetch_failures-1, RED)
        log_crash(e)
        reset_after(FETCH_STATUS_HOLD_MS, "too many fetch failures")
      draw_fetch_status(fetch_failures-1, ORANGE)
      display_ms = FETCH_RETRY_INTERVAL
    else:
      draw_fetch_status(fetch_failures, GREEN)
      fetch_failures = 0
      display_ms = REQUEST_INTERVAL
    # show_screens clears the screen, so hold the status long enough to see
    sleep_ms_fed(FETCH_STATUS_HOLD_MS)

    # fragmentation mostly changes when a fetch swaps old info for new, so
    # measuring once per fetch is enough
    feed_watchdog()
    largest = largest_free_block()
    feed_watchdog()
    free = gc.mem_free()
    heap_frag_y = frag_y(largest, boot_largest)
    print(f"showing screens at {time.ticks_ms()} with mem {free} largest block {largest} frag_y {heap_frag_y}")

    if info is None:
      # nothing to show yet
      sleep_ms_fed(display_ms)
    else:
      show_screens(info, display_ms, heap_frag_y)

if __name__=="__main__":
  try:
    main()
  except Exception as e:
    # KeyboardInterrupt isn't an Exception, so ctrl-c still drops to the REPL
    # (but the watchdog will reset us shortly after unless it was disabled at boot)
    sys.print_exception(e)
    log_crash(e)
    reset_after(CRASH_RESET_DELAY_MS, "crash")
