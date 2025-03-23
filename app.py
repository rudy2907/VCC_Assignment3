from flask import Flask, render_template_string, jsonify
import psutil
import threading
import time
import os
import subprocess

app = Flask(__name__)

# Variables to control load generation
cpu_load = False
memory_blocks = []

def cpu_intensive_task():
    """Function to generate CPU load"""
    while cpu_load:
        [x**2 for x in range(100000)]

def get_migration_status():
    """Check if migration is in progress"""
    try:
        with open('/var/log/vm_monitor.log', 'r') as f:
            logs = f.readlines()
            # Check last 10 lines for migration messages
            for line in logs[-10:]:
                if "initiating cloud migration" in line:
                    return "Migration in progress"
                if "Migration completed successfully" in line:
                    return "Migration completed"
        return "Monitoring"
    except:
        return "Unknown"

@app.route('/')
def home():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    status = get_migration_status()
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>VM Auto-Scaling Demo</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: #f5f5f5;
            }
            .card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            h1 { color: #333; }
            .meter { 
                height: 20px; 
                background: #e0e0e0; 
                border-radius: 5px; 
                margin-bottom: 15px; 
                overflow: hidden;
            }
            .meter > div { 
                height: 100%; 
                background: #4CAF50; 
                border-radius: 5px; 
                transition: width 0.5s;
            }
            .high { background: #f44336 !important; }
            .warning { background: #ff9800 !important; }
            button { 
                padding: 10px 15px; 
                margin: 5px; 
                cursor: pointer; 
                background: #2196F3;
                border: none;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            button:hover { background: #0b7dda; }
            .controls { 
                display: flex; 
                flex-wrap: wrap; 
                gap: 10px;
                justify-content: center;
                margin: 20px 0;
            }
            .status {
                padding: 10px 15px;
                border-radius: 4px;
                background: #e0e0e0;
                display: inline-block;
                margin-top: 10px;
            }
            .monitoring { background: #90caf9; }
            .migrating { background: #ffab91; }
            .completed { background: #a5d6a7; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>VM Auto-Scaling Demonstration</h1>
            <p>This application demonstrates automatic migration to Google Cloud Platform when resource usage exceeds 75%.</p>
            
            <div class="status {{ 'monitoring' if status == 'Monitoring' else 'migrating' if status == 'Migration in progress' else 'completed' }}">
                Status: {{ status }}
            </div>
        </div>
        
        <div class="card">
            <h2>Resource Monitoring</h2>
            
            <h3>CPU Usage: {{ cpu }}%</h3>
            <div class="meter">
                <div style="width: {{ cpu }}%" class="{{ 'high' if cpu > 75 else 'warning' if cpu > 60 else '' }}"></div>
            </div>
            
            <h3>Memory Usage: {{ memory }}%</h3>
            <div class="meter">
                <div style="width: {{ memory }}%" class="{{ 'high' if memory > 75 else 'warning' if memory > 60 else '' }}"></div>
            </div>
            
            <h3>Disk Usage: {{ disk }}%</h3>
            <div class="meter">
                <div style="width: {{ disk }}%" class="{{ 'high' if disk > 75 else 'warning' if disk > 60 else '' }}"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>Load Generation</h2>
            <p>Use these controls to generate load and trigger auto-scaling:</p>
            
            <div class="controls">
                <button onclick="window.location.href='/start-cpu-load'">Start CPU Load</button>
                <button onclick="window.location.href='/stop-cpu-load'">Stop CPU Load</button>
                <button onclick="window.location.href='/allocate-memory'">Allocate Memory</button>
                <button onclick="window.location.href='/free-memory'">Free Memory</button>
                <button onclick="window.location.href='/run-stress-test'">Run Full Stress Test</button>
            </div>
        </div>
        
        <div class="card">
            <h2>Auto-Scaling Configuration</h2>
            <ul>
                <li>Threshold: Resource usage > 75%</li>
                <li>Check interval: 60 seconds</li>
                <li>Consecutive checks needed: 5</li>
                <li>Target cloud: Google Cloud Platform</li>
                <li>VM type: e2-standard-2</li>
                <li>Region: us-central1</li>
            </ul>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template, cpu=cpu, memory=memory, disk=disk, status=status)

@app.route('/start-cpu-load')
def start_cpu_load():
    global cpu_load
    cpu_load = True
    # Start multiple threads to generate load
    for _ in range(4):  # Create 4 worker threads
        threading.Thread(target=cpu_intensive_task).start()
    return '<script>window.location.href="/"</script>'

@app.route('/stop-cpu-load')
def stop_cpu_load():
    global cpu_load
    cpu_load = False
    return '<script>window.location.href="/"</script>'

@app.route('/allocate-memory')
def allocate_memory():
    global memory_blocks
    # Allocate approximately 500MB
    memory_blocks.append(' ' * (500 * 1024 * 1024))
    return '<script>window.location.href="/"</script>'

@app.route('/free-memory')
def free_memory():
    global memory_blocks
    memory_blocks = []
    return '<script>window.location.href="/"</script>'

@app.route('/run-stress-test')
def run_stress_test():
    # Run the stress test in background
    subprocess.Popen(["stress", "--cpu", "8", "--vm", "2", "--vm-bytes", "500M", "--timeout", "300"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL)
    return '<script>window.location.href="/"</script>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
