from flask import *
import os
import time
import datetime
import sys
import json
import re
import requests
import dateutil.parser
from elasticsearch import Elasticsearch
import logging



app = Flask(__name__, template_folder='/home/epikapa/ws/work/incident-db/incidentdb/templates')

app.secret_key = '0FS21'
index_name = 'test'
doc_type_name = 'event'
#TODO: redirect pages if es is down.

@app.route("/")
def main():
    return render_template('main.html')

'''
Used for checking status of elasticsearch
'''
@app.route("/test")
def test():
    try:
        res = requests.get("http://localhost:9200/").status_code
    except:
        res = 404
    return render_template("test.html", res=res)

'''
Adds events
'''
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
            data['date'] = datetime.datetime.now().replace(second=0, microsecond=0).strftime("%m/%d/%Y %H:%M")    
        try:
             results = add_to_event(es, data)
        except Exception as e:
            flash(e)
            return render_template("addevent.html")
        
        flash('Data added successfully. (id=%s)' %(results['_id']))
    return render_template("addevent.html")

'''
Uploads json and attempts parse
'''
@app.route("/json_upload", methods=['GET', 'POST'])
def upload_json():
    if request.method == 'POST':
        es = Elasticsearch()
        ALLOWED_EXT = set(['json'])
        f = request.files['filez']
        if f and allowed_file(f.filename, ALLOWED_EXT):
            d = json.loads(f.read().decode("utf-8"))
            try:
                for data in d:
                    add_to_event(es, data)
            except:
                flash("Indexing failed. Check upload file")
                return render_template("json_upload.html")

        flash("File successfully indexed")
    return render_template("json_upload.html")

'''
Returns JSON dump
'''

@app.route("/json", methods=['GET', 'POST'])
def to_json():
    es = Elasticsearch()
    d = []
    if not check_index(es):
        return "No index. Please index an event"
    results = search_event(es)
    for hit in results['hits']['hits']:
        hit['_source']['date'] = datetime.datetime.fromtimestamp(int(hit['_source']['date'])).strftime("%m/%d/%Y %H:%M")
        d.append(hit['_source'])
    return json.dumps(d)

'''
Queries a Json dump
'''

@app.route("/json-query", methods=['GET', 'POST'])
def json_query():
    if request.method == 'POST':
        es = Elasticsearch()
        d = []
        query = {"range" : { "date" : {}}}
        print (request.form['from_date'])
        if request.form['from_date']:
            query['range']['date']['from'] = time.mktime(datetime.datetime.strptime(request.form['from_date'], "%m/%d/%Y %H:%M").timetuple())
        if request.form['to_date']:
            query['range']['date']['to'] = time.mktime(datetime.datetime.strptime(request.form['to_date'], "%m/%d/%Y %H:%M").timetuple())
        results = search_event(es, query)
        
        #TODO: make this compatible with the search_events method
               
        for hit in results['hits']['hits']:
            hit['_source']['date'] = datetime.datetime.fromtimestamp(int(hit['_source']['date'])).strftime("%m/%d/%Y %H:%M")
            if not request.form['tag'] or request.form['tag'] in hit['_source']['tags']:
                d.append(hit['_source'])
        return json.dumps(d)

    return render_template("json_query.html")

'''
Lists out events
'''
@app.route("/event-list/", methods=['GET'])
def event_list():
    es = Elasticsearch()
    d = []
    q = {'from_date': '', 'to_date': '', 'tag' : ''}
    query = { "range" : { "date" : {}}}
    if request.args.get('fd'):
        q['from_date'] = float(request.args.get('fd'))
        query['range']['date']['from'] = q['from_date']

    if request.args.get('td'):
        q['to_date'] = float(request.args.get('td'))
        query['range']['date']['to'] = q['to_date']
    if request.args.get('tag'):
        q['tag'] =  request.args.get('tag')

    print(q) 
    results = search_event(es, query)
    if not results:
        return("No index")
    for hit in results['hits']['hits']:
        if not q['tag'] or q['tag'] in hit['_source']['tags']:
            hit['_source']['date'] = datetime.datetime.fromtimestamp(float(hit['_source']['date'])).strftime("%m/%d/%Y %H:%M")
            d.append((hit['_source'], hit['_id']))
    if q['from_date']:
        q['from_date'] = datetime.datetime.fromtimestamp(q['from_date']).strftime("%m/%d/%Y %H:%M")
    if q['to_date']:
        q['to_date'] = datetime.datetime.fromtimestamp(q['to_date']).strftime("%m/%d/%Y %H:%M")
    d = sorted(d, key=lambda id: int(id[1]))
    print(q)
    return render_template("event_list.html", data=d, q=q)

'''
Filters out events
'''
@app.route("/event-search", methods=['POST'])
def event_search():
    data = []
    if request.form['from_date']:
        data.append("fd=" + str(time.mktime(datetime.datetime.strptime(str(request.form['from_date']), "%m/%d/%Y %H:%M").timetuple())))
    if request.form['to_date']:
        data.append("td=" + str(time.mktime(datetime.datetime.strptime(str(request.form['to_date']), "%m/%d/%Y %H:%M").timetuple())))
    if request.form['tag']:
        data.append('tag=' + request.form['tag'])
    uri_string = '&'.join(data)
    print (data)
    return redirect("/event-list/?%s" %(uri_string))
    


    
'''FROM HERE UNDER SHOULD BE MOVED TO utils.py '''
def allowed_file(filename, ALLOWED_EXT):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXT

def process_data(data):
    new_data = {}
    new_data['description'] = data['description']
    # Fixing date to be a datetime format.
    new_data['date'] = time.mktime(datetime.datetime.strptime(data['date'], "%m/%d/%Y %H:%M").timetuple())
    # Fixing tags to be delimited by a comma. 
    new_data['tags'] = re.split('; |;', data['tags'])
    return new_data

def check_index(es):
    results = es.indices.exists_type(index=index_name, doc_type=doc_type_name)
    return results

def search_event(es, query={"match_all" : {}}):
    if check_index(es):
        return es.search(index=index_name, size=index_count(es), body={"query": query})
    else:
        return(False)
    
    
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
        return False
    return es.index(index=index_name, doc_type=doc_type_name, id=count, body=data)
@app.context_processor
def check_status():
    try:
        res = requests.get("http://localhost:9200/").status_code
        return dict(status=res)
    except:
        res = 404
        return res

def index_count(es):
    es.indices.refresh(index=index_name)
    return es.count(index=index_name, doc_type=doc_type_name)['count'] 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


