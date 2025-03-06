from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import io
import contextlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from threading import Thread
import queue
import signal
import time
import traceback
import re

app = Flask(__name__)
CORS(app)

# Stores user notebooks {userId: {sessionId: {"cells": [{"id": "cell_1", "code": "x = 10", "output": ""}], "lastActive": timestamp}}}
user_sessions = {}
SESSION_TIMEOUT = 1800  # 30 minutes

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Code execution timed out")

class CodeExecutor:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.globals = {
            'print': print,
            'plt': plt,
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }

    def remove_comments(self, code):
        """Removes both single-line and multi-line comments from the code."""
        code = re.sub(r'\#.*', '', code)  # Remove single-line comments
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)  # Remove multi-line comments
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)  # Remove multi-line comments using single quotes
        return code  
     
    def capture_output(self, code, session_globals):
        output = io.StringIO()
        error = None
        images = []

        # Remove all types of comments from the code before checking for input()
        code_without_comments = self.remove_comments(code)
        if "input(" in code_without_comments:
            return {
                "text": "",
                "error": "User input is disabled. Please use predefined variables instead.",
                "images": None
            }
        
        def save_plot():
            try:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2)
                plt.close('all')
                buf.seek(0)
                return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            except Exception as e:
                print(f"Error saving plot: {e}")
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
                    
        return {
            "text": output.getvalue(),
            "error": error,
            "images": images if images else None
        }

executor = CodeExecutor()

def cleanup_sessions():
    """Removes sessions that have been inactive for more than 30 minutes."""
    current_time = time.time()
    for user_id in list(user_sessions.keys()):
        for session_id in list(user_sessions[user_id].keys()):
            if current_time - user_sessions[user_id][session_id]["lastActive"] > SESSION_TIMEOUT:
                del user_sessions[user_id][session_id]
        if not user_sessions[user_id]:
            del user_sessions[user_id]

@app.route('/execute', methods=['POST'])
def execute():
    cleanup_sessions()
    try:
        data = request.json
        user_id = data.get('userId')
        session_id = data.get('sessionId')
        code = data.get('code', '')
        
        if not user_id:
            return jsonify({"error": "UserID missing, required parameters."}), 400
        if not session_id :
            return jsonify({"error": "SessionID missing, required parameters."}), 400
        if not code:
            return jsonify({"error": "Code missing, required parameters."}), 400

               
        if user_id not in user_sessions:
            user_sessions[user_id] = {}

        if session_id not in user_sessions[user_id]:
            user_sessions[user_id][session_id] = {
                "cells": [],
                "globals": {"__builtins__": __builtins__},  
                "lastActive": time.time()
            }
        else:
            # Ensure globals exists for the session
            if "globals" not in user_sessions[user_id][session_id]:
                user_sessions[user_id][session_id]["globals"] = {"__builtins__": __builtins__}

        
        session = user_sessions[user_id][session_id]
        session["lastActive"] = time.time()
        
        result = executor.capture_output(code, session["globals"])
        session["cells"].append({"code": code, "output": result["text"]})
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "text": "",
            "images": None
        }), 500

@app.route('/notebooks', methods=['POST'])
def get_notebooks():
    """Fetches all notebooks for a given user."""
    data = request.json
    user_id = data.get('userId')
    if not user_id:
        return jsonify({"error": "Missing userId."}), 400
    
    notebooks = [
        {"sessionId": session_id, "name": f"Notebook {session_id}"}
        for session_id in user_sessions.get(user_id, {})
    ]
    return jsonify({"notebooks": notebooks})

@app.route('/load_notebook', methods=['POST'])
def load_notebook():
    """Loads the saved code for a user's notebook."""
    data = request.json
    user_id = data.get('userId')
    session_id = data.get('sessionId')
    
    if not user_id or not session_id:
        return jsonify({"error": "Missing parameters."}), 400
    
    if user_id in user_sessions and session_id in user_sessions[user_id]:
        return jsonify({"cells": user_sessions[user_id][session_id]["cells"]})
    
    return jsonify({"error": "Notebook not found."}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)