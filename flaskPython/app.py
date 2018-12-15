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
 


app = Flask(__name__)
app.debug = True
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/ckan_metadata'
# db = SQLAlchemy(app)
def connect():
	conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
	conn = psycopg2.connect(conn_string)
	return conn;
def selectData(select_value):
	conn = connect();
	cursor = conn.cursor('cursor_unique_name', cursor_factory=psycopg2.extras.DictCursor)
	cursor.execute("SELECT * FROM metadata_table WHERE tokens @@ to_tsquery('"+select_value +"');");
	return cursor;

Articles = Articles()

POSTGRES = {
    'user': 'postgres',
    'pw': 'root',
    'db': 'ckan_metadata',
    'host': 'localhost',
    'port': '5432',
}




# class metadata_table(db.Model):
# 	id = db.Column(db.Text);
# 	id_increment = db.Column(db.Integer, primary_key=True)
# 	title = db.Column(db.Text);
# 	description = db.Column(db.Text);
# 	metadata_created = db.Column(db.Text);
# 	extent = db.Column(db.Text)
# 	geojson_url = db.Column(db.Text);
# 	local_geojson_url = db.Column(db.Text);
# 	csvurl = db.Column(db.Text);
# 	local_csv_url = db.Column(db.Text);
# 	tags = db.Column(db.Text);

# 	def cleanHtml(rawDescription):
# 		cleanr = re.compile('<.*?>');
# 		cleantext = re.sub(cleanr, '', rawDescription)
# 		return cleantext
# 	def __init__(self,id, title, description, metadata_created, id_increment, extent, geojson_url, local_geojson_url,csvurl,local_csv_url,tags):
# 		self.id = id;
# 		self.id_increment = id_increment;
# 		self.title = title;
# 		print(description)
# 		self.description = self.cleanHtml(description);
# 		print(self.description)
# 		self.metadata_created = metadata_created;
# 		self.extent = extent;
# 		self.geojson_url = geojson_url;
# 		self.local_geojson_url = local_geojson_url;
# 		self.csvurl = csvurl;
# 		self.local_csv_url = local_csv_url;
# 		self.tags = tags;
# 	def __repr__(self):
# 		return '<result %r>' % self.id;

@app.route('/')

def index():
	return render_template('front.html');

@app.route('/result',methods=['POST','GET'])

def result():
	if request.method == 'POST':
		form_data = ['Hello','hi'];
		# mymetadata = selectData();
		# for metadata in mymetadata.fetchall():
		# 	soup = BeautifulSoup(mymetadata, "html.parser");
		# 	mymetadata.append(soup.get_text());
		# mymetadata = metadata_table.query.filter(and_(metadata_table.id_increment>=5000, metadata_table.id_increment<=5005));
		mymetadata = selectData();
		soup = BeautifulSoup(mymetadata.fetchall());
		mymetadata = soup.get_text();
		return render_template('result.html',mymetadata=mymetadata,form_data=form_data);
	else:
		# print('hello');
		form_data = ['population','ireland'];
		geocoding_result = requests.get('http://api.geonames.org/searchJSON?q='+form_data[1]+'&maxRows=10&username=brhanebt01')
		conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+form_data[0].lower()+'');
		conceptnet_all = [];
		wordnet_all = [];
		conceptnet_all_selected = [];
		offset = 0;
		all_words = "";
		all__words = [];
		stop = set(stopwords.words('english'));
		# print(conceptnet_result1.text);
		while len(conceptnet_result1.text)>=480:
			# print('here')
			# print(conceptnet_result1.text);
			# print(len(conceptnet_result1.text));
			conceptnet_result1 = requests.get('http://api.conceptnet.io/c/en/'+form_data[0].lower()+'?offset='+str(offset)+'&limit='+str(20));
			# print(conceptnet_result1.text);
			# print(json.loads(conceptnet_result1.text)['edges']);
			for edge in json.loads(conceptnet_result1.text)['edges']:
				# print(edge);
				if 'weight' in edge and edge['weight']>1:
					if edge['start']['language']=='en' and edge['start']['label'] not in conceptnet_all_selected:
						conceptnet_all_selected.append(edge['start']['label']);
						filtered_words = [word for word in word_tokenize(conceptnet_all_selected[len(conceptnet_all_selected)-1].lower()) if word not in stop];
					elif edge['end']['language']=='en' and edge['end']['label'] not in conceptnet_all_selected:
						# print(conceptnet_all_selected[len(conceptnet_all_selected)-1]);
						conceptnet_all_selected.append(edge['end']['label']);
						filtered_words = [word for word in word_tokenize(conceptnet_all_selected[len(conceptnet_all_selected)-1].lower()) if word not in stop];
						# print(conceptnet_all_selected[len(conceptnet_all_selected)-1]);
					# print(filtered_words);
					for word in filtered_words:
						if word not in all__words:
							all_words = all_words + "|" + word;
							all__words.append(word);
			offset = offset + 20;
			#print(conceptnet_all);
		# print(conceptnet_all_selected);
		# print(all_words);
		for syn in wn.synsets(form_data[0]):
			for l in syn.lemmas():
				if l.name() not in wordnet_all:
					wordnet_all.append(l.name());
				if l.name() not in conceptnet_all_selected:
					all_words = all_words + "|" + l.name();
		if all_words[0]=="|":
			all_words = all_words[1:];
		if all_words[len(all_words)-1]=="|":
			all_words = all_words[:-1];
		mymetadata = selectData(all_words);
		my_metadata = [];
		i=0;
		for metadata in mymetadata.fetchall():
			my_metadata.append(metadata);
			if metadata[2]:
				soup = BeautifulSoup(metadata[2]);
				# print(my_metadata[0][2]);
				my_metadata[i][2] = soup.get_text();
			i = i+1;
		return render_template('result.html',mymetadata=my_metadata,wordnet_all=wordnet_all,conceptnet_result=conceptnet_all_selected,all_words = all_words, geocoding_result=json.loads(geocoding_result.text)['geonames'][0]);


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
	app.run(debug=True)
	#Define our connection string postgresql://postgres:root@localhost/ckan_metadata'

# @app.route('/result', methods=['GET','POST'])

# def result():
	

def details():
	return render_template('details.html');


#################
