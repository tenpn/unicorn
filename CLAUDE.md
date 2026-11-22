# unicorn

MicroPython app for a Pimoroni Galactic Unicorn (RP2040). It fetches weather and train info and scrolls it on the LED matrix. Everything except `tools.py` runs on the board. `tools.py` runs on the Mac in `.venv`.

## tools.py

Run it as `.venv/bin/python tools.py {upload,run,dump} [--port PORT]`. It's a wrapper around mpremote and finds the board by the Raspberry Pi USB vendor id.

- `upload` copies every project `.py` file to the board, except `tools.py`. That includes `proj_secrets.py`, which is gitignored; copy it from `proj_secrets.py.example`.
- `run` does three things over one connection: upload, delete `crash.txt`, then `run main.py` and stream its output.
  - If the board resets mid-run, mpremote dies with `OSError: [Errno 6] Device not configured`. `run` catches that, waits for the port to come back, then listens on the serial port directly (pyserial) without interrupting the program.
  - Ctrl-C stops the program on the board, both while mpremote is attached and while `run` is only listening.
- `dump` prints `crash.txt` from the board. It stops `main.py`, because mpremote has to send ctrl-C to get into the raw REPL. That can't be avoided. The user doesn't want `dump` to reset the board afterwards, so don't add that back.
- Uploading or running resets the board. Don't run any of these commands without asking the user first.

Related behaviour in `main.py`:

- When `WATCHDOG_ENABLED = False`, or A is held at boot, the watchdog is off and so is the hourly `RESET_INTERVAL` reset (dev mode).
- The watchdog and the hourly reset should both be on in the copy the board normally runs.
- Unexpected exceptions get appended to `crash.txt`. A scheduled reset isn't a crash, so it doesn't write anything there.

## Type annotations

Annotate every function's parameters and return type, and any variable whose type the checker can't work out, such as `x: T | None = None`. Lambdas and obvious constants don't need annotations.

- MicroPython parses annotations and then throws them away, so they cost nothing at runtime. `X | None` and `list[str]` are fine in device code.
- The board has no `typing` module. Never import it at the top level of device code. Import names that only the type checker needs (`Callable`, `Any`, `PicoGraphics`) like this:

  ```python
  # typing isn't on the board; this block is only seen by type checkers
  TYPE_CHECKING = False
  if TYPE_CHECKING:
    from typing import Callable
  ```

- PicoGraphics pens are `int`s. The JSON `info` from the API is a `dict`.
- `tools.py` is normal CPython, so use `typing` there as usual.

## Pylance

Pylance has no MicroPython stubs. These errors are expected and can be ignored:

- `Import "machine" / "galactic" / "picographics" / "network" / "uasyncio" / "rp2" could not be resolved`
- the warning `Import "requests" could not be resolved from source`. Pyright's bundled CPython `requests` stubs still type-check the calls, and the subset the board uses (`get`, `timeout`, `status_code`, `json()`, `close()`) has the same signatures.
- `"ticks_ms" / "ticks_diff" / "ticks_add" / "sleep_ms" is not a known attribute of module "time"`, plus `gc.mem_free`, `gc.mem_alloc` and `sys.print_exception`
- tuple-size mismatches on `time.localtime()` (MicroPython returns 8 fields, CPython returns 9)

`pyrightconfig.json` points Pylance and pyright at `.venv` (Python 3.15). If "Alternative syntax for unions requires Python 3.10 or newer" shows up, Pylance has lost that setting. Fix the config or reload the editor; don't change the annotations.

To type-check every file, run `.venv/bin/pyright` (it's in `requirements.txt`). Pylance only checks files that are open. Every error should be one of the expected ones above. Treat anything else as a real problem.

## Style

`main.py`, `icons.py` and `tools.py` use 2-space indentation. `network_manager.py` and `ntp_time.py` use 4 (they came from sample code). Match the file you're editing.
