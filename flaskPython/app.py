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
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/ckan_metadata'
# db = SQLAlchemy(app)

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
# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
	print('hallo');
	form = RegisterForm(request.form)
	print(request.method);
	print(form.name.data);
	if request.method == 'POST':
		if(form.name.data != "" and form.username.data != ""):
			name = form.name.data;
			username = form.username.data;
			conn = connect();
			cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
			print('here');
			try:
				cursor.execute("Update users set active = False;");
				cursor.execute("INSERT INTO users(name, username) VALUES(%s, %s)", (name, username));
				conn.commit();
			except Exception:
				traceback.print_exc();
			return render_template('home.html');
	return render_template('register.html', form=form);
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
def selectData(themes):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	words = formulate_keywords(themes);
	if(len(themes)):
		cursor.execute("SELECT mt.id,mt.id_increment,concat(mt.title, ts_rank(mt.tokens,tsq)) as title,mt.description,ts_rank(mt.tokens,tsq) rank FROM metadata_table mt,to_tsquery('"+words +"') as tsq where ts_rank(mt.tokens,tsq) > 0 order by rank desc;");
	return cursor;

Articles = Articles();

@app.route('/')

def index():
	return render_template('front.html');

def formulate_keywords(themes):
	words = "";
	for word in themes:
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
				themes.append(key);
		mymetadata = selectData(themes);
		my_metadata= mymetadata.fetchall();
		item = itemgetter(4);
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
		 # = ['my_metadata',['hjksfh']],themes=themes,locations=location
	return render_template('result_base.html');

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
    strategy=1;
    conn = connect();
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
    cursor.execute("Insert into ratings values("+str(user_id)+","+str(id_dataset)+",array"+str(searchKeywords)+","+str(strategy)+","+str(rating)+") on conflict (id,id_dataset,search_keywords,strategy) do update set rating=Excluded.rating;");
    conn.commit();
    return 'jsdata'

@app.route('/articles')

def articles():
	return render_template('articles.html',articles = Articles);

@app.route('/details/<string:id>')

def details(id, methods=['GET','POST']):
	selectedMetadata = selectDetails(id);
	selected_metadata= selectedMetadata.fetchall();
	selected_similar = selectSimilar(selected_metadata[0][0]);
	return render_template('details.html',selected_metadata=selected_metadata,selected_similar=selected_similar.fetchall());

if __name__ == '__main__':
	app.run(debug=True,host='localhost',port=5001);
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'
def details():
	return render_template('details.html');


#################
