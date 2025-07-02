import customtkinter as ctk
import subprocess
import sys
import threading
import time
from dronekit import connect, VehicleMode, Command
import serial.tools.list_ports

MDWPF = "attemp.waypoints"
BAUDRATE = 57600
TIMEOUT = 90
venv_python = sys.executable

def scan_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def read_mission(file_path):
    cmds = []
    with open(file_path, "r") as f:
        lines = f.readlines()[1:]  # skip first line
        for line in lines:
            vals = line.strip().split('\t')
            if len(vals) >= 12:
                cmds.append(Command(0, 0, 0, int(vals[2]), int(vals[3]), 0, 0,
                                    float(vals[4]), float(vals[5]), float(vals[6]), float(vals[7]),
                                    float(vals[8]), float(vals[9]), float(vals[10])))
    return cmds

def upload_mission(vehicle, mission_cmds):
    vehicle.commands.clear()
    for cmd in mission_cmds:
        vehicle.commands.add(cmd)
    vehicle.commands.upload()

def wait_for_mode(vehicle, mode):
    vehicle.mode = VehicleMode(mode)
    start = time.time()
    while time.time() - start < 10:
        if vehicle.mode.name == mode:
            return True
        time.sleep(1)
    raise TimeoutError(f"Failed to set mode {mode}")

def disarm_vehicle(vehicle):
    vehicle.armed = False
    start = time.time()
    while vehicle.armed and time.time() - start < 10:
        time.sleep(1)
        vehicle.armed = False
    if vehicle.armed:
        raise TimeoutError("Failed to disarm")

def land_vehicle(vehicle):
    vehicle.mode = VehicleMode("LAND")
    start = time.time()
    while vehicle.mode.name != "LAND" and time.time() - start < 10:
        time.sleep(1)
    if vehicle.mode.name != "LAND":
        raise TimeoutError("Failed to switch to LAND")

def arm_vehicle(vehicle):
    vehicle.armed = True
    start = time.time()
    while not vehicle.armed and time.time() - start < 10:
        time.sleep(1)
    if not vehicle.armed:
        raise TimeoutError("Failed to arm")

def wait_for_mission_completion(vehicle):
    while vehicle.commands.next > 0:
        time.sleep(2)

class DroneGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.title("Drone Control")
        self.root.geometry("1280x720")

        self.vehicle = None
        self.top_vehicle = None
        self.bottom_vehicle = None

        self.status = ctk.CTkLabel(self.root, text="Disconnected", text_color="red", font=ctk.CTkFont(size=14))
        self.status.pack(pady=5)

        self.mother_status = ctk.CTkLabel(self.root, text="Mother: Not connected", text_color="red")
        self.mother_status.pack()
        self.top_status = ctk.CTkLabel(self.root, text="Top: Not connected", text_color="red")
        self.top_status.pack()
        self.bottom_status = ctk.CTkLabel(self.root, text="Bottom: Not connected", text_color="red")
        self.bottom_status.pack()

        # === Buttons ===
        button_container = ctk.CTkFrame(self.root)
        button_container.pack(pady=10, fill="x")


        # Then the frame itself
        # === Button Container ===


        # === Frame 1: Main Controls ===
        button_frame1 = ctk.CTkFrame(button_container)
        button_frame1.pack(side="left", padx=20)

        title_label1 = ctk.CTkLabel(
            button_frame1,
            text="All Drones",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label1.pack(pady=(5, 10))

        buttons1 = [
            ("Upload Model", self.upload_model_gui),
            ("Start Mission", self.start_mission_gui),
        ]

        for text, cmd in buttons1:
            ctk.CTkButton(button_frame1, text=text, command=cmd, width=240).pack(pady=5)

        # === Frame 2: Top Drone Controls ===
        button_frame2 = ctk.CTkFrame(button_container)
        button_frame2.pack(side="left", padx=20)

        title_label2 = ctk.CTkLabel(
            button_frame2,
            text="Main Drone",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label2.pack(pady=(5, 10))

        buttons2 = [
            ("Connect to Drone", self.connect_mother_drone),
            ("Launch Mapping Tool", self.launch_M_map_tool),
            ("Upload Mission", self.upload_mission_main_drone),
            ("Upload Model", self.upload_model_gui),
            ("Start Mission", self.start_mission_main_drone),
            ("Open Servo", lambda: self.set_servo(1000)),
            ("Close Servo", lambda: self.set_servo(2000)),
            ("Arm", self.arm_main),
            ("Disarm", self.disarm_main),
            ("Land", self.land_main),
        ]

        for text, cmd in buttons2:
            ctk.CTkButton(
                button_frame2,
                text=text,
                command=cmd,
                width=240,
                fg_color="green",
                hover_color="#aa0000"
            ).pack(pady=5)

        # === Frame 3: Bottom Drone Controls ===
        button_frame3 = ctk.CTkFrame(button_container)
        button_frame3.pack(side="left", padx=20)

        title_label3 = ctk.CTkLabel(
            button_frame3,
            text="Bottom Drone",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label3.pack(pady=(5, 10))

        buttons3 = [
            ("Connect to Drone", self.connect_bottom_drone),
            ("Launch Mapping Tool", self.launch_B_map_tool),
            ("Upload Mission", self.upload_mission_bottom_drone),
            ("Start Mission", self.start_mission_bottom_drone),
            ("Arm", self.arm_bottom),
            ("Disarm", self.disarm_bottom),
            ("Land", self.land_bottom),
        ]

        for text, cmd in buttons3:
            ctk.CTkButton(
                button_frame3,
                text=text,
                command=cmd,
                width=240,
                fg_color="purple",
                hover_color="#aa0000"
            ).pack(pady=5)

        # === Frame 4: All Drones Controls ===
        button_frame4 = ctk.CTkFrame(button_container)
        button_frame4.pack(side="left", padx=20)

        title_label4 = ctk.CTkLabel(
            button_frame4,
            text="Top Drones",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label4.pack(pady=(5, 10))

        buttons4 = [
            ("Connect to Drone", self.connect_top_drone),
            ("Launch Mapping Tool", self.launch_T_map_tool),
            ("Upload Mission", self.upload_mission_top_drone),
            ("Start Mission", self.start_mission_top_drone),
            ("Arm", self.arm_top),
            ("Disarm", self.disarm_top),
            ("Land", self.land_top),
        ]

        for text, cmd in buttons4:
            ctk.CTkButton(
                button_frame4,
                text=text,
                command=cmd,
                width=240,
                fg_color="#A948BE",
                hover_color="#aa0000"
            ).pack(pady=5)

        # === Side-by-side Frame for Logs and Flight Mode ===
        bottom_frame = ctk.CTkFrame(self.root)
        bottom_frame.pack(pady=10, fill="both", expand=True)

        # === Main Drone Flight Mode Panel ===
        self.main_mode_var = ctk.StringVar(value="Unknown")
        main_mode_frame = ctk.CTkFrame(bottom_frame)
        main_mode_frame.pack(side="left", padx=10, pady=10, anchor="n")

        ctk.CTkLabel(main_mode_frame, text="Main Flight Mode:").pack()
        ctk.CTkLabel(main_mode_frame, textvariable=self.main_mode_var, text_color="cyan").pack(pady=5)

        self.main_mode_options = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "AUTO", "LAND", "RTL"]
        self.selected_main_mode = ctk.StringVar(value=self.main_mode_options[0])
        ctk.CTkOptionMenu(main_mode_frame, variable=self.selected_main_mode, values=self.main_mode_options).pack(pady=5)
        ctk.CTkButton(main_mode_frame, text="Change Mode", command=self.change_main_mode).pack(pady=5)

        # === Bottom Drone Flight Mode Panel ===
        self.bottom_mode_var = ctk.StringVar(value="Unknown")
        bottom_mode_frame = ctk.CTkFrame(bottom_frame)
        bottom_mode_frame.pack(side="left", padx=10, pady=10, anchor="n")

        ctk.CTkLabel(bottom_mode_frame, text="Bottom Flight Mode:").pack()
        ctk.CTkLabel(bottom_mode_frame, textvariable=self.bottom_mode_var, text_color="cyan").pack(pady=5)

        self.bottom_mode_options = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "AUTO", "LAND", "RTL"]
        self.selected_bottom_mode = ctk.StringVar(value=self.bottom_mode_options[0])
        ctk.CTkOptionMenu(bottom_mode_frame, variable=self.selected_bottom_mode, values=self.bottom_mode_options).pack(
            pady=5)
        ctk.CTkButton(bottom_mode_frame, text="Change Mode", command=self.change_bottom_mode).pack(pady=5)

        # === Top Drone Flight Mode Panel (optional) ===
        self.top_mode_var = ctk.StringVar(value="Unknown")
        top_mode_frame = ctk.CTkFrame(bottom_frame)
        top_mode_frame.pack(side="left", padx=10, pady=10, anchor="n")

        ctk.CTkLabel(top_mode_frame, text="Top Flight Mode:").pack()
        ctk.CTkLabel(top_mode_frame, textvariable=self.top_mode_var, text_color="cyan").pack(pady=5)

        self.top_mode_options = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "AUTO", "LAND", "RTL"]
        self.selected_top_mode = ctk.StringVar(value=self.top_mode_options[0])
        ctk.CTkOptionMenu(top_mode_frame, variable=self.selected_top_mode, values=self.top_mode_options).pack(pady=5)
        ctk.CTkButton(top_mode_frame, text="Change Mode", command=self.change_top_mode).pack(pady=5)

        # === Log Boxes Panel ===
        logs_frame = ctk.CTkFrame(bottom_frame)
        logs_frame.pack(side="left", fill="both", expand=True, padx=10)

        # Main Log Box (Drone Log)
        self.log_text = ctk.CTkTextbox(logs_frame, height=200, width=400, wrap="word")
        self.log_text.pack(side="left", pady=5, fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(logs_frame, text="Drone Log").pack(side="left", anchor="n", padx=(0, 10))

        # Terminal Mirror Log Box (Terminal Output)
        self.terminal_log = ctk.CTkTextbox(logs_frame, height=200, width=400, wrap="word", text_color="red")
        self.terminal_log.pack(side="left", pady=5, fill="both", expand=True)
        ctk.CTkLabel(logs_frame, text="Terminal Output").pack(side="left", anchor="n")

        # === Redirect stdout and stderr to terminal_log ===
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget

            def write(self, message):
                self.text_widget.insert("end", message)
                self.text_widget.see("end")

            def flush(self):
                pass

        sys.stdout = StdoutRedirector(self.terminal_log)
        sys.stderr = StdoutRedirector(self.terminal_log)


        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def connect_mother_drone(self):
        def _connect():
            self.mother_status.configure(text="Connecting...", text_color="orange")
            self.log("Scanning ports for Mother drone...")
            ports = scan_ports()
            for port in ports:
                # Avoid connecting to a port already used by another drone
                if port == getattr(self.vehicle, 'port', None) or \
                        port == getattr(self.top_vehicle, 'port', None) or \
                        port == getattr(self.bottom_vehicle, 'port', None):
                    continue
                try:
                    drone = connect(port, baud=BAUDRATE, wait_ready=True, timeout=TIMEOUT)
                    drone.port = port  # Save port info for checking later
                    self.vehicle = drone
                    self.mother_status.configure(text=f"Mother: {port}", text_color="green")
                    self.status.configure(text="Connected", text_color="green")
                    self.log(f"Mother drone connected on {port}")
                    self.update_mode_display()
                    return
                except Exception as e:
                    self.log(f"Mother drone connection failed on {port}: {e}")
            self.mother_status.configure(text="Mother: Not connected", text_color="red")
            self.status.configure(text="Failed", text_color="red")
            self.log("Mother drone connection failed.")

        threading.Thread(target=_connect, daemon=True).start()

    def connect_top_drone(self):
        def _connect():
            self.top_status.configure(text="Connecting...", text_color="orange")
            self.log("Scanning ports for Top drone...")
            ports = scan_ports()
            for port in ports:
                if port == getattr(self.vehicle, 'port', None) or \
                        port == getattr(self.top_vehicle, 'port', None) or \
                        port == getattr(self.bottom_vehicle, 'port', None):
                    continue
                try:
                    drone = connect(port, baud=BAUDRATE, wait_ready=True, timeout=TIMEOUT)
                    drone.port = port
                    self.top_vehicle = drone
                    self.top_status.configure(text=f"Top: {port}", text_color="green")
                    self.log(f"Top drone connected on {port}")
                    return
                except Exception as e:
                    self.log(f"Top drone connection failed on {port}: {e}")
            self.top_status.configure(text="Top: Not connected", text_color="red")
            self.log("Top drone connection failed.")

        threading.Thread(target=_connect, daemon=True).start()

    def connect_bottom_drone(self):
        def _connect():
            self.bottom_status.configure(text="Connecting...", text_color="orange")
            self.log("Scanning ports for Bottom drone...")
            ports = scan_ports()
            for port in ports:
                if port == getattr(self.vehicle, 'port', None) or \
                        port == getattr(self.top_vehicle, 'port', None) or \
                        port == getattr(self.bottom_vehicle, 'port', None):
                    continue
                try:
                    drone = connect(port, baud=BAUDRATE, wait_ready=True, timeout=TIMEOUT)
                    drone.port = port
                    self.bottom_vehicle = drone
                    self.bottom_status.configure(text=f"Bottom: {port}", text_color="green")
                    self.log(f"Bottom drone connected on {port}")
                    self.update_B_mode_display()
                    return
                except Exception as e:
                    self.log(f"Bottom drone connection failed on {port}: {e}")
            self.bottom_status.configure(text="Bottom: Not connected", text_color="red")
            self.log("Bottom drone connection failed.")

        threading.Thread(target=_connect, daemon=True).start()

    def launch_M_map_tool(self):
        try:
            self.log("Launching mapping tool...")
            subprocess.run([venv_python, "GUImaploader.py"], check=True)
            self.log("Mapping complete.")
        except Exception as e:
            self.log(f"Map tool failed: {e}")

    def launch_B_map_tool(self):
        try:
            self.log("Launching mapping tool...")
            subprocess.run([venv_python, "bottommaploader.py"], check=True)
            self.log("Mapping complete.")
        except Exception as e:
            self.log(f"Map tool failed: {e}")

    def launch_T_map_tool(self):
        try:
            self.log("Launching mapping tool...")
            subprocess.run([venv_python, "topmaploader.py"], check=True)
            self.log("Mapping complete.")
        except Exception as e:
            self.log(f"Map tool failed: {e}")

    def upload_mission_main_drone(self):
        def _upload():
            if not self.vehicle:
                self.log("No Mother/Main drone connected")
                return
            try:
                cmds = read_mission("attemp.waypoints")
                upload_mission(self.vehicle, cmds)
                self.log("Mission uploaded to Mother/Main drone")
            except Exception as e:
                self.log(f"Upload failed: {e}")

        threading.Thread(target=_upload, daemon=True).start()
    def upload_mission_top_drone(self):
        if not self.top_vehicle:
            self.log("No Top drone connected")
            return
        try:
            cmds = read_mission("TDWP.waypoints")
            upload_mission(self.top_vehicle, cmds)
            self.log("Mission uploaded to Top drone")
        except Exception as e:
            self.log(f"Upload to Top drone failed: {e}")

    def upload_mission_bottom_drone(self):
        if not self.bottom_vehicle:
            self.log("No Bottom drone connected")
            return
        try:
            cmds = read_mission("BDWP.waypoints")
            upload_mission(self.bottom_vehicle, cmds)
            self.log("Mission uploaded to Bottom drone")
        except Exception as e:
            self.log(f"Upload to Bottom drone failed: {e}")

    def upload_model_gui(self):
        if not self.vehicle:
            self.log("No drone connected")
            return
        try:
            cmds = read_mission("model.waypoints")
            upload_mission(self.vehicle, cmds)
            self.log("Model mission uploaded")
        except Exception as e:
            self.log(f"Upload failed: {e}")

    def arm_main(self):
        if self.vehicle:
            try:
                wait_for_mode(self.vehicle, "GUIDED")
                self.log("Arming Mother/Main drone...")
                arm_vehicle(self.vehicle)
                wait_for_mode(self.vehicle, "STABILIZE")
                self.log("Mother/Main drone armed")
            except Exception as e:
                self.log(f"Mother/Main drone arm failed: {e}")
        else:
            self.log("No Mother/Main drone connected")

    def arm_top(self):
        if self.top_vehicle:
            try:
                wait_for_mode(self.top_vehicle, "GUIDED")
                self.log("Arming Top drone...")
                arm_vehicle(self.top_vehicle)
                wait_for_mode(self.top_vehicle, "STABILIZE")
                self.log("Top drone armed")
            except Exception as e:
                self.log(f"Top drone arm failed: {e}")
        else:
            self.log("No Top drone connected")

    def arm_bottom(self):
        if self.bottom_vehicle:
            try:
                wait_for_mode(self.bottom_vehicle, "GUIDED")
                self.log("Arming Bottom drone...")
                arm_vehicle(self.bottom_vehicle)
                time.sleep(5)
                wait_for_mode(self.bottom_vehicle, "STABILIZE")
                self.log("Bottom drone armed")
            except Exception as e:
                self.log(f"Bottom drone arm failed: {e}")
        else:
            self.log("No Bottom drone connected")

    def land_main(self):
        if self.vehicle:
            try:
                land_vehicle(self.vehicle)
                self.log("Mother/Main drone landing initiated")
            except Exception as e:
                self.log(f"Mother/Main drone land failed: {e}")
        else:
            self.log("No Mother/Main drone connected")

    def land_top(self):
        if self.top_vehicle:
            try:
                land_vehicle(self.top_vehicle)
                self.log("Top drone landing initiated")
            except Exception as e:
                self.log(f"Top drone land failed: {e}")
        else:
            self.log("No Top drone connected")

    def land_bottom(self):
        if self.bottom_vehicle:
            try:
                land_vehicle(self.bottom_vehicle)
                self.log("Bottom drone landing initiated")
            except Exception as e:
                self.log(f"Bottom drone land failed: {e}")
        else:
            self.log("No Bottom drone connected")

    def disarm_main(self):
        if self.vehicle:
            try:
                wait_for_mode(self.vehicle, "STABILIZE")
                disarm_vehicle(self.vehicle)
                self.log("Mother/Main drone disarmed")
            except Exception as e:
                self.log(f"Mother/Main drone disarm failed: {e}")
        else:
            self.log("No Mother/Main drone connected")

    def disarm_top(self):
        if self.top_vehicle:
            try:
                wait_for_mode(self.top_vehicle, "STABILIZE")
                disarm_vehicle(self.top_vehicle)
                self.log("Top drone disarmed")
            except Exception as e:
                self.log(f"Top drone disarm failed: {e}")
        else:
            self.log("No Top drone connected")

    def disarm_bottom(self):
        if self.bottom_vehicle:
            try:
                wait_for_mode(self.bottom_vehicle, "STABILIZE")
                disarm_vehicle(self.bottom_vehicle)
                self.log("Bottom drone disarmed")
            except Exception as e:
                self.log(f"Bottom drone disarm failed: {e}")
        else:
            self.log("No Bottom drone connected")

    def start_mission_gui(self):
        def _start():
            try:
                wait_for_mode(self.vehicle, "GUIDED")
                arm_vehicle(self.vehicle)
                wait_for_mode(self.vehicle, "AUTO")
                self.log("Mission started")
                wait_for_mission_completion(self.vehicle)
                self.log("Mission complete")
            except Exception as e:
                self.log(f"Mission failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    def start_mission_main_drone(self):
        def _start():
            if not self.vehicle:
                self.log("No Mother/Main drone connected")
                return
            try:
                wait_for_mode(self.vehicle, "GUIDED")
                arm_vehicle(self.vehicle)
                wait_for_mode(self.vehicle, "AUTO")
                self.log("Mission started on Mother/Main drone")
                wait_for_mission_completion(self.vehicle)
                self.log("Mother/Main drone mission complete")
            except Exception as e:
                self.log(f"Mother/Main drone mission failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    def start_mission_top_drone(self):
        def _start():
            if not self.top_vehicle:
                self.log("No Top drone connected")
                return
            try:
                wait_for_mode(self.top_vehicle, "GUIDED")
                arm_vehicle(self.top_vehicle)
                wait_for_mode(self.top_vehicle, "AUTO")
                self.log("Mission started on Top drone")
                wait_for_mission_completion(self.top_vehicle)
                self.log("Top drone mission complete")
            except Exception as e:
                self.log(f"Top drone mission failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    def start_mission_bottom_drone(self):
        def _start():
            if not self.bottom_vehicle:
                self.log("No Bottom drone connected")
                return
            try:
                wait_for_mode(self.bottom_vehicle, "GUIDED")
                arm_vehicle(self.bottom_vehicle)
                wait_for_mode(self.bottom_vehicle, "AUTO")
                self.log("Mission started on Bottom drone")
                wait_for_mission_completion(self.bottom_vehicle)
                self.log("Bottom drone mission complete")
            except Exception as e:
                self.log(f"Bottom drone mission failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    def set_servo(self, pwm):
        if self.vehicle:
            self.vehicle.channels.overrides['8'] = pwm
            self.log(f"Set RC8 to {pwm}")
        else:
            self.log("No drone connected")

    def change_main_mode(self):
        if self.vehicle:
            mode = self.selected_main_mode.get()
            try:
                wait_for_mode(self.vehicle, mode)
                self.log(f"Main drone mode changed to {mode}")
            except Exception as e:
                self.log(f"Failed to change main drone mode: {e}")
        else:
            self.log("No Mother/Main drone connected")

    def change_bottom_mode(self):
        if self.bottom_vehicle:
            mode = self.selected_bottom_mode.get()
            try:
                wait_for_mode(self.bottom_vehicle, mode)
                self.log(f"Bottom drone mode changed to {mode}")
            except Exception as e:
                self.log(f"Failed to change bottom drone mode: {e}")
        else:
            self.log("No Bottom drone connected")

    def change_top_mode(self):
        if self.top_vehicle:
            mode = self.selected_top_mode.get()
            try:
                wait_for_mode(self.top_vehicle, mode)
                self.log(f"Top drone mode changed to {mode}")
            except Exception as e:
                self.log(f"Failed to change top drone mode: {e}")
        else:
            self.log("No Top drone connected")

    def update_mode_display(self):
        def _update():
            while self.vehicle:
                self.main_mode_var.set(self.vehicle.mode.name)
                time.sleep(1)
        threading.Thread(target=_update, daemon=True).start()

    def update_B_mode_display(self):
        def _update():
            while self.bottom_vehicle:
                self.bottom_mode_var.set(self.bottom_vehicle.mode.name)
                time.sleep(1)

        threading.Thread(target=_update, daemon=True).start()

    def update_T_mode_display(self):
        def _update():
            while self.top_vehicle:
                self.top_mode_var.set(self.top_vehicle.mode.name)
                time.sleep(1)

        threading.Thread(target=_update, daemon=True).start()

    def close(self):
        for v in [self.vehicle, self.top_vehicle, self.bottom_vehicle]:
            if v:
                v.close()
        self.root.destroy()


if __name__ == "__main__":
    DroneGUI()
