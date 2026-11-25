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
# weather Condition icons, 10x11 to fill the screen's height. see CONDITION_ICONS in screens.py for their pens
SUN = [
  "          ",
  "     #    ",
  "  #     # ",
  "    ###   ",
  "   #####  ",
  " # ##### #",
  "   #####  ",
  "    ###   ",
  "  #     # ",
  "     #    ",
  "          ",
]
MOON = [
  "    ####  ",
  "   ###    ",
  "  ###     ",
  "  ###     ",
  "  ###     ",
  "  ###     ",
  "  ###     ",
  "  ###     ",
  "  ###     ",
  "   ###    ",
  "    ####  ",
]
CLOUD = [
  "          ",
  "          ",
  "    ###   ",
  "   #####  ",
  " ######## ",
  "##########",
  "##########",
  "##########",
  " ######## ",
  "          ",
  "          ",
]
PART_CLOUD = [
  "          ",
  "  ...     ",
  " .....    ",
  ".......   ",
  "....###   ",
  "...#####  ",
  " ######## ",
  "##########",
  "##########",
  "##########",
  " ######## ",
]
FOG = [
  "          ",
  "########  ",
  "          ",
  "  ########",
  "          ",
  "########  ",
  "          ",
  "  ########",
  "          ",
  "########  ",
  "          ",
]
RAIN_CLOUD = [
  "    ###   ",
  "   #####  ",
  " ######## ",
  "##########",
  " ######## ",
  "          ",
  "  .  .  . ",
  " .  .  .  ",
  "          ",
  "  .  .  . ",
  " .  .  .  ",
]
SNOW_CLOUD = [
  "    ###   ",
  "   #####  ",
  " ######## ",
  "##########",
  " ######## ",
  "  .    .  ",
  " ...  ... ",
  "  .    .  ",
  "     .    ",
  "    ...   ",
  "     .    "
  ]
THUNDER_CLOUD = [
  "    ###   ",
  "   #####  ",
  " ######## ",
  "##########",
  " ######## ",
  "     ..   ",
  "    ..    ",
  "   ....   ",
  "    ..    ",
  "   ..     ",
  "   .      ",
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

def draw(graphics: PicoGraphics, icon: list[str], origin_x: int, origin_y: int, pen: int, second_pen: Callable[[int, int], int | None] | None = None, x_scroll: int = 0, y_scroll: int = 0) -> None:
  last_pen = pen
  graphics.set_pen(pen)
  
  for y in range(len(icon)):
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
