from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect, Markup
from data import Articles
from model import db
from sqlalchemy import and_
import re, sys
from bs4 import BeautifulSoup
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk import word_tokenize

import psycopg2, requests, json
from string import digits
# from config import config
import psycopg2
import sys
import psycopg2.extras
from flask import jsonify
from operator import itemgetter

app = Flask(__name__)
app.debug = True
def connect():
	conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
	conn = psycopg2.connect(conn_string)
	return conn;

def selectSession():
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	cursor.execute("select id, name, username, active from users where active='t';");
	return cursor;

def getGeom(location):
	polygonpoints = [];
	bbox = "";
	geojsonFeature = "";
	polyPoints = [];
	poly_wkt=[];
	geocoding_result = requests.get('https://nominatim.openstreetmap.org/search?q='+location+'&format=json&polygon=1&addressdetails=1');
	if 'polygonpoints' in geocoding_result.json()[0].keys():
		polygonpoints = geocoding_result.json()[0]['polygonpoints'];
		polyPoints[:] = [[float(e) for e in sl] for sl in polygonpoints]
		if(polyPoints[0]!=polyPoints[-1]):
			polyPoints.append(polyPoints[0]);
		geojsonFeature = {"type":"Polygon","coordinates":[polyPoints]};
		geojsonFeature=json.dumps(geojsonFeature);
	else:
		bbox = geocoding_result.json()[0]['boundingbox'];
		poly_wkt.append([float(bbox[2]),float(bbox[0])]);
		poly_wkt.append([float(bbox[3]),float(bbox[0])]);
		poly_wkt.append([float(bbox[3]),float(bbox[1])]);
		poly_wkt.append([float(bbox[2]),float(bbox[1])]);
		poly_wkt.append([float(bbox[2]),float(bbox[0])]);
		geojsonFeature = {"type":"Polygon","coordinates":[poly_wkt]};
		geojsonFeature=json.dumps(geojsonFeature);
	# print(geojsonFeature);
	return geojsonFeature;
def selectData(themes,location):
	conn = connect();
	cursor_IsA = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_Synonym = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_RelatedTo = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_MannerOf = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	words_IsA, words_Synonym, words_RelatedTo, words_MannerOf = formulate_keywords(themes,location);
	# print(words);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,ts_rank(mt.tokens,tsq) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_IsA +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_Synonym.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_Synonym +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_RelatedTo.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+ words_RelatedTo +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_MannerOf +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
	elif(len(themes)):
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)),mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words_IsA +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		cursor_Synonym.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.8),mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank FROM metadata_table mt,to_tsquery('"+words_Synonym +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		cursor_RelatedTo.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.7),mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank FROM metadata_table mt,to_tsquery('"+words_RelatedTo +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.6),mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank FROM metadata_table mt,to_tsquery('"+words_MannerOf +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,ts_rank(mt.tokens,tsq) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_IsA +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_Synonym.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.8,'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_Synonym +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_RelatedTo.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.7,'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+ words_RelatedTo +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");
		cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.6,'-',st_area(ST_Intersection(st_makevalid(st_geomfromgeojson('"+geocoding_result+"'))::geometry, poly_geometry))), mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank,st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) area FROM metadata_table mt,to_tsquery('"+words_MannerOf +"') as tsq where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc,area desc;");	
	return cursor_IsA,cursor_Synonym,cursor_RelatedTo,cursor_MannerOf;
Articles = Articles()

@app.route('/')

def index():
	return render_template('front-base.html');
def conceptnetExpansion(theme):
	conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+theme.lower()+'').json();
	conceptnet_all = [];
	conceptnet_weights = [];
	conceptnet_all_selected = [];
	conceptnet_RelatedTo=[];
	conceptnet_FormOf=[];
	conceptnet_IsA=[];
	conceptnet_MannerOf=[];
	conceptnet_Synonym=[];
	offset = 0;
	conceptnet__words = [];
	counter = 0;
	while len(conceptnet_result1['edges'])>0:
		counter += 1;
		for edge in conceptnet_result1['edges']:
			if 'weight' in edge and edge['weight']>=1:
				if 'language' in edge['start'] and 'language' in edge['end']:
					if edge['start']['language']=='en' and edge['start']['label'] not in conceptnet_all_selected:						
						if(edge['rel']['label']=='IsA'):
							conceptnet_IsA.append(edge['start']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='FormOf'):
							conceptnet_FormOf.append(edge['start']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='RelatedTo'):
							conceptnet_RelatedTo.append(edge['start']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='MannerOf'):
							conceptnet_MannerOf.append(edge['start']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='Synonym'):
							conceptnet_Synonym.append(edge['start']['label'].replace(" ", "_"));
						conceptnet_all_selected.append(edge['start']['label'].replace(" ", "_"));
						conceptnet_weights.append(edge['end']['label'] + '-' + str(edge['weight']));
					if edge['end']['language']=='en' and edge['end']['label'] not in conceptnet_all_selected:
						if(edge['rel']['label']=='IsA'):
							conceptnet_IsA.append(edge['end']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='FormOf'):
							conceptnet_FormOf.append(edge['end']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='RelatedTo'):
							conceptnet_RelatedTo.append(edge['end']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='MannerOf'):
							conceptnet_MannerOf.append(edge['end']['label'].replace(" ", "_"));
						elif(edge['rel']['label']=='Synonym'):
							conceptnet_Synonym.append(edge['end']['label'].replace(" ", "_"));
						conceptnet_all_selected.append(edge['end']['label']);
						conceptnet_weights.append(edge['end']['label'] + '-' + str(edge['weight']));
		offset = offset + 20;
		conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+theme.lower()+'?offset='+str(offset)+'&limit='+str(20)).json();
	return conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf;
def formulate_keywords(themes,locations):
	words_IsA = "";words_Synonym = "";words_RelatedTo = "";words_MannerOf = "";
	for theme in themes:
		conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(theme);
		for word in conceptnet_IsA:
			word = re.sub('[^_a-zA-Z0-9]', '', word);
			words_IsA = words_IsA + "|"+word.lower();
		for word in conceptnet_Synonym:
			word = re.sub('[^_a-zA-Z0-9]', '', word);
			words_Synonym = words_Synonym + "|"+word.lower();
		for word in conceptnet_RelatedTo:
			word = re.sub('[^_a-zA-Z0-9]', '', word);
			words_RelatedTo = words_RelatedTo + "|"+word.lower();
		for word in conceptnet_MannerOf:
			word = re.sub('[^_a-zA-Z0-9]', '', word);
			words_MannerOf = words_MannerOf + "|"+word.lower();
	if words_IsA:
		if(words_IsA[0] == "|"):
			words_IsA = words_IsA[1:];
		if(words_IsA[len(words_IsA)-1] == "|"):
			words_IsA = words_IsA[:-1];
	if words_Synonym:
		if(words_Synonym[0] == "|"):
			words_Synonym = words_Synonym[1:];
		if(words_Synonym[len(words_Synonym)-1] == "|"):
			words_Synonym = words_Synonym[:-1];
	if words_RelatedTo:
		if(words_RelatedTo[0] == "|"):
			words_RelatedTo = words_RelatedTo[1:];
		if(words_RelatedTo[len(words_RelatedTo)-1] == "|"):
			words_RelatedTo = words_RelatedTo[:-1];
	if words_MannerOf:
		if(words_MannerOf[0] == "|"):
			words_MannerOf = words_MannerOf[1:];
		if(words_MannerOf[len(words_MannerOf)-1] == "|"):
			words_MannerOf = words_MannerOf[:-1];
	print(words_IsA,words_Synonym,words_RelatedTo,words_MannerOf);
	return words_IsA, words_Synonym, words_RelatedTo, words_MannerOf;
@app.route('/result_conceptnet',methods=['POST','GET'])

def result_conceptnet():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		for key, k_type in zip(keywords, key_types):
			# print(k_type);
			if(k_type=='Location'):
				location.append(key);
			else:
				themes.append(key);
		# print(themes,location);
		my_metadata = [];
		mymetadata_IsA,mymetadata_Synonym,mymetadata_RelatedTo,mymetadata_MannerOf = selectData(themes,location);
		my_metadata = mymetadata_IsA.fetchall();
		for metadata in mymetadata_Synonym.fetchall():
			my_metadata.append(metadata);
		for metadata in mymetadata_RelatedTo.fetchall():
			my_metadata.append(metadata);
		for metadata in mymetadata_MannerOf.fetchall():
			my_metadata.append(metadata);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[1])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				for i in range(len(my_metadata)):
					if(diff_b!=0 and diff_c!=0):
						my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					elif(diff_c==0):
						diff_c = max(c)-(min(c)/2);
						my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					else:
						diff_b = max(b)-(min(b)/2);
						my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
				item = itemgetter(6);
			my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_conceptnet.html');

@app.route('/postmethod', methods = ['POST'])
def postmethod():
    jsdata = request.form;
    # print(dict(jsdata));
    keywords = dict(jsdata).get('javascript_data[]');
    user_id=selectSession().fetchall()[0][0];
    keywords_split = keywords[1].split('&');
    id_split = keywords[0].split('-');
    searchKeywords = [];
    i=0;
    while i<len(keywords_split):
    	keyword=keywords_split[i].split('=');
    	if(keyword[0]=='keyword'):
    		searchKeywords.append(keyword[1]);
    	i=i+1;
    rating = id_split[2];
    id_dataset = id_split[3];
    strategy=5;
    conn = connect();
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
    cursor.execute("Insert into ratings values("+str(user_id)+","+str(id_dataset)+",array"+str(searchKeywords)+","+str(strategy)+","+str(rating)+") on conflict (id,id_dataset,search_keywords,strategy) do update set rating=Excluded.rating;");
    conn.commit();
    return 'base';
	
@app.route('/articles')

def articles():
	return render_template('articles.html',articles = Articles);

@app.route('/details')

def details():
	return render_template('details.html');

# @app.route('/harvest')

# def articles():
# 	return render_template('harvest.html',harvest = Harvest);

if __name__ == '__main__':
	app.run(debug=True,host='localhost',port=50030)
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'

# @app.route('/result', methods=['GET','POST'])

# def result():
	

def details():
	return render_template('details.html');


#################