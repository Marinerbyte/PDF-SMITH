import os
import logging
from flask import Flask, request, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix
from bot import setup_bot, process_update

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize bot
bot = setup_bot()

@app.route('/')
def index():
    """Landing page with webhook setup instructions"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', 'NOT_SET')
    webhook_url = request.url_root + 'webhook'
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram PDF Bot</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h2 class="card-title mb-0">🤖 Telegram PDF Bot</h2>
                        </div>
                        <div class="card-body">
                            <h4>Webhook Setup Instructions</h4>
                            <div class="alert alert-info">
                                <strong>Bot Token Status:</strong> 
                                {% if bot_token != 'NOT_SET' %}
                                    <span class="text-success">✅ Configured</span>
                                {% else %}
                                    <span class="text-danger">❌ Not Set</span>
                                {% endif %}
                            </div>
                            
                            <h5>1. Set Environment Variables:</h5>
                            <pre class="bg-dark text-light p-3 rounded">
TELEGRAM_BOT_TOKEN=your_bot_token_here
SESSION_SECRET=your_session_secret_here
                            </pre>
                            
                            <h5>2. Set Webhook URL:</h5>
                            <div class="input-group mb-3">
                                <input type="text" class="form-control" value="{{ webhook_url }}" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="copyToClipboard('{{ webhook_url }}')">Copy</button>
                            </div>
                            
                            <h5>3. Use this command to set webhook:</h5>
                            <pre class="bg-dark text-light p-3 rounded">
curl -F "url={{ webhook_url }}" https://api.telegram.org/bot{{ bot_token }}/setWebhook
                            </pre>
                            
                            <div class="alert alert-success mt-3">
                                <strong>Bot Features:</strong>
                                <ul class="mb-0">
                                    <li>📝 Text to PDF conversion</li>
                                    <li>🖼️ Images to PDF conversion</li>
                                    <li>📄 Document to PDF conversion</li>
                                    <li>📚 PDF merge and split</li>
                                    <li>❓ Interactive help system</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('Webhook URL copied to clipboard!');
            });
        }
        </script>
    </body>
    </html>
    """, webhook_url=webhook_url, bot_token=bot_token)

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Handle incoming Telegram updates"""
    if request.method == 'GET':
        return {
            "status": "Webhook endpoint is active",
            "method": "This endpoint only accepts POST requests from Telegram",
            "bot": "DocuSmith (@FlexiPDF_bot)",
            "features": ["txt2pdf", "img2pdf", "doc2pdf", "mergepdf", "splitpdf"]
        }, 200
    
    try:
        update_data = request.get_json()
        if update_data:
            logger.info(f"Received update: {update_data}")
            process_update(bot, update_data)
            return "OK", 200
        else:
            logger.warning("Received empty update")
            return "Bad Request", 400
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "bot": "running"}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
