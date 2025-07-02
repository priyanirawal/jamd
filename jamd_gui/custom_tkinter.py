import customtkinter as ctk
from tkintermapview import TkinterMapView
from PIL import Image, ImageTk
import io
import requests
import cv2
import threading

ctk.set_appearance_mode("dark")  # 'light', 'dark', or 'system'
ctk.set_default_color_theme("blue")  # or "green", "dark-blue", etc.

class DroneMissionGUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("JAMD Drone Mission GUI")
        self.geometry("1200x700")
        self.minsize(900, 600)

        # Layout: sidebar, map panel, console
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=10)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        self.map_frame = ctk.CTkFrame(self, corner_radius=10)
        self.map_frame.pack(side="left", fill="both", expand=True, padx=10, pady=(10, 5))

        self.console = ctk.CTkTextbox(self, height=100)
        self.console.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        self.setup_sidebar()
        self.setup_map()

        self.log("GUI Initialized")

    def setup_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="Controls", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 20))

        self.connect_btn = ctk.CTkButton(self.sidebar, text="Connect Drones", command=lambda: self.log("Connect Drones clicked"))
        self.connect_btn.pack(pady=10, fill="x")

        self.upload1_btn = ctk.CTkButton(self.sidebar, text="Upload Mission 1", command=lambda: self.log("Upload Mission 1 clicked"))
        self.upload1_btn.pack(pady=5, fill="x")

        self.upload2_btn = ctk.CTkButton(self.sidebar, text="Upload Mission 2", command=lambda: self.log("Upload Mission 2 clicked"))
        self.upload2_btn.pack(pady=5, fill="x")

        self.arm_btn = ctk.CTkButton(self.sidebar, text="Arm Drones", command=lambda: self.log("Arm Drones clicked"))
        self.arm_btn.pack(pady=15, fill="x")

        self.start_btn = ctk.CTkButton(self.sidebar, text="Start Missions", command=lambda: self.log("Start Missions clicked"))
        self.start_btn.pack(pady=5, fill="x")

        self.clear_btn = ctk.CTkButton(self.sidebar, text="Clear Map", command=lambda: self.log("Clear Map clicked"))
        self.clear_btn.pack(pady=25, fill="x")

        self.cam_label = ctk.CTkLabel(self.sidebar, text="Live Camera")
        self.cam_label.pack(pady=(20, 5))

        self.cam_view = ctk.CTkLabel(self.sidebar, text="(No Feed)")
        self.cam_view.pack(padx=10, pady=5, fill="x")

        # ESP32-CAM Stream URL (Change this!)
        self.esp32_url = "http://192.168.4.1/capture"

        self.update_camera()  # Start polling for camera images

        

    def setup_map(self):
        self.map_widget = TkinterMapView(self.map_frame, corner_radius=10)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(42.384187, -71.066847)  # Example: Boston
        self.map_widget.set_zoom(15)

        self.map_widget.add_left_click_map_command(self.add_marker)

    def add_marker(self, coords):
        lat, lon = coords
        self.map_widget.set_marker(lat, lon, text=f"Waypoint ({lat:.5f}, {lon:.5f})")
        self.log(f"Marker added: ({lat:.5f}, {lon:.5f})")

    def log(self, message):
        self.console.insert("end", message + "\n")
        self.console.see("end")

    def update_camera(self):
        try:
            response = requests.get(self.esp32_url, timeout=2)
            if response.status_code == 200:
                img_data = response.content
                image = Image.open(io.BytesIO(img_data)).resize((240, 180))
                photo = ImageTk.PhotoImage(image)
                self.cam_view.configure(image=photo, text="")
                self.cam_view.image = photo
        except Exception as e:
            self.cam_view.configure(text="Camera Error", image=None)
            print("Camera error:", e)
            # Repeat every 150ms
            self.after(150, self.update_camera)

if __name__ == "__main__":
    app = DroneMissionGUI()
    app.mainloop()
