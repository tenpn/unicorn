# unicorn

A Galactic Unicorn LED matrix that shows local weather and train departures, cycling through them one screen at a time.

## Language

**Screen**:
One full-display view of a single topic, such as trains, temperature, atmosphere or the timeline. Only one screen is shown at a time, apart from the slide between two.
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

## Status indicators

**Connection status**:
The left edge of the display, showing wifi state in the first column and fetch attempts in the second.
_Avoid_: Status column

**Heap status**:
Single pixels on the right edge, showing how much memory is used and how fragmented it is.

**Screen timer**:
The bar on the right edge that shrinks as the current screen's time runs out.
_Avoid_: Progress bar
