from urllib.request import urlopen
from urllib.request import urlretrieve
from urllib.parse import urlparse
from urllib.parse import quote
from urllib.request import FancyURLopener
import urllib.parse
import urllib.error
from osgeo import gdal, ogr
from geomet import wkt
import json
import csv
import requests
import os
import pymongo
from pymongo.errors import BulkWriteError
from bs4 import BeautifulSoup
import psycopg2
import sys
import traceback
import re
from decimal import Decimal
filenames = [];
def databaseConnection():
    conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
    # print ("Connecting to database\n ->%s" % (conn_string))
    conn = psycopg2.connect(conn_string);
    return conn;
def generateBounding():
        cursor = selectDataset();
        country = "";
        country_ ="";
        country_1 = "";
        for row in cursor:#united-kingdom/39bc26ae67cf47f395cdec351c36b43a_0.geojson
            try:
                polygonpoints = "";
                bbox = "";
                poly_wkt = [];
                geojsonFeature="";
                polygonpoints_list=[];
                polyPoints = [];
                # print(row[3]);
                title = row[2];
                description = row[3];
                if not title:
                    title="";
                if not description:
                    description="";
                print(title + " " + description);
                response=requests.get("https://api.dbpedia-spotlight.org/en/annotate?text="+title+"&confidence=0.4&types=DBpedia%3APlace");
                source_code = response.content;
                soup = BeautifulSoup(source_code,"html.parser");
                print(title);
                print(soup);
                if soup.a and soup.a['title'] and 'http://dbpedia.org/resource/' in soup.a['title']:
                    # print('here');
                    geocoding_result = requests.get('https://nominatim.openstreetmap.org/search?q='+soup.a.string+'&format=json&polygon=1&addressdetails=1');
                    if 'polygonpoints' in geocoding_result.json()[0].keys():
                        polygonpoints = geocoding_result.json()[0]['polygonpoints'];
                        polyPoints[:] = [[float(e) for e in sl] for sl in polygonpoints]
                        print(polyPoints);
                        if(polyPoints[0]!=polyPoints[-1]):
                            polyPoints.append(polyPoints[0]);
                        geojsonFeature = {"type":"Polygon","coordinates":[polyPoints]};
                        # print(geojsonFeature);
                        geojsonFeature=json.dumps(geojsonFeature);    
                    else:
                        bbox = geocoding_result.json()[0]['boundingbox'];
                        poly_wkt.append([float(bbox[2]),float(bbox[0])]);
                        poly_wkt.append([float(bbox[3]),float(bbox[0])]);
                        poly_wkt.append([float(bbox[3]),float(bbox[1])]);
                        poly_wkt.append([float(bbox[2]),float(bbox[1])]);
                        poly_wkt.append([float(bbox[2]),float(bbox[0])]);
                        geojsonFeature = {"type":"Polygon","coordinates":[poly_wkt]};
                        print(geojsonFeature);
                        geojsonFeature=json.dumps(geojsonFeature);
                    updateDataset(row[1],"ST_GeomFromGeoJSON('" + str(geojsonFeature) + "')");
            except Exception:
                traceback.print_exc();
            # cursor.close();

def updateDataset(id_inc,bbox):
    conn = databaseConnection();
    cursor = conn.cursor();
    # print(bbox);
    query =  "update metadata_table set poly_geometry = "+bbox+ " where id_increment = " + str(id_inc)+";";
    # query =  "update metadata_table set extent = "+bbox+ ", epsg= "+epsg+" where id_increment = id_inc;";
    # print(str(epsg) +"-"+ str(bbox));
    cursor.execute(query);
    # print(cursor.rowcount);
    cursor.close();
    conn.commit();
    conn.close();
def selectDataset():
    try:
        conn = databaseConnection();
        cursor = conn.cursor();
        print("Connected!\n")
        #print(json_metadataList)
        query =  "select id,id_increment,title,description,local_geojson_url,local_geojson_url,geojson_url,csvurl from metadata_table where poly_geometry is null order by local_geojson_url asc;"
        cursor.execute(query);
        # for row in cursor:
        #     print(row);
        return cursor;
    except Exception:
        traceback.print_exc();
generateBounding();