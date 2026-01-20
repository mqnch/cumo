from flask import Flask, request, jsonify
from parsing.parser import Parser

app = Flask(__name__)
parser = Parser()


@app.route('/parse', methods=['POST'])
def parse_text():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' field in request body"}), 400
    
    text = data.get('text', '')
    
    if not isinstance(text, str):
        return jsonify({"error": "'text' must be a string"}), 400
    try:
        result = parser.parse(text)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Parsing failed: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6767)
