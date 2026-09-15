import re
import json
from urllib.parse import quote
import webbrowser
from flask import Flask, render_template, request, jsonify
import threading
import os
from contextlib import redirect_stdout, redirect_stderr

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
media_type = "None"
def instagram_post_to_graphql(post_url, doc_id="24368985919464652"):
    global media_type
    """Convert Instagram post URL to GraphQL query URL"""
    match = re.search(r"/p/([^/]+)/?", post_url)
    media_type = "picture"
    if not match:
        match = re.search(r"/reel/([^/]+)/?", post_url)
        media_type = "video"
        if not match:
            raise ValueError("Could not find shortcode in URL. Please enter a valid Instagram post URL.")
    shortcode = match.group(1)

    variables = {
        "shortcode": shortcode,
        "fetch_tagged_user_count": None,
        "hoisted_comment_id": None,
        "hoisted_reply_id": None
    }

    variables_json = json.dumps(variables, separators=(",", ":"))
    encoded_variables = quote(variables_json, safe="")

    return f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={encoded_variables}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """Convert Instagram URL to GraphQL URL"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'Please enter an Instagram post URL'}), 400
        
        graphql_url = instagram_post_to_graphql(url)
        return jsonify({'url': graphql_url}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/process-json', methods=['POST'])
def process_json():
    """Process JSON response"""
    global media_type
    try:
        data = request.json
        json_text = data.get('json', '').strip()
        if not json_text:
            return jsonify({'error': 'Please paste a JSON response'}), 400
        
        parsed_data = json.loads(json_text)
        
        # Extract user info and post content
        json_items = parsed_data["data"]["xdt_api__v1__media__shortcode__web_info"]["items"]
        user = json_items[0]["user"]
        post_urls = []

        if media_type == "None":
            try:
                json_items[0]["video_versions"][0]["url"]
                media_type = "video"
            except:
                media_type = "picture"
        if media_type == "picture":
            post_content = json_items[0]["carousel_media"]
            for post in post_content:
                post_urls.append(post["image_versions2"]["candidates"][0]["url"])
            
        elif media_type == "video":
            post_content = json_items[0]["video_versions"][0]["url"]
            post_urls.append(post_content)

        result = {
                'username': user.get('username', 'N/A'),
                'full_name': user.get('full_name', 'N/A'),
                'profile_pic_url': user.get('profile_pic_url', 'N/A'),
                'media_type': media_type,
                'post_urls': post_urls
            }
        
        return jsonify(result), 200
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    except KeyError as e:
        return jsonify({'error': f'Missing key in JSON: {str(e)}'}), 400

def open_browser():
    """Open browser after a short delay"""
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Open browser in a separate thread
    threading.Timer(1.0, open_browser).start()
    
    # Run Flask app silently: redirect stdout/stderr and disable reloader
    with open(os.devnull, 'w') as devnull:
        with redirect_stdout(devnull), redirect_stderr(devnull):
            app.run(debug=False, port=5000, use_reloader=False)