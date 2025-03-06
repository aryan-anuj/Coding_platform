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

app = Flask(__name__)
CORS(app)

# Connect to MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in .env file")

client = MongoClient(MONGO_URI)
db = client["NotebookDB"]
user_sessions = db["user_sessions"]

class CodeExecutor:
    def __init__(self, timeout=10):
        self.timeout = timeout

    def remove_comments(self, code):
        code = re.sub(r'\#.*', '', code)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
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
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"notebooks": []})
    
    # Extract only notebook_name and notebook_id from each notebook
    notebooks_in = [
        {"notebook_id": nb["notebook_id"], "notebook_name": nb["notebook_name"]}
        for nb in user_data.get("notebooks", [])
    ]
    
    return jsonify({"notebooks": notebooks_in})

@app.route('/<user_id>/create_notebook', methods=['POST'])
def create_notebook(user_id):
    data = request.json
    notebook_name = data.get("name", f"Notebook_{user_id}_{int(time.time())}")
    
    # Check if the notebook name already exists for the user
    user_data = user_sessions.find_one({"user_id": user_id})
    if user_data:
        for notebook in user_data.get("notebooks", []):
            if notebook["notebook_name"] == notebook_name:
                return jsonify({"error": "Notebook name already exists."}), 400
    
    # Generate a unique notebook ID
    notebook_id = f"notebook_{user_id}_{int(time.time())}"
    
    # Create the new notebook
    new_notebook = {
        "notebook_id": notebook_id,
        "notebook_name": notebook_name,
        "cells": []
    }
    
    # Update the user's notebooks in the database
    user_sessions.update_one(
        {"user_id": user_id},
        {"$push": {"notebooks": new_notebook}},
        upsert=True
    )
    return jsonify({"notebookId": notebook_id, "name": notebook_name})

@app.route('/<user_id>/<notebook_id>', methods=['GET'])
def load_notebook(user_id, notebook_id):
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "Notebook not found."}), 404
    
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    return jsonify({"cells": notebook["cells"]})

@app.route('/<user_id>/<notebook_id>/execute', methods=['POST'])
def execute_code(user_id, notebook_id):
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "Code is required."}), 400
    
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "Notebook not found."}), 404
    
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    result = executor.capture_output(code, {})
    new_cell = {"cell_id": f"cell_{int(time.time())}", "code": code, "output": result}
    
    user_sessions.update_one(
        {"user_id": user_id, "notebooks.notebook_id": notebook_id},
        {"$push": {"notebooks.$.cells": new_cell}}
    )
    return jsonify(result)

@app.route('/<user_id>/delete_notebook', methods=['POST'])
def delete_notebook(user_id):
    data = request.json
    notebook_id = data.get('notebookId')
    
    user_sessions.update_one(
        {"user_id": user_id},
        {"$pull": {"notebooks": {"notebook_id": notebook_id}}}
    )
    return jsonify({"message": "Notebook deleted successfully."})

@app.route('/')
def home():
    return "Welcome to Notebook API"

if __name__ == '__main__':
    app.run(debug=True, port=5000)