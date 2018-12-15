from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postges:root@localhost/ckan_metadata'
db = SQLAlchemy(app)

class Ckan_metadata(db.Model):
	id = db.Column(db.Text)
    title = db.Column(db.Text);
    description = db.Column(db.Text);
    metadata_created = db.Column(db.Text);
    id_increment = db.Column(db.Integer, primary_key=True)
    extent = db.Column(db.Text)
    geojson_url = db.Column(db.Text);
    local_geojson_url = db.Column(db.Text);
    csvurl = db.Column(db.Text);
    local_csv_url = db.Column(db.Text);
    tags = db.Column(db.Text);

    def __init__(self,id, title, description, metadata_created, id_increment, extent, geojson_url, local_geojson_url,csvurl,local_csv_url,tags):
    	self.id = id;
    	self.id_increment = id_increment;
    	self.title = title;
    	self.description = description;
    	self.metadata_created = metadata_created;
    	self.extent = extent;
    	self.geojson_url = geojson_url;
    	self.local_geojson_url = local_geojson_url;
    	self.csvurl = csvurl;
    	self.local_csv_url = local_csv_url;
    	self.tags = tags;
