import socket

# Set up the socket to listen on a specific Ethernet port (e.g., 12345)
HOST = ''  # Listen on all available interfaces
PORT = 12345  # Change this to your desired port

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Listening on port {PORT}...")
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print("Received:", data.decode('utf-8', errors='replace'))