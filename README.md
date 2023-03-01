
# Huawei SUN2000 

## Description

Read Huawei inverter real-time data to a sqlite database.

This data can then be used by other applications to run home automations or to monitor the solar production when the inverter is not connected to the internet.

Very bespoke to my setup. Published for reference.

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Docker 

* Run: 

```bash
docker rm -f $(docker ps -aq -f ancestor=hksun)
docker rmi hksun
docker build -t hksun .
docker run -d --name=solar --restart=unless-stopped -p 5000:5000 -v "/home/docker/solar:/database" -l autoheal=true hksun
```

Autoheal

```bash
docker run -d --name autoheal --restart=always -v /var/run/docker.sock:/var/run/docker.sock willfarrell/autoheal
```

 * Query database:

```bash
watch -n 5 'sqlite3 /home/docker/solar/readings.db "SELECT * FROM Inverter ORDER BY Timestamp DESC LIMIT 10"'
```

## Service

A potential service to reset the network connection if the inverter stops responding.

* Install service:

```bash
cp solar.service /etc/systemd/system/solar.service
systemctl daemon-reload
systemctl enable solar.service
systemctl start solar.service
systemctl status solar.service
```

## Tests

```bash
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock python:3.11 bash
pip install docker
python
import docker
client = docker.from_env()
client.containers.list()
```

## TODO

* Add push notifications https://www.pushsafer.com/en/apps 
