from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    organization: Optional[str] = Field(None, description="User organization")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "organization": "NGO"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    role: str = Field(..., description="User role (admin, data_manager, analyst, reviewer, public)")
    organization: Optional[str] = Field(None, description="User organization")
    is_active: bool = Field(default=True, description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "uuid-here",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "analyst",
                "organization": "NGO",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00",
                "last_login": "2024-01-20T14:30:00"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
            }
        }


# ============================================================================
# Dataset Schemas
# ============================================================================

class DatasetSlotResponse(BaseModel):
    """Schema for available dataset upload slots"""
    slot_id: str = Field(..., description="Slot identifier")
    dataset_type: str = Field(..., description="Type of dataset (hazard, landuse, census, etc.)")
    name: str = Field(..., description="Slot name")
    description: str = Field(..., description="Slot description")
    required: bool = Field(default=False, description="Whether this slot is required")
    status: str = Field(..., description="Current status (empty, uploaded, processing, ready)")
    file_format: str = Field(..., description="Expected file format (GeoTIFF, Shapefile, etc.)")
    geometry_type: Optional[str] = Field(None, description="For vector: Point, LineString, Polygon, etc.")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class DatasetUploadResponse(BaseModel):
    """Schema for dataset upload response"""
    upload_id: str = Field(..., description="Unique upload identifier")
    dataset_type: str = Field(..., description="Type of dataset")
    file_name: str = Field(..., description="Uploaded file name")
    file_size_mb: float = Field(..., description="File size in MB")
    status: str = Field(..., description="Upload status (uploaded, validating, validated, failed)")
    crs: Optional[str] = Field(None, description="Detected CRS")
    geometry_count: Optional[int] = Field(None, description="Number of geometries")
    bounds: Optional[Dict[str, float]] = Field(None, description="Geographic bounds")
    qa_stage: Optional[str] = Field(None, description="QA pipeline stage")
    created_at: datetime = Field(..., description="Upload timestamp")
    errors: Optional[List[str]] = Field(None, description="Validation errors if any")

    class Config:
        from_attributes = True


class QAStageResult(BaseModel):
    """Schema for QA pipeline stage result"""
    stage_name: str = Field(..., description="QA stage name")
    status: str = Field(..., description="Stage status (passed, failed, warning)")
    message: str = Field(..., description="Stage result message")
    issues_found: int = Field(default=0, description="Number of issues found")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class QAReport(BaseModel):
    """Schema for complete QA report"""
    upload_id: str = Field(..., description="Upload identifier")
    overall_status: str = Field(..., description="Overall QA status")
    total_issues: int = Field(..., description="Total issues found")
    critical_issues: int = Field(..., description="Critical issues")
    warnings: int = Field(..., description="Warnings")
    stages: List[QAStageResult] = Field(..., description="QA stage results")
    report_path: str = Field(..., description="Path to QA report PDF")
    generated_at: datetime = Field(..., description="Report generation timestamp")

    class Config:
        from_attributes = True


class FixRecord(BaseModel):
    """Schema for data fix record"""
    fix_id: str = Field(..., description="Fix identifier")
    upload_id: str = Field(..., description="Upload identifier")
    issue_type: str = Field(..., description="Type of issue fixed")
    description: str = Field(..., description="Fix description")
    rows_affected: int = Field(..., description="Number of rows affected")
    applied_at: datetime = Field(..., description="Timestamp when fix was applied")

    class Config:
        from_attributes = True


# ============================================================================
# Analysis Schemas
# ============================================================================

class AnalysisCreate(BaseModel):
    """Schema for creating analysis"""
    name: str = Field(..., description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    area_of_interest: Dict[str, Any] = Field(..., description="GeoJSON geometry for AOI")
    hazard_types: List[str] = Field(..., description="Selected hazard types")
    land_use_type: str = Field(..., description="Land use type to assess")
    include_social_factors: bool = Field(default=False, description="Include social vulnerability")
    include_economic_factors: bool = Field(default=False, description="Include economic factors")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Custom analysis parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Flood Risk Analysis - Efate",
                "description": "Assessment of flood risk for agricultural areas",
                "area_of_interest": {"type": "Polygon", "coordinates": [[...]]},
                "hazard_types": ["flood", "cyclone"],
                "land_use_type": "agriculture",
                "include_social_factors": True
            }
        }


class AnalysisResponse(BaseModel):
    """Schema for analysis response"""
    analysis_id: str = Field(..., description="Analysis identifier")
    name: str = Field(..., description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    status: str = Field(..., description="Analysis status")
    user_id: str = Field(..., description="User who created analysis")
    area_of_interest: Dict[str, Any] = Field(..., description="GeoJSON AOI")
    hazard_types: List[str] = Field(..., description="Hazard types included")
    land_use_type: str = Field(..., description="Land use type")
    area_sq_km: Optional[float] = Field(None, description="Area of AOI in km²")
    suitability_score: Optional[float] = Field(None, description="Overall suitability score (0-100)")
    primary_risk: Optional[str] = Field(None, description="Primary risk identified")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        from_attributes = True


class AnalysisStatus(BaseModel):
    """Schema for analysis status update"""
    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Current status")
    progress_percent: int = Field(..., description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

    class Config:
        from_attributes = True


# ============================================================================
# Document Upload Schemas
# ============================================================================

class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    document_id: str = Field(..., description="Document identifier")
    file_name: str = Field(..., description="Original file name")
    file_size_mb: float = Field(..., description="File size in MB")
    document_type: str = Field(..., description="Type of document (survey, report, map, etc.)")
    extraction_status: str = Field(..., description="Status of information extraction")
    pages_processed: Optional[int] = Field(None, description="Number of pages processed")
    text_extracted_chars: Optional[int] = Field(None, description="Characters of text extracted")
    confidence_score: Optional[float] = Field(None, description="Average confidence score")
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        from_attributes = True


class ExtractionItem(BaseModel):
    """Schema for extracted information item"""
    item_id: str = Field(..., description="Item identifier")
    item_type: str = Field(..., description="Type of item (coordinate, boundary, classification, etc.)")
    value: str = Field(..., description="Extracted value")
    context: str = Field(..., description="Context around the extracted value")
    confidence: float = Field(..., description="Extraction confidence (0-1)")
    page_number: Optional[int] = Field(None, description="Page number where found")
    needs_verification: bool = Field(default=False, description="Whether item needs manual verification")

    class Config:
        from_attributes = True


class ExtractionResponse(BaseModel):
    """Schema for complete extraction response"""
    document_id: str = Field(..., description="Document identifier")
    extracted_items: List[ExtractionItem] = Field(..., description="List of extracted items")
    summary: str = Field(..., description="Summary of extracted information")
    next_steps: List[str] = Field(..., description="Recommended next steps")

    class Config:
        from_attributes = True


# ============================================================================
# Knowledge Base Schemas
# ============================================================================

class KnowledgeBaseRecord(BaseModel):
    """Schema for knowledge base record"""
    record_id: str = Field(..., description="Record identifier")
    title: str = Field(..., description="Record title")
    description: str = Field(..., description="Record description")
    category: str = Field(..., description="Knowledge category")
    keywords: List[str] = Field(..., description="Search keywords")
    source: str = Field(..., description="Record source")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry if applicable")
    properties: Dict[str, Any] = Field(..., description="Additional properties")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class KnowledgeBaseQuery(BaseModel):
    """Schema for knowledge base query"""
    query_text: str = Field(..., description="Query text")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    limit: int = Field(default=10, description="Maximum results to return")
    geometry: Optional[Dict[str, Any]] = Field(None, description="Spatial filter")

    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "flood risk assessment",
                "categories": ["hazard", "assessment"],
                "limit": 10
            }
        }


# ============================================================================
# Georeferencing Schemas
# ============================================================================

class GeorefUploadResponse(BaseModel):
    """Schema for georeferencing upload response"""
    upload_id: str = Field(..., description="Upload identifier")
    file_name: str = Field(..., description="File name")
    status: str = Field(..., description="Georeferencing status")
    gcp_count: int = Field(..., description="Number of GCPs collected")
    rmse_pixels: Optional[float] = Field(None, description="RMSE in pixels")
    rmse_meters: Optional[float] = Field(None, description="RMSE in meters")
    gcp_candidates: List['GCPCandidate'] = Field(default_list=[], description="Suggested GCP candidates")

    class Config:
        from_attributes = True


class GCPCandidate(BaseModel):
    """Schema for GCP candidate suggestion"""
    candidate_id: str = Field(..., description="Candidate identifier")
    image_x: int = Field(..., description="Image X coordinate (pixels)")
    image_y: int = Field(..., description="Image Y coordinate (pixels)")
    lon: float = Field(..., description="Longitude")
    lat: float = Field(..., description="Latitude")
    accuracy_meters: float = Field(..., description="Expected accuracy in meters")
    reference_source: str = Field(..., description="Source of reference coordinates")

    class Config:
        from_attributes = True


class GCPUpdate(BaseModel):
    """Schema for GCP update"""
    gcp_id: str = Field(..., description="GCP identifier")
    image_x: int = Field(..., description="Image X coordinate")
    image_y: int = Field(..., description="Image Y coordinate")
    lon: float = Field(..., description="Longitude")
    lat: float = Field(..., description="Latitude")
    is_manual: bool = Field(default=True, description="Whether this is manually entered")

    class Config:
        json_schema_extra = {
            "example": {
                "gcp_id": "gcp-001",
                "image_x": 100,
                "image_y": 150,
                "lon": 167.5,
                "lat": -17.5,
                "is_manual": True
            }
        }


class DigitiisedFeature(BaseModel):
    """Schema for digitized feature from document"""
    feature_id: str = Field(..., description="Feature identifier")
    feature_type: str = Field(..., description="Feature type (point, line, polygon)")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry")
    properties: Dict[str, Any] = Field(..., description="Feature properties")
    source_page: int = Field(..., description="Source document page")
    confidence: float = Field(..., description="Digitization confidence (0-1)")
    needs_verification: bool = Field(default=False, description="Needs verification")

    class Config:
        from_attributes = True


# ============================================================================
# Report Schemas
# ============================================================================

class ReportGenerate(BaseModel):
    """Schema for report generation request"""
    analysis_id: str = Field(..., description="Analysis identifier")
    report_type: str = Field(..., description="Type of report (summary, detailed, technical)")
    include_maps: bool = Field(default=True, description="Include maps in report")
    include_data_tables: bool = Field(default=True, description="Include data tables")
    include_recommendations: bool = Field(default=True, description="Include recommendations")
    format: str = Field(default="pdf", description="Output format (pdf, docx, html)")
    language: str = Field(default="en", description="Report language (en, bi)")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "analysis-123",
                "report_type": "detailed",
                "include_maps": True,
                "include_data_tables": True,
                "format": "pdf",
                "language": "en"
            }
        }


class ReportResponse(BaseModel):
    """Schema for generated report"""
    report_id: str = Field(..., description="Report identifier")
    analysis_id: str = Field(..., description="Associated analysis")
    report_type: str = Field(..., description="Report type")
    status: str = Field(..., description="Report status (generating, ready, failed)")
    file_path: Optional[str] = Field(None, description="Path to generated report file")
    file_size_mb: Optional[float] = Field(None, description="Report file size")
    format: str = Field(..., description="Report format")
    language: str = Field(..., description="Report language")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Report expiration timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Admin Schemas
# ============================================================================

class AdminUserCreate(BaseModel):
    """Schema for admin user creation"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Initial password")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    role: str = Field(..., description="User role to assign")
    organization: Optional[str] = Field(None, description="Organization")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "temppassword123",
                "first_name": "Jane",
                "last_name": "Smith",
                "role": "analyst",
                "organization": "Department"
            }
        }


class AdminUserUpdate(BaseModel):
    """Schema for admin user update"""
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    role: Optional[str] = Field(None, description="User role")
    organization: Optional[str] = Field(None, description="Organization")
    is_active: Optional[bool] = Field(None, description="Account active status")

    class Config:
        json_schema_extra = {
            "example": {
                "role": "reviewer",
                "is_active": True
            }
        }


# Update forward references for models with nested types
DatasetSlotResponse.model_rebuild()
QAReport.model_rebuild()
AnalysisResponse.model_rebuild()
ExtractionResponse.model_rebuild()
GeorefUploadResponse.model_rebuild()
DigitiisedFeature.model_rebuild()
ReportResponse.model_rebuild()
