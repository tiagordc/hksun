
import os, json
from urllib.request import urlopen

avg, last = {}, {}

try:
    response = urlopen('http://127.0.0.1:5000/average/15')
    avg = json.loads(response.read())
    response = urlopen('http://127.0.0.1:5000/last')
    last = json.loads(response.read())
except:
    pass

