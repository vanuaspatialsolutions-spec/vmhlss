from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from app.database import Base


class VanuatuPlace(Base):
    """
    Vanuatu Geographic Places Reference Model.

    Maintains a gazetteer of official place names, administrative boundaries,
    and geographic features within Vanuatu for context in spatial analysis
    and reporting.

    Attributes:
        id: Primary key (auto-incrementing integer)
        name: Official English place name
        name_bi: Official Bislama place name (national language)
        place_type: Category of place (island, village, town, province, river, mountain, reef, settlement, custom_area)
        island: Name of island where place is located (for non-island features)
        province: Name of province where place is located
        geom: Point geometry (WGS84 EPSG:4326) representing the location
    """

    __tablename__ = "vanuatu_places"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique identifier for this place"
    )

    name = Column(
        String(255),
        nullable=False,
        doc="Official English place name (required)"
    )

    name_bi = Column(
        String(255),
        nullable=True,
        doc="Official Bislama (national language) place name"
    )

    place_type = Column(
        String(50),
        nullable=True,
        doc="Category: island, village, town, province, river, mountain, reef, settlement, custom_area, airport, port"
    )

    island = Column(
        String(100),
        nullable=True,
        doc="Name of island (for non-island features, indicates which island the place is on)"
    )

    province = Column(
        String(100),
        nullable=True,
        doc="Name of province (e.g., Torba, Malampa, Penama, Shefa, Tafea)"
    )

    geom = Column(
        Geometry('POINT', srid=4326),
        nullable=True,
        doc="Point geometry representing the location (WGS84 EPSG:4326)"
    )

    def __repr__(self):
        return (
            f"VanuatuPlace("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"type='{self.place_type}', "
            f"island='{self.island}', "
            f"province='{self.province}'"
            f")"
        )

    def to_dict(self):
        """Convert place record to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'name_bi': self.name_bi,
            'place_type': self.place_type,
            'island': self.island,
            'province': self.province,
            'geometry': {
                'type': 'Point',
                'coordinates': [self.geom.x, self.geom.y] if self.geom else None
            }
        }
