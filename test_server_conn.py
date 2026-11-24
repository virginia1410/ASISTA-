import os
import sys
import time
import socket
import ssl
import threading
import urllib.request
import urllib.error

# Forzar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from asista import servicio_asista

def test():
    ip_activa = servicio_asista.obtener_ip_local()
    print(f"IP Activa detectada: {ip_activa}")
    
    # Iniciar servidor en hilo en puerto de prueba 18080 y https 18443
    print("Iniciando servicio_asista...")
    t = threading.Thread(target=servicio_asista.iniciar_servidor, args=(18080,), daemon=True)
    t.start()
    time.sleep(1.5)
    
    # Probar HTTP en loopback y en IP activa
    urls_http = [
        "http://127.0.0.1:18080/api/status",
        f"http://{ip_activa}:18080/api/status",
        f"http://{ip_activa}:18080/profesor",
        f"http://{ip_activa}:18080/",
    ]
    
    for url in urls_http:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                print(f"[OK] {url} -> Status {resp.status}, Content-Type: {resp.headers.get('Content-Type')}, Length: {len(resp.read())}")
        except Exception as e:
            print(f"[FAIL] {url} -> {type(e).__name__}: {e}")

    # Probar HTTPS en puerto 8443 (que inicia iniciar_servidor)
    ctx = ssl._create_unverified_context()
    urls_https = [
        "https://127.0.0.1:8443/api/status",
        f"https://{ip_activa}:8443/api/status",
        f"https://{ip_activa}:8443/profesor",
        f"https://{ip_activa}:8443/",
    ]
    for url in urls_https:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"})
            with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
                print(f"[OK] {url} -> Status {resp.status}, Content-Type: {resp.headers.get('Content-Type')}, Length: {len(resp.read())}")
        except Exception as e:
            print(f"[FAIL] {url} -> {type(e).__name__}: {e}")

if __name__ == "__main__":
    test()
