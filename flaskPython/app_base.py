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
from osgeo import ogr
import traceback
from flask import jsonify


 


app = Flask(__name__)
app.debug = True
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/ckan_metadata'
# db = SQLAlchemy(app)
def connect():
	conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
	conn = psycopg2.connect(conn_string)
	return conn;
def selectSimilar(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	try:
		cursor.execute("SELECT ts_rank(i.tokens, replace(strip(original.tokens)::text, ' ', '|')::tsquery) as similarity, i.id, i.id_increment, i.title, i.description, i.geom,i.poly_geometry FROM metadata_table i, (SELECT tokens, id_increment FROM metadata_table WHERE id_increment="+ str(id_increment) +" limit 1) AS original WHERE i.id_increment != original.id_increment ORDER BY similarity desc limit 5");
	except Exception:
		traceback.print_exc();
		return;
	return cursor;
def selectDetails(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	# words = formulate_keywords(themes,location);
	# print(words);
	# geocoding_result = requests.get('http://api.geonames.org/searchJSON?q='+location[0]+'&maxRows=10&username=brhanebt01');
	# cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title, ts_rank(mt.tokens,tsq)) as title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ST_Intersects('POINT("+geocoding_result.json()['geonames'][0]['lng']+" "+geocoding_result.json()['geonames'][0]['lat']+")'::geography::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	cursor.execute("SELECT id_increment,id,title,description,st_asgeojson(geom),st_asgeojson(poly_geometry) FROM metadata_table where id_increment = "+id_increment+";");
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
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords(themes,location);
	print(words);
	print(len(location));
	print(len(themes));
	if(len(location) and len(themes)):
		# print('here');
		geocoding_result = getGeom(location[0]);
		# print(geocoding_result);
		cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title, ts_rank(mt.tokens,tsq)) as title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	elif(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title, ts_rank(mt.tokens,tsq)) as title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description FROM metadata_table mt where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and ts_rank(mt.tokens,tsq) > 0 order by rank desc;");	
	return cursor;

Articles = Articles()

@app.route('/')

def index():
	return render_template('front-base.html');

def formulate_keywords(themes,locations):
	words = "";
	for word in themes:
		words = words + "|"+word.lower();
	for word in locations:
		words = words + "|"+word.lower();
	if(words[0] == "|"):
		words = words[1:];
	if(words[len(words)-1] == "|"):
		words = words[:-1];
	# print(words);
	return words;
@app.route('/result_base',methods=['POST','GET'])

def result_base():
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
		mymetadata = selectData(themes,location);
		my_metadata= mymetadata.fetchall();
		# print(my_metadata);
		return jsonify(my_metadata);
		 # = ['my_metadata',['hjksfh']],themes=themes,locations=location
	return render_template('result_base.html');


@app.route('/articles')

def articles():
	return render_template('articles.html',articles = Articles);

@app.route('/details/<string:id>')

def details(id, methods=['GET','POST']):
	selectedMetadata = selectDetails(id);
	selected_metadata= selectedMetadata.fetchall();
	selected_similar = selectSimilar(selected_metadata[0][0]);
	print(selected_metadata[0][5]);
	# print(selected_similar.fetchall());
	return render_template('details.html',selected_metadata=selected_metadata,selected_similar=selected_similar.fetchall());
# @app.route('/harvest')

# def articles():
# 	return render_template('harvest.html',harvest = Harvest);

if __name__ == '__main__':
	app.run(debug=True,host='localhost',port=5001)
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'

# @app.route('/result', methods=['GET','POST'])

# def result():
	

def details():
	return render_template('details.html');


#################
