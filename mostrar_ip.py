import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
except Exception:
    ip = "127.0.0.1"
print(f"\n{'='*40}")
print(f"Acesse pelo celular (mesma rede WiFi):")
print(f"http://{ip}:8000")
print(f"{'='*40}\n")
