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


def generateBounding(geojsonFile):
    try:
        with open(geojsonFile, "r", encoding="utf8") as myfile:
            dataset = json.loads(myfile.read())
            epsg = 4326
            bbox = [-180, 180, -180, 180]
            # print('here')
            if('crs' in dataset):
                print(dataset['crs']['properties']['name'])
                epsg = int(re.findall('\d+', dataset['crs']['properties']['name'])[-1])
            else:
                epsg = 4326
            if('bbox' in dataset):
                bbox = dataset['bbox']
            else:
                polygons = []
                envelopes = []
                for f in dataset["features"]:
                    geom = ogr.CreateGeometryFromWkt(
                        wkt.dumps(f["geometry"], decimals=4))
                    env = geom.GetEnvelope()
                    polygons.append([env[0], env[1], env[2], env[3]])
                    envelopes.append(env)
                    # print(envelopes)
                    # print(polygons)
                    bbox = [180, -180, 180, -180]
                for polygon in polygons:
                    if polygon[0] < bbox[0]:
                        bbox[0] = polygon[0]
                    if polygon[1] > bbox[1]:
                        bbox[1] = polygon[1]
                    if polygon[2] < bbox[2]:
                        bbox[2] = polygon[2]
                    if polygon[3] > bbox[3]:
                        bbox[3] = polygon[3]
    except Exception:
        traceback.print_exc()
    return [epsg, bbox]


def insertDataset(json_metadataList):
    conn_string = "host='localhost' dbname='ckan_metadata' user='postgres' password='root'"
    # print ("Connecting to database\n ->%s" % (conn_string))
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    print("Connected!\n")
    print(json_metadataList)
    # for metadata in json_metadataList:
    # print(metadata)
    # city = item[0]
    # price = item[1]
    # info = item[2]
    # query =  "INSERT INTO items (info, city, price) VALUES (%s, %s, %s);"
    # data = (info, city, price)
    # cursor.execute(query, data)
    # conn.commit();


def processDataset(dataset, belongsto, exceptionCount):
    _resultLength = len(dataset['result']['results'])
    _metadatas_array = []
    _metadataNew = {}
    i = 0
    # print(dataset)
    while i < 2:
        # print(i)
        j = 0
        while j < len(dataset['result']['results'][i]["resources"]):
            # print(dataset['result']['results'][i]["resources"])
            # print('id' in _metadataNew and dataset['result']['results'][i]['id']==_metadataNew['id'])
            if(('id' in _metadataNew and dataset['result']['results'][i]['id'] == _metadataNew['id']) == False):
                _metadataNew['id'] = dataset['result']['results'][i]['id']
                _metadataNew['metadata_modified'] = dataset['result']['results'][i]['metadata_modified']
                _metadataNew['metadata_created'] = dataset['result']['results'][i]['metadata_created']
            _format = dataset['result']['results'][i]["resources"][j]['format']
            _access_url = dataset['result']['results'][i]["resources"][j]['access_url'][0] if (
                '_access_url' in dataset['result']['results'][i]["resources"][j]) else dataset['result']['results'][i]["resources"][j]['url']
            # print(_access_url)
            _openDataFound = 0
            # print(_format)
            if _format.lower() == 'geojson' or _format.lower() == 'json':
                # print(_access_url);
                _openDataFound = 1
                # print(dataset['result']['results'][i]["title"])
                title_string = dataset['result']['results'][i]["title"]
                title_string = title_string.encode(
                    'ascii', 'ignore').decode("utf-8")
                # print(title_string.replace('\u', ' '))
                _metadataNew['title'] = title_string
                # print(dataset['result']['results'][i]["notes"])
                notes_string = dataset['result']['results'][i]["notes"]
                notes_string = notes_string.encode(
                    'ascii', 'ignore').decode("utf-8")
                # print(notes_string.replace('\u',' '))
                # print(notes_string)
                _metadataNew['notes'] = notes_string
                geojson_fileName = os.path.basename(urlparse(_access_url).path)
                if " " in _access_url:
                    _access_url = _access_url.replace(" ", "")
                try:
                    # print(_access_url)
                    epsg_bbox = generateBounding(r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/" + belongsto + "/" + os.path.basename(geojson_fileName))
                    _metadataNew['epsg'] = epsg_bbox[0];
                    _metadataNew['bbox'] = epsg_bbox[1];
                    urlretrieve(_access_url, r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/" +
                                belongsto + "/" + os.path.basename(geojson_fileName))
                    _metadataNew['geojson-url'] = _access_url
                except:
                    try:
                        page = urllib.request.urlopen(_access_url)
                        filename = r'F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/' + \
                            belongsto + '/' + \
                                dataset['result']['results'][i]["resources"][j]['name']
                        f = open('%s.geojson' % filename, "wb")
                        geojson_fileName = filename + '.geojson'
                        content = page.read()
                        f.write(content)
                        f.close()
                    except:
                         print("Exception: "+_access_url);
                         exceptionCount = exceptionCount + 1;
                         print(exceptionCount)
                    # fileName = os.path.basename(urlparse(_access_url).path)
                    # #_openData = urllib.request.urlopen(_access_url)
                    # #_realData = json.loads(_openData.read())
                    # #print(_realData)
                finally:
                    _metadataNew['local-geojson-url']=r'/' + \
                        belongsto + '/' + geojson_fileName
            elif _format.lower() == 'csv':
                # print(dataset['result']['results'][i]["title"])
                title_string=dataset['result']['results'][i]["title"]
                title_string=title_string.encode(
                    'ascii', 'ignore').decode("utf-8")
                # print(title_string.replace('\u', ' '))
                _metadataNew['title']=title_string
                # print(dataset['result']['results'][i]["notes"])
                notes_string=dataset['result']['results'][i]["notes"]
                notes_string=notes_string.encode(
                    'ascii', 'ignore').decode("utf-8")
                # print(notes_string.replace('\u',' '))
                # print(notes_string)
                _metadataNew['notes']=notes_string
                _openDataFound=1
                fileName=os.path.basename(urlparse(_access_url).path)
                if " " in _access_url:
                    _access_url=_access_url.replace(" ", "")
                _metadataNew['local-csv-url']=r'/' + \
                    belongsto + '/' + fileName
                _metadataNew['csv-url']=_access_url
                try:
                   urlretrieve(_access_url, r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/"+belongsto+"/"+os.path.basename(fileName))
                except:
                    try:
                        page = urllib.request.urlopen(_access_url)
                        filename = r'F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/'+belongsto+'/'+dataset['result']['results'][i]["resources"][j]['name'];
                        f = open('%s.csv' % filename, "wb")
                        content = page.read()
                        filename = r'F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/'+belongsto+'/'+dataset['result']['results'][i]["resources"][j]['name'];
                        f.write(content)
                        f.close()
                    except:
                        print("Exception " + _access_url);
                        exceptionCount =exceptionCount + 1;
                        print(exceptionCount)
                #
                # #_openData = urllib.request.urlopen(_access_url)
                # _openData = requests.get(_access_url, stream=1)
                # k=0;
                # for line in _openData:
                #     print(list(csv.reader((line.decode("utf-8")).splitlines()))[0]);
                #     k +=1;
                #     if(k>5):
                #         break;
            # elif _format.lower() == 'wfs':
            #     # print(dataset['result']['results'][i]["title"])
            #     title_string = dataset['result']['results'][i]["title"]
            #     title_string = title_string.encode('ascii', 'ignore').decode("utf-8")
            #     # print(title_string.replace('', ' '))
            #     _metadataNew['title'] = title_string
            #     # print(dataset['result']['results'][i]["notes"])
            #     notes_string = dataset['result']['results'][i]["notes"]
            #     notes_string = notes_string.encode('ascii', 'ignore').decode("utf-8")
            #     # print(notes_string.replace('',' '))
            #     # print(notes_string)
            #     _metadataNew['notes'] = notes_string
            #     _metadataNew['wfs-url'] = _access_url
            #     _openDataFound = 1
            #
            #     _openData = urllib.request.urlopen(_access_url)
            #     _realData = _openData.read()
            #     print(_realData)
            j += 1
        # print(_metadataNew)
        # insertDataset(_metadataNew)
        # json_metadata = json.dumps(_metadataNew)
        _metadatas_array.append(_metadataNew)
        # print(_metadataNew)
        i += 1
    insertDataset(_metadatas_array)
    # print(_metadatas_array)


def apiCall(dataportal, category, belongsto, datatype, exceptionCount):
    rows=10
    i=0
    _count=1
    _resultLength=10
    while i < 1 and _resultLength > 0:
        _resultLength=0
        url=dataportal + "/api/3/action/package_search?fq=" + str(datatype) + "&rows=" + \
            str(rows) + "&start=" + str(rows + i)
        response=requests.get(url)
        # print(response.json())
        # html = urllib.request.urlopen(url)
        jsonData=response.json()
        # print(jsonData)
        if (_count == 1):
            _count=jsonData['result']['count']
        processDataset(jsonData, belongsto, exceptionCount)
        _resultLength=len(jsonData['result']['results'])
        i += _resultLength
        # print(i)
        # print(_resultLength)

def Harvest():
    dataportals=[{'country': 'united-kingdom', 'dataportal': "https://data.gov.uk"}, {'country': 'ireland','dataportal': "https://data.gov.ie"}, {'country': 'us', 'dataportal': 'https://catalog.data.gov'}]
    category=""
    datatype="geojson"
    exceptionCount=0
    for dataportal_ckan in dataportals:
    apiCall(dataportal_ckan['dataportal'], category, dataportal_ckan['country'], datatype, exceptionCount)
