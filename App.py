import os
import sqlite3
import subprocess
import time
from datetime import datetime
import psutil
import webview

DB_PATH = "usage_history.db"

class NetPulseAPI:
    def __init__(self):
        self._init_db()
        self.last_io = psutil.net_io_counters()
        self.last_time = time.time()
        self.session_down = 0
        self.session_up = 0

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                date TEXT PRIMARY KEY,
                bytes_recv INTEGER DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def _log_daily(self, d_recv, d_sent):
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO daily_usage (date, bytes_recv, bytes_sent) VALUES (?, 0, 0)", (today,))
        c.execute("UPDATE daily_usage SET bytes_recv = bytes_recv + ?, bytes_sent = bytes_sent + ? WHERE date = ?", (d_recv, d_sent, today))
        conn.commit()
        conn.close()

    def get_stats(self):
        now = time.time()
        current_io = psutil.net_io_counters()
        elapsed = max(now - self.last_time, 0.1)

        d_recv = max(0, current_io.bytes_recv - self.last_io.bytes_recv)
        d_sent = max(0, current_io.bytes_sent - self.last_io.bytes_sent)

        self.last_io = current_io
        self.last_time = now
        self.session_down += d_recv
        self.session_up += d_sent

        if d_recv > 0 or d_sent > 0:
            self._log_daily(d_recv, d_sent)

        app_counts = {}
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED" and conn.pid:
                    try:
                        name = psutil.Process(conn.pid).name()
                        app_counts[name] = app_counts.get(name, 0) + 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception:
            pass

        top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT date, bytes_recv, bytes_sent FROM daily_usage ORDER BY date DESC LIMIT 7")
        rows = c.fetchall()[::-1]
        conn.close()

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_total = 0
        history = []
        for r_date, r_recv, r_sent in rows:
            total_gb = round((r_recv + r_sent) / (1024 ** 3), 3)
            if r_date == today_str:
                today_total = total_gb
            history.append({"date": r_date[5:], "gb": total_gb})

        return {
            "down_kbps": round((d_recv / elapsed) / 1024, 1),
            "up_kbps": round((d_sent / elapsed) / 1024, 1),
            "session_mb": round((self.session_down + self.session_up) / (1024 ** 2), 2),
            "today_gb": today_total,
            "top_apps": [{"name": k, "conns": v} for k, v in top_apps],
            "history": history
        }

    def _get_active_interface(self):
        stats = psutil.net_if_stats()
        for iface, info in stats.items():
            if info.isup and "loopback" not in iface.lower() and "vethernet" not in iface.lower():
                if "wi-fi" in iface.lower() or "ethernet" in iface.lower():
                    return iface
        for iface, info in stats.items():
            if info.isup and "loopback" not in iface.lower():
                return iface
        return "Wi-Fi"

    def set_dns(self, primary, secondary):
        iface = self._get_active_interface()
        try:
            if primary == "auto":
                cmd = f'netsh interface ip set dns name="{iface}" dhcp'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            else:
                cmd1 = f'netsh interface ip set dns name="{iface}" static {primary}'
                cmd2 = f'netsh interface ip add dns name="{iface}" {secondary} index=2'
                res = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
                subprocess.run(cmd2, shell=True, capture_output=True, text=True)

            subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
            if res.returncode != 0:
                return {"ok": False, "msg": "Run terminal as Administrator to change DNS."}
            return {"ok": True, "msg": f"DNS updated on {iface} & cache flushed!"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def ping_test(self):
        try:
            res = subprocess.run("ping -n 1 1.1.1.1", shell=True, capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "time=" in line.lower():
                    ms = line.lower().split("time=")[1].split("ms")[0].strip()
                    return {"ok": True, "ping": f"{ms} ms"}
            return {"ok": False, "ping": "Timeout"}
        except Exception:
            return {"ok": False, "ping": "Error"}

if __name__ == "__main__":
    api = NetPulseAPI()
    html_path = os.path.abspath("index.html")
    webview.create_window("NetPulse — Bandwidth & DNS Monitor", html_path, js_api=api, width=920, height=640)
    webview.start()