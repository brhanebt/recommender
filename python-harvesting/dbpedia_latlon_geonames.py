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
filenames = [];
def databaseConnection():
    conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
    # print ("Connecting to database\n ->%s" % (conn_string))
    conn = psycopg2.connect(conn_string);
    return conn;
def generateBounding():
        cursor = selectDataset();
        for row in cursor:#united-kingdom/39bc26ae67cf47f395cdec351c36b43a_0.geojson
            try:
                # print();
                response=requests.get("https://api.dbpedia-spotlight.org/en/annotate?text="+row[2].replace(" ", "%20")+"&confidence=0.4&types=DBpedia%3APlace");
                source_code = response.content;
                soup = BeautifulSoup(source_code,"html.parser");
                # print(soup);
                if soup.a and soup.a['title'] and 'http://dbpedia.org/resource/' in soup.a['title']:
                    geocoding_result = requests.get('http://api.geonames.org/searchJSON?q='+soup.a.string+'&maxRows=10&username=brhanebt01');
                    point_wkt = "SRID=4326;"+"Point("+geocoding_result.json()['geonames'][0]['lng']+" "+geocoding_result.json()['geonames'][0]['lat']+")";
                    updateDataset(row[1],"ST_GeomFromEWKT('"+point_wkt+"')");
            except Exception:
                filenames.append(row[3]);
                # print(filenames);
                print(len(filenames));
                traceback.print_exc();
        # cursor.close();
def updateDataset(id_inc,bbox):
    conn = databaseConnection();
    cursor = conn.cursor();
    # print(bbox);
    query =  "update metadata_table set geom = "+bbox+ " where id_increment = " + str(id_inc);
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
        query =  "select id,id_increment,description,local_geojson_url from metadata_table where geom is null order by local_geojson_url asc;"
        cursor.execute(query);
        # for row in cursor:
        #     print(row);
        return cursor;
    except Exception:
        traceback.print_exc();
generateBounding();