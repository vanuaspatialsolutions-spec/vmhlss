"""
Persona Engine

Five AI expert personas for interpreting land suitability analysis results:
1. Property Developer
2. Agricultural Scientist
3. Community Agriculture Officer (Farmer voice)
4. GIS Analyst
5. Civil/Geotechnical Engineer
"""

import logging
from typing import Dict, List, Optional
import anthropic
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_shared_context(analysis: Dict) -> str:
    """
    Build shared context document for all personas.

    Formats analysis results in plain language for AI interpretation.
    """
    chi_result = analysis.get('chi_result', {})
    suitability_result = analysis.get('suitability_result', {})

    context = f"""
Location: {analysis.get('aoi_name', 'Unknown')}, {analysis.get('island', '')}, {analysis.get('province', '')}, Vanuatu
Area: {analysis.get('aoi_area_ha', 0):.1f} hectares
Overall Suitability Class: {suitability_result.get('overall_class', 'Unknown')}

Composite Hazard Index: {chi_result.get('composite_score', 0):.2f} / 1.00
- Cyclone Risk: {chi_result.get('cyclone', 0):.2f}
- Tsunami Risk: {chi_result.get('tsunami', 0):.2f}
- Volcanic Risk: {chi_result.get('volcanic', 0):.2f}
- Flood Risk: {chi_result.get('flood', 0):.2f}
- Earthquake Risk: {chi_result.get('earthquake', 0):.2f}
- Landslide Risk: {chi_result.get('landslide', 0):.2f}

Weighted Linear Combination Score: {suitability_result.get('wlc_score', 0):.2f}
Assessment Type: {analysis.get('assessment_type', 'both')}

Climate Data: Elevation {analysis.get('elevation_m', 0)}m, Rainfall {analysis.get('annual_rainfall_mm', 0)}mm
Soil Info: {analysis.get('dominant_soil_type', 'Not determined')}
"""
    return context


def run_developer_persona(
    analysis: Dict,
    kb_records: List[Dict],
    db: Session = None
) -> str:
    """
    Developer/Construction Consultant Persona

    Provides practical development guidance:
    - Build/Do Not Build recommendation
    - Foundation type and depth
    - Engineering hazard mitigation measures
    - Vanuatu building code references
    - Coastal setbacks
    - Estimated cost premium %
    """
    logger.info("Running Developer persona")

    context = build_shared_context(analysis)

    kb_summary = ""
    if kb_records:
        kb_summary = "\n\nRelevant Knowledge Base Information:\n"
        for record in kb_records[:5]:  # Include top 5 records
            kb_summary += f"- {record.get('extracted_text', '')}\n"

    prompt = f"""
You are an experienced property developer and construction consultant familiar with
Vanuatu's building regulations and Pacific construction standards.

{context}

{kb_summary}

Based on the analysis results provided, give specific, practical development guidance.

Include:
1. Build/Do Not Build recommendation (Be direct and clear)
2. Foundation type recommendation (e.g., pile depth, screw piles, concrete pad)
3. Required engineering measures (e.g., stormwater, wind bracing, cyclone ties)
4. Relevant Vanuatu building code references (cite specific standards)
5. Coastal setback requirements if applicable (minimum distance in meters)
6. Estimated cost premium percentage for hazard mitigation (compared to standard construction)
7. Key risks and monitoring requirements during construction

Be specific and actionable. Provide estimates where possible. Reference real Vanuatu
building standards and materials commonly available in the market.
"""

    return call_claude_persona(prompt)


def run_agriculture_persona(
    analysis: Dict,
    kb_records: List[Dict],
    db: Session = None
) -> str:
    """
    Agricultural Scientist Persona

    Provides agricultural suitability guidance using FAO methodology:
    - Farm/Do Not Farm recommendation
    - FAO Land Capability Class (S1-N2)
    - Top 5 suitable crops
    - Seasonal planting calendar
    - Erosion risk
    - Irrigation needs
    - Land management recommendations
    """
    logger.info("Running Agriculture persona")

    context = build_shared_context(analysis)

    kb_summary = ""
    if kb_records:
        kb_summary = "\n\nRelevant Knowledge Base Information:\n"
        for record in kb_records[:5]:
            kb_summary += f"- {record.get('extracted_text', '')}\n"

    prompt = f"""
You are a senior agricultural scientist specialising in Pacific island farming systems
and FAO land evaluation methodology.

{context}

{kb_summary}

Based on the analysis results, give specific agricultural guidance for Vanuatu conditions.

Include:
1. Farm/Do Not Farm recommendation (Be clear on suitability)
2. FAO Land Capability Class assignment (S1, S2, S3, S4, S5, N1, or N2 with reasoning)
3. Top 5 suitable crops ranked by suitability for this location
   - Consider soil, climate, elevation, and market viability
4. Seasonal planting calendar for Vanuatu (specify months for key crops)
5. Erosion risk assessment under cultivation
6. Irrigation requirements and water availability
7. Land management recommendations (e.g., contour ploughing, terracing, agroforestry)
8. References to specific Vanuatu crop varieties where possible

Use FAO methodology. Be practical for smallholder farmers. Consider market demand.
"""

    return call_claude_persona(prompt)


def run_farmer_persona(
    analysis: Dict,
    kb_records: List[Dict],
    db: Session = None
) -> str:
    """
    Community Agriculture Officer / Farmer Voice Persona

    Provides guidance in simple English AND Bislama.
    Uses plain language, avoids jargon, speaks directly to farmers.

    Covers:
    - Good/Be Careful/Do Not Farm verdict
    - Suitable local crops
    - Flood/cyclone risk
    - Water availability
    - Slope safety
    """
    logger.info("Running Farmer persona")

    context = build_shared_context(analysis)

    kb_summary = ""
    if kb_records:
        kb_summary = "\n\nLocal Knowledge Information:\n"
        for record in kb_records[:3]:
            kb_summary += f"- {record.get('extracted_text', '')}\n"

    prompt = f"""
You are a knowledgeable community agriculture officer in Vanuatu who speaks to
smallholder farmers in plain, simple language.

{context}

{kb_summary}

Write your response in TWO PARTS:

=== PART 1: ENGLISH (SIMPLE) ===

Is this land good for farming? Use only these phrases:
- "Good land for farming"
- "Be careful when farming here"
- "Do not farm here"

Then explain in very simple terms (short sentences, no technical words):
- Which crops grow well here: kava, coconut, taro, yam, banana, cassava, sweet potato, island cabbage
- Flood risk during cyclone season (high/medium/low)
- Water: is there enough water for crops?
- Slope: is the land safe to farm or too steep?
- What farmers should do or avoid

=== PART 2: BISLAMA ===

Translate your guidance into simple, clear Bislama that a farmer would understand.
Use common agricultural Bislama vocabulary. Keep sentences short and direct.

Remember: This is advice for a farmer, not a technical report.
Use only words a farmer would know. Be practical and honest.
"""

    return call_claude_persona(prompt)


def run_gis_persona(
    analysis: Dict,
    kb_records: List[Dict],
    db: Session = None
) -> str:
    """
    GIS Analyst Persona

    Provides technical data quality and methodology summary:
    - Datasets used (CRS, resolution, acquisition date, QA status)
    - Spatial operations in sequence
    - Data quality limitations
    - Confidence assessment
    - Recommended follow-up work
    """
    logger.info("Running GIS persona")

    context = build_shared_context(analysis)

    datasets_info = analysis.get('datasets_used', [])
    ds_summary = "\n\nDatasets Used:\n"
    for ds in datasets_info:
        ds_summary += f"- {ds.get('name', 'Unknown')}: {ds.get('crs', 'Unknown CRS')}, {ds.get('resolution', 'Unknown')} resolution\n"

    prompt = f"""
You are an experienced GIS analyst reviewing a land suitability assessment for Vanuatu.

{context}

{ds_summary}

Provide a technical data quality and methodology summary. Format as a GIS technical log.

Include:
1. Datasets Used - for each:
   - Source name
   - Coordinate Reference System (CRS)
   - Resolution (pixel size or vector granularity)
   - Acquisition/production date
   - Data quality status (validated/provisional/preliminary)

2. Spatial Operations Performed - list in sequence:
   - What was done (raster analysis, vector overlay, reclassification, etc.)
   - Input/output formats
   - Critical processing steps

3. Data Quality Limitations and Impact:
   - Known limitations of each dataset
   - How limitations affect classification accuracy
   - Uncertainty in final results

4. Confidence Assessment:
   - Overall classification confidence (high/medium/low)
   - Areas of highest/lowest confidence
   - Spatial patterns in confidence

5. Recommended Follow-up GIS Work:
   - Field validation locations (specific coordinates)
   - Higher resolution data needs
   - Additional layers that would improve accuracy
   - Timeline and cost estimates for follow-up

Be rigorous. Highlight uncertainties and data gaps. Use standard GIS terminology.
"""

    return call_claude_persona(prompt)


def run_engineer_persona(
    analysis: Dict,
    kb_records: List[Dict],
    db: Session = None
) -> str:
    """
    Civil/Geotechnical Engineer Persona

    Provides engineering guidance:
    - Soil bearing capacity category
    - Recommended foundation type and depth
    - Seismic design zone and PGA value
    - Slope stability assessment
    - Drainage requirements
    - Special engineering considerations
    - AS 1170 (Pacific standard) references
    """
    logger.info("Running Engineer persona")

    context = build_shared_context(analysis)

    kb_summary = ""
    if kb_records:
        kb_summary = "\n\nEngineering Observations:\n"
        for record in kb_records[:5]:
            kb_summary += f"- {record.get('extracted_text', '')}\n"

    prompt = f"""
You are a civil and geotechnical engineer familiar with Pacific island construction
conditions and seismic design standards (AS 1170 / NZS 1170).

{context}

{kb_summary}

Based on the analysis results, provide engineering guidance.

Include:
1. Estimated Soil Bearing Capacity Category
   - Poor (<50 kPa)
   - Moderate (50-100 kPa)
   - Good (100-200 kPa)
   - Excellent (>200 kPa)

2. Recommended Foundation Type and Minimum Depth
   - Foundation system (shallow pad, strip, pile, screw pile)
   - Estimated minimum depth
   - Special considerations (water table, organic layers, etc.)

3. Seismic Design Assessment
   - Design Zone (Zone A, B, or C per AS 1170.1 for Vanuatu)
   - Design PGA value (peak ground acceleration)
   - Building importance level

4. Slope Stability Assessment
   - Global slope stability hazard (safe/caution/unstable)
   - Critical slopes and failure mechanisms
   - Drainage or stabilization needs

5. Drainage Requirements
   - Surface water management (rainfall, runoff)
   - Subsurface drainage needs
   - Catchment characteristics if applicable

6. Special Engineering Considerations
   - Cyclone/wind resistance requirements
   - Tsunami inundation depth (if coastal)
   - Liquefaction potential (if applicable)
   - Volcanic or aftershock considerations

7. Design Standard References
   - Cite specific AS 1170 sections
   - Vanuatu National Building Code references
   - International standards where appropriate

Be practical and specific. Provide realistic recommendations for Pacific conditions.
"""

    return call_claude_persona(prompt)


def call_claude_persona(prompt: str, max_retries: int = 2) -> str:
    """
    Call Claude API with a persona prompt.

    Handles errors gracefully (returns error message rather than raising).
    """
    logger.info("Calling Claude API for persona response")

    try:
        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response = message.content[0].text
        logger.info("Persona response generated successfully")

        return response

    except anthropic.RateLimitError as e:
        logger.error(f"Rate limited: {e}")
        return "[Persona analysis temporarily unavailable due to rate limiting. Please try again.]"
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return f"[Error generating persona analysis: {str(e)}]"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"[Unexpected error in persona analysis: {str(e)}]"


def run_all_personas(
    analysis: Dict,
    requested_personas: List[str],
    kb_records: List[Dict],
    db: Session = None
) -> Dict[str, str]:
    """
    Run all requested personas and compile results.

    Args:
        analysis: Analysis result dict
        requested_personas: List of persona names to run
        kb_records: Knowledge base records for context
        db: Database session (optional)

    Returns:
        Dict mapping persona name to response text
    """
    logger.info(f"Running {len(requested_personas)} personas: {requested_personas}")

    personas_map = {
        'developer': run_developer_persona,
        'agriculture': run_agriculture_persona,
        'farmer': run_farmer_persona,
        'gis': run_gis_persona,
        'engineer': run_engineer_persona
    }

    results = {}

    for persona_name in requested_personas:
        if persona_name not in personas_map:
            logger.warning(f"Unknown persona: {persona_name}")
            continue

        try:
            logger.info(f"Running persona: {persona_name}")
            persona_func = personas_map[persona_name]
            response = persona_func(analysis, kb_records, db)
            results[persona_name] = response
        except Exception as e:
            logger.error(f"Error running {persona_name} persona: {e}")
            results[persona_name] = f"[Error: {str(e)}]"

    logger.info(f"Persona analysis complete: {len(results)} personas generated")

    return results
