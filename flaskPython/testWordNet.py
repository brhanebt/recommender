import sys
from nltk.corpus import wordnet as wn
synonyms = []
antonyms = []

for syn in wn.synsets(sys.argv[1]):
    for l in syn.lemmas():
        if l.name().lower() not in synonyms:
            synonyms.append(l.name().lower())
            if l.antonyms():
                antonyms.append(l.antonyms()[0].name())
print(set(synonyms))
print(set(antonyms))

SELECT row_number() over(),id, title, COUNT(*) FROM metadata_table GROUP BY id, title HAVING COUNT(*) > 1;

SELECT count(distinct id + "  " + title) FROM metadata_table GROUP BY id, title HAVING COUNT(*) > 1;

DELETE t1 FROM table t1
  JOIN table t2
  ON t2.refID = t1.refID
  AND t2.ID < t1.ID;

DELETE from tt t1
  JOIN tt t2
  ON (t2.id = t1.id and t2.title = t1.title)
  AND t2.id_increment < t1.id_increment;

DELETE
FROM
    metadata_table_backup_10_02_19 a
        USING metadata_table_backup_10_02_19 b
WHERE
    a.id_increment < b.id_increment
    AND (a.id = b.id and a.title = b.title and a.local_geojson_url = b.local_geojson_url and a.local_csv_url = b.local_csv_url  and a.local_csv_url = b.local_csv_url);


DELETE
FROM
    metadata_table a
        USING metadata_table b
WHERE
    a.id_increment < b.id_increment
    AND (a.id = b.id and a.title = b.title and a.local_geojson_url = b.local_geojson_url and a.local_csv_url = b.local_csv_url  and a.local_csv_url = b.local_csv_url);


DELETE
FROM
    metadata_table_backup_10_02 a
        USING metadata_table_backup_10_02 b;
WHERE
    a.id_increment < b.id_increment
    AND (concat(a.title,a.description) = concat(b.title,b.description));


  delete from metadata_table where 
id_increment not in (select min(id_increment) from metadata_table t group by id,title,metadata_created,geojson_url,csvurl having count(*) > 1)
and Id in (select Id from metadata_table t group by id,title,metadata_created,geojson_url,csvurl  having count(*) > 1)


SELECT t1 FROM table t1
  JOIN table t2
  ON t2.refID = t1.refID
  AND t2.ID < t1.ID;


insert into metadata_table select * from metadata_table_backup_10_02 where not exists (select * from metadata_table)
insert into metadata_table_2 select * from metadata_table_backup_10_02 where not exists (select * from metadata_table_2)