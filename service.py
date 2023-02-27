
import os, json, datetime, logging, subprocess, time
from urllib.request import urlopen

def check():
    try:
        container = subprocess.check_output('docker ps -aq -f ancestor=hksun', shell=True).decode('utf-8').strip()
        if not container: 
            logging.error('Container not found')
            return
        status = subprocess.check_output(f'docker inspect -f {{.State.Running}} {container}', shell=True).decode('utf-8').strip()
        if status == 'paused':
            logging.warning(f'Container {container} is paused. Unpausing...')
            os.system(f'docker unpause {container}')
            return
        elif status == 'exited':
            logging.warning(f'Container {container} is exited. Starting...')
            os.system(f'docker start {container}')
            return
        elif status != 'running':
            logging.error(f'Container {container} is not running. Status: {status}')
            return
        container_started = subprocess.check_output(f'docker inspect -f {{.State.StartedAt}} {container}', shell=True).decode('utf-8').strip()
        container_started = container_started[:container_started.rfind('.')] # remove the milliseconds
        container_started = datetime.datetime.strptime(container_started, '%Y-%m-%dT%H:%M:%S') 
        if container_started > datetime.datetime.now() - datetime.timedelta(minutes=5): 
            return # container started less than 5 minutes ago
        response = urlopen('http://127.0.0.1:5000/last')
        last = json.loads(response.read())
        last_error = last['faults'] == 1
        if not last_error: return # last reading is not faulty
        last_date = datetime.datetime.strptime(last['last'], '%Y-%m-%d %H:%M:%S') 
        if last_date < datetime.datetime.now() - datetime.timedelta(minutes=30): # 30 minutes since last reading
            logging.warning(f'Container {container} is not working. Restarting...')
            os.system(f'docker restart {container}')
            return
        response = urlopen('http://127.0.0.1:5000/average/15')
        avg = json.loads(response.read())
        faults = avg['faults']
        count = avg['count'] 
        if count < 10: return # less than 10 readings in the last 15 minutes, not enough data
        if faults < count / 2: return # less than 50% of the readings are faulty, keep pushing
        logging.warning(f'Container {container} is not working. Restarting wlan0...')
        os.system('sudo ifconfig wlan0 down')
        os.system('sudo ifconfig wlan0 up')
        start = datetime.datetime.now()
        while True:
            ret = os.system('ping -c 1 192.168.200.1')
            if ret == 0: 
                logging.info(f'wlan0 restarted and connected to the inverter')
                return
            if datetime.datetime.now() > start + datetime.timedelta(minutes=5):
                logging.error(f'Failed to restart wlan0 and connect to the inverter')
                return
            time.sleep(1)
    except Exception as e:
        logging.error(f'Service error: {e}')

if __name__ == '__main__':
    while True:
        check()
        time.sleep(60)
