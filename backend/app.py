"""
PDS-32: Backend Server - Système IoT de Gestion Énergétique
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import paho.mqtt.client as mqtt
import sqlite3
import json
from datetime import datetime, timedelta
import threading
import time
import os

app = Flask(__name__)
CORS(app)

# ==================== CONFIGURATION ====================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPICS = [
    ("home/energy/power", 0),
    ("home/sensors/environment", 0),
    ("home/sensors/presence", 0),
    ("home/actuators/status", 0),
    ("home/status/device", 0)
]

DATA_DIR = '/app/data'
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, 'energy_data.db')
ELECTRICITY_TARIF = 0.15  # TND/kWh

# ... GLOBAL STATES ...
device_live_status = "offline"
last_seen = "Jamais"
# ==================== DATABASE SETUP ====================
def init_database():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Table: energy_data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS energy_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            power REAL,
            voltage REAL,
            current REAL,
            energy_total REAL,
            cost REAL
        )
    ''')
    
    # Table: sensor_readings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            temperature REAL,
            humidity REAL,
            light_level INTEGER
        )
    ''')
    
    # Table: presence_data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presence_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            presence BOOLEAN
        )
    ''')
    
    # Table: actuator_states
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actuator_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            relay1 BOOLEAN,
            relay2 BOOLEAN,
            auto_mode BOOLEAN
        )
    ''')
    
    # Table: alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            resolved BOOLEAN DEFAULT 0
        )
    ''')
    
    # Indexes pour performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_timestamp ON energy_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensors_timestamp ON sensor_readings(timestamp)')
    
    conn.commit()
    conn.close()
    print("✓ Database initialized")

# ==================== MQTT CLIENT ====================
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    """Callback quand connecté au broker MQTT"""
    if rc == 0:
        print("✓ Connected to MQTT Broker")
        for topic, qos in MQTT_TOPICS:
            client.subscribe(topic, qos)
            print(f"  Subscribed to: {topic}")
    else:
        print(f"✗ Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback quand un message MQTT est reçu"""
    global device_live_status, last_seen
    try:
        # 1. On décode d'abord le message en texte brut (String)
        raw_payload = msg.payload.decode()
        topic = msg.topic
        # 2. Cas spécial : Le Statut (ce n'est pas du JSON !)
        if topic == "home/status/device":
            device_live_status = raw_payload.strip().lower()  # Stocke "online" ou "offline"
            print(f"📡 Device is now: {device_live_status.upper()}")
            print(f"DEBUG: Statut reçu sur Python -> {device_live_status}")
            if device_live_status == "online":
                last_seen = (datetime.now() + timedelta(hours=1)).strftime("%H:%M:%S")

            return # On s'arrête ici pour ce topic

        # 3. Pour les autres topics, on décode le JSON
        payload = json.loads(raw_payload)
        print(f"📨 Received [{topic}]: {payload}")
        
        # 4. Traitement des données JSON
        if topic == "home/energy/power":
            store_energy_data(payload)
            check_energy_alerts(payload)
            
        elif topic == "home/sensors/environment":
            store_sensor_data(payload)
            check_temperature_alerts(payload)
            
        elif topic == "home/sensors/presence":
            store_presence_data(payload)
            
        elif topic == "home/actuators/status":
            store_actuator_state(payload)
            
    except json.JSONDecodeError:
        print(f"✗ Erreur : Le message sur {topic} n'est pas un JSON valide")
    except Exception as e:
        print(f"Error processing message: {e}")

def store_energy_data(data):
    """Stocke les données énergétiques"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cost = data.get('energy_total', 0) * ELECTRICITY_TARIF
    
    cursor.execute('''
        INSERT INTO energy_data (device_id, power, voltage, current, energy_total, cost)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get('device_id'),
        data.get('power'),
        data.get('voltage'),
        data.get('current'),
        data.get('energy_total'),
        cost
    ))
    
    conn.commit()
    conn.close()

def store_sensor_data(data):
    """Stocke les données des capteurs"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sensor_readings (device_id, temperature, humidity, light_level)
        VALUES (?, ?, ?, ?)
    ''', (
        data.get('device_id'),
        data.get('temperature'),
        data.get('humidity'),
        data.get('light_level')
    ))
    
    conn.commit()
    conn.close()

def store_presence_data(data):
    """Stocke les données de présence"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO presence_data (device_id, presence)
        VALUES (?, ?)
    ''', (
        data.get('device_id'),
        data.get('presence')
    ))
    
    conn.commit()
    conn.close()

def store_actuator_state(data):
    """Stocke l'état des actionneurs"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Vérifier si la table a la colonne 'window'
    cursor.execute("PRAGMA table_info(actuator_states)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'window' not in columns:
        # Ajouter la colonne window si elle n'existe pas
        cursor.execute('ALTER TABLE actuator_states ADD COLUMN window BOOLEAN DEFAULT 0')
        conn.commit()
        print("✓ Column 'window' added to actuator_states table")

    cursor.execute('''
        INSERT INTO actuator_states (device_id, relay1, relay2, window, auto_mode)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('device_id'),
        data.get('relay1'),
        data.get('relay2'),
        data.get('window', False),
        data.get('auto_mode')
    ))
    
    conn.commit()
    conn.close()

def check_energy_alerts(data):
    """Vérifie et génère des alertes énergétiques"""
    power = data.get('power', 0)
    
    if power > 2000:
        create_alert("HIGH_CONSUMPTION", "WARNING", f"Consommation élevée: {power}W")
    
    if power == 0:
        create_alert("POWER_FAILURE", "CRITICAL", "Aucune consommation détectée")

def check_temperature_alerts(data):
    """Vérifie les alertes de température"""
    temp = data.get('temperature', 0)
    
    if temp > 30:
        create_alert("HIGH_TEMPERATURE", "WARNING", f"Température élevée: {temp}°C")
    elif temp < 15:
        create_alert("LOW_TEMPERATURE", "WARNING", f"Température basse: {temp}°C")

def create_alert(alert_type, severity, message):
    """Crée une alerte dans la base de données"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM alerts 
        WHERE alert_type = ? AND resolved = 0 
        AND timestamp > datetime('now', '-1 hour')
    ''', (alert_type,))
    
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO alerts (alert_type, severity, message)
            VALUES (?, ?, ?)
        ''', (alert_type, severity, message))
        
        conn.commit()
        print(f"🚨 ALERT: [{severity}] {message}")
    
    conn.close()

# ==================== API ENDPOINTS ====================
@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('api.html')

@app.route('/dashboard')
def dashboard():
    """Page dashboard"""
    return render_template('dashboard.html')

@app.route('/api/energy/current', methods=['GET'])
def get_current_energy():
    """Récupère les données énergétiques actuelles"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT power, voltage, current, energy_total, cost, timestamp
        FROM energy_data
        ORDER BY timestamp DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'power': row[0],
            'voltage': row[1],
            'current': row[2],
            'energy_total': row[3],
            'cost': row[4],
            'timestamp': row[5]
        })
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/api/energy/history', methods=['GET'])
def get_energy_history():
    """Récupère l'historique énergétique"""
    hours = request.args.get('hours', default=24, type=int)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, power, energy_total, cost
        FROM energy_data
        WHERE timestamp > datetime('now', '-' || ? || ' hours')
        ORDER BY timestamp ASC
    ''', (hours,))
    
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'timestamp': row[0],
            'power': row[1],
            'energy_total': row[2],
            'cost': row[3]
        })
    
    return jsonify(data)

@app.route('/api/history', methods=['GET'])
def get_device_history():
    """Récupère l'historique consolidé des dernières activités"""
    limit = request.args.get('limit', default=20, type=int)
    limit = max(1, min(limit, 100))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM (
            SELECT
                timestamp,
                'energy' as category,
                device_id,
                printf('Puissance: %.2fW | Énergie: %.3fkWh | Coût: %.3f TND', power, energy_total, cost) as details
            FROM energy_data

            UNION ALL

            SELECT
                timestamp,
                'sensor' as category,
                device_id,
                printf('Temp: %.1f°C | Humidité: %.1f%% | Luminosité: %d%%', temperature, humidity, light_level) as details
            FROM sensor_readings

            UNION ALL

            SELECT
                timestamp,
                'presence' as category,
                device_id,
                CASE
                    WHEN presence = 1 THEN 'Présence détectée'
                    ELSE 'Aucune présence'
                END as details
            FROM presence_data

            UNION ALL

            SELECT
                timestamp,
                'actuator' as category,
                device_id,
                printf('HVAC: %s | Lumière: %s | Auto: %s',
                    CASE WHEN relay1 = 1 THEN 'ON' ELSE 'OFF' END,
                    CASE WHEN relay2 = 1 THEN 'ON' ELSE 'OFF' END,
                    CASE WHEN auto_mode = 1 THEN 'ON' ELSE 'OFF' END
                ) as details
            FROM actuator_states
        )
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))

    history = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(history)

@app.route('/api/sensors/current', methods=['GET'])
def get_current_sensors():
    """Récupère les données des capteurs actuelles"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT temperature, humidity, light_level, timestamp
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'temperature': row[0],
            'humidity': row[1],
            'light_level': row[2],
            'timestamp': row[3]
        })
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/api/presence/current', methods=['GET'])
def get_current_presence():
    """Récupère l'état de présence actuel"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT presence, timestamp
        FROM presence_data
        ORDER BY timestamp DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'presence': bool(row[0]),
            'timestamp': row[1]
        })
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/api/actuators/status', methods=['GET'])
def get_actuators_status():
    """Récupère l'état des actionneurs"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Vérifier si la colonne window existe
    cursor.execute("PRAGMA table_info(actuator_states)")
    columns = [column[1] for column in cursor.fetchall()]
    has_window = 'window' in columns
    if has_window:
        cursor.execute('''
            SELECT relay1, relay2, window, auto_mode, timestamp
            FROM actuator_states
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
    else:
        cursor.execute('''
            SELECT relay1, relay2, auto_mode, timestamp
            FROM actuator_states
            ORDER BY timestamp DESC
            LIMIT 1
        ''')

    row = cursor.fetchone()
    conn.close()

    if row:
        if has_window:
            return jsonify({
                'relay1': bool(row[0]),
                'relay2': bool(row[1]),
                'window': bool(row[2]),
                'auto_mode': bool(row[3]),
                'timestamp': row[4]
            })
        else:
            return jsonify({
                'relay1': bool(row[0]),
                'relay2': bool(row[1]),
                'window': False,
                'auto_mode': bool(row[2]),
                'timestamp': row[3]
            })
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/api/control/relay', methods=['POST'])
def control_relay():
    """Contrôle les relais"""
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'Command required'}), 400
    
    # Publier la commande via MQTT
    payload = json.dumps({'command': command})
    mqtt_client.publish('home/control/command', payload)
    
    print(f"📤 Command sent: {command}")
    
    return jsonify({'status': 'success', 'command': command})

@app.route('/api/analytics/consumption', methods=['GET'])
def get_consumption_analytics():
    """Analyse de consommation"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Consommation aujourd'hui
    cursor.execute('''
        SELECT MAX(energy_total) - MIN(energy_total), MAX(cost) - MIN(cost)
        FROM energy_data
        WHERE DATE(timestamp) = DATE('now')
    ''')
    
    today_row = cursor.fetchone()
    today_energy = today_row[0] if today_row[0] else 0
    today_cost = today_row[1] if today_row[1] else 0
    
    # Consommation hier
    cursor.execute('''
        SELECT MAX(energy_total) - MIN(energy_total), MAX(cost) - MIN(cost)
        FROM energy_data
        WHERE DATE(timestamp) = DATE('now', '-1 day')
    ''')
    
    yesterday_row = cursor.fetchone()
    yesterday_energy = yesterday_row[0] if yesterday_row[0] else 0
    yesterday_cost = yesterday_row[1] if yesterday_row[1] else 0
    
    # Moyenne
    cursor.execute('''
        SELECT AVG(power)
        FROM energy_data
        WHERE timestamp > datetime('now', '-24 hours')
    ''')
    
    avg_power = cursor.fetchone()[0] or 0
    
    # Pic
    cursor.execute('''
        SELECT MAX(power), timestamp
        FROM energy_data
        WHERE timestamp > datetime('now', '-24 hours')
    ''')
    
    peak_row = cursor.fetchone()
    peak_power = peak_row[0] if peak_row[0] else 0
    peak_time = peak_row[1] if peak_row[1] else None
    
    conn.close()
    
    potential_savings = today_cost * 0.15
    
    return jsonify({
        'today': {
            'energy': round(today_energy, 3),
            'cost': round(today_cost, 3)
        },
        'yesterday': {
            'energy': round(yesterday_energy, 3),
            'cost': round(yesterday_cost, 3)
        },
        'average_power': round(avg_power, 2),
        'peak': {
            'power': round(peak_power, 2),
            'time': peak_time
        },
        'potential_savings': round(potential_savings, 3),
        'monthly_estimate': round(today_cost * 30, 2)
    })

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Récupère les alertes"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, timestamp, alert_type, severity, message, resolved
        FROM alerts
        ORDER BY timestamp DESC
        LIMIT 50
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        alerts.append({
            'id': row[0],
            'timestamp': row[1],
            'alert_type': row[2],
            'severity': row[3],
            'message': row[4],
            'resolved': bool(row[5])
        })
    
    return jsonify(alerts)

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Résout une alerte"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE alerts
        SET resolved = 1
        WHERE id = ?
    ''', (alert_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'alert_id': alert_id})

@app.route('/api/statistics/hourly', methods=['GET'])
def get_hourly_statistics():
    """Statistiques par heure (dernières 24h)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            strftime('%H:00', timestamp) as hour,
            AVG(power) as avg_power,
            MAX(power) as max_power,
            MIN(power) as min_power
        FROM energy_data
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY hour
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'hour': row[0],
            'avg_power': round(row[1], 2),
            'max_power': round(row[2], 2),
            'min_power': round(row[3], 2)
        })
    
    return jsonify(data)

@app.route('/api/statistics/daily', methods=['GET'])
def get_daily_statistics():
    """Statistiques journalières (derniers 7 jours)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            DATE(timestamp) as day,
            MAX(energy_total) - MIN(energy_total) as daily_energy,
            MAX(cost) - MIN(cost) as daily_cost,
            AVG(power) as avg_power
        FROM energy_data
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'day': row[0],
            'energy': round(row[1], 3) if row[1] else 0,
            'cost': round(row[2], 3) if row[2] else 0,
            'avg_power': round(row[3], 2) if row[3] else 0
        })
    
    return jsonify(data)
@app.route('/api/status/live', methods=['GET'])
def get_live_status():
    return jsonify({
        'status': device_live_status,
        #'color': 'green' if device_live_status == 'online' else 'red',
        'label': 'LIVE' if device_live_status == 'online' else 'DOWN',
        'last_seen': last_seen
    })
# ==================== MQTT THREAD ====================
def mqtt_loop():
    """Thread pour le client MQTT"""
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    print("Connecting to MQTT Broker...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"MQTT Error: {e}")

# ==================== MAIN ====================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  PDS-32: Smart Energy Management Backend")
    print("="*50 + "\n")
    
    # Initialiser la base de données
    init_database()
    
    # Démarrer le thread MQTT
    mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
    mqtt_thread.start()
    
    print("✓ MQTT thread started")
    print("✓ Starting Flask server...\n")
    
    # Démarrer le serveur Flask
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
