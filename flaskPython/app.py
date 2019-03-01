from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect, Markup
from sqlalchemy import and_
import re, sys
from bs4 import BeautifulSoup
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk import word_tokenize
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

import psycopg2, requests, json
from string import digits
# from config import config
import psycopg2
import sys
import psycopg2.extras
from osgeo import ogr
import traceback
from flask import jsonify
from operator import itemgetter

app = Flask(__name__)
app.debug = True


def formulate_keywords(themes,locations):
	words = "";
	for word in themes:
		words = words + "&" + word.lower();
	# for word in locations:
	# 	words = words + "|"+word.lower();
	# print(words);
	if(words[0] == "&") :
		words = words[1:];
	if(words[len(words)-1] == "&"):
		words = words[:-1];
	# print(words);
	return words;

def wordnetAllExpansion(theme):
	wordnet_all = [];
	wordnet_lemmas = [];
	wordnet_syns = [];
	wordnet_hypo = [];
	wordnet_hyper = [];
	wordnet_part_mero = [];
	for synset in wn.synsets(theme[0]):
		for lemma in synset.lemma_names():
			lemma = re.sub('[^_a-zA-Z0-9]', '', lemma)
			if(lemma not in wordnet_all):
				wordnet_syns.append(lemma);
				wordnet_all.append(lemma);
		synsets = synset.hypernyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					lemma = re.sub('[^_a-zA-Z0-9]', '', lemma);
					if(lemma not in wordnet_all):
						wordnet_hyper.append(lemma);
						wordnet_all.append(lemma);
		synsets = synset.hyponyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					lemma = re.sub('[^_a-zA-Z0-9]', '', lemma)
					if(lemma not in wordnet_all):
						wordnet_hypo.append(lemma);
						wordnet_all.append(lemma);
	return wordnet_syns,wordnet_hypo,wordnet_hyper;

def formulate_keywords_WordNetAll(themes,locations):
	wordSyns = "";
	wordHypo = "";
	wordHyper = "";
	wordPartMero = "";
	for theme in themes:
		wordnetSyns, wordnetHypo, wordnetHyper=wordnetAllExpansion(theme);
		for word in wordnetSyns:
			wordSyns = wordSyns + "|"+word.lower();
		for word in wordnetHypo:
			wordHypo = wordHypo + "|"+word.lower();
		for word in wordnetHyper:
			wordHyper = wordHyper + "|"+word.lower();
	if(len(wordSyns)):
		if(wordSyns[0] == "|"):
			wordSyns = wordSyns[1:];
	if(len(wordHypo)):
		if(wordHypo[0] == "|"):
			wordHypo = wordHypo[1:];
	if(len(wordHyper)):
		if(wordHyper[0] == "|"):
			wordHyper = wordHyper[1:];
	return wordSyns, wordHypo, wordHyper;# wordPartMero;
def wordnetExpansion(theme):
	wordnet_all = [];
	wordnet_lemmas = [];
	wordnet_syns = [];
	wordnet_hypo = [];
	wordnet_hyper = [];
	wordnet_part_mero = [];
	for synset in wn.synsets(theme[0]):
		for lemma in synset.lemma_names():
			lemma = re.sub('[^_a-zA-Z0-9]', '', lemma)
			if(lemma not in wordnet_all):
				wordnet_syns.append(lemma);
				wordnet_all.append(lemma);
		synsets = synset.hypernyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					lemma = re.sub('[^_a-zA-Z0-9]', '', lemma);
					if(lemma not in wordnet_all):
						wordnet_hyper.append(lemma);
						wordnet_all.append(lemma);
		synsets = synset.part_meronyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					lemma = re.sub('[^_a-zA-Z0-9]', '', lemma)
					if(lemma not in wordnet_all):
						wordnet_part_mero.append(lemma);
						wordnet_all.append(lemma);
		synsets = synset.hyponyms();
		if(synsets):
			for syn in synsets:
				for lemma in syn.lemma_names():
					lemma = re.sub('[^_a-zA-Z0-9]', '', lemma)
					if(lemma not in wordnet_all):
						wordnet_hypo.append(lemma);
						wordnet_all.append(lemma);
	return wordnet_syns,wordnet_hypo,wordnet_hyper,wordnet_part_mero;

def formulate_keywords_base(themes,locations):
	print(themes);
	words = "";
	for word in themes:
		words = words + "|"+word.lower();
	# for word in locations:
	# 	words = words + "|"+word.lower();
	if(words[0] == "|"):
		words = words[1:];
	if(words[len(words)-1] == "|"):
		words = words[:-1];
	# print(words);
	return words;

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
						if(edge['start']['label'].replace(" ", "_") not in conceptnet_all_selected):										
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
						if(edge['start']['label'].replace(" ", "_") not in conceptnet_all_selected):
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
							conceptnet_all_selected.append(edge['start']['label'].replace(" ", "_"));
							conceptnet_weights.append(edge['end']['label'] + '-' + str(edge['weight']));
		offset = offset + 20;
		conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+theme.lower()+'?offset='+str(offset)+'&limit='+str(20)).json();
	return conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf;


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password');

def connect():
	conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
	conn = psycopg2.connect(conn_string)
	return conn;
def selectSession():
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	cursor.execute("select id, name, username, active from users where active='t';");
	return cursor;


def selectSimilar(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	try:
		cursor.execute("SELECT ts_rank(i.tokens, replace(strip(original.tokens)::text, ' ', '|')::tsquery) as similarity, i.id, i.id_increment, i.title, i.description, i.geom,i.poly_geography FROM metadata_table i, (SELECT tokens, id_increment FROM metadata_table WHERE id_increment="+ str(id_increment) +" limit 1) AS original WHERE i.id_increment != original.id_increment ORDER BY similarity desc limit 5");
	except Exception:
		traceback.print_exc();
		return;
	return cursor;
def selectDetails(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	cursor.execute("SELECT id_increment,id,title,description,st_asgeojson(geom),st_asgeojson(poly_geography) FROM metadata_table where id_increment = "+id_increment+";");
	return cursor;
def getGeom(location):
	polygonpoints = [];
	bbox = "";
	geojsonFeature = "";
	polyPoints = [];
	poly_wkt=[];
	geocoding_result = requests.get('https://nominatim.openstreetmap.org/search?q='+location+'&format=json&polygon=1&addressdetails=1');
	bbox = geocoding_result.json()[0]['boundingbox'];
	poly_wkt.append([float(bbox[2]),float(bbox[0])]);
	poly_wkt.append([float(bbox[3]),float(bbox[0])]);
	poly_wkt.append([float(bbox[3]),float(bbox[1])]);
	poly_wkt.append([float(bbox[2]),float(bbox[1])]);
	poly_wkt.append([float(bbox[2]),float(bbox[0])]);
	geojsonFeature = {"type":"Polygon","coordinates":[poly_wkt],"crs":{"type":"name","properties":{"name":"EPSG:4326"}}};
	geojsonFeature=json.dumps(geojsonFeature);
	return geojsonFeature;

def selectData_Keyword(themes,location):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords(themes,location);
	# print(words);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') tsq where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) and tsq @@ mt.tokens order by rank desc;");
	elif(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') tsq where tsq @@ mt.tokens order by rank desc;");
	return cursor;

def selectData_base(themes,location):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords_base(themes,location);
	print(words);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT id,id_increment,title,description,ts_rank(tokens,tsq) rank, area from (SELECT mt.id,mt.id_increment,mt.title,mt.description,mt.tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography)) spatial, to_tsquery('"+words +"') tsq where tsq @@ tokens order by rank desc;");
	elif(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') tsq where tsq @@ mt.tokens order by rank desc;");
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description FROM metadata_table mt where ST_Intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography) and tsq @@ mt.tokens order by rank desc;");	
	return cursor;

def selectData_Hausdorff(themes,location):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords_base(themes,location);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		print(geocoding_result);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank,mt.distance from (SELECT id,id_increment,title, description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt, to_tsquery('"+words +"') tsq where tsq @@ tokens order by rank desc;");
	elif(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where tsq @@ mt.tokens order by rank desc;");
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,ts_rank(mt.tokens,tsq) rank,mt.distance from (SELECT id,id_increment,title, description,tokens,ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt, to_tsquery('"+words +"') tsq where tsq @@ tokens order by rank desc;");
	return cursor;

def selectData_WordNet(themes,location):
	conn = connect();
	words_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHypo_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHyper_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordPartMero_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# wordSyns,wordHypo,wordHyper,wordPartMero = formulate_keywords(themes,location);
	wordSyns,wordHypo,wordHyper,wordPartMero = wordnetExpansion(themes);
	# print(wordSyns,wordHypo,wordHyper,wordPartMero);
	wordSyns_all = [];
	indexes = [];
	# print(wordSyns);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+themes[0] +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
		# words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.5) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+themes[0] +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
		words_arr = words_cursor.fetchall();
		# print(wordSyns);
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
			# wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
	elif(len(themes)):
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		wordSyns_arr = words_cursor.fetchall();
		for rows in wordSyns_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);		
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography) order by area desc;");
		wordSyns_all = wordSyns_cursor.fetchall();
	return wordSyns_all;

def selectData_WordNetHausdorff(themes,location):
	conn = connect();
	words_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHypo_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHyper_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordPartMero_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# wordSyns,wordHypo,wordHyper,wordPartMero = formulate_keywords(themes,location);
	wordSyns,wordHypo,wordHyper,wordPartMero = wordnetExpansion(themes);
	# print(wordSyns,wordHypo,wordHyper,wordPartMero);
	wordSyns_all = [];
	indexes = [];
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+themes[0] +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
		words_arr = words_cursor.fetchall();
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
	elif(len(themes)):		
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title ,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		words_arr = words_cursor.fetchall();
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_arr.append(rows);
		# print(len(wordSyns_arr));
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);		
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) order by distance desc;");
		wordSyns_all = wordSyns_cursor.fetchall();
	return wordSyns_all;

def selectData_WordNetAll(themes,location):
	conn = connect();
	words_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHypo_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHyper_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# wordPartMero_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# wordSyns,wordHypo,wordHyper,wordPartMero = formulate_keywords(themes,location);
	wordSyns,wordHypo,wordHyper = wordnetExpansion(themes);
	# print(wordSyns,wordHypo,wordHyper);
	wordSyns_all = [];
	indexes = [];
	# print(wordSyns);
	# print(wordHypo);
	# print(wordHyper);
	# print(wordPartMero);
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+themes[0] +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
		words_arr = words_cursor.fetchall();
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank ,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			# print(len(wordSyns_arr));
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		# print(len(wordSyns_all));
		for word in wordHyper:
			wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
			wordHyper_arr = wordHyper_cursor.fetchall();
			for rows in wordHyper_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		for word in wordHypo:#0.8
			wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,mt.area from( SELECT id,id_increment,title,description,tokens,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,area desc;");
			wordHypo_arr = wordHypo_cursor.fetchall();
			for rows in wordHypo_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
	elif(len(themes)):
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		wordSyns_arr = words_cursor.fetchall();
		for rows in wordSyns_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);	
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		for word in wordHypo:
			wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordHypo_arr = wordHypo_cursor.fetchall();
			for rows in wordHypo_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		for word in wordHyper:
			wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordHyper_arr = wordHyper_cursor.fetchall();
			for rows in wordHyper_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);	
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography) order by area desc;");
		wordSyns_all = wordSyns_cursor.fetchall();
	return wordSyns_all;
def selectData_WordNetAll_Hausdorff(themes,location):
	conn = connect();
	words_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHypo_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordHyper_cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	wordSyns,wordHypo,wordHyper = wordnetExpansion(themes);
	# print(wordSyns,wordHypo,wordHyper);
	wordSyns_all = [];
	indexes = [];
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+themes[0] +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
		words_arr = words_cursor.fetchall();
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_all.append(rows);
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank ,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		for word in wordHyper:
			wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
			wordHyper_arr = wordHyper_cursor.fetchall();
			for rows in wordHyper_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		# print(wordSyns_all);
		for word in wordHypo:
			wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank ,mt.distance from ( SELECT id,id_increment,title,description,tokens,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt, to_tsquery('"+word +"') tsq  where tsq @@ mt.tokens order by rank desc,distance desc;");
			wordHypo_arr = wordHypo_cursor.fetchall();
			for rows in wordHypo_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
	elif(len(themes)):		
		words_cursor.execute("SELECT mt.id,mt.id_increment,mt.title ,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
		words_arr = words_cursor.fetchall();
		for rows in words_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				wordSyns_arr.append(rows);
		# print(len(wordSyns_arr));
		for word in wordSyns:
			wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordSyns_arr = wordSyns_cursor.fetchall();
			for rows in wordSyns_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		# print(len(wordSyns_arr));
		for word in wordHypo:
			wordHypo_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordHypo_arr = wordHypo_cursor.fetchall();
			for rows in wordHypo_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);
		for word in wordHyper:
			wordHyper_cursor.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.8) rank FROM metadata_table mt,to_tsquery('"+word +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
			wordHyper_arr = wordHyper_cursor.fetchall();
			for rows in wordHyper_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					wordSyns_all.append(rows);	
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		wordSyns_cursor.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography) order by area desc;");
		wordSyns_all = wordSyns_cursor.fetchall();
	return wordSyns_all;

def selectData_ConceptNet(themes,location):
	conn = connect();
	cursor_IsA = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_Synonym = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_RelatedTo = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_MannerOf = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# words_IsA, words_Synonym, words_RelatedTo, words_MannerOf = formulate_keywords(themes,location);
	conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(themes[0]);
	# print(conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo);
	conceptnetAll = [];
	indexes=[];
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(themes)):
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);		
		for concept in conceptnet_Synonym:
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt order by area desc;");
		conceptnetAll=cursor_IsA.fetchall();
	return conceptnetAll;

def selectData_ConceptNetAll(themes,location):
	conn = connect();
	cursor_IsA = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_Synonym = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_RelatedTo = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_MannerOf = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(themes[0]);
	conceptnetAll = [];
	indexes=[];
	if(len(location) and len(themes)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,ts_rank(mt.tokens,tsq) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
		for concept in conceptnet_IsA:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
			cursorIsA_arr = cursor_IsA.fetchall();
			for rows in cursorIsA_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);				
		for concept in conceptnet_MannerOf:
			cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
			cursorMannerOf_arr = cursor_MannerOf.fetchall();
			for rows in cursorMannerOf_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(themes)):
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);
		for concept in conceptnet_IsA:
			cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorIsA_arr = cursor_IsA.fetchall();
			for rows in cursorIsA_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);				
		for concept in conceptnet_Synonym:
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
		for concept in conceptnet_MannerOf:
			cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorMannerOf_arr = cursor_MannerOf.fetchall();
			for rows in cursorMannerOf_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);	
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt order by area desc;");
		conceptnetAll=cursor_IsA.fetchall();
	return conceptnetAll;
def selectData_ConceptNetHausdorff(themes,location):
	conn = connect();
	cursor_IsA = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_Synonym = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_RelatedTo = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_MannerOf = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# words_IsA, words_Synonym, words_RelatedTo, words_MannerOf = formulate_keywords(themes,location);
	conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(themes[0]);
	print(conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo);
	conceptnetAll = [];
	indexes=[];
	if(len(location) and len(themes)):		
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);	
	elif(len(themes)):
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);				
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, mt.poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt order distance desc;");
		conceptnetAll=cursor_IsA.fetchall();
	return conceptnetAll;
def selectData_ConceptNetHausdorffAll(themes,location):
	conn = connect();
	cursor_IsA = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_Synonym = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_RelatedTo = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	cursor_MannerOf = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
	# words_IsA, words_Synonym, words_RelatedTo, words_MannerOf = formulate_keywords(themes,location);
	conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(themes[0]);
	# print(conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo);
	conceptnetAll = [];
	indexes=[];
	if(len(location) and len(themes)):		
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);	
		for concept in conceptnet_IsA:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
			cursorIsA_arr = cursor_IsA.fetchall();
			for rows in cursorIsA_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
		for concept in conceptnet_MannerOf:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank,mt.distance from (SELECT  id,id_increment,title,description,tokens, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,distance desc;");
			cursorMannerOf_arr = cursor_MannerOf.fetchall();
			for rows in cursorMannerOf_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(themes)):
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+themes[0] +"') as tsq where tsq @@ mt.tokens order by rank desc;");
		cursorIsA_arr = cursor_IsA.fetchall();
		for rows in cursorIsA_arr:
			if(rows[0] not in indexes):
				indexes.append(rows[0]);
				conceptnetAll.append(rows);				
		for concept in conceptnet_Synonym:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_Synonym.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorSyn_arr = cursor_Synonym.fetchall();
			for rows in cursorSyn_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
		for concept in conceptnet_IsA:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorIsA_arr = cursor_IsA.fetchall();
			for rows in cursorIsA_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
		for concept in conceptnet_MannerOf:
			concept = re.sub('[^_a-zA-Z0-9]', '', concept);
			cursor_MannerOf.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.9) rank FROM metadata_table mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc;");
			cursorMannerOf_arr = cursor_MannerOf.fetchall();
			for rows in cursorMannerOf_arr:
				if(rows[0] not in indexes):
					indexes.append(rows[0]);
					conceptnetAll.append(rows);
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description, Greatest(ST_HausdorffDistance(st_geomfromgeojson('"+geocoding_result+"')::geometry, mt.poly_geometry),ST_HausdorffDistance(poly_geometry,st_geomfromgeojson('"+geocoding_result+"')::geometry)) distance FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"')::geometry, poly_geometry)) mt order distance desc;");
		conceptnetAll=cursor_IsA.fetchall();
	return conceptnetAll;



@app.route('/result_base_keyword',methods=['POST','GET'])

def result_base_keyword():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		# print(keywords);
		# print(key_types);
		themes = [];
		location = [];
		for key in keywords:
				key = re.sub(r"\s+", '_', key);
				themes.append(key);
		print(themes);
		mymetadata = selectData_Keyword(themes,location);
		my_metadata= mymetadata.fetchall();
		indexes =[];
		metadata_all=[];
		for row in my_metadata:
			if(row[0] not in indexes):
				indexes.append(row[0]);
				metadata_all.append(row);
		my_metadata=metadata_all;
		# print(my_metadata);
		item = itemgetter(4);
		if(len(my_metadata)):
			print(len(my_metadata));
			if(len(my_metadata[0]) and len(my_metadata[0])>5):
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
	return render_template('result_base_keyword.html');



@app.route('/result_base',methods=['POST','GET'])

def result_base():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		indexes = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		print(location,themes);
		mymetadata = selectData_base(themes,location);
		my_metadata= mymetadata.fetchall();
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = float(max(b)-min(b));
				diff_c = float(max(c)-min(c));
				if(len(my_metadata)>1 and (diff_b!=0 and diff_c !=0)):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							my_metadata[i].append((float(my_metadata[i][4])-float(min(b)))/(diff_b) + (float(my_metadata[i][5])-float(min((c))))/(diff_c)); 
						elif(diff_c==0):
							diff_c = float(max(c)-(min(c)/2));
							my_metadata[i].append((float(my_metadata[i][4])-float(min(b)))/(diff_b) + (float(my_metadata[i][5])-float(min((c))))/(diff_c)); 
						else:
							diff_b = float(max(b)-(min(b)/2));
							my_metadata[i].append((float(my_metadata[i][4])-float(min(b)))/(diff_b) + (float(my_metadata[i][5])-float(min((c))))/(diff_c)); 
					item = itemgetter(6);
				my_metadata = sorted(my_metadata, key=item, reverse=True);
		indexes =[];
		metadata_all=[];
		for row in my_metadata:
			if(row[0] not in indexes):
				indexes.append(row[0]);
				metadata_all.append(row);
		my_metadata=metadata_all;
		return jsonify(my_metadata);
	return render_template('result_base.html',spatialMethod='Area of Overlap');


@app.route('/result_base_hausdorff',methods=['POST','GET'])

def result_base_hausdorff():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		mymetadata = selectData_Hausdorff(themes,location);
		my_metadata= mymetadata.fetchall();
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							spatialWeight = (my_metadata[i][5]-min(c))/(diff_c);
							thematicWeight = (my_metadata[i][4]-min(b))/(diff_b);
							# print(spatialWeight,abs(spatialWeight - diff_c));
							my_metadata[i].append((thematicWeight) + abs(spatialWeight - diff_c)); 
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
				my_metadata = sorted(my_metadata, key=item, reverse=True);
		indexes =[];
		metadata_all=[];
		for row in my_metadata:
			if(row[0] not in indexes):
				# print(row[1],row[4],row[5],row[6]);
				indexes.append(row[0]);
				metadata_all.append(row);
		my_metadata=metadata_all;
		return jsonify(my_metadata);
	return render_template('result_base_hausdorff.html',spatialMethod='Hausdorff Distance');


@app.route('/result_wordnet',methods=['POST','GET'])

def result_wordnet():
	if request.method == 'POST':
		# start_time = time.time();
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = selectData_WordNet(themes,location);
		item = itemgetter(4);
		# print(len(my_metadata));
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				# print(b,c);
				if(len(my_metadata)>1 and (diff_b!=0 and diff_c !=0)):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
							print(my_metadata[i][1],my_metadata[i][len(my_metadata[i])-3],my_metadata[i][len(my_metadata[i])-1]);
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c));
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
				my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_wordnet.html',spatialMethod='Area of overlap', expansion='WordNet Synonyms');

@app.route('/result_wordnet_hausdorff',methods=['POST','GET'])

def result_wordnet_hausdorff():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = selectData_WordNetHausdorff(themes,location);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							spatialWeight = (my_metadata[i][5]-min(c))/(diff_c);
							thematicWeight = (my_metadata[i][4]-min(b))/(diff_b)
							my_metadata[i].append((thematicWeight) + abs(spatialWeight - diff_c));
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
			my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_wordnet_hausdorff.html',spatialMethod='Hausdorff Distance', expansion='WordNet Synonyms');

@app.route('/result_wordnet_all',methods=['POST','GET'])

def result_wordnet_all():
	if request.method == 'POST':
		# start_time = time.time();
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = selectData_WordNetAll(themes,location);
		item = itemgetter(4);
		# print(len(my_metadata));
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1 and (diff_b!=0 and diff_c !=0)):
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
	return render_template('result_wordnet_all.html',spatialMethod='Area of overlap', expansion='WordNet Synonyms. hypernyms, hyponyms');

@app.route('/result_wordnet_hausdorff_all',methods=['POST','GET'])

def result_wordnet_hausdorff_all():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		# for key, k_type in zip(keywords, key_types):
		# 	print(k_type);
		# 	if(k_type=='Location'):
		# 		location.append(key);
		# 	else:
		# 		themes.append(key);
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = selectData_WordNetAll_Hausdorff(themes,location);
		item = itemgetter(4);
		# print(len(mymetadata_syn));
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							spatialWeight = (my_metadata[i][5]-min(c))/(diff_c);
							thematicWeight = (my_metadata[i][4]-min(b))/(diff_b)
							my_metadata[i].append((thematicWeight) + abs(spatialWeight - diff_c));
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
			my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_wordnet_hausdorff_all.html',spatialMethod='Hausdorff Distance', expansion='WordNet Synonyms, Hypernyms, Hyponyms');


@app.route('/result_conceptnet',methods=['POST','GET'])

def result_conceptnet():
	if request.method == 'POST':
		keywords = request.form.getlist('keywordConceptNet');
		key_types = request.form.getlist('keyword_typeConceptNet');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = [];
		my_metadata = selectData_ConceptNet(themes,location);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
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
	return render_template('result_conceptnet.html', method="Area of Overlap");
@app.route('/result_conceptnet_all',methods=['POST','GET'])

def result_conceptnet_all():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = [];
		my_metadata = selectData_ConceptNetAll(themes,location);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
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
	return render_template('result_conceptnet_all.html', method="Area of Overlap");

@app.route('/result_conceptnet_hausdorff',methods=['POST','GET'])

def result_conceptnet_hausdorff():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = [];
		my_metadata = selectData_ConceptNetHausdorff(themes,location);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							spatialWeight = (my_metadata[i][5]-min(c))/(diff_c);
							thematicWeight = (my_metadata[i][4]-min(b))/(diff_b)
							my_metadata[i].append((thematicWeight) + abs(spatialWeight - diff_c));
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
				my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_conceptnet_hausdorff.html',spatialMethod='Hausdorff Distance', expansion='ConceptNet Synonyms');

@app.route('/result_conceptnet_hausdorff_all',methods=['POST','GET'])

def result_conceptnet_hausdorff_all():
	if request.method == 'POST':
		keywords = request.form.getlist('keyword');
		key_types = request.form.getlist('keyword_type');
		themes = [];
		location = [];
		location.append(keywords[1]);
		themes.append(keywords[0]);
		my_metadata = [];
		# mymetadata_IsA,mymetadata_Synonym,mymetadata_RelatedTo,mymetadata_MannerOf = selectData(themes,location);
		my_metadata = selectData_ConceptNetHausdorffAll(themes,location);
		item = itemgetter(4);
		if(len(my_metadata)):
			if(len(my_metadata[0])>5):
				b = [el[4] for el in my_metadata];
				c = [el[5] for el in my_metadata];
				diff_b = max(b)-min(b);
				diff_c = max(c)-min(c);
				if(len(my_metadata)>1):
					for i in range(len(my_metadata)):
						if(diff_b!=0 and diff_c!=0):
							spatialWeight = (my_metadata[i][5]-min(c))/(diff_c);
							thematicWeight = (my_metadata[i][4]-min(b))/(diff_b)
							my_metadata[i].append((thematicWeight) + abs(spatialWeight - diff_c));
						elif(diff_c==0):
							diff_c = max(c)-(min(c)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
						else:
							diff_b = max(b)-(min(b)/2);
							my_metadata[i].append((my_metadata[i][4]-min(b))/(diff_b) + (my_metadata[i][5]-min(c))/(diff_c)); 
					item = itemgetter(6);
				my_metadata = sorted(my_metadata, key=item, reverse=True);
		return jsonify(my_metadata);
	return render_template('result_conceptnet_hausdorff_all.html',spatialMethod='Hausdorff Distance', expansion='ConceptNet Synonyms, IsA, MannerOf');


@app.route('/postmethod', methods = ['POST'])
def postmethod():
    jsdata = request.form;
    print(dict(jsdata));
    keywords = dict(jsdata).get('javascript_data[]');
    user_id=selectSession().fetchall()[0][0];
    keywords_split = keywords[2].split('&');
    ranking_split = keywords[1].split('-');
    # print(ranking_split);
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
    strategy=2;
    conn = connect();
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
    cursor.execute("Insert into ratings values("+str(user_id)+","+str(id_dataset)+",array"+str(searchKeywords)+","+str(strategy)+","+str(rating)+","+str(ranking_split[3])+") on conflict (id,id_dataset,search_keywords,strategy) do update set rating=Excluded.rating;");
    conn.commit();
    return 'success';

@app.route('/details/<string:id>')

def details(id, methods=['GET','POST']):
	selectedMetadata = selectDetails(id);
	selected_metadata= selectedMetadata.fetchall();
	selected_similar = selectSimilar(selected_metadata[0][0]);
	return render_template('details.html',selected_metadata=selected_metadata,selected_similar=selected_similar.fetchall());

if __name__ == '__main__':
	app.run(debug=True,host='localhost',port=5001);
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'
# def details():
# 	return render_template('details.html');


#################
