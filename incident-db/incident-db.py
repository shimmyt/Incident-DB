from flask import *
import os
import datetime
import sys
import json
import re
import requests
import dateutil.parser
from elasticsearch import Elasticsearch

app = Flask(__name__)
index_name = 'test'
doc_type_name = 'event'
#TODO: redirect pages if es is down.

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
            data['date'] = datetime.datetime.now().replace(second=0, microsecond=0)#.strftime("%m/%d/%Y %H:%M")            
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
    if request.method == 'POST':
        es = Elasticsearch()
        ALLOWED_EXT = set(['json'])
        f = request.files['filez']
        if f and allowed_file(f.filename, ALLOWED_EXT):
            d = json.loads(f.read().decode("utf-8"))#.encode("string-escape"))
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
    if not check_index(es):
        return "No index. Please index an event"
    results = search_event(es)
    for hit in results['hits']['hits']:
        hit['_source']['date'] = dateutil.parser.parse(hit['_source']['date']).strftime("%m/%d/%Y %H:%M")
        d.append(hit['_source'])
    return json.dumps(d)
    #return render_template("json.html", data=d)

@app.route("/json-query", methods=['GET', 'POST'])
def json_query():
    if request.method == 'POST':
        es = Elasticsearch()
        data = {}
        query = []
        data['from_date'], data['to_date'], data['tag'] = request.form['from_date'], request.form['to_date'], request.form['tag']

        print(query)
        #TODO: make this compatible with the search_events method
        results = es.search(index='test', doc_type='event', size=index_count(es), body={"query" : { "range" : {"date" : {"from" : datetime.datetime.strptime(data['from_date'], "%m/%d/%Y %H:%M %p")
, "to" : datetime.datetime.strptime(data['to_date'], "%m/%d/%Y %H:%M %p")
}}}})
        d = []
        for hit in results['hits']['hits']:
            hit['_source']['date'] = dateutil.parser.parse(hit['_source']['date']).strftime("%m/%d/%Y %H:%M")
            if data['tag'] and data['tag'] in hit['_source']['tags']:
                d.append(hit['_source'])

        return json.dumps(d)
        #search_event(es, query)
    return render_template("json_query.html")


@app.route("/event-list/", methods=['GET'])
def event_list():
    es = Elasticsearch()
    query = { "range" : { "date" : {}}}
    if request.args.get('fd'):
        query['range']['date']['from'] = dateutil.parser.parse(request.args.get('fd'))
    if request.args.get('td'):
        query['range']['date']['to'] = dateutil.parser.parse(request.args.get('td'))
    if request.args.get('tag'):
        tag = request.args.get('tag')
    print(query)
    d = []
    results = search_event(es, query)
    for hit in results['hits']['hits']:
        if not request.args.get('tag') or request.args.get('tag') in hit['_source']['tags']:
            hit['_source']['date'] = dateutil.parser.parse(hit['_source']['date']).strftime("%m/%d/%Y %H:%M")
            d.append((hit['_source'], hit['_id']))     
    return render_template("event_list.html", data=d)

@app.route("/event-search", methods=['POST'])
def event_search():
    data = []
    if request.form['from_date']:
        data.append("fd=" + datetime.datetime.strptime(request.form['from_date'], "%m/%d/%Y %H:%M %p").isoformat())
    if request.form['to_date']:
        data.append("td=" + datetime.datetime.strptime(request.form['to_date'], "%m/%d/%Y %H:%M %p").isoformat())
    if request.form['tag']:
        data.append('tag=' + request.form['tag'])
        uri_string = '&'.join(data)
        print (data)
        return redirect("/event-list/?%s" %uri_string)
    


    
'''FROM HERE UNDER SHOULD BE MOVED TO utils.py '''
def allowed_file(filename, ALLOWED_EXT):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXT

def process_data(data):
    new_data = {}
    new_data['description'] = data['description']
    # Fixing date to be a datetime format.
    new_data['date'] = datetime.datetime.strptime(data['date'], "%m/%d/%Y %H:%M %p")
    # Fixing tags to be delimited by a comma. 
    new_data['tags'] = re.split('; |;', data['tags'])
    return new_data

def check_index(es):
    results = es.indices.exists_type(index=index_name, doc_type=doc_type_name)
    return results

def search_event(es, query={"match_all" : {}}):
    print (query)
    return es.search(index='test', size=index_count(es), body={"query": query})
    
    
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
    
def check_status():
    try:
        res = requests.get("http://localhost:9200/").status_code
    except:
        res = 404
    return res

def index_count(es):
    es.indices.refresh(index="test")
    return es.count(index=index_name, doc_type=doc_type_name)['count'] 

if __name__ == '__main__':
    app.jinja_env.globals.update(check_status=check_status)
    app.secret_key = '01'
    app.run(host='0.0.0.0', debug=True)


