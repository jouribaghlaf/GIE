# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from gie_engine import gie_engine

app = Flask(__name__)

# Allow frontend (Live Server / GitHub Pages) to call backend API
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/api/gie")
def gie_endpoint():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    result = gie_engine("individual", text)  
    # If engine returns error -> 400 for validation errors, else 500
    if result.get("status") == "error":
        code = int(result.get("code", 400))
        return jsonify(result), code

    return jsonify(result), 200


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({
            "status": "error",
            "error": e.name,
            "message": e.description,
            "code": e.code
        }), e.code

    return jsonify({
        "status": "error",
        "error": "internal_server_error",
        "message": "Unexpected server error",
        "code": 500
    }), 500


if __name__ == "__main__":
    # http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
