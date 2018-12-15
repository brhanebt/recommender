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


app = Flask(__name__)
app.debug = True
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/ckan_metadata'
# db = SQLAlchemy(app)
def connect():
	conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
	conn = psycopg2.connect(conn_string)
	return conn;
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
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords(themes,location);
	if(len(location) and len(themes)):
		# print('here');
		geocoding_result = getGeom(location[0]);
		# print(geocoding_result);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	elif(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title, ts_rank(mt.tokens,tsq)) as title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description FROM metadata_table mt where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc;");	
	return cursor;
Articles = Articles()

@app.route('/')

def index():
	return render_template('front-base.html');
def conceptnetExpansion(theme):
	conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+theme.lower()+'');
	conceptnet_all = [];
	conceptnet_weights = [];
	conceptnet_all_selected = [];
	offset = 0;
	# conceptnet_words = "";
	stop = set(stopwords.words('english'));
	conceptnet__words = [];
	# print('here');
	counter = 0;
	while len(conceptnet_result1.text)>=480:
		counter += 1;
		for edge in json.loads(conceptnet_result1.text)['edges']:
			if 'weight' in edge and edge['weight']>=1:
				if 'language' in edge['start'] and 'language' in edge['end']:
					if edge['start']['language']=='en' and edge['start']['label'] not in conceptnet_all_selected:
						conceptnet_all_selected.append(edge['start']['label']);
						conceptnet_weights.append(edge['end']['label'] + "-" + str(edge['weight']));
						filtered_words = [word for word in word_tokenize(conceptnet_all_selected[len(conceptnet_all_selected)-1].lower()) if word not in stop];
					elif edge['end']['language']=='en' and edge['end']['label'] not in conceptnet_all_selected:
						conceptnet_all_selected.append(edge['end']['label']);
						conceptnet_weights.append(edge['end']['label'] + "-" + str(edge['weight']));
						filtered_words = [word for word in word_tokenize(conceptnet_all_selected[len(conceptnet_all_selected)-1].lower()) if word not in stop];
					for word in filtered_words:
						if word not in conceptnet__words:
							# conceptnet_words = conceptnet_words + "|" + word;
							conceptnet__words.append(re.sub('[^A-Za-z0-9]+', '', word));
		offset = offset + 20;
		# print(counter);
		# print(conceptnet_weights);
		if(counter>1):
			break;
		conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+theme.lower()+'?offset='+str(offset)+'&limit='+str(20));
	# print(conceptnet__words);
	return conceptnet__words;
def formulate_keywords(themes,locations):
	words = "";
	for theme in themes:
		for word in conceptnetExpansion(theme):
			words = words + "|"+word.lower();
	for location in locations:
		for word in conceptnetExpansion(location):
			words = words + "|"+word.lower();	
	if(words[0] == "|"):
		words = words[1:];
	if(words[len(words)-1] == "|"):
		words = words[:-1];
	print(words);
	return words;
@app.route('/result_conceptnet',methods=['POST','GET'])

def result_conceptnet():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		for key, k_type in zip(keywords, key_types):
			print(k_type);
			if(k_type=='Location'):
				location.append(key);
			else:
				themes.append(key);
		print(themes,location);
		mymetadata = selectData(themes,location);
		my_metadata= mymetadata.fetchall();	# print(my_metadata);
		return jsonify(my_metadata);
		 # = ['my_metadata',['hjksfh']],themes=themes,locations=location
	return render_template('result_conceptnet.html');
	


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
	app.run(debug=True,host='localhost',port=5003)
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'

# @app.route('/result', methods=['GET','POST'])

# def result():
	

def details():
	return render_template('details.html');


#################