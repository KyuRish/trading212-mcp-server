"""
Home Assistant notification module for Trading 212 alerts.
Uses HA's REST API to send push notifications via the Companion app.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


class HomeAssistantNotifier:
    def __init__(self, config: dict):
        self.ha_url = config["url"].rstrip("/")
        self.token = config["token"]
        self.device_name = config["device_name"]

    def _call_service(self, domain: str, service: str, data: dict) -> bool:
        """Call a Home Assistant service via REST API."""
        url = f"{self.ha_url}/api/services/{domain}/{service}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f"[{datetime.now()}] HA API error: {e}")
            return False

    def send_alert(self, title: str, message: str, data: dict = None) -> bool:
        """
        Send a push notification via Home Assistant Companion app.

        Args:
            title: Notification title
            message: Notification body text
            data: Optional extra data (actions, color, etc.)
        """
        service_data = {
            "title": title,
            "message": message,
            "data": data or {}
        }

        # Add default notification styling
        if "data" not in service_data:
            service_data["data"] = {}

        service_data["data"].setdefault("push", {})
        service_data["data"]["push"]["sound"] = "default"

        # Use the mobile app notify service
        service_name = f"mobile_app_{self.device_name}"

        success = self._call_service("notify", service_name, service_data)

        if success:
            print(f"[{datetime.now()}] Notification sent: {title}")
        else:
            print(f"[{datetime.now()}] Failed to send notification: {title}")

        return success

    def send_critical_alert(self, title: str, message: str) -> bool:
        """Send a critical/important notification that bypasses DND."""
        data = {
            "push": {
                "sound": {
                    "name": "default",
                    "critical": 1,
                    "volume": 1.0
                }
            },
            "importance": "high",
            "priority": "high",
            "ttl": 0
        }
        return self.send_alert(title, message, data)

    def send_actionable_alert(self, title: str, message: str, actions: list) -> bool:
        """
        Send notification with action buttons.

        Args:
            actions: List of dicts with 'action', 'title' keys
                    e.g., [{"action": "BUY", "title": "Buy Now"}]
        """
        data = {
            "actions": actions,
            "push": {"sound": "default"}
        }
        return self.send_alert(title, message, data)


def build_trading_notification(alert_type: str, data: dict) -> tuple[str, str, dict]:
    """
    Build notification content based on alert type.

    Returns: (title, message, extra_data)
    """

    if alert_type == "gold_opportunity":
        title = "Gold Buying Opportunity"
        message = (
            f"Gold dropped {data['drop_percent']:.1f}% to EUR {data['current_price']:.2f}/g\n"
            f"Your EUR 400 now buys {data['grams_per_400']:.2f}g\n"
            f"Progress: {data['current_grams']}g / {data['target_grams']}g"
        )
        extra = {
            "group": "trading",
            "tag": "gold-opportunity",
            "color": "#22c55e",  # Green
            "icon_url": "https://em-content.zobj.net/source/apple/391/chart-increasing_1f4c8.png"
        }
        return title, message, extra

    elif alert_type == "take_profit":
        title = "Consider Taking Profit"
        message = (
            f"Gold up {data['gain_percent']:.1f}% to EUR {data['current_price']:.2f}/g\n"
            f"{data['reason']}"
        )
        extra = {
            "group": "trading",
            "tag": "take-profit",
            "color": "#f59e0b",  # Amber
            "icon_url": "https://em-content.zobj.net/source/apple/391/money-bag_1f4b0.png"
        }
        return title, message, extra

    elif alert_type == "weekly_summary":
        status = "On track" if data.get('on_track', False) else "Behind target"
        title = f"Weekly Gold Report - {status}"
        message = (
            f"Portfolio: EUR {data['portfolio_value']:.2f}\n"
            f"Gold price: EUR {data['current_price']:.2f}/g ({data['weekly_change']:+.1f}%)\n"
            f"Equivalent: {data['equivalent_grams']:.2f}g\n"
            f"Target: {data['target_grams']}g by {data['target_date']}\n"
            f"Projected: {data['projected_grams']:.1f}g"
        )
        extra = {
            "group": "trading",
            "tag": "weekly-summary",
            "color": "#3b82f6",  # Blue
        }
        return title, message, extra

    elif alert_type == "exit_signal":
        title = f"Exit Signal - {data['ticker']}"
        message = f"{data['reason']}\n\nRecommendation: {data['recommendation']}"
        extra = {
            "group": "trading",
            "tag": "exit-signal",
            "color": "#ef4444",  # Red
            "importance": "high"
        }
        return title, message, extra

    elif alert_type == "news_alert":
        title = f"Market Alert"
        message = f"{data['headline']}\n\n{data['impact']}"
        extra = {
            "group": "trading",
            "tag": "news",
            "color": "#8b5cf6",  # Purple
        }
        return title, message, extra

    else:
        return alert_type, str(data), {}
