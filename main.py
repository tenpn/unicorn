from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
from network_manager import NetworkManager
import proj_secrets
import time
import math
import machine
import uasyncio
from urllib.urequest import urlopen
import json
import icons
import ntp_time
import trains_azure
import gc

ROW_SCROLL_DURATION = 0.5
ROW_PAUSE_DURATION = 15
INFO_SCROLL_SPEED = 5
REQUEST_INTERVAL = 9*60*1000

# "overclock" from the sample code???
machine.freq(200000000)

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# create our GalacticUnicorn object
gu = GalacticUnicorn()

gu.set_brightness(0.5)

# pen colours to draw with
DARK_GREY = graphics.create_pen(15,15,15)
GREY = graphics.create_pen(50,50,50)
LIGHT_GREY = graphics.create_pen(150,150,150)
BLACK = graphics.create_pen(0, 0, 0)
YELLOW = graphics.create_pen(255, 255, 50)
LIGHT_PURPLE = graphics.create_pen(50, 0, 100)
PURPLE = graphics.create_pen(200, 50, 150)
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

graphics.set_font("bitmap6")

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
    scroll_offset = math.ceil(lerp(1, -max_scroll-1, scroll_t))
  else:
    scroll_offset = 0
  
  graphics.text(text, left + scroll_offset, top, scale=0.5)
  graphics.remove_clip()

def draw_temp(forecast, departures, y: int, time_on_row: floatb) -> None:
  temp = forecast["current"]["temp_c"]  
  feels_like = forecast["current"]["feelslike_c"]
  
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
  
  temp_max = forecast["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
  icons.draw(graphics, icons.UP_ARROW, col, y-1, GREY)
  graphics.set_pen(get_col_for_temp(temp_max))
  graphics.text(str(temp_max), col+7, y-2, scale=0.5)
  
  temp_min = forecast["forecast"]["forecastday"][0]["day"]["mintemp_c"]
  icons.draw(graphics, icons.DOWN_ARROW, col, y+5, GREY)
  graphics.set_pen(get_col_for_temp(temp_min))
  graphics.text(str(temp_min), col+7, y+4, scale=0.5)
  
def draw_atmosphere(forecast, departures, y: int, time_on_row: float) -> None:
  wind = forecast["current"]["wind_mph"]
  humidity = forecast["current"]["humidity"]
  rain_chance = forecast["forecast"]["forecastday"][0]["day"]["daily_chance_of_rain"]
  condition = forecast["current"]["condition"]["text"]
  
  wind_animate = math.floor(time_on_row*1.7)
  rain_animate = math.floor(time_on_row*1.5)
  
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
  scroll_text(condition, col, y+4, GalacticUnicorn.WIDTH-col-1, math.ceil(GalacticUnicorn.HEIGHT*0.5), time_on_row)
  
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

def draw_clock(forecast, departures, y: int, time_on_row: float) -> None:
  graphics.set_font("bitmap8")
      
  (_,month,monthday,h,m,_,_,_) = time.localtime(time.time())
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
      
def draw_timeline(forecast, departures, y: int, time_on_row: float) -> None:
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
  
  sunrise = decimal_time_from_time_str(forecast["forecast"]["forecastday"][0]["astro"]["sunrise"])
  sunset = decimal_time_from_time_str(forecast["forecast"]["forecastday"][0]["astro"]["sunset"])
  
  #MAX_RAIN = 1.5
  
  # 53 pixels, 2 pixels per hour
  for h_tick in range(1,25):
    # h_tick represents the hour we're building towards. eg first loop is midnight to 1am
    
    left_tick_x = h_tick*2
    right_tick_x = left_tick_x+1
    
    hour = forecast["forecast"]["forecastday"][0]["hour"][h_tick-1]
    
    rain = hour["chance_of_rain"]
    #rain_height = math.ceil(8.0*min(1, rain))
    
    if rain > 20:
      graphics.set_pen(LIGHT_PURPLE if rain < 50 else PURPLE)
      graphics.pixel(left_tick_x, y+6)
      graphics.pixel(right_tick_x, y+6)
      #graphics.rectangle(left_tick_x, 7-rain_height+y, 1, rain_height)
      
    temp = hour["feelslike_c"]
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
      
def draw_trains(forecast, departures, y: int, time_on_row: float) -> None:
  # make the train animate by leaving some holes in the smoke
  missing_smoke = icons.TRAIN_SMOKES[math.floor(time_on_row*3)%len(icons.TRAIN_SMOKES)]
  icons.draw(graphics, icons.TRAIN, 0, y-1, BLUE, 
             second_pen=lambda px,py: BLACK if px==missing_smoke[0] and py==missing_smoke[1] else GREY)
  
  if departures is None or len(departures) == 0:
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
  
  # scroll train departure times across two rows
  col = 16
  row = y-2
  for departure in until_departures:
    departure_col = RED if departure <= 10 \
      else ORANGE if departure <= 15 \
      else GREEN if departure <= 20 \
      else GREY
    departure_width = graphics.measure_text(str(departure), scale=0.5) + 2
    if col + departure_width >= GalacticUnicorn.WIDTH:
      if row < y: 
        row = y+4
        col = 16
      else:
        break
    graphics.set_pen(departure_col)    
    graphics.text(str(departure), col, row, scale=0.5)  
    col += departure_width

# message to scroll
rows = [
  #draw_clock,
  draw_timeline,
  draw_atmosphere,
  draw_temp,
  draw_trains,
]

if __name__=="__main__":

  try:
    network_manager = NetworkManager(proj_secrets.WIFI_COUNTRY, status_handler=status_handler)
    uasyncio.get_event_loop().run_until_complete(network_manager.client(proj_secrets.WIFI_SSID, proj_secrets.WIFI_PSK))
  except Exception as e:
    print(f'Wifi connection failed! {e}')
    exit()
    
  ntp_time.set_time()  
  
  forecast_url = f"https://api.weatherapi.com/v1/forecast.json?q={proj_secrets.WEATHER_POSTCODE}&key={proj_secrets.WEATHER_API_KEY}"
  
  while True:
      
    gc.collect()
    print(f"starting requests with mem {gc.mem_free()}")
    current_row = 0
    row_start_tickms = time.ticks_ms()
    prev_scroll = 0
    current_scroll = 0
      
    forecast = {}
    forecast_req = urlopen(forecast_url)
    if forecast_req is None:
      print("fetching forecast failed " + forecast_req.status)
      break
    
    forecast = json.loads(forecast_req.read())
    forecast_req.close()
    if forecast is None or len(forecast) == 0:
      print("forecast json failed " + forecast_req.status)
      break

    gc.collect()
    print("got weather")
    
    timetables = trains_azure.get_timetables()
    next_departures = [] if timetables is None \
      else [timetable_entry[0]["time"]
            for timetable_entry in timetables.rl_timetable]

    brightness_btn_prev : int = 0
    speed_btn_prev : int = 0
    
    req_tickms = time.ticks_ms()
    print(f"new request {req_tickms} with mem {gc.mem_free()}")

    while time.ticks_diff(time.ticks_ms(), req_tickms) < REQUEST_INTERVAL:
      
      now = time.ticks_ms()
      time_on_row = time.ticks_diff(time.ticks_ms(), row_start_tickms)/1000.0

      graphics.set_pen(BLACK)
      graphics.clear()
      
      scroll_t = ease_in(min(1, time_on_row/ROW_SCROLL_DURATION))

      prev_y = int(lerp(1, GalacticUnicorn.HEIGHT+1, scroll_t))
      current_y = int(lerp(-GalacticUnicorn.HEIGHT, 1, scroll_t))
      rows[current_row-1](forecast, next_departures, prev_y, time_on_row)
      rows[current_row](forecast, next_departures, current_y, time_on_row)
      
      # progres bar for next row 
      graphics.set_pen(DARK_GREY)
      row_t = (time_on_row) / (ROW_PAUSE_DURATION+ROW_SCROLL_DURATION)
      progress_pixels = math.ceil(lerp(0, GalacticUnicorn.HEIGHT, (1-row_t)))
      for progress_y in range(0, progress_pixels):
        graphics.pixel(GalacticUnicorn.WIDTH-1, (current_y - 1) + (GalacticUnicorn.HEIGHT - 1) - progress_y)
      
      if time_on_row > (ROW_SCROLL_DURATION + ROW_PAUSE_DURATION):
        current_row = (current_row + 1) % len(rows)
        row_start_tickms = now
        
      # inputs
      
      brightness_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP) \
        else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN) \
        else 0
      if brightness_btn != brightness_btn_prev and brightness_btn != 0:
        gu.adjust_brightness(0.1 * brightness_btn)
      brightness_btn_prev = brightness_btn
        
      speed_btn = 1 if gu.is_pressed(GalacticUnicorn.SWITCH_VOLUME_UP) \
        else -1 if gu.is_pressed(GalacticUnicorn.SWITCH_SLEEP) \
        else 0
      if speed_btn != speed_btn_prev and speed_btn != 0:
        ROW_PAUSE_DURATION = max(0, ROW_PAUSE_DURATION + speed_btn)
      speed_btn_prev = speed_btn
        
      # update the display
      gu.update(graphics)

      time.sleep(0.02)