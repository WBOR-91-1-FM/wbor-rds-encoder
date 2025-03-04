"""
Simple dummy server to simulate a SmartGen device for testing purposes.
"""

import socket

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000


def start_server():
    """
    Makes the server listen for incoming connections and echo back received messages.

    The server listens on all interfaces on port 5137. It accepts incoming connections
    and echoes back the received messages with an "OK" response.

    The server will run indefinitely until interrupted.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Dummy SmartGen server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_socket.accept()
            print(f"Connection received from {addr}")
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break  # Client disconnected
                    message = data.decode("ascii", errors="ignore").strip()
                    print(f"Received message: {message}")

                    # Echo the received command with an "OK" response (always)
                    response = "OK"
                    conn.sendall(response.encode("ascii"))


if __name__ == "__main__":
    start_server()
