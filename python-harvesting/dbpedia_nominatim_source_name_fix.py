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
                country = "";
                country_ ="";
                # print(row[3]);
                print(row[4]);
                # print(row[5]);
                if(row[4]):
                    country = row[4];
                    country=country.split('/');
                    print(country);
                    country_ = country[1];
                elif(row[3]):
                    country = row[3];
                    country=country.split('/');
                    print(country);
                    country_ = country[1];
                else:
                    continue;
            except Exception:
                traceback.print_exc();
            if(country_ == "us"):
                country_ = "united states";
            elif (country_== "united-kingdom"):
                country_ = "united kingdom";
            elif (country_ == "ie" or country_ == "ireland"):
                country_ = "republic+of+ireland";
            country_=country_.replace (" ", "+");
            # print(country_1);
            geocoding_result = requests.get('https://nominatim.openstreetmap.org/search?q='+country_+'&format=json&polygon=1&addressdetails=1');
            polygonpoints = "";
            bbox = "";
            poly_wkt = [];
            geojsonFeature="";
            polygonpoints_list=[];
            polyPoints = [];
            # print(geocoding_result.json());
            try:
                # if 'polygonpoints' in geocoding_result.json()[0].keys():
                #     polygonpoints = geocoding_result.json()[0]['polygonpoints'];
                #     polyPoints[:] = [[float(e) for e in sl] for sl in polygonpoints]
                #     # print(polyPoints);
                #     if(polyPoints[0]!=polyPoints[-1]):
                #         polyPoints.append(polyPoints[0]);
                #         # print(polyPoints[0]);
                #         # print(polyPoints[-1]);
                #     geojsonFeature = {"type":"Polygon","coordinates":[polyPoints]};
                #     # print(geojsonFeature);
                #     geojsonFeature=json.dumps(geojsonFeature);    
                # else:
                bbox = geocoding_result.json()[0]['boundingbox'];
                poly_wkt.append([float(bbox[2]),float(bbox[0])]);
                poly_wkt.append([float(bbox[3]),float(bbox[0])]);
                poly_wkt.append([float(bbox[3]),float(bbox[1])]);
                poly_wkt.append([float(bbox[2]),float(bbox[1])]);
                poly_wkt.append([float(bbox[2]),float(bbox[0])]);
                # print(poly_wkt);
                print(row[1]);
                # ; = "[[["+str(bbox[2])+","+str(bbox[0])+"],["+str(bbox[3])+","+str(bbox[0])+"],["+str(bbox[3])+","+str(bbox[1])+"],["+str(bbox[2])+","+str(bbox[1])+"],["+str(bbox[2])+","+str(bbox[0])+"]]]";
                geojsonFeature = {"type":"Polygon","coordinates":[poly_wkt]};
                # print(geojsonFeature);
                geojsonFeature=json.dumps(geojsonFeature);
            except Exception:
                traceback.print_exc();
            # print(geojsonFeature);
            updateDataset(row[1],"ST_GeomFromGeoJSON('" + str(geojsonFeature) + "')");
            # cursor.close();

def updateDataset(id_inc,bbox):
    conn = databaseConnection();
    cursor = conn.cursor();
    # print(bbox);
    query =  "update metadata_table set poly_geometry = "+bbox+ " where id_increment = " + str(id_inc);
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
        # print("Connected!\n")
        #print(json_metadataList)
        # query =  "select id,id_increment,description,local_geojson_url,local_geojson_url,geojson_url,csvurl from metadata_table where poly_geometry is null order by local_geojson_url desc;"
        query =  "SELECT id,id_increment,description,local_geojson_url,local_csv_url,local_geojson_url,geojson_url,csvurl from metadata_table where ST_NPoints(poly_geometry)>5 or poly_geometry is null;"
        cursor.execute(query);
        # for row in cursor:
        #     print(row);
        return cursor;
    except Exception:
        traceback.print_exc();
generateBounding();