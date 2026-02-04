"""
Email notification module for Trading 212 alerts.
Sends clean, formatted emails only when there's something worth reporting.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class EmailNotifier:
    def __init__(self, config: dict):
        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]
        self.sender_email = config["sender_email"]
        self.sender_password = config["sender_password"]
        self.recipient_email = config["recipient_email"]

    def send_alert(self, subject: str, html_content: str) -> bool:
        """Send an HTML email alert."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Trading Alert <{self.sender_email}>"
            msg["To"] = self.recipient_email

            # Create plain text version
            plain_text = html_content.replace("<br>", "\n").replace("</p>", "\n\n")
            plain_text = "".join(c for c in plain_text if c not in "<>")

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"[{datetime.now()}] Alert sent: {subject}")
            return True

        except Exception as e:
            print(f"[{datetime.now()}] Failed to send email: {e}")
            return False


def format_currency(value: float, symbol: str = "EUR") -> str:
    """Format a number as currency."""
    return f"{symbol} {value:,.2f}"


def format_percent(value: float) -> str:
    """Format a number as percentage with color indicator."""
    sign = "+" if value >= 0 else ""
    color = "#22c55e" if value >= 0 else "#ef4444"
    return f'<span style="color: {color}; font-weight: bold;">{sign}{value:.2f}%</span>'


def build_alert_email(alert_type: str, data: dict) -> tuple[str, str]:
    """
    Build email subject and HTML content based on alert type.

    Returns: (subject, html_content)
    """
    timestamp = datetime.now().strftime("%d %b %Y, %H:%M")

    base_style = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white;
                  padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }
        .metric { background: white; padding: 15px; border-radius: 8px; margin: 10px 0;
                  border-left: 4px solid #fbbf24; }
        .metric-label { color: #6b7280; font-size: 12px; text-transform: uppercase; }
        .metric-value { font-size: 24px; font-weight: bold; color: #1f2937; }
        .action { background: #fef3c7; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .footer { text-align: center; padding: 15px; color: #9ca3af; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 8px 0; }
        .progress-bar { background: #e5e7eb; border-radius: 10px; height: 20px; overflow: hidden; }
        .progress-fill { background: linear-gradient(90deg, #fbbf24, #22c55e); height: 100%; }
    </style>
    """

    if alert_type == "gold_opportunity":
        subject = f"Gold Buying Opportunity - Price dropped {data['drop_percent']:.1f}%"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="header">
                <h1 style="margin:0;">Gold Buying Opportunity</h1>
                <p style="margin:5px 0 0 0; opacity:0.9;">{timestamp}</p>
            </div>
            <div class="content">
                <div class="metric">
                    <div class="metric-label">Current Gold Price</div>
                    <div class="metric-value">{format_currency(data['current_price'])}/gram</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Price Change (7 days)</div>
                    <div class="metric-value">{format_percent(-data['drop_percent'])}</div>
                </div>
                <div class="action">
                    <strong>Why this matters:</strong><br>
                    Gold has dropped significantly. At this price, your monthly EUR 400 buys
                    <strong>{data['grams_per_400']:.2f}g</strong> instead of the usual amount.
                    Consider if this is a good entry point for additional investment.
                </div>
                <p><strong>Your progress:</strong> {data['current_grams']}g / {data['target_grams']}g target</p>
            </div>
            <div class="footer">Trading 212 Alert System</div>
        </body>
        </html>
        """
        return subject, html

    elif alert_type == "take_profit":
        subject = f"Consider Taking Profit - Gold up {data['gain_percent']:.1f}%"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="header" style="background: linear-gradient(135deg, #22c55e, #16a34a);">
                <h1 style="margin:0;">Profit Opportunity</h1>
                <p style="margin:5px 0 0 0; opacity:0.9;">{timestamp}</p>
            </div>
            <div class="content">
                <div class="metric">
                    <div class="metric-label">Current Gold Price</div>
                    <div class="metric-value">{format_currency(data['current_price'])}/gram</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Your Unrealized Gain</div>
                    <div class="metric-value">{format_percent(data['gain_percent'])}</div>
                </div>
                <div class="action">
                    <strong>Analysis:</strong><br>
                    {data['reason']}
                </div>
            </div>
            <div class="footer">Trading 212 Alert System</div>
        </body>
        </html>
        """
        return subject, html

    elif alert_type == "weekly_summary":
        progress_percent = (data['current_grams'] / data['target_grams']) * 100
        subject = f"Weekly Gold Tracker - {data['current_grams']}g / {data['target_grams']}g"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="header">
                <h1 style="margin:0;">Weekly Progress Report</h1>
                <p style="margin:5px 0 0 0; opacity:0.9;">{timestamp}</p>
            </div>
            <div class="content">
                <h3>Gold Accumulation Progress</h3>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(progress_percent, 100):.0f}%;"></div>
                </div>
                <p style="text-align:center; margin-top:5px;">
                    <strong>{data['current_grams']}g</strong> of <strong>{data['target_grams']}g</strong>
                    ({progress_percent:.1f}%)
                </p>

                <table>
                    <tr><td>Portfolio Value</td><td style="text-align:right;"><strong>{format_currency(data['portfolio_value'])}</strong></td></tr>
                    <tr><td>Gold Price (now)</td><td style="text-align:right;">{format_currency(data['current_price'])}/g</td></tr>
                    <tr><td>Weekly Change</td><td style="text-align:right;">{format_percent(data['weekly_change'])}</td></tr>
                    <tr><td>Equivalent Gold</td><td style="text-align:right;"><strong>{data['equivalent_grams']:.2f}g</strong></td></tr>
                    <tr><td>Target Date</td><td style="text-align:right;">{data['target_date']}</td></tr>
                    <tr><td>Months Remaining</td><td style="text-align:right;">{data['months_remaining']}</td></tr>
                </table>

                <div class="action">
                    <strong>Projection:</strong><br>
                    At current pace and prices, you'll accumulate approximately
                    <strong>{data['projected_grams']:.1f}g</strong> by your target date.
                    {data['projection_note']}
                </div>
            </div>
            <div class="footer">Trading 212 Alert System</div>
        </body>
        </html>
        """
        return subject, html

    elif alert_type == "exit_signal":
        subject = f"Exit Signal - {data['ticker']}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="header" style="background: linear-gradient(135deg, #ef4444, #dc2626);">
                <h1 style="margin:0;">Exit Signal</h1>
                <p style="margin:5px 0 0 0; opacity:0.9;">{timestamp}</p>
            </div>
            <div class="content">
                <div class="metric">
                    <div class="metric-label">Position</div>
                    <div class="metric-value">{data['ticker']}</div>
                </div>
                <div class="action">
                    <strong>Reason:</strong><br>
                    {data['reason']}
                </div>
                <p><strong>Recommendation:</strong> {data['recommendation']}</p>
            </div>
            <div class="footer">Trading 212 Alert System</div>
        </body>
        </html>
        """
        return subject, html

    elif alert_type == "news_alert":
        subject = f"Market Alert - {data['headline']}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="header" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">
                <h1 style="margin:0;">Market Alert</h1>
                <p style="margin:5px 0 0 0; opacity:0.9;">{timestamp}</p>
            </div>
            <div class="content">
                <h3>{data['headline']}</h3>
                <p>{data['summary']}</p>
                <div class="action">
                    <strong>Impact on your portfolio:</strong><br>
                    {data['impact']}
                </div>
            </div>
            <div class="footer">Trading 212 Alert System</div>
        </body>
        </html>
        """
        return subject, html

    else:
        return f"Trading Alert - {alert_type}", f"<p>{str(data)}</p>"
