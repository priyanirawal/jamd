from flask import Flask, render_template_string, request, jsonify
import threading
import webbrowser
import time
import os

app = Flask(__name__)

saved_coords = []
phase = 1

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
        </style>
    </head>
    <body>
        <div id="map"></div>
        <button id="finishBtn" onclick="finish()">Finish</button>
        <script>
            var map = L.map('map').setView([42.384187, -71.066847], 40);
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Tiles © Esri',
                maxZoom: 18
            }).addTo(map);

            var points = [];
            var markers = [];
            var polyline = L.polyline(points, {color: 'blue'}).addTo(map);

            map.on('click', function(e) {
                var lat = e.latlng.lat.toFixed(6);
                var lon = e.latlng.lng.toFixed(6);
                points.push([lat, lon]);
                polyline.setLatLngs(points);
                var marker = L.marker(e.latlng).addTo(map);
                markers.push(marker);
                marker.bindPopup("Waypoint " + points.length + "<br>Lat: " + lat + "<br>Lon: " + lon).openPopup();
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
    ''', phase=phase)

@app.route('/save_coords', methods=['POST'])
def save_coords():
    data = request.get_json()
    lat = float(data['lat'])
    lon = float(data['lon'])
    saved_coords.append((lat, lon))
    print(f"[\u2713] Saved: ({lat}, {lon})")
    return jsonify(status='ok')

@app.route('/finish', methods=['POST'])
def finish():
    threading.Thread(target=complete_after_map).start()
    return jsonify(done=True)

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
    global phase, saved_coords
    time.sleep(1)

    if not saved_coords:
        print("No coordinates selected.")
        return

    print(f"\n=== Phase {phase} Coordinates Collected ===")
    for i, (lat, lon) in enumerate(saved_coords, 1):
        print(f"coord{i} = ({lat}, {lon})")

    waypoints = [
        {'seq': 0, 'current': 0, 'frame': 3, 'command': 22, 'param1': 0, 'param2': 0, 'param3': 0, 'param4': 0,
         'latitude': 0.0, 'longitude': 0.0, 'altitude': 3.0},
    ]

    seq = 1
    for i, (lat, lon) in enumerate(saved_coords, start=1):
        command = 21 if i == len(saved_coords) else 16
        altitude = 0 if command == 21 else 4
        waypoints.append({
            'seq': seq, 'current': 0, 'frame': 3, 'command': command,
            'param1': 0, 'param2': 0, 'param3': 0, 'param4': 0,
            'latitude': lat, 'longitude': lon, 'altitude': altitude
        })
        seq += 1

    for idx, wp in enumerate(waypoints):
        wp['seq'] = idx + 1

    create_waypoint_file("BDWP.waypoints", waypoints)
    print("\n[\u2713] Saved 'BDWP.waypoints'")

    saved_coords.clear()
    phase = 2
    threading.Timer(1, open_browser).start()
    os._exit(0)

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=False, use_reloader=False)
