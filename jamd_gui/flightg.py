from dronekit import connect, VehicleMode, Command
import time
import serial.tools.list_ports

DRONE1_WAYPOINT_FILE = "drone1.waypoints"
DRONE2_WAYPOINT_FILE = "drone2.waypoints"
SERVO_CHANNEL = 8
TRIGGER_PWM = 1900

def scan_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def connect_to_drone(ignore_ports=[], baudrate=57600, timeout=10):
    ports = scan_ports()
    print(f"Available COM ports: {ports}")
    for port in ports:
        if port in ignore_ports:
            continue
        try:
            print(f"Trying to connect on {port}...")
            vehicle = connect(port, baud=baudrate, wait_ready=True, timeout=timeout)
            print(f"Connected to vehicle on {port}")
            return vehicle, port
        except Exception as e:
            print(f"Failed to connect on {port}: {e}")
    raise RuntimeError("No MAVLink devices found on available COM ports")

def arm_vehicle_guided(vehicle):
    print("Switching to GUIDED mode for Drone 1...")
    vehicle.mode = VehicleMode("GUIDED")
    while vehicle.mode.name != "GUIDED":
        print(f" Waiting for GUIDED mode. Current: {vehicle.mode.name}")
        time.sleep(1)
    print("Arming Drone 1...")
    vehicle.armed = True
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)
    print("Drone 1 Armed!")

def arm_vehicle_stabilize(vehicle):
    print("Switching to STABILIZE mode for Drone 2...")
    vehicle.mode = VehicleMode("STABILIZE")
    while vehicle.mode.name != "STABILIZE":
        print(f" Waiting for STABILIZE mode. Current: {vehicle.mode.name}")
        time.sleep(1)
    print("Arming Drone 2...")
    vehicle.armed = True
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)
    print("Drone 2 Armed in STABILIZE!")
    print("Increasing throttle slightly...")
    vehicle.channels.overrides['3'] = 100
    time.sleep(2)
    print("Throttle nudge done. Clearing override.")
    vehicle.channels.overrides['3'] = None

def read_mission(file_path):
    cmds = []
    with open(file_path, "r") as f:
        lines = f.readlines()
    if not lines[0].strip() == "QGC WPL 110":
        raise ValueError("Invalid .waypoints file format")
    for line in lines[1:]:
        vals = line.strip().split('\t')
        cmd = Command(
            0, 0, 0,
            int(vals[2]), int(vals[3]), 0, 0,
            float(vals[4]), float(vals[5]), float(vals[6]), float(vals[7]),
            float(vals[8]), float(vals[9]), float(vals[10])
        )
        cmds.append(cmd)
    return cmds

def upload_mission(vehicle, mission_cmds):
    print("Clearing existing mission...")
    vehicle.commands.clear()
    vehicle.flush()
    print(f"Uploading mission with {len(mission_cmds)} commands...")
    for cmd in mission_cmds:
        vehicle.commands.add(cmd)
    vehicle.flush()
    print("Mission upload complete.")

def start_mission(vehicle):
    print("Switching to AUTO mode...")
    vehicle.mode = VehicleMode("AUTO")
    while vehicle.mode.name != "AUTO":
        print(f" Waiting for AUTO mode. Current: {vehicle.mode.name}")
        time.sleep(1)
    print("Mission started!")

def wait_for_rcin_pwm(vehicle, channel, threshold):
    latest_pwm = {'value': 0}

    def rc_listener(self, name, message):
        pwm = getattr(message, f'chan{channel}_raw', 0)
        latest_pwm['value'] = pwm
        print(f"RC Input channel {channel} PWM update: {pwm}")

    print(f"Waiting for RC Input channel {channel} to reach ≥ {threshold} PWM...")
    vehicle.add_message_listener('RC_CHANNELS', rc_listener)

    while latest_pwm['value'] < threshold:
        print(f"Current PWM: {latest_pwm['value']} (waiting for {threshold})")
        time.sleep(1)

    print(f"RC Input channel {channel} triggered at {latest_pwm['value']} PWM!")
    vehicle.remove_message_listener('RC_CHANNELS', rc_listener)

def run_drone_1(ignored_ports):
    print("\n==== Connecting to Drone 1 ====")
    vehicle, port = connect_to_drone(ignore_ports=ignored_ports)
    mission = read_mission(DRONE1_WAYPOINT_FILE)
    upload_mission(vehicle, mission)
    arm_vehicle_guided(vehicle)
    start_mission(vehicle)
    return vehicle, port

def run_drone_2(ignored_ports, drone1_vehicle):
    print("\n==== Connecting to Drone 2 ====")
    vehicle, port = connect_to_drone(ignore_ports=ignored_ports)
    print("Waiting for RCIN channel condition on Drone 1 before arming Drone 2...")
    wait_for_rcin_pwm(drone1_vehicle, SERVO_CHANNEL, TRIGGER_PWM)
    arm_vehicle_stabilize(vehicle)

    # Load and run mission for Drone 2
    mission = read_mission(DRONE2_WAYPOINT_FILE)
    upload_mission(vehicle, mission)
    start_mission(vehicle)

    return vehicle, port

if __name__ == "__main__":
    used_ports = []

    drone1, port1 = run_drone_1(used_ports)
    used_ports.append(port1)

    drone2, port2 = run_drone_2(used_ports, drone1)
    used_ports.append(port2)

    print("\n✅ Setup complete.")
    print("✅ Drone 1 and Drone 2 missions both started.")
