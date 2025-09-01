# service_template_dynamic.py
from flask import Flask
import os, requests, consul

SERVICE_NAME = os.environ.get("SERVICE_NAME", "service-1")
PORT = int(os.environ.get("PORT", 5001))

app = Flask(__name__)
c = consul.Consul(host="127.0.0.1", port=8500)

# Register service in Consul
c.agent.service.register(
    name=SERVICE_NAME,
    service_id=f"{SERVICE_NAME}-1",
    address="127.0.0.1",
    port=PORT
)

@app.route("/health")
def health():
    return f"{SERVICE_NAME} is healthy"

@app.route("/")
def home():
    return f"Hello from {SERVICE_NAME}"

@app.route("/call/<target_service>")
def call_service(target_service):
    # Discover target service instances via Consul
    index, services = c.catalog.service(target_service)
    if not services:
        return f"{target_service} not found in Consul", 404

    # Pick the first instance (you could implement load-balancing here)
    service = services[0]
    target_address = service['Address']
    target_port = service['ServicePort']

    url = f"http://{target_address}:{target_port}/"

    try:
        resp = requests.get(url, timeout=3)
        return f"{SERVICE_NAME} -> {target_service}: {resp.text}"
    except Exception as e:
        return f"{SERVICE_NAME} -> {target_service} failed: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)



"""
service-1.json:
{
  "service": {
    "name": "service-1",
    "port": 5001,
    "connect": { "sidecar_service": {} }
  }
}

-----------------------------
Run:
----------------
consul reload
consul agent -dev -ui -bind=127.0.0.1 -hcl 'connect { enabled = true }'
or
consul agent -dev -ui -bind=127.0.0.1 -enable-script-checks
----------------------
consul catalog services
----------------------------
consul services deregister -id=service-1-1
consul services deregister -id=service-2-1
consul services deregister -id=service-3-1
consul services deregister -id=service-4-1

consul services register service-1.json
consul services register service-2.json
consul services register service-3.json
consul services register service-4.json

SERVICE_NAME=service-1 PORT=5001 python service_template_with_proxy.py &
SERVICE_NAME=service-2 PORT=5002 python service_template_with_proxy.py &
SERVICE_NAME=service-3 PORT=5003 python service_template_with_proxy.py &
SERVICE_NAME=service-4 PORT=5004 python service_template_with_proxy.py &






consul connect proxy -sidecar-for service-1 -listen 127.0.0.1:21001 &
consul connect proxy -sidecar-for service-2 -listen 127.0.0.1:21002 &
consul connect proxy -sidecar-for service-3 -listen 127.0.0.1:21003 &
consul connect proxy -sidecar-for service-4 -listen 127.0.0.1:21004 &

  
consul intention create -allow service-1 service-2
consul intention create -allow service-1 service-3
consul intention create -allow service-1 service-4
consul intention create -allow service-2 service-1
consul intention create -allow service-2 service-3
consul intention create -allow service-2 service-4
consul intention create -allow service-3 service-1
consul intention create -allow service-3 service-2
consul intention create -allow service-3 service-4
consul intention create -allow service-4 service-1
consul intention create -allow service-4 service-2
consul intention create -allow service-4 service-3

consul intention create -allow service-1 service-2
or,
consul intention create -deny service-1 service-2

consul intention delete service-2 service-1
----------------------------------------------
$ jobs
[1]   Running                 SERVICE_NAME=service-1 PORT=5001 python service_template_with_proxy.py &
[2]   Running                 SERVICE_NAME=service-2 PORT=5002 python service_template_with_proxy.py &
[3]   Running                 SERVICE_NAME=service-3 PORT=5003 python service_template_with_proxy.py &
[4]   Running                 SERVICE_NAME=service-4 PORT=5004 python service_template_with_proxy.py &
[5]   Running                 consul connect proxy -sidecar-for service-1 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21001 &
[6]   Running                 consul connect proxy -sidecar-for service-2 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21002 &
[7]-  Running                 consul connect proxy -sidecar-for service-3 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21003 &
[8]+  Running                 consul connect proxy -sidecar-for service-4 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21004 &
----------------------------
Now when service-1 calls /call/service-2, the request flows:
service-1 app → localhost:21001 → Consul Connect proxy → service-2 proxy → service-2 app

-----------------------------------------------
Test:
curl http://127.0.0.1:5001/call/service-2
curl http://127.0.0.1:5003/call/service-4

"""



"""
http://127.0.0.1:5001/call/service-2  -> Error calling service-2: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

"""


"""
consul connect proxy -sidecar-for service-1 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21001 &
consul connect proxy -sidecar-for service-2 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21002 &
consul connect proxy -sidecar-for service-3 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21003 &
consul connect proxy -sidecar-for service-4 -http-addr=127.0.0.1:8500 -listen 127.0.0.1:21004 &
"""