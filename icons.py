# typing isn't on the board; this block is only seen by type checkers
TYPE_CHECKING = False
if TYPE_CHECKING:
  from typing import Callable
  from picographics import PicoGraphics

UP_ARROW = [
  "   #   ",
  "  ###  ",
  " ##### ",
  "   #   ",
  "   #   ",
]
DOWN_ARROW = list(reversed(UP_ARROW))
# 7 wide, the width of "99" in DIGITS, so the rain chance can sit centred under it
RAIN = [
  "#   #  ",
  "# #   #",
  "  # # #",
  "#   #  ",
  "# #    ",
  "  #   #",
  "#   # #",
  "  #    ",
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
# weather Condition icons, 9x11 to fill the screen's height. see CONDITION_ICONS in screens.py for their pens
SUN = [
  "         ",
  "    #    ",
  " #     # ",
  "   ###   ",
  "  #####  ",
  "# ##### #",
  "  #####  ",
  "   ###   ",
  " #     # ",
  "    #    ",
  "         ",
]
MOON = [
  "         ",
  "    #### ",
  "   ###   ",
  "  ###    ",
  "  ###    ",
  "  ###    ",
  "  ###    ",
  "  ###    ",
  "   ###   ",
  "    #### ",
  "         ",
]
CLOUD = [
  "         ",
  "         ",
  "    ###  ",
  "   ##### ",
  " ########",
  "#########",
  "#########",
  "#########",
  " ####### ",
  "         ",
  "         ",
]
PART_CLOUD = [
  "         ",
  "  ...    ",
  " .....   ",
  ".......  ",
  "....###  ",
  "...##### ",
  " ########",
  "#########",
  "#########",
  "#########",
  " ####### ",
]
FOG = [
  "         ",
  "#######  ",
  "         ",
  "  #######",
  "         ",
  "#######  ",
  "         ",
  "  #######",
  "         ",
  "#######  ",
  "         ",
]
RAIN_CLOUD = [
  "    ###  ",
  "   ##### ",
  " ########",
  "#########",
  " ####### ",
  "         ",
  " .   .   ",
  " . .   . ",
  "   . . . ",
  " .   .   ",
  " . .   . ",
]
SNOW_CLOUD = [
  "    ###  ",
  "   ##### ",
  " ########",
  "#########",
  " ####### ",
  " .     . ",
  "...   ...",
  " .     . ",
  "    .    ",
  "   ...   ",
  "    .    ",
]
THUNDER_CLOUD = [
  "    ###  ",
  "   ##### ",
  " ########",
  "#########",
  " ####### ",
  "    ..   ",
  "   ..    ",
  "  ....   ",
  "   ..    ",
  "  ..     ",
  "  .      ",
]
# pixel coords of the train smoke
# to animate it 
TRAIN_SMOKES = [
  (1,0), (2,0), (3,0), (4,0), (5,0),
  (5,1), (6,1), (7,1),
  (7,0), (8,0)
]
TRAIN_WHEELS = [
  (12,9), (13,9), 
  (13,8), (12,8),   
]

# 3x5 digits and a minus sign, for numbers that have to fit tighter than bitmap6 allows
DIGITS = {
  "0": [
    "###",
    "# #",
    "# #",
    "# #",
    "###",
  ],
  "1": [
    " # ",
    "## ",
    " # ",
    " # ",
    "###",
  ],
  "2": [
    "###",
    "  #",
    "###",
    "#  ",
    "###",
  ],
  "3": [
    "###",
    "  #",
    " ##",
    "  #",
    "###",
  ],
  "4": [
    "# #",
    "# #",
    "###",
    "  #",
    "  #",
  ],
  "5": [
    "###",
    "#  ",
    "###",
    "  #",
    "###",
  ],
  "6": [
    "###",
    "#  ",
    "###",
    "# #",
    "###",
  ],
  "7": [
    "###",
    "  #",
    "  #",
    " # ",
    " # ",
  ],
  "8": [
    "###",
    "# #",
    "###",
    "# #",
    "###",
  ],
  "9": [
    "###",
    "# #",
    "###",
    "  #",
    "###",
  ],
  "-": [
    "   ",
    "   ",
    "## ",
    "   ",
    "   ",
  ],
}
DIGIT_WIDTH = 3

def digit_advance(c: str) -> int:
  """columns from the start of c to the start of the next digit: a blank column between them,
  except after a minus, which sits right up against the digit to save a column"""
  return DIGIT_WIDTH if c == "-" else DIGIT_WIDTH + 1

def digits_width(digits: str) -> int:
  """width of digits drawn by draw_digits, from the first lit column to the last"""
  return DIGIT_WIDTH + sum(digit_advance(c) for c in digits[:-1])

def draw_digits(graphics: PicoGraphics, digits: str, origin_x: int, origin_y: int, pen: int) -> None:
  """draws a string of 0-9 and - in the 3x5 DIGITS, spaced by digit_advance"""
  for c in digits:
    draw(graphics, DIGITS[c], origin_x, origin_y, pen)
    origin_x += digit_advance(c)

def draw(graphics: PicoGraphics, icon: list[str], origin_x: int, origin_y: int, pen: int, second_pen: Callable[[int, int], int | None] | None = None, x_scroll: int = 0, y_scroll: int = 0, rows: int | None = None) -> None:
  """rows crops the icon to its top rows, after scrolling"""
  last_pen = pen
  graphics.set_pen(pen)
  
  for y in range(len(icon) if rows is None else min(rows, len(icon))):
    py = (y+y_scroll)%len(icon)
    
    for x in range(len(icon[py])):
      px = (x + x_scroll)%len(icon[py])
      
      current_pen = pen if icon[py][px] == '#' \
        else second_pen(px,py) if icon[py][px] == '.' and second_pen is not None \
        else None
      if current_pen is not None:
        if current_pen != last_pen:
          graphics.set_pen(current_pen)
          last_pen = current_pen          
          
        # no offset here
        graphics.pixel(origin_x + x, origin_y + y)
