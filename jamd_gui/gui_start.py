import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import threading
import requests

class DroneControlGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Drone Management System")

        self.stream_url = "http://192.168.1.123:81/stream"  # Update this with actual url

        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(menu=filemenu, label='File')
        self.root.config(menu=menubar)

        # Connection
        tk.Label(self.root, text="Drone Connection", font=('Arial', 16, 'bold')).pack(pady=(10, 0))
        tk.Button(self.root, text="Connect to Drone", command=self.connect_drone).pack()
        self.status_label = tk.Label(self.root, text="Status: Disconnected", fg="red")
        self.status_label.pack()

        # Command buttons
        tk.Label(self.root, text="Controls", font=('Arial', 16, 'bold')).pack(pady=(15, 0))
        control_frame = tk.Frame(self.root)
        control_frame.pack()
        tk.Button(control_frame, text="Takeoff", command=self.takeoff).grid(row=0, column=0, padx=5)
        tk.Button(control_frame, text="Land", command=self.land).grid(row=0, column=1, padx=5)
        tk.Button(control_frame, text="Return", command=self.return_home).grid(row=0, column=2, padx=5)

        # Telemetry
        tk.Label(self.root, text="Telemetry", font=('Arial', 16, 'bold')).pack(pady=(15, 0))
        self.telemetry_text = tk.Text(self.root, height=6, width=50)
        self.telemetry_text.pack()

        # Camera Feed
        tk.Label(self.root, text="Live Camera Feed", font=('Arial', 16, 'bold')).pack(pady=(15, 0))
        self.video_label = tk.Label(self.root)
        self.video_label.pack()
        self.cap = None
        self.running = True

        # Start video thread
        threading.Thread(target=self.show_video, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def connect_drone(self):
        self.status_label.config(text="Status: Connected", fg="green")
        messagebox.showinfo("Connected", "Drone connected successfully")

    def takeoff(self):
        self.append_log("Command: Takeoff sent")

    def land(self):
        self.append_log("Command: Land sent")

    def return_home(self):
        self.append_log("Command: Return to home sent")

    def append_log(self, text):
        self.telemetry_text.insert(tk.END, text + "\n")
        self.telemetry_text.see(tk.END)

    def show_video(self):
        try:
            self.cap = cv2.VideoCapture(self.stream_url)
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)
                else:
                    self.append_log("Camera feed error...")
        except Exception as e:
            self.append_log(f"Error connecting to camera: {e}")

    def on_closing(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.root.destroy()

DroneControlGUI()
