from galactic import GalacticUnicorn
from display import graphics, get_col_for_temp, lerp, ease_in_out, TEMPERATURE_COLOURS, \
  BLACK, GREY, LIGHT_GREY, YELLOW, LIGHT_PURPLE, PURPLE, RED, GREEN, ORANGE, LIGHT_BLUE, DARK_BLUE, BLUE
import icons
import math
import time

# how long a screen takes to slide in. text waits for this before scrolling
SCREEN_SCROLL_DURATION = 0.5
TEXT_SCROLL_SPEED = 5

def get_thermometer_col_from_y(icon_y: int, temp: float) -> int:
  temp_index = min(len(TEMPERATURE_COLOURS), 7-icon_y)
  (max_temp, temp_pen) = TEMPERATURE_COLOURS[temp_index]
  min_temp = -99 if temp_index == 0 else TEMPERATURE_COLOURS[temp_index-1][0]
  return temp_pen if temp >= max_temp or (temp > min_temp and temp <= max_temp) else BLACK  
  
def scroll_text(text: str, left: int, top: int, width: int, height: int, time: float) -> None:
  """will clip text to box. eases in/out, uses TEXT_SCROLL_SPEED
  """
  graphics.set_clip(left, top, width, height)
  max_scroll = (graphics.measure_text(text, scale=0.5)) - width
  if max_scroll > 0:
    time -= SCREEN_SCROLL_DURATION # don't start early 
    scroll_duration = max_scroll / TEXT_SCROLL_SPEED
    scroll_t = ease_in_out((time % scroll_duration) / scroll_duration)
    # back and forth
    if math.floor(time/scroll_duration)%2 == 1: 
      scroll_t = 1 - scroll_t      
    # with a touch of padding
    scroll_offset = math.ceil(lerp(1, -max_scroll-1, scroll_t))
  else:
    scroll_offset = 0
  
  graphics.text(text, left + scroll_offset, top, scale=0.5)
  graphics.remove_clip()

def draw_temp(info: dict, y: int, time_on_screen: float) -> None:
  temp = info["temp_now"]
  feels_like = info["temp_feelslike_now"]
  
  col = 0
  icons.draw(graphics, icons.TEMP, col, y, GREY, 
             second_pen=lambda _, sec_y: get_thermometer_col_from_y(sec_y, temp))
  col += 7
  
  graphics.set_pen(get_col_for_temp(temp))
  graphics.text(str(temp), col, y-2, scale=0.5)
  graphics.set_pen(get_col_for_temp(feels_like))
  feels_like_str = f"({feels_like})"
  graphics.text(feels_like_str, col, y+4, scale=0.5)
  col += max(graphics.measure_text(str(temp), scale=0.5), graphics.measure_text(feels_like_str, scale=0.5))  
  if col < GalacticUnicorn.WIDTH*0.5:
    col = math.floor(GalacticUnicorn.WIDTH*0.5)
  
  temp_max = info["temp_max"]
  icons.draw(graphics, icons.UP_ARROW, col, y-1, GREY)
  graphics.set_pen(get_col_for_temp(temp_max))
  graphics.text(str(temp_max), col+7, y-2, scale=0.5)
  
  temp_min = info["temp_min"]
  icons.draw(graphics, icons.DOWN_ARROW, col, y+5, GREY)
  graphics.set_pen(get_col_for_temp(temp_min))
  graphics.text(str(temp_min), col+7, y+4, scale=0.5)
  
def draw_atmosphere(info: dict, y: int, time_on_screen: float) -> None:
  wind = info["wind_now"]
  humidity = info["humidity_now"]
  rain_chance = info["rain_%_today"]
  condition = info["condition"] 
  
  wind_animate = math.floor(time_on_screen*1.7)
  rain_animate = math.floor(time_on_screen*1.5)
  
  col = 1
  icons.draw(graphics, icons.WIND, col, y-1, GREY, x_scroll=-wind_animate)
  icons.draw(graphics, icons.RAIN, col, y+5, LIGHT_BLUE, y_scroll=-rain_animate)

  col += 7
  
  wind_colour = RED if wind > 20 \
    else YELLOW if wind > 10 \
    else GREEN if wind < 3 \
    else LIGHT_GREY
  graphics.set_pen(wind_colour)
  graphics.text(str(wind), col, y-2, scale=0.5)
  
  rain_colour = PURPLE if rain_chance > 70 \
    else LIGHT_PURPLE if rain_chance > 30 \
    else GREEN if rain_chance == 0 \
    else LIGHT_GREY
  graphics.set_pen(rain_colour)
  graphics.text(str(rain_chance), col, y+4, scale=0.5)
  
  col += max(graphics.measure_text(str(wind), scale=0.5), graphics.measure_text(str(rain_chance), scale=0.5))  
  if col < GalacticUnicorn.WIDTH*0.5:
    col = math.floor(GalacticUnicorn.WIDTH*0.5)
    
  graphics.set_pen(LIGHT_GREY)  
  scroll_text(condition, col, y+4, GalacticUnicorn.WIDTH-col-1, math.ceil(GalacticUnicorn.HEIGHT*0.5), time_on_screen)
  
  icons.draw(graphics, icons.HUMIDITY, col, y-1, LIGHT_BLUE, second_pen=lambda _x,_y: GREY)
  
  col += 7
  
  graphics.set_pen(LIGHT_GREY)
  graphics.text(str(humidity), col, y-2, scale=0.5)
  
def decimal_time_from_time_str(time_str: str) -> float:
  """easier to do maths with decimal time!

  Args:
      time_str (str): "HH:MM AM"/"HH:MM PM"

  Returns:
      float: 24hour.fraction-through-hour
  """
  h12 = int(time_str[0:2]) 
  m = float(time_str[3:5])
  h24 = h12 if time_str[6] == "A" else (h12+12)
  return h24 + (m/60.0)
  
MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def draw_clock(info: dict, y: int, time_on_screen: float) -> None:
  graphics.set_font("bitmap8")
      
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time())
  graphics.set_pen(LIGHT_GREY)
  graphics.text(f"{h:02d}:{m:02d}", 2, y, scale=0.5)
  graphics.set_font("bitmap6")
  
  sunrise = info["sunrise"] 
  sunset = info["sunset"] 
  
  monthday_str = str(monthday)
  monthday_str_width = graphics.measure_text(monthday_str, scale=0.5)
  graphics.text(monthday_str, 52-monthday_str_width, y, scale=0.5)
  
  graphics.set_pen(GREY)
  month_str = MONTHS[month-1]
  month_str_width = graphics.measure_text(month_str, scale=0.5)
  graphics.text(month_str, 52-monthday_str_width-month_str_width-1, y, scale=0.5)
  
  # 53 pixels, 2 pixels per hour
  for h_tick in range(1,25):
    # h_tick represents the hour we're building towards. eg first loop is midnight to 1am
    tick_colour = LIGHT_GREY if h_tick == 12 \
      else ORANGE if (math.floor(sunrise) == h_tick or math.floor(sunset) == h_tick) \
      else DARK_BLUE if (sunrise > h_tick or sunset < h_tick) \
      else YELLOW
    graphics.set_pen(tick_colour)
    graphics.pixel(h_tick*2+1, y+8)
    
    # set first tick after half past of prev hour
    graphics.set_pen(GREY)
    if h >= h_tick or (h == h_tick-1 and m >= 30):
      graphics.pixel(h_tick*2,y+9)
      
    # set second tick after the new hour
    if h >= h_tick:
      graphics.pixel(h_tick*2+1,y+9)
      
def draw_timeline(info: dict, y: int, time_on_screen: float) -> None:
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time())
  
  graphics.set_pen(LIGHT_GREY)
  graphics.text(f"{h:02d}:{m:02d}", 1, y-2, scale=0.5)  
  
  monthday_str = str(monthday)
  monthday_str_width = graphics.measure_text(monthday_str, scale=0.5)
  graphics.text(monthday_str, 52-monthday_str_width, y-2, scale=0.5)
  
  graphics.set_pen(GREY)
  month_str = MONTHS[month-1]
  month_str_width = graphics.measure_text(month_str, scale=0.5)
  graphics.text(month_str, 52-monthday_str_width-month_str_width-1, y-2, scale=0.5)
  
  sunrise = info["sunrise"] 
  sunset = info["sunset"] 
  
  #MAX_RAIN = 1.5
  
  # 53 pixels, 2 pixels per hour
  for h_tick in range(1,25):
    # h_tick represents the hour we're building towards. eg first loop is midnight to 1am
    
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
  draw_atmosphere,
  draw_temp,
  draw_trains,
  draw_timeline,
]
