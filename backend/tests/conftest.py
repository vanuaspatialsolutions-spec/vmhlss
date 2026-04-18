import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
import os

# Test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test.db"
)

@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def client(db):
    """Create test client with overridden database"""
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token(client, db):
    """Create admin user and return JWT token"""
    from app.models import User
    from app.utils.auth import get_password_hash

    admin_user = User(
        email="admin@vmhlss.gov.vu",
        full_name="Admin User",
        password_hash=get_password_hash("testpassword123"),
        role="ADMIN",
        is_active=True
    )
    db.add(admin_user)
    db.commit()

    response = client.post("/api/auth/login", json={
        "email": "admin@vmhlss.gov.vu",
        "password": "testpassword123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

@pytest.fixture
def analyst_token(client, db):
    """Create analyst user and return JWT token"""
    from app.models import User
    from app.utils.auth import get_password_hash

    analyst_user = User(
        email="analyst@vmhlss.gov.vu",
        full_name="Analyst User",
        password_hash=get_password_hash("testpassword123"),
        role="ANALYST",
        is_active=True
    )
    db.add(analyst_user)
    db.commit()

    response = client.post("/api/auth/login", json={
        "email": "analyst@vmhlss.gov.vu",
        "password": "testpassword123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

@pytest.fixture
def sample_shapefile(tmp_path):
    """Create a minimal valid shapefile for testing"""
    try:
        import fiona
        from fiona.crs import from_epsg
        from shapely.geometry import mapping, Point

        shp_path = tmp_path / "test.shp"
        schema = {
            'geometry': 'Point',
            'properties': {'id': 'int', 'name': 'str'}
        }
        with fiona.open(
            str(shp_path),
            'w',
            driver='ESRI Shapefile',
            schema=schema,
            crs=from_epsg(4326)
        ) as shp:
            shp.write({
                'geometry': mapping(Point(167.5, -17.7)),
                'properties': {'id': 1, 'name': 'Test'}
            })
        return shp_path
    except ImportError:
        pytest.skip("fiona/shapely not installed")

@pytest.fixture
def sample_aoi():
    """Sample AOI GeoJSON polygon within Vanuatu"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [167.1, -17.7],
            [167.3, -17.7],
            [167.3, -17.9],
            [167.1, -17.9],
            [167.1, -17.7]
        ]]
    }

@pytest.fixture
def sample_geojson_point():
    """Sample GeoJSON point within Vanuatu"""
    return {
        "type": "Point",
        "coordinates": [167.5, -17.7]
    }

@pytest.fixture
def sample_geojson_polygon():
    """Sample GeoJSON polygon within Vanuatu"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [167.2, -17.6],
            [167.4, -17.6],
            [167.4, -17.8],
            [167.2, -17.8],
            [167.2, -17.6]
        ]]
    }
