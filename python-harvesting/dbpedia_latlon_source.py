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
        country = "";
        country_ ="";
        for row in cursor:#united-kingdom/39bc26ae67cf47f395cdec351c36b43a_0.geojson
            try:
                country = "";
                country_ ="";
                if(row[3]):
                    country = row[3];
                    country=country.split('/');
                    country_ = country[1];
                elif(row[4]):
                    country = row[4];
                    country=country.split('/');
                    country_ = country[1];
                elif(row[5]):
                    country = row[5];
                    country=country.split('/');
                    country_ = country[1];
                else:
                    continue;
            except Exception:
                traceback.print_exc();
            finally:
                if(country_ == "us"):
                    country_ = "united states";
                elif (country_== "united-kingdom"):
                    country_ = "united kingdom";
                elif (country_ == "ie"):
                    country_ = "ireland";
                print(country_);
                geocoding_result = requests.get('http://api.geonames.org/searchJSON?q='+country_+'&maxRows=10&username=brhanebt01');
                point_wkt = "SRID=4326;"+"Point("+geocoding_result.json()['geonames'][0]['lng']+" "+geocoding_result.json()['geonames'][0]['lat']+")";
                # print(geocoding_result.json());
                print(point_wkt);
                updateDataset(row[1],"ST_GeomFromEWKT('"+point_wkt+"')");
        # cursor.close();
def updateDataset(id_inc,bbox):
    conn = databaseConnection();
    cursor = conn.cursor();
    # print(bbox);
    query =  "update metadata_table set geom = "+bbox+ " where id_increment = " + str(id_inc);
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
        query =  "select id,id_increment,description,local_geojson_url,local_geojson_url,geojson_url,csvurl from metadata_table where geom is null order by local_geojson_url asc;"
        cursor.execute(query);
        # for row in cursor:
        #     print(row);
        return cursor;
    except Exception:
        traceback.print_exc();
generateBounding();