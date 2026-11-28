from galactic import GalacticUnicorn
from display import graphics, get_col_for_temp, \
  BLACK, DARK_GREY, DARK_GREY_MARK, DIM_ICY_BLUE, GREY, LIGHT_GREY, YELLOW, LIGHT_PURPLE, PURPLE, RED, GREEN, ORANGE, LIGHT_BLUE, DARK_BLUE, BLUE
import icons
import math
import time

# typing isn't on the board; this block is only seen by type checkers
TYPE_CHECKING = False
if TYPE_CHECKING:
  from typing import Callable
  # a screen draws itself from info at y, time_on_screen seconds after it started sliding in
  Screen = Callable[[dict, int, float], None]

# how long a screen takes to slide in
SCREEN_SCROLL_DURATION = 0.5

# Rain chance looks at least this many hours ahead, and always until this hour (9pm)
RAIN_CHANCE_MIN_HOURS = 3
RAIN_CHANCE_UNTIL_HOUR = 21

# Condition icon for each category, with its pen and the pen for its '.' pixels
CONDITION_ICONS = {
  "sun": (icons.SUN, YELLOW, None),
  "moon": (icons.MOON, LIGHT_GREY, None),
  "part_cloud": (icons.PART_CLOUD, GREY, YELLOW),
  "cloud": (icons.CLOUD, GREY, None),
  "fog": (icons.FOG, GREY, None),
  "rain": (icons.RAIN_CLOUD, GREY, LIGHT_BLUE),
  "snow": (icons.SNOW_CLOUD, GREY, LIGHT_GREY),
  "thunder": (icons.THUNDER_CLOUD, GREY, YELLOW),
}

# the first category with a keyword in the Condition wins, so order matters.
# Conditions are weatherapi.com's: https://www.weatherapi.com/docs/weather_conditions.json
CONDITION_KEYWORDS = [
  ("thunder", ["thunder"]),
  ("snow", ["snow", "sleet", "ice", "blizzard"]),
  ("rain", ["rain", "drizzle", "shower"]),
  ("fog", ["fog", "mist", "haze", "smoke", "smog", "dust", "sand"]),
  ("part_cloud", ["partly"]),
  ("cloud", ["cloud", "overcast"]),
  ("sun", ["sunny"]),
  ("moon", ["clear"]),
]

def condition_category(condition: str) -> str:
  condition = condition.strip().lower()
  for (category, keywords) in CONDITION_KEYWORDS:
    for keyword in keywords:
      if keyword in condition:
        return category
  return "cloud"

# the temperature scale's ends snap outwards to multiples of this
TEMP_SCALE_SNAP = 5
# the top of the scale is never below this, so mild days don't fill the whole column
TEMP_SCALE_MIN_TOP = 10
# ruler marks are every 5 degrees, or every 10 if that would put them closer than this many rows
TEMP_SCALE_MARK_MIN_ROWS = 2.5

def temp_scale_ends(low: float, high: float) -> tuple[int, int]:
  """(top, bottom) of the temperature scale: 0 or -5 if it's freezing, up to at least 10"""
  top = max(TEMP_SCALE_MIN_TOP, math.ceil(high / TEMP_SCALE_SNAP) * TEMP_SCALE_SNAP)
  bottom = 0 if low >= 0 else -TEMP_SCALE_SNAP
  return (top, bottom)

def temp_scale_row(temp: float, top: int, bottom: int) -> int:
  """row from the top of the temperature scale nearest to temp, clamped to the display"""
  step = (top - bottom) / (GalacticUnicorn.HEIGHT - 1)
  row = round((top - temp) / step)
  return max(0, min(GalacticUnicorn.HEIGHT - 1, row))

def temp_scale_pen(row: int, top: int, bottom: int) -> int:
  """pen for the temperature a scale row stands for, so everything on one row matches"""
  step = (top - bottom) / (GalacticUnicorn.HEIGHT - 1)
  return get_col_for_temp(top - row*step)

def draw_weather(info: dict, y: int, time_on_screen: float) -> None:
  (icon, pen, dot_pen) = CONDITION_ICONS[condition_category(info["condition"])]
  icons.draw(graphics, icon, 0, y-1, pen,
             second_pen=None if dot_pen is None else lambda _x, _y: dot_pen)
  
  # temperature scale: a ruler, today's range as a bar, and the current temp as a dot
  # the column after the 9-wide Condition icon and a gap
  col = 10
  temp_now = info["temp_now"]
  # the current temp counts too, so its dot is never clamped when it's outside the forecast
  (top, bottom) = temp_scale_ends(min(info["temp_min"], temp_now), max(info["temp_max"], temp_now))

  # ruler: a dim line, with lighter marks on the rows nearest each multiple of 5 (or 10, on
  # wide scales), and 0 in icy blue
  step = (top - bottom) / (GalacticUnicorn.HEIGHT - 1)
  mark_every = TEMP_SCALE_SNAP if TEMP_SCALE_SNAP / step >= TEMP_SCALE_MARK_MIN_ROWS else 2*TEMP_SCALE_SNAP
  graphics.set_pen(DARK_GREY)
  graphics.line(col, y-1, col, y-1+GalacticUnicorn.HEIGHT)
  # from the first multiple of mark_every, so a -5 bottom doesn't shift 10-degree marks to -5, 5, ...
  for t in range(math.ceil(bottom / mark_every) * mark_every, top+1, mark_every):
    graphics.set_pen(DIM_ICY_BLUE if t == 0 else DARK_GREY_MARK)
    graphics.pixel(col, y-1+temp_scale_row(t, top, bottom))

  row_max = temp_scale_row(info["temp_max"], top, bottom)
  row_min = temp_scale_row(info["temp_min"], top, bottom)
  for row in range(row_max, row_min+1):
    graphics.set_pen(temp_scale_pen(row, top, bottom))
    graphics.pixel(col+1, y-1+row)

  # the dot and the digits are coloured by their row too, not their exact temp, so they match
  # the bar beside them
  row_now = temp_scale_row(temp_now, top, bottom)
  graphics.set_pen(temp_scale_pen(row_now, top, bottom))
  graphics.pixel(col+2, y-1+row_now)

  # whole degrees: decimals are too fine-grained, and they crowd out the rain chance.
  # in the 3x5 digits, to leave the clock room
  temp_max = str(round(info["temp_max"]))
  icons.draw_digits(graphics, temp_max, col+4, y-1, temp_scale_pen(row_max, top, bottom))

  temp_min = str(round(info["temp_min"]))
  icons.draw_digits(graphics, temp_min, col+4, y+5, temp_scale_pen(row_min, top, bottom))

  # the rain chance goes on the bottom row, centred under the falling rain. both are as wide as
  # 99 and right-aligned against the Screen timer in the last column, so the clock always has
  # the same room on that side.
  # capped at 99 to save room for the clock: 100% and 99% mean the same when leaving the house
  rain_chance = min(99, get_rain_chance(info))
  rain_chance_str = str(rain_chance)
  rain_block_col = GalacticUnicorn.WIDTH - 1 - len(icons.RAIN[0])
  rain_col = rain_block_col + (len(icons.RAIN[0]) - icons.digits_width(rain_chance_str)) // 2
  rain_animate = math.floor(time_on_screen*1.5)
  # only the top 5 rows, above the % and a blank row
  icons.draw(graphics, icons.RAIN, rain_block_col, y-1, LIGHT_BLUE, y_scroll=-rain_animate, rows=5)

  rain_colour = PURPLE if rain_chance > 70 \
    else LIGHT_PURPLE if rain_chance > 30 \
    else GREEN if rain_chance == 0 \
    else LIGHT_GREY
  icons.draw_digits(graphics, rain_chance_str, rain_col, y+5, rain_colour)

  # vertically centred, between the temps and the rain
  temps_end = col+4 + max(icons.digits_width(temp_max), icons.digits_width(temp_min))
  draw_clock_row(temps_end, rain_block_col, y+1)

def draw_clock_row(left: int, right: int, text_y: int) -> None:
  """24h clock with no colon, a column between the hours and minutes, which are also told
  apart by their greys. centred between left (the first free column) and right (the first
  used one)"""
  (_,_,_,h,m,_,_,_) = time.localtime(time.time())
  hours = f"{h:02d}"
  minutes = f"{m:02d}"
  hours_width = graphics.measure_text(hours, scale=0.5)
  width = hours_width + 1 + graphics.measure_text(minutes, scale=0.5)
  x = left + (right - left - width) // 2
  graphics.set_pen(LIGHT_GREY)
  graphics.text(hours, x, text_y, scale=0.5)
  graphics.set_pen(GREY)
  graphics.text(minutes, x + hours_width + 1, text_y, scale=0.5)

def get_rain_chance(info: dict) -> int:
  """the highest hourly chance of rain from this hour until 9pm or 3 hours on,
  whichever is later. the hours are only today's, so it stops at midnight"""
  h = time.localtime(time.time())[3]
  end = min(24, max(h + RAIN_CHANCE_MIN_HOURS, RAIN_CHANCE_UNTIL_HOUR))
  return max(info["rain_%_hours"][h:end])

MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def draw_date(month: int, monthday: int, text_y: int) -> None:
  """month and day, right-aligned to the end of the hour ticks"""
  graphics.set_pen(LIGHT_GREY)
  monthday_str = str(monthday)
  monthday_str_width = graphics.measure_text(monthday_str, scale=0.5)
  graphics.text(monthday_str, 52-monthday_str_width, text_y, scale=0.5)
  
  graphics.set_pen(GREY)
  month_str = MONTHS[month-1]
  month_str_width = graphics.measure_text(month_str, scale=0.5)
  graphics.text(month_str, 52-monthday_str_width-month_str_width-1, text_y, scale=0.5)

def draw_hour_tick(h_tick: int, h: int, m: int, sunrise: float, sunset: float, y: int) -> None:
  """one hour of the 24 hour bar along the bottom: 2 pixels per hour, so 53 wide.
  h_tick is the hour we're building towards, eg 1 is midnight to 1am.
  the top pixel shows day or night, the bottom two fill in as the hour passes"""
  left_tick_x = h_tick*2
  right_tick_x = left_tick_x+1
  
  tick_colour = LIGHT_GREY if h_tick == 12 \
    else ORANGE if (math.floor(sunrise) == h_tick or math.floor(sunset) == h_tick) \
    else DARK_BLUE if (sunrise > h_tick or sunset < h_tick) \
    else YELLOW
  graphics.set_pen(tick_colour)
  graphics.pixel(right_tick_x, y+8)
  
  # set first tick after half past of prev hour
  graphics.set_pen(GREY)
  if h >= h_tick or (h == h_tick-1 and m >= 30):
    graphics.pixel(left_tick_x,y+9)
    
  # set second tick after the new hour
  if h >= h_tick:
    graphics.pixel(right_tick_x,y+9)

def draw_clock(info: dict, y: int, time_on_screen: float) -> None:
  graphics.set_font("bitmap8")
      
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time())
  graphics.set_pen(LIGHT_GREY)
  graphics.text(f"{h:02d}:{m:02d}", 2, y, scale=0.5)
  graphics.set_font("bitmap6")
  
  draw_date(month, monthday, y)
  
  for h_tick in range(1,25):
    draw_hour_tick(h_tick, h, m, info["sunrise"], info["sunset"], y)
      
def draw_timeline(info: dict, y: int, time_on_screen: float) -> None:
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time())
  
  graphics.set_pen(LIGHT_GREY)
  graphics.text(f"{h:02d}:{m:02d}", 1, y-2, scale=0.5)  
  
  draw_date(month, monthday, y-2)
  
  #MAX_RAIN = 1.5
  
  for h_tick in range(1,25):
    left_tick_x = h_tick*2
    right_tick_x = left_tick_x+1
    
    rain = info["rain_%_hours"][h_tick-1]
    #rain_height = math.ceil(8.0*min(1, rain))
    
    if rain > 20:
      graphics.set_pen(LIGHT_PURPLE if rain < 50 else PURPLE)
      graphics.pixel(left_tick_x, y+6)
      graphics.pixel(right_tick_x, y+6)
      #graphics.rectangle(left_tick_x, 7-rain_height+y, 1, rain_height)
      
    temp = info["temp_hours"][h_tick-1]
    graphics.set_pen(get_col_for_temp(temp))
    graphics.pixel(right_tick_x, y+7)
    graphics.pixel(left_tick_x, y+7)
    
    draw_hour_tick(h_tick, h, m, info["sunrise"], info["sunset"], y)
      
def draw_trains(info: dict, y: int, time_on_screen: float) -> None:
  # make the train animate by leaving some holes in the smoke
  missing_smoke = icons.TRAIN_SMOKES[math.floor(time_on_screen*3)%len(icons.TRAIN_SMOKES)]
  missing_wheel = icons.TRAIN_WHEELS[math.floor(time_on_screen*4)%len(icons.TRAIN_WHEELS)]
  icons.draw(graphics, icons.TRAIN, 0, y-1, BLUE, 
             second_pen=lambda px,py: BLACK if (px==missing_smoke[0] and py==missing_smoke[1]) \
                                                or (px==missing_wheel[0] and py==missing_wheel[1]) \
                                      else GREY)
  
  departures = info["departures_times"]
  
  if len(departures) == 0:
    graphics.set_pen(ORANGE)    
    graphics.text("No", 16, y-2, scale=0.5)  
    graphics.text("Trains", 16, y+4, scale=0.5)  
    return
  
  # how long until departures
  (_,_,_,h,m,_,_,_) = time.localtime(time.time())
  now_decimal = h + (m/60)
  until_departures = [math.floor(60*(departure_time - now_decimal))
                      for departure_time in departures]
  until_departures = [until_departure
                      for until_departure in until_departures
                      if until_departure >= 0]
  
  # scroll train departure times across two lines
  col = 16
  line_y = y-2
  for departure in until_departures:
    departure_col = RED if departure <= 10 \
      else ORANGE if departure <= 15 \
      else GREEN if departure <= 20 \
      else GREY
    departure_width = graphics.measure_text(str(departure), scale=0.5) + 2
    if col + departure_width >= GalacticUnicorn.WIDTH:
      if line_y < y: 
        line_y = y+4
        col = 16
      else:
        break
    graphics.set_pen(departure_col)    
    graphics.text(str(departure), col, line_y, scale=0.5)  
    col += departure_width

# the carousel shows these in order, skipping occasional screens on days they're not shown
SCREENS: list[Screen] = [
  #draw_clock,
  draw_weather,
  draw_trains,
  draw_timeline,
]

# occasional screens, each with a check of whether it's shown on the day in time.localtime()
OCCASIONAL_SCREENS: dict[Screen, Callable[[tuple], bool]] = {}

def todays_screens() -> list[Screen]:
  """SCREENS, minus occasional screens that aren't shown today"""
  now = time.localtime(time.time())
  return [screen for screen in SCREENS
          if screen not in OCCASIONAL_SCREENS or OCCASIONAL_SCREENS[screen](now)]
