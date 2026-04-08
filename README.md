# AirMouse

Turn your phone into a wireless mouse, trackpad, and keyboard for your computer.

## Features

- **Trackpad** — move your cursor by dragging on your phone screen
- **Scroll** — velocity-based scrolling: drag distance from tap point controls scroll speed
- **Resizable layout** — drag the divider between trackpad and scroll strip to allocate more space to either
- **Keyboard input** — type text directly from your phone, with real-time character streaming
- **Shortcuts** — common hotkeys (⌘C, ⌘V, ⌘Z, etc.), arrow keys, Escape, Enter, Space
- **Click controls** — tap for left click, double-tap or button for double click, dedicated right click button
- **Media keys** — play/pause, next, previous track

## Requirements

- Python 3
- Both devices on the same WiFi network
- macOS or Linux (macOS recommended)

## Setup

```bash
pip install pyautogui websockets qrcode
python server.py
```

Scan the QR code shown in the terminal with your phone, or open the printed URL in your phone's browser.

## How it works

The server runs two services:

- **HTTP server** (port 8234) — serves the mobile web interface
- **WebSocket server** (port 8235) — receives touch/keyboard events and translates them to system input via `pyautogui`

The phone's browser connects over WebSocket and sends touch deltas, scroll velocities, key presses, and text input in real time.

## Scroll behavior

Scrolling uses a velocity model rather than discrete swipe-to-scroll:

1. Touch the scroll strip (right side of trackpad)
2. Drag up or down — the further you drag from your initial touch point, the faster it scrolls
3. Move back toward the touch point to slow down
4. Release to stop

## Customization

In `index.html`:
- `SCROLL_VELOCITY_SCALE` — scroll sensitivity (default `0.02`)

In `server.py`:
- `SENSITIVITY` — mouse movement multiplier (default `1.8`)
- `SCROLL_SENSITIVITY` — scroll multiplier (default `0.5`)
- `HTTP_PORT` / `WS_PORT` — server ports

## License

MIT
