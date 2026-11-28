"""Fake micropython module for the simulator. The code emitters are left as
plain Python, which is fine for anything that doesn't use viper's pointer
built-ins. Functions that do (like display._reverse_pixels) mustn't be called."""

# typing isn't on the board, but this file only runs on the Mac
from typing import Any, Callable


def viper(f: Callable[..., Any]) -> Callable[..., Any]:
  return f


def native(f: Callable[..., Any]) -> Callable[..., Any]:
  return f
