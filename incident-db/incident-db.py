from flask import *
import os
import sys
import json
import psycopg2

app = Flask(__name__)

@app.route("/")
def main():
    return render_template('main.html')

@app.route("/test")
def test():
    return render_template("test.html")

@app.route("/test2")
def test2():
    return render_template("test2.html")
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


