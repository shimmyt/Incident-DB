from flask import *
import os
import sys
import json
import psycopg2

app = Flask(__name__)

@app.route("/")
def main():
    return "OK"
    
@app.route("/post", methods=['POST'])
def postz():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


