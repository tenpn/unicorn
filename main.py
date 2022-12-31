from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
from network_manager import NetworkManager
import proj_secrets
import time
import math
import machine
import uasyncio
import urequests

# "overclock" from the sample code???
machine.freq(200000000)

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# create our GalacticUnicorn object
gu = GalacticUnicorn()

# pen colours to draw with
GREY = graphics.create_pen(50,50,50)
LIGHT_GREY = graphics.create_pen(150,150,150)
BLACK = graphics.create_pen(0, 0, 0)
YELLOW = graphics.create_pen(255, 255, 50)
RED = graphics.create_pen(255, 50, 50)
GREEN = graphics.create_pen(50, 255, 50)
ORANGE = graphics.create_pen(255, 127, 50)
LIGHT_BLUE = graphics.create_pen(100, 100, 255)
DARK_BLUE = graphics.create_pen(50, 50, 200)
BLUE = graphics.create_pen(50, 50, 255)

TEMPERATURE_COLOURS = [
  # below temp, pen
  [-3, graphics.create_pen(50,50,255)], 
  [3, graphics.create_pen(50,125,255)], 
  [10, graphics.create_pen(50,225,150)],
  [15, graphics.create_pen(50,255,50)], 
  [25, graphics.create_pen(255,125,50)],
  [99, graphics.create_pen(255,50,50)], 
]
def get_col_for_temp(temp: float):
  for (max_temp, col) in TEMPERATURE_COLOURS:
    if temp <= max_temp:
      return col
  return TEMPERATURE_COLOURS[-1][1]

ROW_SCROLL_DURATION = 0.5
ROW_PAUSE_DURATION = 15
INFO_SCROLL_SPEED = 5

graphics.set_font("bitmap6")

current_row = 0
row_start_tickms = time.ticks_ms()
prev_scroll = 0
current_scroll = 0

def lerp(a: float, b: float, t: float) -> float:
  return a*(1-t) + b*t

def ease_in_out(t: float) -> float:
  return (2*t*t) if t < 0.5 else (1 - (math.pow(-2*t+2, 2))*0.5)

def ease_out(t: float) -> float:
  return 1-(1-t)*(1-t)

def ease_in(t: float) -> float:
  return t*t

def status_handler(mode, status, ip):
    # reports wifi connection status
    print(mode, status, ip)
    print('Connecting to wifi...')
    
    graphics.clear()
    
    graphics.set_pen(YELLOW)    
    # flash while connecting
    for i in range(GalacticUnicorn.HEIGHT):
      graphics.line(0,0,0,i)
      gu.update(graphics)
      time.sleep(0.02)
      
    graphics.set_pen(BLACK)
    graphics.clear()
    gu.update(graphics)
        
    if status is not None:
      if status:
        print('Wifi connection successful!')
      else:
        print('Wifi connection failed!')
        graphics.set_pen(RED)
        graphics.line(0,0,0,GalacticUnicorn.HEIGHT)
        gu.update(graphics)

try:
  network_manager = NetworkManager(proj_secrets.WIFI_COUNTRY, status_handler=status_handler)
  uasyncio.get_event_loop().run_until_complete(network_manager.client(proj_secrets.WIFI_SSID, proj_secrets.WIFI_PSK))
except Exception as e:
  print(f'Wifi connection failed! {e}')
  exit()
  
forecast_req = urequests.get(f"https://api.weatherapi.com/v1/forecast.json?q={proj_secrets.WEATHER_POSTCODE}&key={proj_secrets.WEATHER_API_KEY}")

if forecast_req.status_code != 200:
  exit()

forecast = forecast_req.json()

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

def draw_icon(icon, origin_x, origin_y, pen, second_pen=None):
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
        
def get_thermometer_col_from_y(icon_y, temp):
  temp_index = min(len(TEMPERATURE_COLOURS), 7-icon_y)
  (max_temp, temp_pen) = TEMPERATURE_COLOURS[temp_index]
  min_temp = -99 if temp_index == 0 else TEMPERATURE_COLOURS[temp_index-1][0]
  return temp_pen if temp >= max_temp or (temp > min_temp and temp <= max_temp) else BLACK  
  
def scroll_text(text:str, left:int, top:int, width:int, height:int, time:float) -> None:
  """will clip text to box. eases in/out, uses INFO_SCROLL_SPEED
  """
  graphics.set_clip(left, top, width, height)
  max_scroll = (graphics.measure_text(text, scale=0.5)) - width
  if max_scroll > 0:
    time -= ROW_SCROLL_DURATION # don't start early 
    scroll_duration = max_scroll / INFO_SCROLL_SPEED
    scroll_t = ease_in_out((time % scroll_duration) / scroll_duration)
    # back and forth
    if math.floor(time/scroll_duration)%2 == 1: 
      scroll_t = 1 - scroll_t      
    # with a touch of padding
    scroll_offset = math.ceil(lerp(2, -max_scroll-2, scroll_t))
  else:
    scroll_offset = 0
  
  graphics.text(text, left + scroll_offset, top, scale=0.5)
  graphics.remove_clip()

def draw_temp(forecast, y: int, time_on_row: float) -> None:
  temp = forecast["current"]["temp_c"]  
  feels_like = forecast["current"]["feelslike_c"]
  
  col = 0
  draw_icon(TEMP, col, y, GREY, 
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
  
  temp_max = forecast["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
  draw_icon(UP_ARROW, col, y-1, GREY)
  graphics.set_pen(get_col_for_temp(temp_max))
  graphics.text(str(temp_max), col+7, y-2, scale=0.5)
  
  temp_min = forecast["forecast"]["forecastday"][0]["day"]["mintemp_c"]
  draw_icon(DOWN_ARROW, col, y+5, GREY)
  graphics.set_pen(get_col_for_temp(temp_min))
  graphics.text(str(temp_min), col+7, y+4, scale=0.5)
  
def draw_atmosphere(forecast, y: int, time_on_row: float) -> None:
  wind = forecast["current"]["wind_mph"]
  humidity = forecast["current"]["humidity"]
  rain_chance = forecast["forecast"]["forecastday"][0]["day"]["daily_chance_of_rain"]
  condition = forecast["current"]["condition"]["text"]
  
  col = 1
  draw_icon(WIND, col, y-1, GREY)
  draw_icon(RAIN, col, y+5, LIGHT_BLUE)

  col += 7
  
  wind_colour = RED if wind > 20 \
    else YELLOW if wind > 10 \
    else GREEN if wind < 3 \
    else LIGHT_GREY
  graphics.set_pen(wind_colour)
  graphics.text(str(wind), col, y-2, scale=0.5)
  
  rain_colour = BLUE if rain_chance > 70 \
    else LIGHT_BLUE if rain_chance > 30 \
    else GREEN if rain_chance == 0 \
    else LIGHT_GREY
  graphics.set_pen(rain_colour)
  graphics.text(str(rain_chance), col, y+4, scale=0.5)
  
  col += max(graphics.measure_text(str(wind), scale=0.5), graphics.measure_text(str(rain_chance), scale=0.5))  
  if col < GalacticUnicorn.WIDTH*0.5:
    col = math.floor(GalacticUnicorn.WIDTH*0.5)
    
  graphics.set_pen(LIGHT_GREY)  
  scroll_text(condition, col, y+4, GalacticUnicorn.WIDTH-col-1, math.ceil(GalacticUnicorn.HEIGHT*0.5), time_on_row)
  
  draw_icon(HUMIDITY, col, y-1, LIGHT_BLUE, second_pen=lambda _x,_y: GREY)
  
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

def draw_clock(forecast, y: int, time_on_row: float) -> None:
  graphics.set_font("bitmap8")
      
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time()) # forecast["locaation"]["localtime"][11:]
  graphics.set_pen(LIGHT_GREY)
  graphics.text(f"{h:02d}:{m:02d}", 2, y, scale=0.5)
  graphics.set_font("bitmap6")
  
  sunrise = decimal_time_from_time_str(forecast["forecast"]["forecastday"][0]["astro"]["sunrise"])
  sunset = decimal_time_from_time_str(forecast["forecast"]["forecastday"][0]["astro"]["sunset"])
  
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
      else DARK_BLUE if (sunrise >= h_tick or sunset <= h_tick) \
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

# message to scroll
rows = [
  #forecast["current"]["condition"]["text"],
  #f'Wind {forecast["current"]["wind_mph"]}mph  Humidity {forecast["current"]["humidity"]}%',
  #"Next train: 3.35pm",
  #f'Sunrise {forecast["forecast"]["forecastday"][0]["astro"]["sunrise"].lower()}  Sunset {forecast["forecast"]["forecastday"][0]["astro"]["sunset"].lower()}',
  draw_clock,
  draw_atmosphere,
  draw_temp,
]

gu.set_brightness(0.5)
brightness_btn_prev : int = 0
speed_btn_prev : int = 0

while True:
  now = time.ticks_ms()
  time_on_row = time.ticks_diff(time.ticks_ms(), row_start_tickms)/1000.0

  graphics.set_pen(BLACK)
  graphics.clear()
  
  scroll_t = ease_in(min(1, time_on_row/ROW_SCROLL_DURATION))

  prev_y = int(lerp(1, GalacticUnicorn.HEIGHT+1, scroll_t))
  current_y = int(lerp(-GalacticUnicorn.HEIGHT, 1, scroll_t))
  rows[current_row-1](forecast, prev_y, time_on_row)
  rows[current_row](forecast, current_y, time_on_row)
  
  if time_on_row > (ROW_SCROLL_DURATION + ROW_PAUSE_DURATION):
    current_row = (current_row + 1) % len(rows)
    row_start_tickms = now
  
  brightness_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP) \
    else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN) \
    else 0
  if brightness_btn != brightness_btn_prev and brightness_btn != 0:
    gu.adjust_brightness(0.1 * brightness_btn)
  brightness_btn_prev = brightness_btn
    
  speed_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_VOLUME_UP) \
    else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_VOLUME_DOWN) \
    else 0
  if speed_btn != speed_btn_prev and speed_btn != 0:
    ROW_PAUSE_DURATION = max(0, ROW_PAUSE_DURATION + speed_btn)
  speed_btn_prev = speed_btn
    
  # update the display
  gu.update(graphics)

  time.sleep(0.02)