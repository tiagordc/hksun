
# Huawei SUN2000 

## Description

Read Huawei inverter real-time data to a sqlite database mounted outside of the container.

This data can then be used by other applications to run home automations or to monitor the solar production when the inverter is not connected to the internet.

## Docker 

* Run: 

```bash
docker rm -f $(docker ps -aq -f ancestor=hksun)
docker build -t hksun .
docker run -d -v "/home/docker/solar:/database" --name solar --restart=unless-stopped hksun
```

 * Query database:

```bash
watch -n 5 'sqlite3 /home/docker/solar/readings.db "SELECT * FROM Inverter ORDER BY Timestamp DESC LIMIT 10"'
```
