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
                with open(r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/" + row[2], "r", encoding="utf8") as myfile:
                    dataset = json.loads(myfile.read());
                    epsg = 4326;
                    bbox = [-180, 180, -180, 180];
                    if('crs' in dataset):
                        print(dataset['crs']['properties']['name'])
                        epsg = int(re.findall('\d+', dataset['crs']['properties']['name'])[-1])
                        bbox = [-180, 123456789, -180, 123456789]
                    else:
                        epsg = 4326
                    if('bbox' in dataset):
                        bbox = dataset['bbox']
                    else:
                        polygons = [];
                        envelopes = [];
                        for f in dataset["features"]:
                            geom = ogr.CreateGeometryFromWkt(wkt.dumps(f["geometry"], decimals=4))
                            env = geom.GetEnvelope()
                            polygons.append([env[0], env[1], env[2], env[3]])
                            envelopes.append(env)
                        for polygon in polygons:
                            # print(polygon);
                            if polygon[0] > bbox[0]:
                                bbox[0] = polygon[0];
                            if polygon[1] < bbox[1]:
                                bbox[1] = polygon[1];
                            if polygon[2] > bbox[2]:
                                bbox[2] = polygon[2];
                            if polygon[3] < bbox[3]:
                                bbox[3] = polygon[3];
                    # listPoint = [[bbox[0], bbox[2]],[bbox[0], bbox[3]],[bbox[1],bbox[3]],[bbox[1],bbox[2]],[bbox[0], bbox[2]]];
                    poly_wkt = "SRID="+str(epsg)+";"+"Polygon(("+str(bbox[0])+" "+str(bbox[2])+","+str(bbox[0])+" "+str(bbox[3])+","+str(bbox[1])+" "+str(bbox[3])+","+str(bbox[1])+" "+str(bbox[2])+","+str(bbox[0])+" "+str(bbox[2])+"))";
                    # print(poly);
                    # print(epsg);
                    # print(row[2])
                    # polygon_geom = {'type': 'Polygon', 'coordinates': [listPoint]};
                    # break;
                    updateDataset(row[1],epsg, "ST_GeomFromEWKT('"+poly_wkt+"')");
                    poly_wkt = "";
                    epsg = 4326;
                    bbox = [-180, 180, -180, 180];
            except Exception:
                filenames.append(row[2]);
                # print(filenames);
                print(len(filenames));
                traceback.print_exc();
        # cursor.close();
def updateDataset(id_inc,epsg,bbox):
    conn = databaseConnection();
    cursor = conn.cursor();
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
        query =  "select id,id_increment,local_geojson_url from metadata_table where geom is null order by local_geojson_url asc;"
        cursor.execute(query);
        # for row in cursor:
        #     print(row);
        return cursor;
    except Exception:
        traceback.print_exc();

generateBounding();