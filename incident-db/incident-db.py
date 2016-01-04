from flask import *
import os
import datetime
import sys
import json
from elasticsearch import Elasticsearch

app = Flask(__name__)

@app.route("/")
def main():
    return render_template('main.html')

@app.route("/test")
def test():
    return render_template("test.html")

@app.route("/eventadd", methods=['GET', 'POST'])
def add_event_page():
    if request.method == 'POST':
        es = Elasticsearch()
        count = es.count(index='test', doc_type='event')['count']
        data = {}
        data['description'], data['date'], data['tags'] = request.form['description'], request.form['date'], request.form['tags']
        
        #if nothing was supplied, give defaults
        if not data['description']:
            data['description'] = "None"
        if not data['date']:
            data['date'] = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        #TODO: add ability to upload json and parse 
        try:
            print(es.index(index="test", doc_type='event', id=count, body=data))
        except Exception as e:
            flash('indexing failed')
            return render_template("addevent.html")
        flash('Data added successfully')
    return render_template("addevent.html")


if __name__ == '__main__':
    app.secret_key = '01'
    app.run(host='0.0.0.0', debug=True)


