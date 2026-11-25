from galactic import GalacticUnicorn
from display import graphics, get_col_for_temp, \
  BLACK, GREY, LIGHT_GREY, YELLOW, LIGHT_PURPLE, PURPLE, RED, GREEN, ORANGE, LIGHT_BLUE, DARK_BLUE, BLUE
import icons
import math
import time

# how long a screen takes to slide in
SCREEN_SCROLL_DURATION = 0.5

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

def draw_weather(info: dict, y: int, time_on_screen: float) -> None:
  (icon, pen, dot_pen) = CONDITION_ICONS[condition_category(info["condition"])]
  icons.draw(graphics, icon, 0, y-1, pen,
             second_pen=None if dot_pen is None else lambda _x, _y: dot_pen)
  
  # whole degrees: decimals are too fine-grained, and they crowd out the rain chance
  col = 10
  temp_max = round(info["temp_max"])
  icons.draw(graphics, icons.UP_ARROW, col, y-1, GREY)
  graphics.set_pen(get_col_for_temp(temp_max))
  graphics.text(str(temp_max), col+7, y-2, scale=0.5)
  
  temp_min = round(info["temp_min"])
  icons.draw(graphics, icons.DOWN_ARROW, col, y+5, GREY)
  graphics.set_pen(get_col_for_temp(temp_min))
  graphics.text(str(temp_min), col+7, y+4, scale=0.5)
  
  # rain chance right-aligned, so wide temperatures can't push it off the edge
  rain_chance = info["rain_%_today"]
  rain_chance_str = str(rain_chance)
  rain_col = GalacticUnicorn.WIDTH - 1 - graphics.measure_text(rain_chance_str, scale=0.5)
  rain_animate = math.floor(time_on_screen*1.5)
  icons.draw(graphics, icons.RAIN, rain_col-7, y, LIGHT_BLUE, y_scroll=-rain_animate)
  
  rain_colour = PURPLE if rain_chance > 70 \
    else LIGHT_PURPLE if rain_chance > 30 \
    else GREEN if rain_chance == 0 \
    else LIGHT_GREY
  graphics.set_pen(rain_colour)
  graphics.text(rain_chance_str, rain_col, y+1, scale=0.5)
  
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
      
    temp = info["temp_feelslike_hours"][h_tick-1]
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

# the carousel shows these in order
SCREENS = [
  #draw_clock,
  draw_weather,
  draw_trains,
  draw_timeline,
]
