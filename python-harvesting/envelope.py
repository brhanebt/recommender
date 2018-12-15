import sys
from osgeo import gdal, ogr
with open (r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/united-kingdom/5fb8813978cc4e4892da4b57bcf4491f_0.geojson", "r") as myfile:
	data = myfile.read()
    dataset = json.loads(data)
    c1, c2;
    for f in dataset["features"]:
        for coordinate in f["geometry"]["coordinates"]: 
            c1 = [x[0] for x in coordinate] # first coordinate
            c2 = [x[1] for x in coordinate]
        bbox = [[min(c1),min(c2)],[min(c1),max(c2)],[max(c1),max(c2)],[max(c1),min(c2)],[min(c1),min(c2)]]
        print(bbox);


        import sys
from osgeo import gdal, ogr
from geomet import wkt
import json
with open(r"F:/Master Course Materials/Second Semester/Recommender-Implementation/harvested-datasets/united-kingdom/5fb8813978cc4e4892da4b57bcf4491f_0.geojson", "r") as myfile:
    data = myfile.read()
    dataset = json.loads(data)
    envelopes=[]
    for f in dataset["features"]:
    	geom = ogr.CreateGeometryFromWkt(wkt.dumps(f["geometry"], decimals=4)))
    	env = geom.GetEnvelope()
    	envelopes.append(env)
    print(envelopes)

    # Get Envelope returns a tuple (minX, maxX, minY, maxY)
    env = geom.GetEnvelope()
    print(env[0],env[2],env[1],env[3])