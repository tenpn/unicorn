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

SCROLL_DURATION = 0.4
PAUSE_DURATION = 12
SCROLL_PADDING = 4

graphics.set_font("bitmap8")

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
  "#######",
  "   #   ",
  "   #   ",
  "   #   ",
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

def draw_minmax_temp(forecast, y: int):
  temp_min = str(forecast["forecast"]["forecastday"][0]["day"]["mintemp_c"])
  temp_max = str(forecast["forecast"]["forecastday"][0]["day"]["maxtemp_c"])
  
  col = 1
  draw_icon(DOWN_ARROW, col, y, BLUE)  
  col += 8
  
  graphics.text(temp_min, col, y+1, scale=0.5)
  min_width = graphics.measure_text(temp_min, scale=0.5)  
  col += min_width
  
  draw_icon(UP_ARROW, col, y, ORANGE)
  col += 8
  graphics.text(temp_max, col, y+1, scale=0.5)
  
def draw_temp(forecast, y: int):
  temp = f'{forecast["current"]["temp_c"]} ({forecast["current"]["feelslike_c"]})'
  
  col = 0
  draw_icon(TEMP, col, y, BLUE, second_pen=RED)
  col += 8
  
  graphics.text(temp, col, y+1, scale=0.5)

# message to scroll
rows = [
  #forecast["current"]["condition"]["text"],
  #f'Wind {forecast["current"]["wind_mph"]}mph  Humidity {forecast["current"]["humidity"]}%',
  #"Next train: 3.35pm",
  #f'Sunrise {forecast["forecast"]["forecastday"][0]["astro"]["sunrise"].lower()}  Sunset {forecast["forecast"]["forecastday"][0]["astro"]["sunset"].lower()}',
  draw_temp,
  draw_minmax_temp,
]

gu.set_brightness(0.5)
brightness_btn_prev : int = 0

while True:
  now = time.ticks_ms()
  time_on_row = time.ticks_diff(time.ticks_ms(), row_start_tickms)/1000.0

  graphics.set_pen(BLACK)
  graphics.clear()

  """
  scroll_t = min(1, time_on_row/SCROLL_DURATION)

  prev_y = int(lerp(2, GalacticUnicorn.HEIGHT, scroll_t))
  current_y = int(lerp(-GalacticUnicorn.HEIGHT, 2, scroll_t))
  
  current_width = graphics.measure_text(rows[current_row], 1)
  if time_on_row > SCROLL_DURATION and current_width > GalacticUnicorn.WIDTH and time_on_row > (SCROLL_DURATION*2):
    current_scroll += 0.25
    while current_scroll >= (current_width + SCROLL_PADDING):
      current_scroll -= (current_width + SCROLL_PADDING)

  # if we scroll long text, we'll draw it again like it's wrapping around
  
  graphics.set_pen(YELLOW)
  graphics.text(rows[current_row-1], round(1 - prev_scroll), prev_y, -1, 0.5);    
  if prev_scroll > 0:
    prev_width = graphics.measure_text(rows[current_row-1], 1)
    graphics.text(rows[current_row-1], round(1 - prev_scroll) + prev_width + SCROLL_PADDING, prev_y, -1, 0.5);    
    
  graphics.text(rows[current_row], round(1 - current_scroll), current_y, -1, 0.5);
  if current_scroll > 0:
    graphics.text(rows[current_row], round(1 - current_scroll) + current_width + SCROLL_PADDING, current_y, -1, 0.5);

  if time_on_row > (SCROLL_DURATION + PAUSE_DURATION):
    current_row = (current_row + 1) % len(rows)
    row_start_tickms = now
    prev_scroll = current_scroll
    current_scroll = 0
  """
  
  scroll_t = min(1, time_on_row/SCROLL_DURATION)

  prev_y = int(lerp(1, GalacticUnicorn.HEIGHT, scroll_t))
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