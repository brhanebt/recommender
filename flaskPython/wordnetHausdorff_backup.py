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
		cursor.execute("SELECT ts_rank(i.tokens, replace(strip(original.tokens)::text, ' ', '|')::tsquery) as similarity, i.id, i.id_increment, i.title, i.description, i.geom,i.the_geom FROM metadata_table i, (SELECT tokens, id_increment FROM metadata_table WHERE id_increment="+ str(id_increment) +" limit 1) AS original WHERE i.id_increment != original.id_increment ORDER BY similarity desc limit 5");
	except Exception:
		traceback.print_exc();
		return;
	return cursor;

def selectDetails(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	cursor.execute("SELECT id_increment,id,title,description,st_asgeojson(geom),st_asgeojson(the_geom) FROM metadata_table where id_increment = "+id_increment+";");
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
	wordSyns_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHypo_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHyper_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordPartMero_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns,wordHypo,wordHyper,wordPartMero = formulate_keywords(themes,location);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		print('hohu');
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.9,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordSyns +"') as tsq where ts_rank(mt.tokens,tsq) > 0;");
		wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.8,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordHypo +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.7,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordHyper +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		wordPartMero_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.6,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordPartMero +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		print('huho');
	elif(len(themes)):
		print('hoha');
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.9) title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+wordSyns +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.8) title,mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank FROM metadata_table mt,to_tsquery('"+wordHypo +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.7) title,mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank FROM metadata_table mt,to_tsquery('"+wordHyper +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		wordPartMero_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.6) title,mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank FROM metadata_table mt,to_tsquery('"+wordPartMero +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		print('haho');
	elif(len(location)):
		print('hohe');
		geocoding_result = getGeom(location[0]);
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.9,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordSyns +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.8,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordHypo +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.7,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordHyper +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		wordPartMero_cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq)*0.6,'-',ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)), mt.description,(ts_rank(mt.tokens,tsq)*0.6) rank,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) area FROM metadata_table mt,to_tsquery('"+wordPartMero +"') as tsq where ts_rank(mt.tokens,tsq) > 0 ;");
		print('heho');
	return wordSyns_cursor,wordHypo_cursor,wordHyper_cursor,wordPartMero_cursor;
Articles = Articles()

@app.route('/')

def index():
	return render_template('front-base.html');
def wordnetExpansion(theme):
	wordnet_all = [];
	wordnet_lemmas = [];
	wordnet_syns = [];
	wordnet_hypo = [];
	wordnet_hyper = [];
	wordnet_part_mero = [];
	for synset in wn.synsets(theme):
		for lemma in synset.lemma_names():
			wordnet_syns.append(lemma);
			wordnet_all.append(lemma);
		synsets = synset.hypernyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					wordnet_hyper.append(lemma);
					wordnet_all.append(lemma);
		synsets = synset.part_meronyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					wordnet_part_mero.append(lemma);
					wordnet_all.append(lemma);
		synsets = synset.hyponyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					wordnet_hypo.append(lemma);
					wordnet_all.append(lemma);
	# print(wordnet_all)
	return wordnet_syns,wordnet_hypo,wordnet_hyper,wordnet_part_mero;

def formulate_keywords(themes,locations):
	wordSyns = "";
	wordHypo = "";
	wordHyper = "";
	wordPartMero = "";
	for theme in themes:
		wordnetSyns, wordnetHypo, wordnetHyper, wordnetPartMero=wordnetExpansion(theme);
		for word in wordnetSyns:
			wordSyns = wordSyns + "|"+word.lower();
		for word in wordnetHypo:
			wordHypo = wordHypo + "|"+word.lower();
		for word in wordnetHyper:
			wordHyper = wordHyper + "|"+word.lower();
		for word in wordnetPartMero:
			wordPartMero = wordPartMero + "|"+word.lower();
	for theme in locations:
		wordnetSyns, wordnetHypo, wordnetHyper, wordnetPartMero=wordnetExpansion(theme);
		for word in wordnetSyns:
			wordSyns = wordSyns + "|"+word.lower();
		for word in wordnetHypo:
			wordHypo = wordHypo + "|"+word.lower();
		for word in wordnetHyper:
			wordHyper = wordHyper + "|"+word.lower();
		for word in wordnetPartMero:
			wordPartMero = wordPartMero + "|"+word.lower();
	if(wordSyns[0] == "|"):
		wordSyns = wordSyns[1:];
	if(wordHypo[0] == "|"):
		wordHypo = wordHypo[1:];
	if(wordHyper[0] == "|"):
		wordHyper = wordHyper[1:];
	if(wordPartMero[0] == "|"):
		wordPartMero = wordPartMero[1:];
	# print(wordSyns);
	# print(wordHypo);
	# print(wordHyper);
	# print(wordPartMero);
	return wordSyns, wordHypo, wordHyper, wordPartMero;
@app.route('/result_wordnet',methods=['POST','GET'])

def result_wordnet():
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
		print('hello');
		mymetadata_syns,mymetadata_hypo,mymetadata_hyper,mymetadata_partMero = selectData(themes,location);
		mymetadata_syn= mymetadata_syns.fetchall();
		print('hi');
		for metadata in mymetadata_hypo.fetchall():
			mymetadata_syn.append(metadata);
		for metadata in mymetadata_hyper.fetchall():
			mymetadata_syn.append(metadata);
		for metadata in mymetadata_partMero.fetchall():
			mymetadata_syn.append(metadata);
		item = itemgetter(4);
		if(len(mymetadata_syn[1])>5):
			b = [el[4] for el in mymetadata_syn];
			c = [el[5] for el in mymetadata_syn];
			print(b);
			# print(c);
			for i in range(len(mymetadata_syn)):
				mymetadata_syn[i].append((mymetadata_syn[i][4]-min(b))/(max(b)-min(b)) + (mymetadata_syn[i][5]-min(c))/(max(c)-min(c))); 
			item = itemgetter(6);
		mymetadata_syn = sorted(mymetadata_syn, key=item, reverse=True)
		return jsonify(mymetadata_syn);
	return render_template('result_wordnet.html');

@app.route('/articles')

def articles():
	return render_template('articles.html',articles = Articles);

@app.route('/details/<string:id>')

def details(id, methods=['GET','POST']):
	selectedMetadata = selectDetails(id);
	selected_metadata= selectedMetadata.fetchall();
	selected_similar = selectSimilar(selected_metadata[0][0]);
	print(selected_similar.fetchall());
	return render_template('details.html',selected_metadata=selected_metadata,selected_similar=selected_similar.fetchall());

# @app.route('/harvest')

# def articles():
# 	return render_template('harvest.html',harvest = Harvest);

if __name__ == '__main__':
	app.run(debug=True,host='localhost',port=5002)
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'

# @app.route('/result', methods=['GET','POST'])

# def result():
	

def details():
	return render_template('details.html');


#################