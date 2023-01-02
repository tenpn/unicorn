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
  "  #  ",
  "#   #",
  "  #  ",
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

def draw(graphics, icon, origin_x:int, origin_y:int, pen, second_pen=None, x_scroll:int=0, y_scroll:int=0) -> None:
  last_pen = pen
  graphics.set_pen(pen)
  
  for y in range(len(icon)):
    py = (y+y_scroll)%len(icon)
    
    for x in range(len(icon[py])):
      px = (x + x_scroll)%len(icon[py])
      
      current_pen = pen if icon[py][px] == '#' \
        else second_pen(px,py) if icon[py][px] == '.' \
        else None
      if current_pen is not None:
        if current_pen != last_pen:
          graphics.set_pen(current_pen)
          last_pen = current_pen          
          
        # no offset here
        graphics.pixel(origin_x + x, origin_y + y)
