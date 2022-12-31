UP_ARROW = [
  "   #   ",
  "  ###  ",
  " ##### ",
  "   #   ",
  "   #   ",
]
DOWN_ARROW = list(reversed(UP_ARROW))
TEMP = [
  "  ###  ",
  "  # #  ",
  "  #.#  ",
  "  #.#  ",
  "  #.#  ",
  "  #.#  ",
  " #...# ",
  " #...# ",
  "  ###  ",
]
WIND = [
  "#  ## ",
  " ##  #",
  "      ",
  "#  ## ",
  " ##  #",
]
HUMIDITY = [
  "# #. .",
  "# #  .",
  "### . ",
  "# #.  ",
  "# #. .",
]
RAIN = [
  "#   #",
  "# #  ",
  "  # #",
  "#   #",
  "# #  ",
]

def draw(graphics, icon, origin_x, origin_y, pen, second_pen=None):
  last_pen = pen
  graphics.set_pen(pen)
  for y in range(len(icon)):
    for x in range(len(icon[y])):
      current_pen = pen if icon[y][x] == '#' \
        else second_pen(x,y) if icon[y][x] == '.' \
        else None
      if current_pen is not None:
        if current_pen != last_pen:
          graphics.set_pen(current_pen)
          last_pen = current_pen          
        graphics.pixel(origin_x + x, origin_y + y)
