"""
Trading 212 Gold Tracker Service

A simple HTTP service that runs the analyzer and can be controlled via REST API.
Home Assistant can use this to start/stop analysis and trigger manual runs.

Usage:
    python analyzer_service.py

Endpoints:
    GET  /status     - Check if service is running
    POST /run        - Trigger manual analysis now
    POST /stop       - Stop the service gracefully
    GET  /health     - Health check endpoint
"""

import json
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from daily_analyzer import DailyAnalyzer

# Global state
service_running = True
last_analysis = None
analyzer = None


class AnalyzerHandler(BaseHTTPRequestHandler):
    """HTTP handler for analyzer control endpoints."""

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        global last_analysis

        if self.path == "/status":
            self.send_json({
                "running": service_running,
                "last_analysis": last_analysis,
                "time": datetime.now().isoformat()
            })

        elif self.path == "/health":
            self.send_json({"status": "ok"})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        global service_running, last_analysis, analyzer

        if self.path == "/run":
            # Trigger manual analysis
            try:
                if analyzer is None:
                    config_path = Path(__file__).parent / "alert_config.json"
                    analyzer = DailyAnalyzer(str(config_path))

                alerts = analyzer.run()
                last_analysis = datetime.now().isoformat()
                self.send_json({
                    "success": True,
                    "alerts_sent": alerts,
                    "time": last_analysis
                })
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)

        elif self.path == "/stop":
            service_running = False
            self.send_json({"success": True, "message": "Service stopping..."})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_scheduler(run_time: str = "08:00"):
    """Background thread for scheduled analysis."""
    global last_analysis, analyzer, service_running

    last_run_date = None

    while service_running:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.date()

        # Check if it's time to run
        if current_time >= run_time and last_run_date != current_date:
            print(f"\n[{now}] Running scheduled analysis...")
            try:
                if analyzer is None:
                    config_path = Path(__file__).parent / "alert_config.json"
                    analyzer = DailyAnalyzer(str(config_path))

                analyzer.run()
                last_analysis = now.isoformat()
                last_run_date = current_date
            except Exception as e:
                print(f"Error during analysis: {e}")

        time.sleep(60)


def main():
    global analyzer, service_running

    import argparse

    parser = argparse.ArgumentParser(description="Trading 212 Analyzer Service")
    parser.add_argument("--port", "-p", type=int, default=8212, help="Port to listen on")
    parser.add_argument("--time", "-t", default="08:00", help="Daily run time (HH:MM)")
    args = parser.parse_args()

    # Initialize analyzer
    config_path = Path(__file__).parent / "alert_config.json"
    if not config_path.exists():
        print("ERROR: alert_config.json not found!")
        sys.exit(1)

    analyzer = DailyAnalyzer(str(config_path))

    # Start scheduler thread
    scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(args.time,),
        daemon=True
    )
    scheduler_thread.start()

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", args.port), AnalyzerHandler)
    print(f"\n{'='*50}")
    print(f"Trading 212 Analyzer Service")
    print(f"{'='*50}")
    print(f"Listening on: http://0.0.0.0:{args.port}")
    print(f"Daily analysis at: {args.time}")
    print(f"\nEndpoints:")
    print(f"  GET  /status  - Check status")
    print(f"  GET  /health  - Health check")
    print(f"  POST /run     - Run analysis now")
    print(f"  POST /stop    - Stop service")
    print(f"{'='*50}\n")

    # Send startup notification
    if analyzer.notifier:
        analyzer.notifier.send_alert(
            "Gold Tracker Online",
            f"Service started on port {args.port}\nDaily analysis at {args.time}",
            {"group": "trading", "tag": "startup"}
        )

    try:
        while service_running:
            server.handle_request()
    except KeyboardInterrupt:
        print("\nShutting down...")

    print("Service stopped.")


if __name__ == "__main__":
    main()
