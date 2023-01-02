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
TRAIN = [
  " ..... ..      ",
  "#### ...  #####",
  " ##       #   #",
  " ##   # # #.   ",
  "###########.   ",
  "###############",
  "#########..####",
  "#########.##..#",
  "#.........#....",
  " .. .. ..  ....",
  " .. .. ..   .. ",  
]
# pixel coords of the train smoke
# to animate it 
TRAIN_SMOKES = [
  (1,0), (2,0), (3,0), (4,0), (5,0),
  (5,1), (6,1), (7,1),
  (7,0), (8,0)
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
