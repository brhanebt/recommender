from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class BaseModel(db.Model):
    """Base data model for all objects"""
    __abstract__ = True

    def __init__(self, *args):
        super().__init__(*args)

    def __repr__(self):
        """Define a base way to print models"""
        return '%s(%s)' % (self.__class__.__name__, {
            column: value
            for column, value in self._to_dict().items()
        })

    def json(self):
        """
                Define a base way to jsonify models, dealing with datetime objects
        """
        return {
            column: value if not isinstance(value, datetime.date) else value.strftime('%Y-%m-%d')
            for column, value in self._to_dict().items()
        }


class Station(BaseModel, db.Model):
    """Model for the stations table"""
    __tablename__ = 'metadata_table'
    id = db.Column(db.Text, primary_key = True)
    title = db.Column(db.Text);
    description = db.Column(db.Text);
    metadata_created = db.Column(db.Text);
    id_increment = db.Column(db.Text)
    extent = db.Column(db.Text)
    geojson_url = db.Column(db.Text);
    local_geojson_url = db.Column(db.Text);
    csvurl = db.Column(db.Text);
    local_csv_url = db.Column(db.Text);
    tags = db.Column(db.Text);