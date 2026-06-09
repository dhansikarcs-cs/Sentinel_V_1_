"""Background crisis monitor — sends Windows toast alerts when not logged in.

Run: python crisis_monitor.py
Optional: pythonw crisis_monitor.py  (no console window)
"""
import os
import sys
import time
import sqlite3
import subprocess
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "sentinel.db")
POLL_INTERVAL = 3
NOTIFIED_FILE = os.path.join(DATA_DIR, ".crisis_notified")


def _load_notified():
    try:
        with open(NOTIFIED_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"triggered_at": "", "patient": ""}


def _save_notified(state):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump(state, f)


def _get_crisis():
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM crisis_state ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return dict(row)
    except Exception:
        return None


def _windows_toast(title, body):
    try:
        ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) | Out-Null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{body}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Sentinel Crisis Monitor").Show($toast)
'''
        subprocess.run(
            ["powershell", "-Command", ps],
            capture_output=True, timeout=5,
        )
        return True
    except Exception:
        pass
    try:
        subprocess.run(
            ["powershell", "-Command",
             f'Add-Type -AssemblyName System.Windows.Forms; '
             f'$n = New-Object System.Windows.Forms.NotifyIcon; '
             f'$n.Icon = [System.Drawing.SystemIcons]::Warning; '
             f'$n.BalloonTipTitle = "{title}"; '
             f'$n.BalloonTipText = "{body}"; '
             f'$n.Visible = $true; '
             f'$n.ShowBalloonTip(15000); '
             f'Start-Sleep 15; $n.Dispose()'],
            capture_output=True, timeout=20,
        )
        return True
    except Exception:
        return False


def _play_beep():
    try:
        import ctypes
        ctypes.windll.kernel32.Beep(880, 500)
        time.sleep(0.2)
        ctypes.windll.kernel32.Beep(880, 500)
        time.sleep(0.2)
        ctypes.windll.kernel32.Beep(880, 500)
    except Exception:
        print("\a", end="", flush=True)


def main():
    print(f"[{datetime.now().isoformat()[:19]}] Sentinel Crisis Monitor started")
    print(f"  Watching: {DB_PATH}")
    print(f"  Interval: {POLL_INTERVAL}s")
    print("  Press Ctrl+C to stop")

    _notified = _load_notified()
    while True:
        try:
            crisis = _get_crisis()
            if crisis and crisis.get("active"):
                ts = crisis.get("triggered_at", "")
                patient = crisis.get("patient_username", "")
                if ts != _notified.get("triggered_at") or patient != _notified.get("patient"):
                    _name = patient
                    if patient and not patient.startswith("psych:"):
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            row = conn.execute(
                                "SELECT patient_name FROM patient_profiles WHERE username=?", (patient,)
                            ).fetchone()
                            conn.close()
                            if row:
                                _name = row[0]
                        except Exception:
                            pass
                    elif patient.startswith("psych:"):
                        _name = f"Psychologist ({patient[6:]})"
                    _title = "SENTINEL CRISIS ALERT"
                    _body = f"{_name} is in crisis!"
                    print(f"[{datetime.now().isoformat()[:19]}] CRISIS: {_name}")
                    _windows_toast(_title, _body)
                    _play_beep()
                    _notified = {"triggered_at": ts, "patient": patient}
                    _save_notified(_notified)
            elif not (crisis and crisis.get("active")):
                if _notified.get("triggered_at"):
                    print(f"[{datetime.now().isoformat()[:19]}] Crisis resolved")
                    _windows_toast("Sentinel", "Crisis has been resolved.")
                    _notified = {"triggered_at": "", "patient": ""}
                    _save_notified(_notified)
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().isoformat()[:19]}] Stopped")
            break
        except Exception as e:
            print(f"[{datetime.now().isoformat()[:19]}] Error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
