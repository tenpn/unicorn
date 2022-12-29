from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
from network_manager import NetworkManager
import proj_secrets
import time
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
BLACK = graphics.create_pen(0, 0, 0)
YELLOW = graphics.create_pen(255, 255, 50)
RED = graphics.create_pen(255, 50, 50)
ORANGE = graphics.create_pen(255, 127, 50)
BLUE = graphics.create_pen(50, 50, 255)

TEMPERATURE_COLOURS = [
  [-5, graphics.create_pen(50,50,255)],
  [0, graphics.create_pen(50,125,255)],
  [5, graphics.create_pen(50,225,255)],
  [15, graphics.create_pen(50,255,50)],
  [25, graphics.create_pen(255,125,50)],
  [99, graphics.create_pen(255,50,50)],
]
def get_col_for_temp(temp: float):
  for temp_col in TEMPERATURE_COLOURS:
    if temp <= temp_col[0]:
      return temp_col[1]
  return TEMPERATURE_COLOURS[-1][1]

SCROLL_DURATION = 0.4
PAUSE_DURATION = 30
SCROLL_PADDING = 4

graphics.set_font("bitmap6")

current_row = 0
row_start_tickms = time.ticks_ms()
prev_scroll = 0
current_scroll = 0

def lerp(a: float, b: float, t: float):
  return a*(1-t) + b*t

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
  "  # #  ",
  "  #.#  ",
  "  #.#  ",
  "  #.#  ",
  " #...# ",
  " #...# ",
  "  ###  ",
]
WIND = [
  "  #    ",
  "   #   ",
  "###  # ",
  "      #",
  "###### ",
  "       ",
  "####   ",
  "    #  ",
  "   #   ",
]

def draw_icon(icon, origin_x, origin_y, pen, second_pen=None):
  last_pen = pen
  graphics.set_pen(pen)
  for y in range(len(icon)):
    for x in range(len(icon[y])):
      current_pen = pen if icon[y][x] == '#' \
        else second_pen if icon[y][x] == '.' \
        else None
      if current_pen is not None:
        if current_pen != last_pen:
          graphics.set_pen(current_pen)
          last_pen = current_pen          
        graphics.pixel(origin_x + x, origin_y + y)
  
def draw_temp(forecast, y: int):
  temp = forecast["current"]["temp_c"]  
  feels_like = forecast["current"]["feelslike_c"]
  
  col = 0
  draw_icon(TEMP, col, y, BLUE, second_pen=get_col_for_temp(temp))
  col += 8
  
  graphics.set_pen(get_col_for_temp(temp))
  graphics.text(str(temp), col, y-2, scale=0.5)
  graphics.set_pen(get_col_for_temp(feels_like))
  feels_like_str = f"({feels_like})"
  graphics.text(feels_like_str, col, y+4, scale=0.5)
  col += max(graphics.measure_text(str(temp), scale=0.5), graphics.measure_text(feels_like_str, scale=0.5))  
  
  temp_max = forecast["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
  draw_icon(UP_ARROW, col, y-1, get_col_for_temp(temp_max))  
  graphics.text(str(temp_max), col+8, y-2, scale=0.5)
  
  temp_min = forecast["forecast"]["forecastday"][0]["day"]["mintemp_c"]
  draw_icon(DOWN_ARROW, col, y+5, get_col_for_temp(temp_min))  
  graphics.text(str(temp_min), col+8, y+4, scale=0.5)
  
def draw_wind_humidity(forecast, y: int):
  wind = str(forecast["current"]["wind_mph"]) + "mph"
  humidity = str(forecast["current"]["humidity"]) + "%"
  
  col = 1
  draw_icon(WIND, col, y, BLUE)
  col += 9
  graphics.text(wind, col, y+1, scale=0.5)

# message to scroll
rows = [
  #forecast["current"]["condition"]["text"],
  #f'Wind {forecast["current"]["wind_mph"]}mph  Humidity {forecast["current"]["humidity"]}%',
  #"Next train: 3.35pm",
  #f'Sunrise {forecast["forecast"]["forecastday"][0]["astro"]["sunrise"].lower()}  Sunset {forecast["forecast"]["forecastday"][0]["astro"]["sunset"].lower()}',
  draw_temp,
  draw_wind_humidity,
]

gu.set_brightness(0.5)
brightness_btn_prev : int = 0

while True:
  now = time.ticks_ms()
  time_on_row = time.ticks_diff(time.ticks_ms(), row_start_tickms)/1000.0

  graphics.set_pen(BLACK)
  graphics.clear()
  
  scroll_t = min(1, time_on_row/SCROLL_DURATION)

  prev_y = int(lerp(1, GalacticUnicorn.HEIGHT+1, scroll_t))
  current_y = int(lerp(-GalacticUnicorn.HEIGHT, 1, scroll_t))
  rows[current_row-1](forecast, prev_y)
  rows[current_row](forecast, current_y)
  
  if time_on_row > (SCROLL_DURATION + PAUSE_DURATION):
    current_row = (current_row + 1) % len(rows)
    row_start_tickms = now
  
  brightness_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP) \
    else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN) \
    else 0
    
  if brightness_btn != brightness_btn_prev and brightness_btn != 0:
    gu.adjust_brightness(0.1 * brightness_btn)
    
  brightness_btn_prev = brightness_btn

  # update the display
  gu.update(graphics)

  time.sleep(0.02)