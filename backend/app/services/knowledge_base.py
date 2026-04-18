"""
Knowledge Base Service

Manages knowledge base record storage, confirmation workflow, spatial queries,
and full-text search over extracted geospatial information.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from geoalchemy2 import functions as geofunc
from geoalchemy2.elements import WKBElement

from app.models.knowledge_base import KnowledgeBaseRecord, InformationType
from app.schemas.knowledge_base import KnowledgeBaseRecordResponse

logger = logging.getLogger(__name__)


def store_extracted_items(
    items: Dict,
    document_name: str,
    document_path: str,
    extracted_by: str,
    db: Session
) -> List[str]:
    """
    Store extracted items as knowledge base records with status='pending'.
    Each item becomes a separate record.

    Returns list of created record IDs.
    """
    logger.info(f"Storing {len(items)} extracted items from {document_name}")

    record_ids = []

    # Process locations_events
    for item in items.get('locations_events', []):
        record = KnowledgeBaseRecord(
            information_type=InformationType.HAZARD_EVENT,
            extracted_text=item.get('description', ''),
            interpreted_value=str(item),
            place_name=item.get('place_name'),
            coordinates=item.get('coordinates'),
            confidence_score=float(item.get('confidence', 0.5)),
            location_source=item.get('location_source', 'unresolved'),
            source_document=document_name,
            source_document_path=document_path,
            extracted_by=extracted_by,
            status='pending'
        )
        db.add(record)
        db.flush()
        record_ids.append(str(record.id))

    # Process hazard_data
    for item in items.get('hazard_data', []):
        record = KnowledgeBaseRecord(
            information_type=InformationType.HAZARD_ZONE,
            extracted_text=item.get('description', ''),
            interpreted_value=str(item),
            place_name=item.get('location_description'),
            confidence_score=float(item.get('confidence', 0.5)),
            location_source='document',
            source_document=document_name,
            source_document_path=document_path,
            extracted_by=extracted_by,
            status='pending'
        )
        db.add(record)
        db.flush()
        record_ids.append(str(record.id))

    # Process soil_agricultural
    for item in items.get('soil_agricultural', []):
        record = KnowledgeBaseRecord(
            information_type=InformationType.SOIL_DATA,
            extracted_text=item.get('description', ''),
            interpreted_value=str(item),
            place_name=item.get('location_description'),
            confidence_score=float(item.get('confidence', 0.5)),
            location_source='document',
            source_document=document_name,
            source_document_path=document_path,
            extracted_by=extracted_by,
            status='pending'
        )
        db.add(record)
        db.flush()
        record_ids.append(str(record.id))

    # Process engineering_data
    for item in items.get('engineering_data', []):
        record = KnowledgeBaseRecord(
            information_type=InformationType.ENGINEERING_DATA,
            extracted_text=item.get('description', ''),
            interpreted_value=str(item),
            place_name=item.get('location_description'),
            confidence_score=float(item.get('confidence', 0.5)),
            location_source='document',
            source_document=document_name,
            source_document_path=document_path,
            extracted_by=extracted_by,
            status='pending'
        )
        db.add(record)
        db.flush()
        record_ids.append(str(record.id))

    # Process policy_legal
    for item in items.get('policy_legal', []):
        record = KnowledgeBaseRecord(
            information_type=InformationType.POLICY_LEGAL,
            extracted_text=item.get('description', ''),
            interpreted_value=str(item),
            place_name=item.get('location_description'),
            confidence_score=float(item.get('confidence', 0.5)),
            location_source='document',
            source_document=document_name,
            source_document_path=document_path,
            extracted_by=extracted_by,
            status='pending'
        )
        db.add(record)
        db.flush()
        record_ids.append(str(record.id))

    db.commit()
    logger.info(f"Stored {len(record_ids)} knowledge base records")

    return record_ids


def confirm_kb_record(record_id: str, user_id: str, db: Session) -> bool:
    """
    Confirm a knowledge base record and mark as verified.
    Updates status='confirmed', confirmed_by, confirmed_at.
    """
    logger.info(f"Confirming KB record: {record_id}")

    record = db.query(KnowledgeBaseRecord).filter(
        KnowledgeBaseRecord.id == record_id
    ).first()

    if not record:
        logger.warning(f"Record not found: {record_id}")
        return False

    record.status = 'confirmed'
    record.confirmed_by = user_id
    record.confirmed_at = datetime.utcnow()

    db.commit()
    logger.info(f"Record confirmed: {record_id}")

    return True


def reject_kb_record(record_id: str, db: Session) -> bool:
    """
    Reject a knowledge base record.
    Updates status='rejected'.
    """
    logger.info(f"Rejecting KB record: {record_id}")

    record = db.query(KnowledgeBaseRecord).filter(
        KnowledgeBaseRecord.id == record_id
    ).first()

    if not record:
        logger.warning(f"Record not found: {record_id}")
        return False

    record.status = 'rejected'
    db.commit()
    logger.info(f"Record rejected: {record_id}")

    return True


def query_kb_for_aoi(
    aoi_geom: WKBElement,
    information_types: List[str],
    db: Session
) -> List[Dict]:
    """
    Query knowledge base for records intersecting AOI geometry.

    Args:
        aoi_geom: AOI geometry as WKBElement (PostGIS)
        information_types: List of InformationType enum values to filter
        db: Database session

    Returns:
        List of KB records as dicts, filtered by:
        - status = 'confirmed'
        - ST_Intersects with aoi_geom
        - information_type IN information_types
        - Not expired (expiry_date > now())
    """
    logger.info(f"Querying KB for AOI with types: {information_types}")

    query = db.query(KnowledgeBaseRecord).filter(
        and_(
            KnowledgeBaseRecord.status == 'confirmed',
            KnowledgeBaseRecord.geom.isnot(None),
            geofunc.ST_Intersects(KnowledgeBaseRecord.geom, aoi_geom),
            KnowledgeBaseRecord.information_type.in_(information_types),
            or_(
                KnowledgeBaseRecord.expiry_date.is_(None),
                KnowledgeBaseRecord.expiry_date > datetime.utcnow()
            )
        )
    ).all()

    logger.info(f"Found {len(query)} KB records for AOI")

    results = []
    for record in query:
        results.append({
            'id': str(record.id),
            'information_type': record.information_type.value,
            'extracted_text': record.extracted_text,
            'interpreted_value': record.interpreted_value,
            'place_name': record.place_name,
            'coordinates': record.coordinates,
            'confidence_score': float(record.confidence_score),
            'location_source': record.location_source,
            'source_document': record.source_document,
            'extracted_by': record.extracted_by,
            'confirmed_by': record.confirmed_by,
            'confirmed_at': record.confirmed_at.isoformat() if record.confirmed_at else None,
            'created_at': record.created_at.isoformat()
        })

    return results


def get_kb_stats(db: Session) -> Dict:
    """
    Return statistics about the knowledge base.

    Returns dict with:
    - total_records
    - by_type (breakdown by information_type)
    - by_status (breakdown by status)
    - most_recent_document
    """
    logger.info("Calculating KB statistics")

    total = db.query(func.count(KnowledgeBaseRecord.id)).scalar()

    type_breakdown = db.query(
        KnowledgeBaseRecord.information_type,
        func.count(KnowledgeBaseRecord.id)
    ).group_by(KnowledgeBaseRecord.information_type).all()

    status_breakdown = db.query(
        KnowledgeBaseRecord.status,
        func.count(KnowledgeBaseRecord.id)
    ).group_by(KnowledgeBaseRecord.status).all()

    most_recent = db.query(KnowledgeBaseRecord).order_by(
        KnowledgeBaseRecord.created_at.desc()
    ).first()

    stats = {
        'total_records': total,
        'by_type': {
            item[0].value: item[1] for item in type_breakdown
        },
        'by_status': {
            item[0]: item[1] for item in status_breakdown
        },
        'most_recent_document': most_recent.source_document if most_recent else None
    }

    logger.info(f"KB stats: {total} total records")

    return stats


def search_kb(
    query: str,
    bbox: Optional[List[float]] = None,
    information_type: Optional[str] = None,
    confidence_min: float = 0.0,
    db: Session = None
) -> List[Dict]:
    """
    Full-text search over knowledge base.

    Filters by:
    - Query text match in extracted_text and interpreted_value (case-insensitive)
    - bbox: [min_lon, min_lat, max_lon, max_lat] using ST_Within
    - information_type: specific type filter
    - confidence_score >= confidence_min

    Args:
        query: Search text
        bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
        information_type: Filter by specific type (string)
        confidence_min: Minimum confidence score (0.0-1.0)
        db: Database session

    Returns:
        List of matching KB records as dicts
    """
    logger.info(f"Searching KB: query='{query}', bbox={bbox}, type={information_type}")

    filters = [
        KnowledgeBaseRecord.confidence_score >= confidence_min,
        or_(
            KnowledgeBaseRecord.extracted_text.ilike(f"%{query}%"),
            KnowledgeBaseRecord.interpreted_value.ilike(f"%{query}%")
        )
    ]

    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        bbox_geom = f"SRID=4326;POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
        filters.append(
            geofunc.ST_Within(KnowledgeBaseRecord.geom, bbox_geom)
        )

    if information_type:
        filters.append(
            KnowledgeBaseRecord.information_type == information_type
        )

    results_query = db.query(KnowledgeBaseRecord).filter(and_(*filters)).all()

    logger.info(f"Found {len(results_query)} matching KB records")

    results = []
    for record in results_query:
        results.append({
            'id': str(record.id),
            'information_type': record.information_type.value,
            'extracted_text': record.extracted_text,
            'interpreted_value': record.interpreted_value,
            'place_name': record.place_name,
            'coordinates': record.coordinates,
            'confidence_score': float(record.confidence_score),
            'location_source': record.location_source,
            'source_document': record.source_document,
            'extracted_by': record.extracted_by,
            'status': record.status,
            'created_at': record.created_at.isoformat()
        })

    return results


def get_pending_records(
    document_name: Optional[str] = None,
    db: Session = None
) -> List[Dict]:
    """
    Get all pending records awaiting confirmation.

    Optionally filter by source document.

    Returns list of pending records as dicts.
    """
    logger.info(f"Fetching pending records: document={document_name}")

    filters = [KnowledgeBaseRecord.status == 'pending']

    if document_name:
        filters.append(KnowledgeBaseRecord.source_document == document_name)

    records = db.query(KnowledgeBaseRecord).filter(and_(*filters)).all()

    logger.info(f"Found {len(records)} pending records")

    results = []
    for record in records:
        results.append({
            'id': str(record.id),
            'information_type': record.information_type.value,
            'extracted_text': record.extracted_text,
            'interpreted_value': record.interpreted_value,
            'place_name': record.place_name,
            'coordinates': record.coordinates,
            'confidence_score': float(record.confidence_score),
            'location_source': record.location_source,
            'source_document': record.source_document,
            'extracted_by': record.extracted_by,
            'created_at': record.created_at.isoformat()
        })

    return results


def bulk_confirm_records(
    record_ids: List[str],
    user_id: str,
    db: Session
) -> Dict:
    """
    Confirm multiple KB records in batch.

    Returns dict with:
    - confirmed_count: number successfully confirmed
    - failed_count: number that failed
    """
    logger.info(f"Bulk confirming {len(record_ids)} records")

    confirmed_count = 0
    failed_count = 0

    for record_id in record_ids:
        if confirm_kb_record(record_id, user_id, db):
            confirmed_count += 1
        else:
            failed_count += 1

    logger.info(f"Bulk confirm complete: {confirmed_count} confirmed, {failed_count} failed")

    return {
        'confirmed_count': confirmed_count,
        'failed_count': failed_count
    }


def bulk_reject_records(
    record_ids: List[str],
    db: Session
) -> Dict:
    """
    Reject multiple KB records in batch.

    Returns dict with rejection summary.
    """
    logger.info(f"Bulk rejecting {len(record_ids)} records")

    rejected_count = 0
    failed_count = 0

    for record_id in record_ids:
        if reject_kb_record(record_id, db):
            rejected_count += 1
        else:
            failed_count += 1

    logger.info(f"Bulk reject complete: {rejected_count} rejected, {failed_count} failed")

    return {
        'rejected_count': rejected_count,
        'failed_count': failed_count
    }
