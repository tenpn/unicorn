import math
import collections
import proj_secrets
from urllib.urequest import urlopen
import json

#URL = "http://localhost:7071/api/trainline"
URL = "https://ldbws-line.azurewebsites.net/api/trainline"
    
def query(left, right):
    """_summary_

    Args:
        left (str): _description_
        right (str): _description_

    Returns:
        _type_: a (u)request object. close this!!
    """
    fullURL = f"{URL}/?left_crs={left}&right_crs={right}&code={proj_secrets.TRAINS_AUTH}"
    return urlopen(fullURL)

def str_from_decimal_time(dec_time) -> str:
    hrs = math.floor(dec_time)
    mins = math.floor((dec_time-hrs)*60)
    return f"{hrs:02}:{mins:02}"

Timetables = collections.namedtuple("Timetables", ["lr_timetable", "rl_timetable", "generatedAt"])

def get_timetables() -> Timetables:
    """ask azure for latest timetables

    Returns:
        Timetables: None if something went wrong
    """
        
    trains_response = query(proj_secrets.TRAINS_TO, proj_secrets.TRAINS_FROM)

    if trains_response is None:
        print(f"something went wrong: code {trains_response.status_code} {trains_response}")
        trains_response.close()
        return None

    trains = json.loads(trains_response.read())
    trains_response.close()
    
    if trains is None or len(trains) == 0:
        print("trains parsing failed")
        return None
    
    return Timetables(trains["lr"], trains["rl"], trains["now"])

def print_timetable(lr_timetable, rl_timetable, now: float) -> None:
    print(str_from_decimal_time(now))

    print(">")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in timetable_entry])
          for timetable_entry in lr_timetable]))

    print("<")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in timetable_entry])
          for timetable_entry in rl_timetable]))