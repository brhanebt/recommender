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

def selectDetails(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	cursor.execute("SELECT id_increment,id,title,description,st_asgeojson(geom),st_asgeojson(the_geom) FROM metadata_table mt where id_increment = "+id_increment+";");
	return cursor;	

def selectSimilar(id_increment):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor);
	try:
		cursor.execute("SELECT ts_rank(i.tokens, replace(strip(original.tokens)::text, ' ', '|')::tsquery) as similarity, i.id, i.id_increment, i.title, i.description, i.poly_geometry,i.poly_geometry FROM metadata_table i, (SELECT tokens, id_increment FROM metadata_table WHERE id_increment="+ str(id_increment) +" limit 1) AS original WHERE i.id_increment != original.id_increment ORDER BY similarity desc limit 5");
	except Exception:
		traceback.print_exc();
		return;
	return cursor;

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
	# if 'polygonpoints' in geocoding_result.json()[0].keys():
	# 	polygonpoints = geocoding_result.json()[0]['polygonpoints'];
	# 	polyPoints[:] = [[float(e) for e in sl] for sl in polygonpoints]
	# 	if(polyPoints[0]!=polyPoints[-1]):
	# 		polyPoints.append(polyPoints[0]);
	# 	geojsonFeature = {"type":"Polygon","coordinates":[polyPoints]};
	# 	geojsonFeature=json.dumps(geojsonFeature);
	# else:
	bbox = geocoding_result.json()[0]['boundingbox'];
	poly_wkt.append([float(bbox[2]),float(bbox[0])]);
	poly_wkt.append([float(bbox[3]),float(bbox[0])]);
	poly_wkt.append([float(bbox[3]),float(bbox[1])]);
	poly_wkt.append([float(bbox[2]),float(bbox[1])]);
	poly_wkt.append([float(bbox[2]),float(bbox[0])]);
	geojsonFeature = {"type":"Polygon","coordinates":[poly_wkt],"crs":{"type":"name","properties":{"name":"EPSG:4326"}}};
	geojsonFeature=json.dumps(geojsonFeature);
	# print(geojsonFeature);
	return geojsonFeature;
def selectData(themes,location):
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
		# for concept in conceptnet_RelatedTo:
		# 	concept = re.sub('[^_a-zA-Z0-9]', '', concept);
		# 	cursor_RelatedTo.execute("SELECT mt.id,mt.id_increment,concat(mt.title,'-',ts_rank(mt.tokens,tsq),'-',mt.area), mt.description,(ts_rank(mt.tokens,tsq)*0.01) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
		# 	cursorRelatedTo_arr = cursor_RelatedTo.fetchall();
		# 	for rows in cursorRelatedTo_arr:
		# 		if(rows[0] not in indexes):
		# 			indexes.append(rows[0]);
		# 			conceptnetAll.append(rows);
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
		# for concept in conceptnet_IsA:
		# 	cursor_RelatedTo.execute("SELECT mt.id,mt.id_increment,mt.title, mt.description,(ts_rank(mt.tokens,tsq)*0.7) rank,mt.area from (SELECT  id,id_increment,title,description,tokens, (st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt,to_tsquery('"+concept +"') as tsq where tsq @@ mt.tokens order by rank desc,area desc;");
		# 	cursorRelatedTo_arr = cursor_RelatedTo.fetchall();
		# 	for rows in cursorRelatedTo_arr:
		# 		if(rows[0] not in indexes):
		# 			indexes.append(rows[0]);
		# 			conceptnetAll.append(rows);
	elif(len(location)):
		geocoding_result = getGeom(location[0]);
		cursor_IsA.execute("SELECT mt.id,mt.id_increment,mt.title,mt.description,(st_area(ST_Intersection(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography))::float / st_area(st_union(st_geomfromgeojson('"+geocoding_result+"'), mt.poly_geography::geometry))::float) area FROM metadata_table mt where st_intersects(st_geomfromgeojson('"+geocoding_result+"'), poly_geography)) mt order by area desc;");
		conceptnetAll=cursor_IsA.fetchall();
	# return cursor_IsA,cursor_Synonym,cursor_RelatedTo,cursor_MannerOf;
	# print(len(conceptnetAll));
	return conceptnetAll;
Articles = Articles();

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
		# print(offset);
		# print(conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf);
	return conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf;
def formulate_keywords(themes,locations):
	words_IsA = "";words_Synonym = "";words_RelatedTo = "";words_MannerOf = "";
	for theme in themes:
		conceptnet_IsA, conceptnet_Synonym, conceptnet_RelatedTo, conceptnet_MannerOf = conceptnetExpansion(theme[0]);
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
	# print(words_IsA,words_Synonym,words_RelatedTo,words_MannerOf);
	return words_IsA, words_Synonym, words_RelatedTo, words_MannerOf;
@app.route('/result_conceptnet',methods=['POST','GET'])

def result_conceptnet():
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
		my_metadata = [];
		# mymetadata_IsA,mymetadata_Synonym,mymetadata_RelatedTo,mymetadata_MannerOf = selectData(themes,location);
		my_metadata = selectData(themes,location);
		# my_metadata = mymetadata_IsA.fetchall();
		# for metadata in mymetadata_Synonym.fetchall():
		# 	my_metadata.append(metadata);
		# for metadata in mymetadata_RelatedTo.fetchall():
		# 	my_metadata.append(metadata);
		# for metadata in mymetadata_MannerOf.fetchall():
		# 	my_metadata.append(metadata);
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

@app.route('/postmethod', methods = ['POST'])
def postmethod():
    jsdata = request.form;
    # print(dict(jsdata));
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
    strategy=3;
    conn = connect();
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor);
    cursor.execute("Insert into ratings values("+str(user_id)+","+str(id_dataset)+",array"+str(searchKeywords)+","+str(strategy)+","+str(rating)+","+str(ranking_split[3])+") on conflict (id,id_dataset,search_keywords,strategy) do update set rating=Excluded.rating;");
    conn.commit();
    return 'base';
	
@app.route('/articles')

def articles():
	return render_template('articles.html',articles = Articles);


@app.route('/details/<string:id>')

def details(id, methods=['GET','POST']):
	selectedMetadata = selectDetails(id);
	selected_metadata= selectedMetadata.fetchall();
	selected_similar = selectSimilar(selected_metadata[0][0]);
	return render_template('details.html',selected_metadata=selected_metadata,selected_similar=selected_similar.fetchall());

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