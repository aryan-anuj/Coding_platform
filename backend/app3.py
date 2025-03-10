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


# # 🔹 Securely load MongoDB URI from .env
# MONGO_URI = os.getenv("MONGO_URI")
# if not MONGO_URI:
#     raise ValueError("MONGO_URI is not set in .env file")



# # 🔹 Connect to MongoDB Atlas
# client = MongoClient(MONGO_URI)
# db = client["myDatabase"]  # Your database name
# user_sessions = db["user_sessions"]  # Collection name



# Stores user notebooks {userId: {notebookId: {"cells": [{"id": "cell_1", "code": "x = 10", "output": ""}], "globals": {}, "lastActive": timestamp}}}
user_sessions = {}
SESSION_TIMEOUT = 1800  # 30 minutes

class CodeExecutor:
    def __init__(self, timeout=10):
        self.timeout = timeout

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
        for notebook_id in list(user_sessions[user_id].keys()):
            if current_time - user_sessions[user_id][notebook_id]["lastActive"] > SESSION_TIMEOUT:
                del user_sessions[user_id][notebook_id]
        if not user_sessions[user_id]:
            del user_sessions[user_id]

@app.route('/<user_id>', methods=['GET'])
def get_user_notebooks(user_id):
    """Returns a list of all notebooks for a user with correct names."""
    if user_id not in user_sessions:
        return jsonify({"notebooks": []})

    notebooks = [
        {
            "notebookId": nb_id,
            "name": user_sessions[user_id][nb_id].get("name", f"Notebook {nb_id}")  # Fetch actual stored name
        }
        for nb_id in user_sessions[user_id]
    ]
    print(user_sessions)
    return jsonify({"notebooks": notebooks})


@app.route('/<user_id>/create_notebook', methods=['POST'])
def create_notebook(user_id):
    """Creates a new notebook for the user, ensuring unique names."""
    data = request.json
    cur_time = int(time.time())
    notebook_name = data.get("name")  # Get user-defined name if provided

    if user_id not in user_sessions:
        user_sessions[user_id] = {}

    # Check if the user-defined name already exists
    if notebook_name and any(nb["name"] == notebook_name for nb in user_sessions[user_id].values()):
        return jsonify({"error": "A notebook with this name already exists."}), 400
    print(notebook_name)

    # Generate a system-defined notebook name if none is provided
    notebook_id = f"notebook_{int(time.time())}"
    if not notebook_name:
        notebook_name = f"Notebook {notebook_id}"
    print(notebook_id,notebook_name)

    # ✅ Ensure the notebook name is saved in the dictionary
    user_sessions[user_id][notebook_id] = {
        "name": notebook_name,
        "cells": [],
        "globals": {"__builtins__": __builtins__},
        "lastActive": time.time()
    }
    print(f"Stored notebook: {user_sessions[user_id][notebook_id]}")
    return jsonify({"notebookId": notebook_id, "name": notebook_name})


@app.route('/<user_id>/<notebook_id>', methods=['GET'])
def load_notebook(user_id, notebook_id):
    """Loads a specific notebook."""
    cleanup_sessions()
    if user_id in user_sessions and notebook_id in user_sessions[user_id]:
        return jsonify({"cells": user_sessions[user_id][notebook_id]["cells"]})
    return jsonify({"error": "Notebook not found."}), 404

@app.route('/<user_id>/<notebook_id>/execute', methods=['POST'])
def execute_code(user_id, notebook_id):
    """Executes code inside a specific notebook in an isolated session."""
    cleanup_sessions()
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "Code is required."}), 400
    if user_id not in user_sessions or notebook_id not in user_sessions[user_id]:
        return jsonify({"error": "Notebook not found."}), 404
    
    session = user_sessions[user_id][notebook_id]
    session["lastActive"] = time.time()
    result = executor.capture_output(code, session["globals"])
    session["cells"].append({"code": code, "output": result["text"]})
    return jsonify(result)

@app.route('/<user_id>/delete_notebook', methods=['POST'])
def delete_notebook(user_id):
    """Deletes a notebook from a user's session."""
    data = request.json
    notebook_id = data.get('notebookId')
    if not notebook_id or user_id not in user_sessions or notebook_id not in user_sessions[user_id]:
        return jsonify({"error": "Notebook not found."}), 404
    del user_sessions[user_id][notebook_id]
    return jsonify({"message": "Notebook deleted successfully."})


@app.route('/')
def home():
    return "welcome to main page"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
from flask import Flask, request, jsonify, send_file
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
import json
import tempfile
import dill  # Use dill for serialization

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

# @app.route('/<user_id>', methods=['GET'])
# def get_user_notebooks(user_id):
#     user_data = user_sessions.find_one({"user_id": user_id})
#     if not user_data:
#         return jsonify({"notebooks": []})
    
#     # Extract only notebook_name and notebook_id from each notebook
#     notebooks_in = [
#         {"notebook_id": nb["notebook_id"], "notebook_name": nb["notebook_name"]}
#         for nb in user_data.get("notebooks", [])
#     ]
    
#     return jsonify({"notebooks": notebooks_in})

@app.route('/<user_id>', methods=['GET'])
def get_user_notebooks(user_id):
    # Fetch fresh data from MongoDB
    user_data = user_sessions.find_one({"user_id": user_id})
    
    # If the user has no remaining notebooks, return an empty list
    if not user_data or "notebooks" not in user_data:
        return jsonify({"notebooks": []})

    # Extract only notebook_name and notebook_id
    notebooks_in = [
        {"notebook_id": nb["notebook_id"], "notebook_name": nb["notebook_name"]}
        for nb in user_data.get("notebooks", [])
    ]

    return jsonify({"notebooks": notebooks_in})


@app.route('/<user_id>/create_notebook', methods=['POST'])
def create_notebook(user_id):
    """Creates a new notebook and initializes the globals dictionary."""
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
    
    # Create the new notebook with an initialized globals dictionary
    new_notebook = {
        "notebook_id": notebook_id,
        "notebook_name": notebook_name,
        "cells": [],
        "globals": {}  # Initialize without __builtins__
    }
    
    # Update the user's notebooks in the database
    user_sessions.update_one(
        {"user_id": user_id},
        {"$push": {"notebooks": new_notebook}},
        upsert=True
    )
    return jsonify({"notebookId": notebook_id, "name": notebook_name})

# @app.route('/<user_id>/<notebook_id>', methods=['GET'])
# def load_notebook(user_id, notebook_id):
#     """Loads a specific notebook and ensures globals are properly initialized."""
#     # Fetch the user's data from MongoDB
#     user_data = user_sessions.find_one({"user_id": user_id})
#     if not user_data:
#         return jsonify({"error": "User not found."}), 404
    
#     # Find the notebook in the user's data
#     notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
#     if not notebook:
#         return jsonify({"error": "Notebook not found."}), 404
    
#     # Deserialize the globals dictionary if it exists
#     if "globals_serialized" in notebook:
#         notebook["globals"] = dill.loads(notebook["globals_serialized"])
#     else:
#         notebook["globals"] = {}  # Initialize globals as empty
    
#     # Add __builtins__ to the globals for execution
#     notebook["globals"]["__builtins__"] = __builtins__
    
#     # Return the notebook's cells
#     return jsonify({"cells": notebook["cells"]})


# @app.route('/<user_id>/<notebook_id>/execute', methods=['POST'])
# def execute_code(user_id, notebook_id):
#     data = request.json
#     code = data.get('code', '')
#     if not code:
#         return jsonify({"error": "Code is required."}), 400
    
#     # Replace escaped newlines with actual newlines
#     # code = code.replace('\\n', '\n')
    
#     # Fetch the user's data from MongoDB
#     user_data = user_sessions.find_one({"user_id": user_id})
#     if not user_data:
#         return jsonify({"error": "User not found."}), 404
    
#     # Find the notebook in the user's data
#     notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
#     if not notebook:
#         return jsonify({"error": "Notebook not found."}), 404
    
#     # Get the notebook's globals (or initialize if it doesn't exist)
#     if "globals" not in notebook:
#         notebook["globals"] = {}  # Initialize without __builtins__
    
#     # Add __builtins__ to the globals for execution
#     execution_globals = notebook["globals"].copy()
#     execution_globals["__builtins__"] = __builtins__
    
#     # Execute the code in the notebook's globals
#     result = executor.capture_output(code, execution_globals)
    
#     # Remove __builtins__ before saving to MongoDB
#     if "__builtins__" in execution_globals:
#         del execution_globals["__builtins__"]
    
#     # Create a new cell with the code and output
#     new_cell = {
#         "cell_id": f"cell_{int(time.time())}",
#         "cell_type": "code",
#         "code": code,
#         "output": result
#     }
    
#     # Update the notebook in the database:
#     # 1. Add the new cell to the notebook's cells
#     # 2. Update the notebook's globals
#     user_sessions.update_one(
#         {"user_id": user_id, "notebooks.notebook_id": notebook_id},
#         {
#             "$push": {"notebooks.$.cells": new_cell},
#             "$set": {"notebooks.$.globals": execution_globals}
#         }
#     )
    
#     return jsonify(result)



@app.route('/<user_id>/<notebook_id>/execute', methods=['POST'])
def execute_code(user_id, notebook_id):
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "Code is required."}), 400
    
    # Fetch the user's data from MongoDB
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404
    
    # Find the notebook in the user's data
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    # Get the notebook's globals (or initialize if it doesn't exist)
    if "globals_serialized" in notebook:
        notebook["globals"] = dill.loads(notebook["globals_serialized"])
    else:
        notebook["globals"] = {}  # Initialize globals as empty
    
    # Add __builtins__ to the globals for execution
    execution_globals = notebook["globals"].copy()
    execution_globals["__builtins__"] = __builtins__
    
    # Execute the code in the notebook's globals
    result = executor.capture_output(code, execution_globals)
    
    # Remove __builtins__ before saving to MongoDB
    if "__builtins__" in execution_globals:
        del execution_globals["__builtins__"]
    
    # Serialize the globals dictionary for storage in MongoDB
    globals_serialized = dill.dumps(execution_globals)
    
    # Create a new cell with the code and output
    new_cell = {
        "cell_id": f"cell_{int(time.time())}",
        "cell_type": "code",
        "code": code,
        "output": result
    }
    
    # Update the notebook in the database:
    # 1. Add the new cell to the notebook's cells
    # 2. Update the notebook's serialized globals
    user_sessions.update_one(
        {"user_id": user_id, "notebooks.notebook_id": notebook_id},
        {
            "$push": {"notebooks.$.cells": new_cell},
            "$set": {"notebooks.$.globals_serialized": globals_serialized}
        }
    )
    
    return jsonify(result)

@app.route('/<user_id>/<notebook_id>', methods=['GET'])
def load_notebook(user_id, notebook_id):
    """Loads a specific notebook and ensures globals are properly initialized."""
    # Fetch the user's data from MongoDB
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404
    
    # Find the notebook in the user's data
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    # Deserialize the globals dictionary if it exists
    if "globals_serialized" in notebook:
        notebook["globals"] = cloudpickle.loads(notebook["globals_serialized"])
    else:
        notebook["globals"] = {}  # Initialize globals as empty
    
    # Add __builtins__ to the globals for execution
    notebook["globals"]["__builtins__"] = __builtins__
    
    # Return the notebook's cells
    return jsonify({"cells": notebook["cells"]})


@app.route('/<user_id>/<notebook_id>/save_markdown', methods=['POST'])
def save_markdown(user_id, notebook_id):
    """Saves a markdown cell in the database."""
    data = request.json
    markdown_content = data.get('content', '')
    if not markdown_content:
        return jsonify({"error": "Markdown content is required."}), 400
    
    # Fetch the user's data from MongoDB
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404
    
    # Find the notebook in the user's data
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    # Create a new markdown cell
    new_cell = {
        "cell_id": f"cell_{int(time.time())}",
        "cell_type": "markdown",
        "code": markdown_content,  # Store markdown content in the 'code' field
        "output": {"text": "", "error": None, "images": None}  # No output for markdown cells
    }
    
    # Update the notebook in the database:
    # Add the new markdown cell to the notebook's cells
    user_sessions.update_one(
        {"user_id": user_id, "notebooks.notebook_id": notebook_id},
        {"$push": {"notebooks.$.cells": new_cell}}
    )
    
    return jsonify({"message": "Markdown cell saved successfully."})

@app.route('/<user_id>/<notebook_id>/export', methods=['GET'])
def export_notebook(user_id, notebook_id):
    """Exports a notebook as an .ipynb file."""
    # Fetch the user's data from MongoDB
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404
    
    # Find the notebook in the user's data
    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404
    
    # Prepare the cells for the .ipynb file
    cells = []
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            cell_data = {
                "cell_type": "code",
                "execution_count": None,  # Execution count is not tracked in this implementation
                "metadata": {},
                "source": cell["code"].splitlines(True),  # Split code into lines
                "outputs": []
            }
            
            # Add output if available
            if cell["output"]:
                output_data = {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": cell["output"]["text"].splitlines(True)  # Split output into lines
                }
                cell_data["outputs"].append(output_data)
        elif cell["cell_type"] == "markdown":
            cell_data = {
                "cell_type": "markdown",
                "metadata": {},
                "source": cell["code"].splitlines(True)  # Split markdown into lines
            }
        
        cells.append(cell_data)
    
    # Create the .ipynb structure
    ipynb_data = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.x"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    
    # Save the .ipynb file temporarily
    with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False) as temp_file:
        temp_filename = temp_file.name
        json.dump(ipynb_data, temp_file, indent=2)
    
    # Return the file as a downloadable response
    return send_file(
        temp_filename,
        as_attachment=True,
        download_name=f"{notebook['notebook_name']}.ipynb"  # Use notebook name as the filename
    )

# @app.route('/<user_id>/delete_notebook', methods=['POST'])
# def delete_notebook(user_id):
#     data = request.json
#     notebook_id = data.get('notebookId')
    
#     user_sessions.update_one(
#         {"user_id": user_id},
#         {"$pull": {"notebooks": {"notebook_id": notebook_id}}}
#     )
#     return jsonify({"message": "Notebook deleted successfully."})

@app.route('/<user_id>/delete_notebook', methods=['DELETE'])
def delete_notebook(user_id):
    data = request.json
    notebook_id = data.get('notebookId')

    if not notebook_id:
        return jsonify({"error": "Notebook ID is required."}), 400

    # Debugging: Check if the user exists before deletion
    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404

    # Perform the deletion
    result = user_sessions.update_one(
        {"user_id": user_id},
        {"$pull": {"notebooks": {"notebook_id": notebook_id}}}
    )

    # Check if the notebook was actually deleted
    if result.modified_count == 0:
        return jsonify({"error": "Notebook not found or already deleted."}), 404

    # Debugging: Check if the notebook still exists
    updated_user_data = user_sessions.find_one({"user_id": user_id})
    
    # If the user has no remaining notebooks, remove the entire user document
    if updated_user_data and not updated_user_data.get("notebooks"):
        user_sessions.delete_one({"user_id": user_id})

    return jsonify({"message": "Notebook deleted successfully."})

# @app.route('/<user_id>/<notebook_id>/delete_cell', methods=['DELETE'])
# def delete_cell(user_id, notebook_id):
#     data = request.json
#     cell_id = data.get('cell_id')
#     if not cell_id:
#         return jsonify({"error": "Cell ID is required."}), 400

#     user_data = user_sessions.find_one({"user_id": user_id})
#     if not user_data:
#         return jsonify({"error": "User not found."}), 404

#     notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
#     if not notebook:
#         return jsonify({"error": "Notebook not found."}), 404

#     cell_to_delete = next((cell for cell in notebook["cells"] if cell["cell_id"] == cell_id), None)
#     if not cell_to_delete:
#         return jsonify({"error": "Cell not found."}), 404

#     # Extract variable assignments from the deleted cell
#     cell_code = cell_to_delete["code"]
#     assigned_vars = re.findall(r'^(\w+)\s*=\s*.*$', cell_code, re.MULTILINE)

#     # Remove cell from notebook
#     user_sessions.update_one(
#         {"user_id": user_id, "notebooks.notebook_id": notebook_id},
#         {"$pull": {"notebooks.$.cells": {"cell_id": cell_id}}}
#     )

#     # Debugging step
#     print(f"Deleted cell {cell_id}. Assigned vars: {assigned_vars}")

#     # Remove matching variables from the notebook's global scope
#     updated_user_data = user_sessions.find_one({"user_id": user_id})
#     updated_notebook = next((nb for nb in updated_user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)

#     if updated_notebook and "globals" in updated_notebook:
#         notebook_globals = updated_notebook["globals"]

#         print(f"Before globals update: {notebook_globals}")

#         for var in assigned_vars:
#             try:
#                 if var in notebook_globals and eval(var, {}, notebook_globals) == eval(var, {}, globals()):
#                     del notebook_globals[var]
#             except Exception as e:
#                 print(f"Error removing global variable {var}: {e}")

#         print(f"After globals update: {notebook_globals}")

#         user_sessions.update_one(
#             {"user_id": user_id, "notebooks.notebook_id": notebook_id},
#             {"$set": {"notebooks.$.globals": notebook_globals}}
#         )

#     return jsonify({"message": "Cell deleted successfully and related globals removed."})

@app.route('/<user_id>/<notebook_id>/delete_cell', methods=['DELETE'])
def delete_cell(user_id, notebook_id):
    data = request.json
    cell_id = data.get('cell_id')
    if not cell_id:
        return jsonify({"error": "Cell ID is required."}), 400

    user_data = user_sessions.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found."}), 404

    notebook = next((nb for nb in user_data["notebooks"] if nb["notebook_id"] == notebook_id), None)
    if not notebook:
        return jsonify({"error": "Notebook not found."}), 404

    cell_to_delete = next((cell for cell in notebook["cells"] if cell["cell_id"] == cell_id), None)
    if not cell_to_delete:
        return jsonify({"error": "Cell not found."}), 404
    
    # Extract variable assignments from the deleted cell
    cell_code = cell_to_delete["code"]
    # assigned_vars = re.findall(r'^(\w+)\s*=\s*.*$', cell_code, re.MULTILINE)
    
    # # Remove matching variables from the notebook's global scope BEFORE deleting the cell
    # if "globals" in notebook:
    #     notebook_globals = notebook["globals"]
    #     for var in assigned_vars:
    #         if var in notebook_globals:
    #             del notebook_globals[var]
        
    #     user_sessions.update_one(
    #         {"user_id": user_id, "notebooks.notebook_id": notebook_id},
    #         {"$set": {"notebooks.$.globals": notebook_globals}}
    #     )
    
    # Remove cell from notebook
    user_sessions.update_one(
        {"user_id": user_id, "notebooks.notebook_id": notebook_id},
        {"$pull": {"notebooks.$.cells": {"cell_id": cell_id}}}
    )
    
    return jsonify({"message": "Cell deleted successfully and related globals removed."})

@app.route('/')
def home():
    return "Welcome to Notebook API"

if __name__ == '__main__':
    app.run(debug=True, port=5000)