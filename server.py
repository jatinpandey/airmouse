#!/usr/bin/env python3
"""
AirMouse Server — Turn your phone into a wireless mouse.

Run this on your laptop:
    pip install pyautogui websockets qrcode
    python server.py

Then scan the QR code with your phone and enter the PIN shown here.
"""

import asyncio
import json
import os
import socket
import sys
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("Installing pyautogui...")
    os.system(f"{sys.executable} -m pip install pyautogui -q")
    import pyautogui

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    os.system(f"{sys.executable} -m pip install websockets -q")
    import websockets

try:
    import qrcode
except ImportError:
    print("Installing qrcode...")
    os.system(f"{sys.executable} -m pip install qrcode -q")
    import qrcode

from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import platform

# ── Config ──────────────────────────────────────────────────────────
HTTP_PORT = 8234
WS_PORT = 8235
SENSITIVITY = 1.8
SCROLL_SENSITIVITY = 0.5

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

IS_MAC = platform.system() == "Darwin"

# ── Get local IP ────────────────────────────────────────────────────
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

# ── HTTP Server ─────────────────────────────────────────────────────
class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    def log_message(self, format, *args):
        pass
    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            pass  # Normal when phone browser drops connections

def start_http_server():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), QuietHandler)
    server.serve_forever()

# ── Media keys (macOS) ───────────────────────────────────────────────
MEDIA_KEY_CODES = {'playpause': 16, 'next': 17, 'previous': 20}

def media_key(key_name):
    """Simulate a media key press (play/pause, next, previous)."""
    code = MEDIA_KEY_CODES.get(key_name)
    if not code:
        return
    if IS_MAC:
        import subprocess
        script = f"""
        ObjC.import('Cocoa');
        var kc = {code};
        var down = $.NSEvent.otherEventWithTypeLocationModifierFlagsTimestampWindowNumberContextSubtypeData1Data2(
            14, {{x:0,y:0}}, 0xa00, 0, 0, null, 8, (kc << 16) | (0xa << 8), -1);
        $.CGEventPost(0, down.CGEvent);
        $.NSThread.sleepForTimeInterval(0.05);
        var up = $.NSEvent.otherEventWithTypeLocationModifierFlagsTimestampWindowNumberContextSubtypeData1Data2(
            14, {{x:0,y:0}}, 0xb00, 0, 0, null, 8, (kc << 16) | (0xb << 8), -1);
        $.CGEventPost(0, up.CGEvent);
        """
        subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True)
    else:
        # Linux: use xdotool with XF86 key names
        import subprocess
        xf86 = {'playpause': 'XF86AudioPlay', 'next': 'XF86AudioNext', 'previous': 'XF86AudioPrev'}
        key = xf86.get(key_name)
        if key:
            subprocess.run(["xdotool", "key", key], capture_output=True)

# ── Type unicode text (macOS AppleScript fallback) ──────────────────
def type_text(text):
    """Type text including unicode characters."""
    if IS_MAC:
        # AppleScript handles unicode properly on macOS
        import subprocess
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        script = f'tell application "System Events" to keystroke "{escaped}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)
    else:
        # xdotool handles unicode on Linux
        import subprocess
        try:
            subprocess.run(["xdotool", "type", "--clearmodifiers", text], capture_output=True)
        except FileNotFoundError:
            # Fallback to pyautogui (ASCII only)
            pyautogui.typewrite(text, interval=0.02, _pause=False)

# ── WebSocket handler ───────────────────────────────────────────────
async def handle_client(websocket):
    client_id = id(websocket)
    addr = websocket.remote_address
    print(f"📱 New connection from {addr}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get("action")

                # ── Mouse ───────────────────────────────────
                if action == "move":
                    dx = data["dx"] * SENSITIVITY
                    dy = data["dy"] * SENSITIVITY
                    pyautogui.moveRel(dx, dy, _pause=False)

                elif action == "click":
                    btn = data.get("button", "left")
                    pyautogui.click(button=btn, _pause=False)

                elif action == "doubleclick":
                    pyautogui.doubleClick(interval=0.05, _pause=False)

                elif action == "rightclick":
                    pyautogui.rightClick(_pause=False)

                elif action == "scroll":
                    amount = data.get("dy", 0) * SCROLL_SENSITIVITY
                    pyautogui.scroll(int(-amount), _pause=False)

                elif action == "scroll_smooth":
                    # Velocity-based: client sends a float velocity each frame
                    velocity = data.get("velocity", 0)
                    amount = velocity * SCROLL_SENSITIVITY
                    if abs(amount) >= 0.1:
                        pyautogui.scroll(int(-amount), _pause=False)

                elif action == "drag_start":
                    pyautogui.mouseDown(_pause=False)

                elif action == "drag_move":
                    dx = data["dx"] * SENSITIVITY
                    dy = data["dy"] * SENSITIVITY
                    pyautogui.moveRel(dx, dy, _pause=False)

                elif action == "drag_end":
                    pyautogui.mouseUp(_pause=False)

                # ── Keyboard ────────────────────────────────
                elif action == "keypress":
                    key = data.get("key", "")
                    if key:
                        pyautogui.press(key, _pause=False)

                elif action == "typetext":
                    text = data.get("text", "")
                    if text:
                        type_text(text)

                elif action == "hotkey":
                    keys = data.get("keys", [])
                    if keys:
                        pyautogui.hotkey(*keys, _pause=False)

                elif action == "backspace":
                    count = data.get("count", 1)
                    for _ in range(count):
                        pyautogui.press("backspace", _pause=False)

                # ── Media ──────────────────────────────────
                elif action == "media":
                    key = data.get("key", "")
                    if key:
                        media_key(key)

            except Exception as e:
                print(f"Error: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"📱 Disconnected: {addr}")

async def start_ws_server():
    async with websockets.serve(handle_client, "0.0.0.0", WS_PORT):
        await asyncio.Future()

# ── Main ────────────────────────────────────────────────────────────
def main():
    ip = get_local_ip()
    url = f"http://{ip}:{HTTP_PORT}"
    ws_url = f"ws://{ip}:{WS_PORT}"


    print()
    print("╔══════════════════════════════════════════════╗")
    print("║           🖱️  A I R M O U S E               ║")
    print("║     Your phone is now a wireless mouse       ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║  Open on phone: {url:<29}║")
    print(f"║  WebSocket:     {ws_url:<29}║")
    print("╠══════════════════════════════════════════════╣")
    print("╠══════════════════════════════════════════════╣")
    print("║  Both devices must be on the same WiFi!      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    try:
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        print("📷 Scan this QR code with your phone:\n")
        qr.print_ascii(invert=True)
        print()
    except Exception:
        print(f"Open this URL on your phone: {url}")

    print("Press Ctrl+C to stop.\n")

    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    try:
        asyncio.run(start_ws_server())
    except KeyboardInterrupt:
        print("\n👋 AirMouse stopped.")

if __name__ == "__main__":
    main()
