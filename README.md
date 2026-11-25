# NetPulse

A lightweight Windows desktop utility built with Python (`psutil`, `sqlite3`, `pywebview`) and a dark-mode HTML/Chart.js interface to monitor real-time bandwidth, log daily data consumption, inspect active network processes, and switch DNS resolvers with one click.

## Features
- **Live Throughput & Usage Tracking:** Monitors real-time download/upload speeds, tracks current session usage, and persists daily totals in SQLite (`usage_history.db`).
- **7-Day Usage Chart:** Visualizes recent daily data consumption directly inside the desktop dashboard.
- **Active Network Processes:** Lists top processes with active `ESTABLISHED` network sockets.
- **One-Click DNS Switcher & Latency Check:** Switch active network adapter DNS between Cloudflare (`1.1.1.1`), Google (`8.8.8.8`), Quad9 (`9.9.9.9`), or ISP DHCP (`Auto`), flush DNS cache, and run a quick ping check *(run terminal as Administrator to modify DNS)*.

## Quick Start (Windows)
1. Clone or download this repository and open a terminal in the project folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
