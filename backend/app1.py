# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
# uri = "mongodb+srv://root:1234@cluster0.15u0y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))
# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)


from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import io
import os
import contextlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
import time
import traceback
import re
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in .env file")

# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI)
db = client["NotebookDB"]  # Database name
user_sessions = db["user_sessions"]  # Collection name

app = Flask(__name__)
CORS(app)

class CodeExecutor:
    def __init__(self, timeout=10):
        self.timeout = timeout

    def remove_comments(self, code):
        code = re.sub(r'\#.*', '', code)  # Single-line comments
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)  # Multi-line comments
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)  # Multi-line single quotes
        return code  
    
    def capture_output(self, code, session_globals):
        output = io.StringIO()
        error = None
        images = []

        code_without_comments = self.remove_comments(code)
        if "input(" in code_without_comments:
            return {"text": "", "error": "User input is disabled.", "images": None}

        def save_plot():
            try:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2)
                plt.close('all')
                buf.seek(0)
                return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            except Exception as e:
                return None
        
        try:
            with contextlib.redirect_stdout(output):
                try:
                    exec(code, session_globals)
                    if plt.get_fignums():
                        img = save_plot()
                        if img:
                            images.append(img)
                except Exception as e:
                    error = str(e)
                    traceback.print_exc(file=output)
        except Exception as e:
            error = f"Execution error: {str(e)}"
        
        return {"text": output.getvalue(), "error": error, "images": images if images else None}

executor = CodeExecutor()

@app.route('/<user_id>', methods=['GET'])
def get_user_notebooks(user_id):
    notebooks = list(user_sessions.find({"user_id": user_id}, {"_id": 0, "notebook_id": 1, "notebook_name": 1}))
    return jsonify({"notebooks": notebooks})

@app.route('/<user_id>/create_notebook', methods=['POST'])
def create_notebook(user_id):
    data = request.json
    notebook_name = data.get("name", f"Notebook_{int(time.time())}")
    notebook_id = f"notebook_{int(time.time())}"
    
    user_sessions.insert_one({
        "user_id": user_id,
        "notebook_id": notebook_id,
        "notebook_name": notebook_name,
        "cells": []
    })
    
    return jsonify({"notebookId": notebook_id, "name": notebook_name})

@app.route('/<user_id>/<notebook_id>', methods=['GET'])
def load_notebook(user_id, notebook_id):
    notebook = user_sessions.find_one({"user_id": user_id, "notebook_id": notebook_id}, {"_id": 0, "cells": 1})
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    return jsonify({"cells": notebook.get("cells", [])})

@app.route('/<user_id>/<notebook_id>/execute', methods=['POST'])
def execute_code(user_id, notebook_id):
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "Code is required."}), 400
    
    notebook = user_sessions.find_one({"user_id": user_id, "notebook_id": notebook_id})
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    session_globals = {"__builtins__": __builtins__}  # Isolated environment
    result = executor.capture_output(code, session_globals)
    
    user_sessions.update_one(
        {"user_id": user_id, "notebook_id": notebook_id},
        {"$push": {"cells": {"code": code, "output": result["text"]}}}
    )
    
    return jsonify(result)

@app.route('/<user_id>/delete_notebook', methods=['POST'])
def delete_notebook(user_id):
    data = request.json
    notebook_id = data.get('notebookId')
    if not notebook_id:
        return jsonify({"error": "Notebook ID is required."}), 400
    
    user_sessions.delete_one({"user_id": user_id, "notebook_id": notebook_id})
    return jsonify({"message": "Notebook deleted successfully."})

@app.route('/')
def home():
    return "Welcome to the main page"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
