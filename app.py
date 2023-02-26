import asyncio, os, sqlite3, datetime
from huawei_solar import HuaweiSolarBridge, register_names as rn

INVERTER = '192.168.200.1'
DATA_PATH = '/database'
DATA_BASE = 'readings.db'

if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)

def init_tables():
    conn = sqlite3.connect(os.path.join(DATA_PATH, DATA_BASE))
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS [Inverter] ([Active] INTEGER, [Meter] INTEGER, [PV1] INTEGER, [PV2] INTEGER, [Temperature] REAL, \
                   [Fault] INTEGER, [Yielded] REAL, [Exported] REAL, [Total] REAL, [Timestamp] DATETIME DEFAULT CURRENT_TIMESTAMP )')
    conn.commit()
    conn.close()

init_tables()
bridge = None

async def connect():
    global bridge
    try:
        bridge = await HuaweiSolarBridge.create(host=INVERTER, port=6607)
    except Exception as e:
        bridge = None
        print(f'Error connecting to inverter: {e}')

async def read():
    conn = sqlite3.connect(os.path.join(DATA_PATH, DATA_BASE))
    if bridge is None: 
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
        conn.execute("INSERT INTO [Inverter] ([Active], [Meter], [PV1], [PV2], [Temperature], [Fault], [Yielded], [Exported], [Total]) \
                     VALUES (?,?,?,?,?,?,?,?,?)", (active, meter, pv1, pv2, temp, fault, yielded, exported, total))
    conn.commit()
    conn.close()
    # if POWER_METER_ACTIVE_POWER < 0 -> GRID CONSUMPTION

async def loop():
    while True:
        if bridge is None: 
            await connect()
        try:
            await read()
        except Exception as e:
            print(f'Error reading inverter: {e}')
            await connect()
        if 6 <= datetime.datetime.now().hour < 21: # In Portugal, the sun is up from 6am to 9pm at most
            await asyncio.sleep(15) # 15 seconds
        else:
            await asyncio.sleep(60 * 15) # 15 minutes

asyncio.run(loop())
