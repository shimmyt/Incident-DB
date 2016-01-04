from flask import *
import os
import datetime
import sys
import json
import requests
from elasticsearch import Elasticsearch

app = Flask(__name__)
index_name = 'test'
doc_type_name = 'event'

@app.route("/")
def main():
    return render_template('main.html')

@app.route("/test")
def test():
    try:
        res = requests.get("http://localhost:9200/").status_code
    except:
        res = 404
    return render_template("test.html", res=res)

@app.route("/eventadd", methods=['GET', 'POST'])
def add_event_page():
    if request.method == 'POST':
        es = Elasticsearch()
        data = {}
        data['description'], data['date'], data['tags'] = request.form['description'], request.form['date'], request.form['tags']
        
        #if nothing was supplied, give defaults
        if not data['description']:
            data['description'] = "None"
        if not data['date']:
            data['date'] = datetime.datetime.now()#.strftime("%m/%d/%Y %H:%M:%S")
        else:
            data['date'] = datetime.datetime.strptime(data['date'], "%m/%d/%Y %H:%M %p")
            
        #TODO: add ability to upload json and parse 
        try:
             results = add_to_event(es, data)
        except Exception as e:
            flash(e)
            return render_template("addevent.html")
        
        flash('Data added successfully. (id=%s)' %(results['_id']))
    return render_template("addevent.html")

@app.route("/json_upload", methods=['GET', 'POST'])
def upload_json():
    es = Elasticsearch()
    ALLOWED_EXT = set(['json'])
    if request.method == 'POST':
        f = request.files['filez']
        if f and allowed_file(f.filename, ALLOWED_EXT):
            d = json.loads(f.read().encode("string-escape"))
            try:
                for data in d:
                    add_to_event(es, data)
                    
            except:
                flash("Indexing failed. Check upload file")
                return render_template("json_upload.html")

        flash("File successfully indexed")
    return render_template("json_upload.html")

@app.route("/json", methods=['GET', 'POST'])
def to_json():
    es = Elasticsearch()
    d = []
    results = search_event(es)
    for hit in results['hits']['hits']:
        print d.append(hit['_source'])    
    return json.dumps(d)
    #return render_template("json.html", data=d)
    
'''FROM HERE UNDER SHOULD BE MOVED TO utils.py '''
def allowed_file(filename, ALLOWED_EXT):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXT

def process_data(data):
    new_data = {}
    new_data['description'], new_data['date'] , new_data['tags']  = data['description'], data['date'], data['tags']
    return new_data

def check_index(es):
    results = es.indices.exists_type(index=index_name, doc_type=doc_type_name)
    print (results)
    return results

def search_event(es, query=''):
    
    return es.search(index='test', body={"query": {"match_all": {}}})
    
    
def add_to_event(es, data):
    #data needs to be processed to only contain certain keys
    if not check_index(es):
        count = 1
    else:
        count = index_count(es)+1
            
    try:
        data = process_data(data)    
    except Exception as e:
        print(e)
        return false
            
    return es.index(index=index_name, doc_type=doc_type_name, id=count, body=data)
    

def index_count(es):
     return es.count(index=index_name, doc_type=doc_type_name)['count'] 

if __name__ == '__main__':
    app.secret_key = '01'
    app.run(host='0.0.0.0', debug=True)


