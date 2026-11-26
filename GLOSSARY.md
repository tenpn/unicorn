# unicorn

A Galactic Unicorn LED matrix that shows local weather and train departures, cycling through them one screen at a time.

## Language

**Screen**:
One full-display view of a single topic, such as trains, weather or the timeline. Only one screen is shown at a time, apart from the slide between two.
_Avoid_: Row, panel, page, card

**Line**:
One line of text inside a screen. A screen fits two of them, top and bottom.
_Avoid_: Row

**Carousel**:
The repeating cycle of screens, each one sliding in and staying for a while before the next.
_Avoid_: Rotation, rows

**Info**:
The bundle of weather and train data fetched from the local-info API, which the screens draw from.
_Avoid_: Data, response, payload

**Condition**:
The current weather in words, such as "Overcast" or "Patchy light drizzle", which the weather screen shows as an icon.
_Avoid_: Forecast, summary

**Temperature scale**:
Three columns on the weather screen against a scale that fits today: it runs from 0° (or -5° if it's freezing) up to at least 10°. The ruler marks every 5° (every 10° on wide scales), with freezing point in icy blue. The range bar beside it fills today's low to high, and the now dot beside that marks the current temperature.
_Avoid_: Thermometer, gauge

**Simulator**:
A window on the Mac that draws screens the way the display would, so they can be iterated on without the board.
_Avoid_: Emulator, preview

## Status indicators

**Connection status**:
The left edge of the display, showing wifi state in the first column and fetch attempts in the second.
_Avoid_: Status column

**Heap status**:
Single pixels on the right edge, showing how much memory is used and how fragmented it is.

**Screen timer**:
The bar on the right edge that shrinks as the current screen's time runs out.
_Avoid_: Progress bar
