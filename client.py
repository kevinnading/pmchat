import pygame
import socket
import threading
import json
import random
import time

# Initial window dimensions and setup
WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Multiplayer Side-Scroller")

PLAYER_SIZE = 50
VEL = 5
JUMP_STRENGTH = 15
GRAVITY = 1
GROUND_Y = 500

def random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

PLAYER_COLOR = random_color()
FIXED_Y = GROUND_Y - PLAYER_SIZE
WORLD_WIDTH = 1600

FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

SERVER = '127.0.0.1'
PORT = 5555
ADDR = (SERVER, PORT)

def connect_to_server():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            client.connect(ADDR)
            return client
        except socket.error:
            print("[RECONNECTING] Trying to reconnect...")
            time.sleep(5)

client = connect_to_server()

player_id = str(client.getsockname()[1])
player_name = f"Player_{random.randint(1000, 9999)}"
state = {"x": WIDTH // 2, "y": FIXED_Y, "vx": 0, "vy": 0}
previous_state = state.copy()
positions = {}
player_info = {player_id: {"color": PLAYER_COLOR, "name": player_name}}

chat_buffer = []
input_active = False
input_text = ""

pygame.init()
pygame.font.init()

stop_event = threading.Event()

sent_data = 0
received_data = 0
network_load_sent = 0
network_load_received = 0

def handle_server():
    global positions, player_info, client, chat_buffer, received_data
    buffer = ""
    while not stop_event.is_set():
        try:
            msg = client.recv(2048).decode(FORMAT)
            received_data += len(msg)
            buffer += msg
            while True:
                try:
                    if not buffer:
                        break
                    update, index = json.JSONDecoder().raw_decode(buffer)
                    buffer = buffer[index:].strip()
                    print(f"[RECEIVED FROM SERVER] {update}")
                    if "connected" in update:
                        positions[update["connected"]] = update["position"]
                        player_info[update["connected"]] = update["info"]
                        print(f"Player {update['connected']} connected with info: {update['info']}")
                    elif "disconnected" in update:
                        if update["disconnected"] in positions:
                            del positions[update["disconnected"]]
                            del player_info[update["disconnected"]]
                            print(f"Player {update['disconnected']} disconnected")
                    elif "all_positions" in update:
                        for pid, pos in update["all_positions"].items():
                            if pid != player_id:
                                positions[pid] = pos
                        print(f"Received all positions: {positions}")
                    elif "all_info" in update:
                        for pid, info in update["all_info"].items():
                            if pid != player_id:
                                player_info[pid] = info
                        print(f"Received all info: {player_info}")
                    elif "chat" in update:
                        chat_buffer.append(update["chat"])
                        if len(chat_buffer) > 100:
                            chat_buffer.pop(0)
                        print(f"Received chat: {update['chat']}")
                    else:
                        for pid, pos in update.items():
                            if pid != player_id:
                                positions[pid] = pos
                        print(f"Received position update: {positions}")
                except json.JSONDecodeError:
                    break
        except Exception as e:
            if not stop_event.is_set():
                print(f"[ERROR] {e}")
            break

def send_state():
    global sent_data
    msg = json.dumps({"id": player_id, "state": state})
    client.send(msg.encode(FORMAT))
    sent_data += len(msg)
    print(f"[SENT TO SERVER] {msg}")

def send_connection_status(status):
    global sent_data
    msg = json.dumps({status: player_id, "position": state, "info": player_info[player_id]})
    client.send(msg.encode(FORMAT))
    sent_data += len(msg)
    print(f"[SENT TO SERVER] {msg}")

def send_chat_message(message):
    global sent_data
    msg = json.dumps({"chat": {"player": player_name, "message": message}})
    client.send(msg.encode(FORMAT))
    sent_data += len(msg)
    print(f"[SENT CHAT TO SERVER] {msg}")

def draw_window():
    global WIDTH, HEIGHT, input_active
    WIN.fill((135, 206, 250))

    # Update dimensions for resizable window
    WIDTH, HEIGHT = WIN.get_size()
    ground_y = HEIGHT - (HEIGHT - GROUND_Y)
    player_size = PLAYER_SIZE * (WIDTH / 800)
    vel = VEL * (WIDTH / 800)

    pygame.draw.line(WIN, (0, 0, 0), (0, ground_y), (WIDTH, ground_y), 5)

    box_size = 50 * (WIDTH / 800)
    for x in range(0, WIDTH, int(box_size)):
        for y in range(int(ground_y + 5), HEIGHT, int(box_size)):
            rect = pygame.Rect(x, y, int(box_size), int(box_size))
            if (x // int(box_size) + y // int(box_size)) % 2 == 0:
                pygame.draw.rect(WIN, (169, 169, 169), rect)
            else:
                pygame.draw.rect(WIN, (211, 211, 211), rect)

    font = pygame.font.SysFont('Arial', int(14 * (WIDTH / 800)))
    coord_text = font.render(f"Coordinates: ({state['x']}, {state['y']})", True, (0, 0, 0))
    coord_rect = coord_text.get_rect(center=(WIDTH // 2, 10))
    WIN.blit(coord_text, coord_rect)

    for pid, pos in positions.items():
        if pid != player_id:
            color = tuple(player_info[pid]["color"])
            pygame.draw.rect(WIN, color, (round(pos["x"] * (WIDTH / 800)), round(pos["y"] * (HEIGHT / 600)), int(player_size), int(player_size)))
            name_text = font.render(player_info[pid]["name"], True, (0, 0, 0))
            text_rect = name_text.get_rect(center=(round(pos["x"] * (WIDTH / 800)) + int(player_size) // 2, round(pos["y"] * (HEIGHT / 600)) - 15))
            WIN.blit(name_text, text_rect)
    pygame.draw.rect(WIN, PLAYER_COLOR, (round(state["x"] * (WIDTH / 800)), round(state["y"] * (HEIGHT / 600)), int(player_size), int(player_size)))
    name_text = font.render(player_name, True, (0, 0, 0))
    text_rect = name_text.get_rect(center=(round(state["x"] * (WIDTH / 800)) + int(player_size) // 2, round(state["y"] * (HEIGHT / 600)) - 15))
    WIN.blit(name_text, text_rect)

    # Draw chat transcript at the top with a 50-pixel space beside and above it
    chat_transcript_surface = pygame.Surface((300, 200), pygame.SRCALPHA)
    chat_transcript_surface.fill((0, 0, 0, 128))
    chat_transcript_rect = chat_transcript_surface.get_rect(topleft=(50, 50))
    WIN.blit(chat_transcript_surface, chat_transcript_rect)

    chat_font = pygame.font.SysFont('Arial', 12)
    chat_y = 55
    for chat in chat_buffer[-10:]:
        chat_text = chat_font.render(f"{chat['player']}: {chat['message']}", True, (255, 255, 255))
        WIN.blit(chat_text, (55, chat_y))
        chat_y += 20

    # Draw input box just under the chat transcript box
    input_box_surface = pygame.Surface((300, 20), pygame.SRCALPHA)
    input_box_surface.fill((0, 0, 0, 128))
    input_box_rect = input_box_surface.get_rect(topleft=(50, 260))
    WIN.blit(input_box_surface, input_box_rect)

    input_text_surface = chat_font.render(input_text, True, (255, 255, 255))
    WIN.blit(input_text_surface, (55, 262))

    # Blinking cursor
    if input_active:
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor = chat_font.render('|', True, (255, 255, 255))
            WIN.blit(cursor, (55 + input_text_surface.get_width(), 262))

    # Draw network load
    network_font = pygame.font.SysFont('Arial', 18)
    sent_text = network_font.render(f"Sent: {network_load_sent} B/s", True, (255, 255, 255))
    received_text = network_font.render(f"Received: {network_load_received} B/s", True, (255, 255, 255))
    WIN.blit(sent_text, (WIDTH - 200, 10))
    WIN.blit(received_text, (WIDTH - 200, 30))

    pygame.display.update()

def update_network_load():
    global sent_data, received_data, network_load_sent, network_load_received
    while not stop_event.is_set():
        network_load_sent = sent_data
        network_load_received = received_data
        sent_data = 0
        received_data = 0
        time.sleep(1)

def main():
    global state, previous_state, input_active, input_text
    clock = pygame.time.Clock()
    run = True
    moving = False
    jumping = False

    send_connection_status("connected")

    server_thread = threading.Thread(target=handle_server)
    server_thread.start()

    network_thread = threading.Thread(target=update_network_load)
    network_thread.start()

    while run:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    run = False
                elif event.key == pygame.K_RETURN:
                    if input_active:
                        send_chat_message(input_text)
                        input_text = ""
                        input_active = False
                    else:
                        input_active = True
                elif input_active:
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        input_text += event.unicode
                elif event.key == pygame.K_SPACE:
                    if not jumping:
                        state["vy"] = -JUMP_STRENGTH
                        jumping = True
            if event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = event.size
                WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

        keys = pygame.key.get_pressed()
        new_state = state.copy()

        new_state["vx"] = 0

        if keys[pygame.K_LEFT] and new_state["x"] > 0:
            new_state["vx"] = -VEL
        elif keys[pygame.K_RIGHT] and new_state["x"] < WORLD_WIDTH - PLAYER_SIZE:
            new_state["vx"] = VEL

        new_state["x"] += new_state["vx"]
        
        # Update vertical position for jumping and gravity
        new_state["y"] += new_state["vy"]
        new_state["vy"] += GRAVITY

        if new_state["y"] >= FIXED_Y:
            new_state["y"] = FIXED_Y
            new_state["vy"] = 0
            jumping = False

        # Send state to server if there is any movement or jumping
        if new_state != state:
            state = new_state.copy()
            send_state()

        state = new_state.copy()

        for pid, pos in positions.items():
            if pid != player_id:
                pos["x"] += pos["vx"] * dt * 60
                pos["y"] += pos["vy"] * dt * 60

        draw_window()

    # Clean up before exiting
    stop_event.set()
    send_connection_status("disconnected")
    client.send(DISCONNECT_MESSAGE.encode(FORMAT))
    client.close()
    server_thread.join()
    network_thread.join()
    pygame.quit()
    print("[EXIT] Client has exited.")

if __name__ == "__main__":
    main()
