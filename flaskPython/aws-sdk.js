var bbox = require('@turf/turf');
console.log(bbox)
var aws = require('aws-sdk');
var s3 = new aws.S3({ accessKeyId: 'AKIAIF4N4QOJK4ISB5RA', secretAccessKey: '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'});
var geojson;
var getParams = {
    Bucket: 'ireland-geojsons', 
    Key: '03556536c68241cfbb522328994b1862_4.geojson'
}
s3.getObject(getParams, function (err, data) {

    if (err) {
        console.log(err);
    } else {
        geojson = data.Body.toString();
    }

})
var bbox = turf.bbox(geojson);
console.log(bbox);
