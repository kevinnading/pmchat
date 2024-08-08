import socket
import threading
import json

SERVER = '127.0.0.1'  # Localhost
PORT = 5555
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

clients = []
positions = {}
player_info = {}
server_running = threading.Event()

def handle_client(conn, addr):
    global positions, player_info
    print(f"[NEW CONNECTION] {addr} connected.")
    connected = True
    player_id = str(addr[1])
    clients.append(conn)
    send_all_positions(conn)  # Send all positions to the newly connected client
    send_all_info(conn)  # Send all player info to the newly connected client

    while connected:
        try:
            msg = conn.recv(2048).decode(FORMAT)
            if msg == DISCONNECT_MESSAGE:
                connected = False
                if conn in clients:
                    clients.remove(conn)
                    if player_id in positions:
                        del positions[player_id]
                    if player_id in player_info:
                        del player_info[player_id]
                broadcast({"disconnected": player_id})
                conn.close()
            else:
                data = json.loads(msg)
                if "connected" in data:
                    positions[data["connected"]] = data["position"]
                    player_info[data["connected"]] = data["info"]
                    broadcast({"connected": data["connected"], "position": data["position"], "info": data["info"]})
                elif "disconnected" in data:
                    if data["disconnected"] in positions:
                        del positions[data["disconnected"]]
                    if data["disconnected"] in player_info:
                        del player_info[data["disconnected"]]
                    broadcast({"disconnected": data["disconnected"]})
                elif "chat" in data:
                    broadcast({"chat": data["chat"]})
                else:
                    player_id = data["id"]
                    state = data["state"]
                    positions[player_id] = state
                    broadcast({player_id: state})
                print(f"[RECEIVED] {data}")
        except ConnectionResetError:
            connected = False
            if conn in clients:
                clients.remove(conn)
                if player_id in positions:
                    del positions[player_id]
                if player_id in player_info:
                    del player_info[player_id]
            broadcast({"disconnected": player_id})
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
            continue

def send_all_positions(conn):
    try:
        msg = json.dumps({"all_positions": positions})
        conn.send(msg.encode(FORMAT))
        print(f"[SENT ALL POSITIONS TO NEW CLIENT] {positions}")
    except Exception as e:
        print(f"Error sending all positions: {e}")
        if conn in clients:
            clients.remove(conn)

def send_all_info(conn):
    try:
        msg = json.dumps({"all_info": player_info})
        conn.send(msg.encode(FORMAT))
        print(f"[SENT ALL INFO TO NEW CLIENT] {player_info}")
    except Exception as e:
        print(f"Error sending all info: {e}")
        if conn in clients:
            clients.remove(conn)

def broadcast(message):
    data = json.dumps(message)
    print(f"[BROADCASTING] {data}")
    for client in clients:
        try:
            client.sendall(data.encode(FORMAT))
        except Exception as e:
            print(f"Error broadcasting: {e}")
            if client in clients:
                clients.remove(client)

def start():
    global server_running
    server.listen()
    print(f"[LISTENING] Server is listening on {SERVER}")
    server_running.set()
    while server_running.is_set():
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except socket.error as e:
            print(f"Socket error: {e}")
            break

def shutdown_server():
    input("Press Enter to shutdown the server...\n")
    print("\n[SHUTTING DOWN] Server is shutting down...")
    server_running.clear()
    server.close()
    for conn in clients:
        conn.close()

if __name__ == "__main__":
    shutdown_thread = threading.Thread(target=shutdown_server)
    shutdown_thread.start()
    print("[STARTING] server is starting...")
    start()
