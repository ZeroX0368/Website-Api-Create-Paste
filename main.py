from flask import Flask, request, jsonify, render_template_string
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__)

# Directory to store pastes
PASTES_DIR = "pastes"
os.makedirs(PASTES_DIR, exist_ok=True)

def generate_paste_id():
    """Generate a short unique ID for pastes"""
    return str(uuid.uuid4())[:8]

def save_paste(paste_id, content, title=None, description=None):
    """Save paste content to file"""
    paste_data = {
        "id": paste_id,
        "content": content,
        "title": title or f"Paste {paste_id}",
        "description": description or "",
        "created_at": datetime.now().isoformat()
    }

    filepath = os.path.join(PASTES_DIR, f"{paste_id}.json")
    with open(filepath, 'w') as f:
        json.dump(paste_data, f)

    return paste_data

def load_paste(paste_id):
    """Load paste content from file"""
    filepath = os.path.join(PASTES_DIR, f"{paste_id}.json")
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r') as f:
        return json.load(f)

@app.route('/api/paste/<paste_id>', methods=['GET'])
def pastebin_get(paste_id):
    """Get a paste by its ID via API"""
    paste_data = load_paste(paste_id)
    
    if not paste_data:
        return jsonify({"error": "Paste not found"}), 404
    
    # Get the base URL from the request
    base_url = request.host_url.rstrip('/')
    paste_url = f"{base_url}/{paste_id}"
    raw_url = f"{base_url}/{paste_id}/raw"
    
    response_data = {
        "success": True,
        "paste_id": paste_data["id"],
        "title": paste_data["title"],
        "description": paste_data["description"],
        "content": paste_data["content"],
        "created_at": paste_data["created_at"],
        "url": paste_url,
        "raw_url": raw_url
    }
    
    return jsonify(response_data)

@app.route('/api/paste', methods=['GET', 'POST'])
def pastebin_create():
    """Create a new paste"""
    # Handle GET requests with query parameters
    if request.method == 'GET':
        content = request.args.get('content') or request.args.get('prompt')
        title = request.args.get('title')
        description = request.args.get('description')
    # Handle both JSON and form data for POST
    elif request.is_json:
        data = request.get_json() or {}
        content = request.args.get('prompt') or data.get('content') or data.get('prompt')
        title = data.get('title')
        description = data.get('description')
    else:
        # Handle form data
        content = request.args.get('prompt') or request.form.get('content') or request.form.get('prompt')
        title = request.form.get('title')
        description = request.form.get('description')

    if not content:
        return jsonify({"error": "No content provided"}), 400

    paste_id = generate_paste_id()
    paste_data = save_paste(paste_id, content, title, description)

    # Get the base URL from the request
    base_url = request.host_url.rstrip('/')
    paste_url = f"{base_url}/{paste_id}"
    raw_url = f"{base_url}/{paste_id}/raw"

    response_data = {
        "success": True,
        "paste_id": paste_id,
        "url": paste_url,
        "raw_url": raw_url,
        "title": paste_data["title"],
        "description": paste_data["description"],
        "created_at": paste_data["created_at"]
    }

    # If it's a POST form submission (not GET with query params), redirect to the paste URL
    if request.method == 'POST' and not request.is_json:
        from flask import redirect
        return redirect(paste_url)

    return jsonify(response_data)

@app.route('/<paste_id>/raw')
def view_paste_raw(paste_id):
    """View raw paste content"""
    paste_data = load_paste(paste_id)

    if not paste_data:
        return "Paste not found", 404

    # Return plain text content
    from flask import Response
    return Response(paste_data["content"], mimetype='text/plain')

@app.route('/<paste_id>')
def view_paste(paste_id):
    """View a paste by its ID"""
    paste_data = load_paste(paste_id)

    if not paste_data:
        return "Paste not found", 404

    # Simple HTML template to display the paste
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ title }}</title>

        <!-- Open Graph meta tags for link embedding -->
        <meta property="og:title" content="{{ title }}" />
        <meta property="og:description" content="{{ description }}" />
        <meta property="og:url" content="{{ paste_url }}" />
        <meta property="og:type" content="article" />
        <meta property="og:site_name" content="Simple Paste" />

        <!-- Twitter Card meta tags -->
        <meta name="twitter:card" content="summary" />
        <meta name="twitter:title" content="{{ title }}" />
        <meta name="twitter:description" content="{{ description }}" />

        <!-- Additional meta tags -->
        <meta name="description" content="{{ description }}" />
        <meta name="author" content="Paste Link" />

        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .paste-container { max-width: 800px; margin: 0 auto; }
            .paste-content { 
                background: #f5f5f5; 
                padding: 20px; 
                border-radius: 5px; 
                white-space: pre-wrap;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <div class="paste-container">
            <h1>{{ title }}</h1>
            <div class="paste-meta">
                Created: {{ created_at }}<br>
                Paste ID: {{ paste_id }}
            </div>
            <div class="paste-content">{{ content }}</div>
        </div>
    </body>
    </html>
    """

    description = paste_data.get("description")
    if not description:
        # Create description from content (first 150 characters)
        description = paste_data["content"][:150] + "..." if len(paste_data["content"]) > 150 else paste_data["content"]
        description = description.replace('\n', ' ').replace('\r', ' ')  # Remove line breaks for meta tags

    # Get current paste URL
    paste_url = f"{request.host_url.rstrip('/')}/{paste_id}"

    return render_template_string(
        template,
        title=paste_data["title"],
        content=paste_data["content"],
        description=description,
        paste_url=paste_url,
        created_at=paste_data["created_at"],
        paste_id=paste_data["id"]
    )

@app.route('/api/paste_list')
def pastebin_list():
    """List all pastes"""
    pastes = []
    for filename in os.listdir(PASTES_DIR):
        if filename.endswith('.json'):
            paste_id = filename[:-5]  # Remove .json extension
            paste_data = load_paste(paste_id)
            if paste_data:
                pastes.append({
                    "id": paste_data["id"],
                    "title": paste_data["title"],
                    "created_at": paste_data["created_at"],
                    "url": f"{request.host_url.rstrip('/')}/{paste_data['id']}"
                })

    return jsonify({"pastes": sorted(pastes, key=lambda x: x["created_at"], reverse=True)})

@app.route('/')
def home():
    """Simple home page with paste creation form"""
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Pastebin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            textarea { width: 100%; height: 200px; margin: 10px 0; }
            input[type="text"] { width: 100%; margin: 10px 0; padding: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Simple Pastebin</h1>
            <form action="/api/paste" method="post" enctype="application/x-www-form-urlencoded">
                <input type="text" name="title" placeholder="Paste title (optional)">
                <input type="text" name="description" placeholder="Paste description (optional)">
                <textarea name="content" placeholder="Enter your content here..." required></textarea>
                <button type="submit">Create Paste</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(template)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
