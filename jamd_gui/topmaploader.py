import threading
import time
import requests
import tkinter as tk
from dronekit import connect, VehicleMode, Command
import serial.tools.list_ports
from TopDroneMap import app  # Your Flask app
import webview

BAUDRATE = 57600
TIMEOUT = 90

# Run Flask app in background thread
def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(debug=False, use_reloader=False)

def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print("[✓] Flask server is live!")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

# Your Drone GUI without map (can expand this with your full functions)
class DroneGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Drone Control GUI")
        label = tk.Label(self.root, text="Drone Control GUI here")
        label.pack(padx=20, pady=20)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

    def close(self):
        self.root.destroy()

if __name__ == "__main__":
    # Start Flask server in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Wait for Flask server to start
    if not wait_for_server("http://127.0.0.1:5000", 15):
        print("❌ Flask server failed to start.")
        exit(1)

    # Start webview in the main thread (this blocks until window closed)
    webview.create_window("TopDroneMap", "http://127.0.0.1:5000")
    webview.start()

    # After webview window closes, launch your Tkinter GUI
