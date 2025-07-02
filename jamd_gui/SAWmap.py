from flask import Flask, render_template_string, request, jsonify
import threading
import webbrowser
import time
import requests  # for shutdown POST
import os

app = Flask(__name__)

saved_coords = []
servo_release_index = None
phase = 1
servo_home = None

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Select Coordinates</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <style>
            html, body, #map { height: 100%; margin: 0; }
            #finishBtn {
                position: fixed; top: 10px; right: 10px;
                padding: 10px; background-color: #28a745;
                color: white; border: none; border-radius: 5px;
                cursor: pointer; z-index: 9999;
            }
            .servo-button {
                margin-top: 5px;
                display: block;
                background-color: #007bff;
                color: white;
                border: none;
                padding: 4px 6px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <button id="finishBtn" onclick="finish()">Finish</button>
        <script>
            var map = L.map('map').setView([42.384187, -71.066847], 40);
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, etc.',
                maxZoom: 18
            }).addTo(map);


            var points = [];
            var markers = [];
            var polyline = L.polyline(points, {color: 'blue'}).addTo(map);

            var phase = {{ phase }};
            var servoReleaseIndex = {{ servo_release_index if servo_release_index is not none else 'null' }};
            var servoHome = {{ servo_home|tojson if servo_home else 'null' }};

            var defaultIcon = new L.Icon.Default();
            var redIcon = new L.Icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });

            function updateMarkerPopup(marker, index) {
                if (phase === 1) {
                    var content = "Waypoint " + (index + 1) + "<br>Lat: " + points[index][0] + "<br>Lon: " + points[index][1];
                    content += `<br><button class="servo-button" onclick="markServo(${index})">Mark as Servo Release</button>`;
                    marker.bindPopup(content);
                } else {
                    var content = "Waypoint " + (index + 1) + "<br>Lat: " + points[index][0] + "<br>Lon: " + points[index][1];
                    marker.bindPopup(content);
                }
            }

            function markServo(index) {
                if (phase !== 1) return;
                fetch('/set_servo_release', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({index: index})
                });
                markers.forEach((m, i) => {
                    m.setIcon(i === index ? redIcon : defaultIcon);
                });
            }

            if (phase === 2 && servoHome) {
                var homeMarker = L.marker(servoHome, {icon: redIcon}).addTo(map);
                homeMarker.bindPopup("Servo Release Point from Drone 1 (Home)").openPopup();
                points.push(servoHome);
                polyline.setLatLngs(points);
            }

            map.on('click', function(e) {
                var lat = e.latlng.lat.toFixed(6);
                var lon = e.latlng.lng.toFixed(6);

                points.push([lat, lon]);
                polyline.setLatLngs(points);

                var marker = L.marker(e.latlng, {icon: defaultIcon}).addTo(map);
                markers.push(marker);

                var idx = markers.length - 1;
                updateMarkerPopup(marker, idx);
                marker.openPopup();

                fetch('/save_coords', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: lat, lon: lon })
                });
            });

            function finish() {
                fetch('/finish', {method: 'POST'}).then(() => {
                    alert("Finished! You can close the browser and check PyCharm.");
                });
            }
        </script>
    </body>
    </html>
    ''', phase=phase, servo_release_index=servo_release_index, servo_home=servo_home)

@app.route('/save_coords', methods=['POST'])
def save_coords():
    data = request.get_json()
    lat = float(data['lat'])
    lon = float(data['lon'])
    saved_coords.append((lat, lon))
    print(f"[✓] Saved: ({lat}, {lon})")
    return jsonify(status='ok')

@app.route('/set_servo_release', methods=['POST'])
def set_servo_release():
    global servo_release_index
    data = request.get_json()
    idx = data.get('index')
    if isinstance(idx, int) and 0 <= idx < len(saved_coords):
        servo_release_index = idx
        print(f"[✓] Servo release waypoint set to index {servo_release_index + 1}")
        return jsonify(status='ok')
    else:
        return jsonify(status='error', message='Invalid index'), 400

@app.route('/finish', methods=['POST'])
def finish():
    threading.Thread(target=complete_after_map).start()
    return jsonify(done=True)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

def create_waypoint_file(filename, waypoints):
    header = "QGC WPL 110\n"
    with open(filename, 'w') as file:
        file.write(header)
        for wp in waypoints:
            line = f"{wp['seq']}\t{wp['current']}\t{wp['frame']}\t{wp['command']}\t"
            line += f"{wp['param1']:.8f}\t{wp['param2']:.8f}\t{wp['param3']:.8f}\t{wp['param4']:.8f}\t"
            line += f"{wp['latitude']:.8f}\t{wp['longitude']:.8f}\t{wp['altitude']:.6f}\t1\n"
            file.write(line)

def complete_after_map():
    global phase, saved_coords, servo_home, servo_release_index
    time.sleep(1)

    if not saved_coords:
        print("No coordinates selected.")
        return

    print(f"\n=== Phase {phase} Coordinates Collected ===")
    for i, (lat, lon) in enumerate(saved_coords, 1):
        print(f"coord{i} = ({lat}, {lon})")

    if phase == 1:
        if servo_release_index is None:
            print("No servo release waypoint marked. Please mark a waypoint before finishing.")
            return

        servo_home = saved_coords[servo_release_index]
        print(f"\n[✓] Servo will trigger after waypoint {servo_release_index + 1}")

        waypoints1 = [
            {'seq': 0, 'current': 0, 'frame': 3, 'command': 22, 'param1': 0, 'param2': 0, 'param3': 0, 'param4': 0,
             'latitude': 0.0, 'longitude': 0.0, 'altitude': 3.0},
        ]

        seq = 1
        inserted_servo = False
        for i, (lat, lon) in enumerate(saved_coords, start=1):
            command = 21 if i == len(saved_coords) else 16
            altitude = 0 if command == 21 else 6  # Fly at 4m normally


            waypoints1.append({
                'seq': seq, 'current': 0, 'frame': 3, 'command': command,
                'param1': 0, 'param2': 0, 'param3': 0, 'param4': 0,
                'latitude': lat, 'longitude': lon, 'altitude': altitude
            })
            seq += 1

            if i == servo_release_index + 1 and not inserted_servo:
                # Trigger servo
                waypoints1.append({
                    'seq': seq, 'current': 0, 'frame': 3, 'command': 183,
                    'param1': 8, 'param2': 1000, 'param3': 0, 'param4': 0,
                    'latitude': lat, 'longitude': lon, 'altitude': altitude  # still at 4m
                })
                seq += 1

                # Climb to 6 meters at same location
                waypoints1.append({
                    'seq': seq, 'current': 0, 'frame': 3, 'command': 16,
                    'param1': 0, 'param2': 0, 'param3': 0, 'param4': 0,
                    'latitude': lat, 'longitude': lon, 'altitude': 6.0
                })
                seq += 1

                inserted_servo = True

        for idx, wp in enumerate(waypoints1):
            wp['seq'] = idx + 1

        create_waypoint_file("attemp.waypoints", waypoints1)
        print("\n[✓] Saved 'attemp.waypoints'")

        saved_coords.clear()
        phase = 2
        threading.Timer(1, open_browser).start()

        os._exit(0)


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=False, use_reloader=False)
