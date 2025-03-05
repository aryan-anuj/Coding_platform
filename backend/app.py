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

app = Flask(__name__)
CORS(app)

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
        
    def capture_output(self, code, user_input):
        output = io.StringIO()
        error = None
        images = []
        
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
                    # Execute the code
                    exec(code, self.globals)
                    
                    # Check for any plots
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

@app.route('/execute', methods=['POST'])
def execute():
    try:
        data = request.json
        code = data.get('code', '')
        user_input = data.get('userInput', '')  # Extract user input safely

        if not code:
            return jsonify({"error": "No code provided"}), 400

        # Corrected function call (only passing 2 arguments)
        result = executor.capture_output(code, user_input)

        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "text": "",
            "images": None,
            "requiresInput": False,
            "inputPrompt": ""
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)