"""Dev helpers for the Galactic Unicorn, built on mpremote.

usage: python tools.py {upload,run,dump} [--port PORT]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

import serial  # pyserial, installed alongside mpremote
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

PROJECT_DIR = Path(__file__).resolve().parent
SECRETS_FILE = "proj_secrets.py"
CRASH_LOG = "crash.txt"  # keep in sync with CRASH_LOG in main.py
RPI_VID = 0x2E8A  # Raspberry Pi USB vendor id, used by RP2040 MicroPython
NO_CRASH_LOG_MARKER = "__tools_no_crash_log__"


def fail(msg: str) -> NoReturn:
  print(f"error: {msg}", file=sys.stderr)
  sys.exit(1)


def board_ports() -> list[ListPortInfo]:
  return [
    p for p in list_ports.comports()
    if p.vid == RPI_VID or "micropython" in (p.manufacturer or "").lower()
  ]


def find_port() -> str:
  ports = list_ports.comports()
  candidates = board_ports()
  if len(candidates) == 1:
    return candidates[0].device
  seen = "\n".join(f"  {p.device}  {p.description}" for p in ports) or "  (none)"
  if not candidates:
    fail(
      "couldn't find the unicorn. is it plugged in, and is Thonny closed?\n"
      f"serial ports seen:\n{seen}"
    )
  fail(
    "found more than one possible board, pick one with --port:\n"
    + "\n".join(f"  {p.device}  {p.description}" for p in candidates)
  )


def mpremote(port: str, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
  cmd = [sys.executable, "-m", "mpremote", "connect", port, *args]
  try:
    return subprocess.run(
      cmd, cwd=PROJECT_DIR, check=True, text=True,
      stdout=subprocess.PIPE if capture else None,
    )
  except subprocess.CalledProcessError as e:
    if capture and e.stdout:
      print(e.stdout, end="")
    fail(f"mpremote exited with code {e.returncode}")
  except KeyboardInterrupt:
    # mpremote has already passed ctrl-c on to the board
    sys.exit(130)


# what mpremote's traceback says when the usb port vanishes mid-read
# (macOS ENXIO, linux EIO, or pyserial's own wording)
DISCONNECT_MARKERS = (
  "Device not configured",
  "Input/output error",
  "device reports readiness to read but returned no data",
  "device disconnected",
)


def mpremote_run_until_disconnect(port: str, *args: str) -> None:
  """run mpremote streaming stdout. returns normally only if the board went away"""
  cmd = [sys.executable, "-m", "mpremote", "connect", port, *args]
  try:
    result = subprocess.run(cmd, cwd=PROJECT_DIR, text=True, stderr=subprocess.PIPE)
  except KeyboardInterrupt:
    # mpremote has already passed ctrl-c on to the board
    sys.exit(130)
  if result.returncode == 0:
    sys.exit(0)
  if any(m in result.stderr for m in DISCONNECT_MARKERS):
    return
  print(result.stderr, end="", file=sys.stderr)
  fail(f"mpremote exited with code {result.returncode}")


def wait_for_port(port: str, explicit: bool) -> str:
  """wait for the board to show up again after a reset"""
  while True:
    if explicit:
      if any(p.device == port for p in list_ports.comports()):
        return port
    else:
      candidates = board_ports()
      # prefer the same port name, which macOS and linux usually keep
      for p in candidates:
        if p.device == port:
          return port
      if len(candidates) == 1:
        return candidates[0].device
    time.sleep(0.25)


def follow(port: str, explicit: bool) -> None:
  """print the board's output without interrupting it, surviving resets.
  ctrl-c stops the program on the board, same as during `mpremote run`"""
  while True:
    print("\n[tools] board went away (probably reset), waiting for it to come back...", flush=True)
    try:
      port = wait_for_port(port, explicit)
    except KeyboardInterrupt:
      sys.exit(130)
    try:
      with serial.Serial(port, 115200, timeout=0.5) as s:
        print(f"[tools] reattached to {port}, following output (ctrl-c to stop)", flush=True)
        try:
          while True:
            data = s.read(s.in_waiting or 1)
            if data:
              sys.stdout.buffer.write(data)
              sys.stdout.buffer.flush()
        except KeyboardInterrupt:
          s.write(b"\x03")
          s.flush()
          sys.exit(130)
    except (serial.SerialException, OSError):
      # port vanished again, or appeared but wasn't ready to open yet
      time.sleep(0.5)


def upload_files() -> list[str]:
  if not (PROJECT_DIR / SECRETS_FILE).exists():
    fail(f"{SECRETS_FILE} is missing. copy {SECRETS_FILE}.example and fill it in")
  this_file = Path(__file__).resolve().name
  return sorted(p.name for p in PROJECT_DIR.glob("*.py") if p.name != this_file)


def upload_args() -> list[str]:
  files = upload_files()
  print(f"uploading: {', '.join(files)}")
  return ["cp", *files, ":"]


DELETE_CRASH_LOG = f"""
import os
try:
  os.remove({CRASH_LOG!r})
  print('deleted {CRASH_LOG}')
except OSError:
  pass
"""

DUMP_CRASH_LOG = f"""
try:
  f = open({CRASH_LOG!r})
except OSError:
  print({NO_CRASH_LOG_MARKER!r})
else:
  print(f.read(), end='')
  f.close()
"""


def cmd_upload(port: str, explicit: bool) -> None:
  mpremote(port, *upload_args())


def cmd_run(port: str, explicit: bool) -> None:
  # one connection: upload, clear the old crash log, then run main.py as
  # __main__ (the uploaded copy is identical) and stream its output.
  # if the board resets, keep following its output once it reboots into the
  # uploaded main.py. ctrl-c to stop.
  mpremote_run_until_disconnect(
    port,
    *upload_args(),
    "+", "exec", DELETE_CRASH_LOG,
    "+", "run", "main.py",
  )
  follow(port, explicit)


def cmd_dump(port: str, explicit: bool) -> None:
  # note: talking to the board means ctrl-c'ing whatever it's running, so
  # main.py stops. reset the board to start it again
  out = mpremote(port, "exec", DUMP_CRASH_LOG, capture=True).stdout
  if out.strip() == NO_CRASH_LOG_MARKER:
    fail(f"no {CRASH_LOG} on the board, so nothing has crashed since it was last cleared")
  if not out:
    print(f"{CRASH_LOG} exists but is empty")
    return
  print(out, end="" if out.endswith("\n") else "\n")


COMMANDS = {
  "upload": (cmd_upload, "copy the project's .py files (including secrets) to the board"),
  "run": (cmd_run, f"upload, delete {CRASH_LOG}, then run main.py and stream its output"),
  "dump": (cmd_dump, f"print {CRASH_LOG} from the board (stops main.py)"),
}


def main() -> None:
  parser = argparse.ArgumentParser(description="Galactic Unicorn dev tools")
  sub = parser.add_subparsers(dest="command", required=True)
  for name, (_, help_text) in COMMANDS.items():
    sub.add_parser(name, help=help_text)
  parser.add_argument("--port", help="serial port, if auto-detection picks wrong")
  args = parser.parse_args()

  port = args.port or find_port()
  COMMANDS[args.command][0](port, args.port is not None)


if __name__ == "__main__":
  main()
