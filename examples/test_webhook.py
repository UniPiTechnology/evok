from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def respond():
    print(dict(request.values))
    return json.dumps({"status": "success"}), 200


if __name__=="__main__":
    app.run(host='0.0.0.0', port=8080)