import asyncio, os, sqlite3, datetime, sys, logging
from huawei_solar import HuaweiSolarBridge, register_names as rn
from quart import Quart

INVERTER = '192.168.200.1'
DATA_PATH = '/database'
DATA_BASE = 'readings.db'

app = Quart(__name__)
bridge = None

log = logging.getLogger('quart.app')
log.setLevel(logging.WARNING)

@app.route("/")
async def ping(): return 'OK'

if sys.platform == 'darwin': # this machine is not on the same network as the inverter

    def database():
        if '_db' in globals(): return globals()['_db'], False
        _db = sqlite3.connect(':memory:')
        globals()['_db'] = _db
        return _db, False
    
    async def connect():
        pass

else: # running inside docker and with access to the inverter

    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)

    def database():
        return sqlite3.connect(os.path.join(DATA_PATH, DATA_BASE)), True

    async def connect():
        global bridge
        try:
            bridge = await HuaweiSolarBridge.create(host=INVERTER, port=6607)
        except Exception as e:
            log.error(f'Error connecting to inverter: {e}')
            bridge = None

def init_tables():
    conn, close = database()
    conn.execute('CREATE TABLE IF NOT EXISTS [Inverter] ([Active] INTEGER, [Meter] INTEGER, [PV1] INTEGER, [PV2] INTEGER, [Temperature] REAL, [Fault] INTEGER, [Yielded] REAL, [Exported] REAL, [Total] REAL, [Timestamp] DATETIME DEFAULT CURRENT_TIMESTAMP )')
    conn.commit()
    if close: conn.close()

init_tables()

async def read():
    conn, close = database()
    if bridge is None: await connect()
    if sys.platform == 'darwin':
        conn.execute("INSERT INTO [Inverter] ([Active], [Meter], [PV1], [PV2], [Temperature], [Fault], [Yielded], [Exported], [Total]) VALUES (?,?,?,?,?,?,?,?,?)", (1000, 500, 300, 700, 28.5, 0, 100.0, 50.0, 150.0))
    elif bridge is None:
        conn.execute("INSERT INTO [Inverter] ([Fault]) VALUES (-1)")
    else:
        data = await bridge.update()
        active = int(data[rn.ACTIVE_POWER].value)
        meter = int(data[rn.POWER_METER_ACTIVE_POWER].value)
        pv1 = int(float(data[rn.PV_01_VOLTAGE].value) * float(data[rn.PV_01_CURRENT].value))
        pv2 = int(float(data[rn.PV_02_VOLTAGE].value) * float(data[rn.PV_02_CURRENT].value))
        temp = float(data[rn.INTERNAL_TEMPERATURE].value)
        fault = int(data[rn.FAULT_CODE].value)
        yielded = float(data[rn.ACCUMULATED_YIELD_ENERGY].value)
        exported = float(data[rn.GRID_EXPORTED_ENERGY].value)
        total = float(data[rn.GRID_ACCUMULATED_ENERGY].value)
        conn.execute("INSERT INTO [Inverter] ([Active], [Meter], [PV1], [PV2], [Temperature], [Fault], [Yielded], [Exported], [Total]) VALUES (?,?,?,?,?,?,?,?,?)", (active, meter, pv1, pv2, temp, fault, yielded, exported, total))
    conn.commit()
    if close: conn.close()

async def loop():
    global bridge
    while True:
        try:
            await read()
        except Exception as e:
            log.error(f'Error reading inverter: {e}')
            if bridge is not None:
                await bridge.stop()
                bridge = None
        if 6 <= datetime.datetime.now().hour < 21: # In Portugal, the sun is up from 6am to 9pm at most
            await asyncio.sleep(15) # 15 seconds
        else:
            await asyncio.sleep(60 * 15) # 15 minutes

@app.before_serving
async def startup(): app.add_background_task(loop)

def format_data(rows):
    result = { 'active': 0.0, 'meter': 0.0, 'pv1': 0.0, 'pv2': 0.0, 'temp': 0.0, 'inported': 0.0, 'exported': 0.0, 'consumed': 0.0, 'produced': 0.0, 'consumption': 0.0, 'import': False, 'export': False, 'faults': 0, 'count': 0, 'first': None, 'last': None }
    for row in rows:
        result['count'] += 1
        if row[5] != 0: 
            result['faults'] += 1
        else:
            result['active'] += row[0]
            result['meter'] += row[1]
            result['pv1'] += row[2]
            result['pv2'] += row[3]
            result['temp'] += row[4]
            if row[1] < 0: 
                result['import'] = True
            elif row[1] > 0: 
                result['export'] = True
    if any(rows):
        f, l = rows[0], rows[-1]
        result['first'] = f[9]
        result['last'] = l[9]
    if len(rows) > result['faults']:
        length = len(rows) - result['faults']
        result['active'] = round(result['active'] / length, 2)
        result['meter'] = round(result['meter'] / length, 2)
        result['pv1'] = round(result['pv1'] / length, 2)
        result['pv2'] = round(result['pv2'] / length, 2)
        result['temp'] = round(result['temp'] / length, 2)
        filtered = [row for row in rows if row[5] == 0] # non-faulty rows
        f, l = filtered[0], filtered[-1]
        solar_production = l[6] - f[6]
        solar_to_grid = l[7] - f[7]
        solar_to_house = solar_production - solar_to_grid
        grid_to_house = l[8] - f[8]
        house_consumption = grid_to_house + solar_to_house
        if solar_to_grid > 0: 
            result['export'] = True
        if solar_to_house > 0: 
            result['import'] = True
        result['inported'] = round(grid_to_house, 2)
        result['exported'] = round(solar_to_grid, 2)
        result['consumed'] = round(solar_to_house, 2)
        result['produced'] = round(solar_production, 2)
        result['consumption'] = round(house_consumption, 2)
    return result

@app.get("/average/<int:minutes>")
async def average(minutes):
    conn, close = database()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM [Inverter] WHERE [Timestamp] > datetime('now', '-{minutes} minutes') ORDER BY [Timestamp]")
    rows = cur.fetchall()
    if close: conn.close()
    return format_data(rows)

@app.get("/last")
async def last():
    conn, close = database()
    cur = conn.cursor()
    cur.execute("SELECT * FROM [Inverter] ORDER BY [Timestamp] DESC LIMIT 1")
    rows = cur.fetchall()
    if close: conn.close()
    return format_data(rows)

if __name__ == "__main__":
    app.run()
