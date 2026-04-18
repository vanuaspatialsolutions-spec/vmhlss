import logging

logger = logging.getLogger(__name__)

# Translation dictionary for English and Bislama
TRANSLATIONS = {
    "en": {
        "good_to_farm": "Good to farm",
        "farm_with_care": "Farm with care — some risks present",
        "do_not_farm": "Do not farm here",
        "good_to_build": "Suitable for development",
        "build_with_conditions": "Can build with conditions",
        "do_not_build": "Do not build here",
        "run_analysis": "Run Analysis",
        "upload_data": "Upload Data",
        "select_area": "Draw your area on the map",
        "analysis": "Analysis",
        "results": "Results",
        "download_report": "Download Report",
        "view_map": "View Map",
        "back": "Back",
        "next": "Next",
        "cancel": "Cancel",
        "save": "Save",
        "delete": "Delete",
        "edit": "Edit",
        "create": "Create",
        "update": "Update",
        "success": "Success",
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "loading": "Loading...",
        "no_data": "No data available",
        "select_hazard": "Select a hazard type",
        "select_land_use": "Select land use type",
        "hazard_analysis": "Hazard Analysis",
        "land_suitability": "Land Suitability Assessment",
        "combined_assessment": "Combined Multi-Hazard Assessment",
        "agriculture": "Agriculture",
        "residential": "Residential Development",
        "commercial": "Commercial Development",
        "critical_infrastructure": "Critical Infrastructure",
        "flood": "Flood Risk",
        "cyclone": "Cyclone Risk",
        "earthquake": "Earthquake Risk",
        "landslide": "Landslide Risk",
        "tsunami": "Tsunami Risk",
        "volcanic": "Volcanic Hazard",
        "coastal_erosion": "Coastal Erosion",
        "drought": "Drought Risk",
        "very_high_risk": "Very High Risk",
        "high_risk": "High Risk",
        "moderate_risk": "Moderate Risk",
        "low_risk": "Low Risk",
        "very_low_risk": "Very Low Risk",
        "area_sq_km": "Area (km²)",
        "total_population": "Total Population",
        "affected_households": "Affected Households",
        "critical_facilities": "Critical Facilities",
        "economic_value": "Economic Value at Risk",
        "average_slope": "Average Slope (%)",
        "soil_type": "Soil Type",
        "drainage": "Drainage",
        "access_road": "Access to Road",
        "proximity_town": "Proximity to Town (km)",
        "water_access": "Access to Water",
        "export_pdf": "Export as PDF",
        "export_geojson": "Export as GeoJSON",
        "export_shp": "Export as Shapefile",
        "share_analysis": "Share Analysis",
        "print_map": "Print Map",
        "zoom_in": "Zoom In",
        "zoom_out": "Zoom Out",
        "fit_bounds": "Fit to Bounds",
        "reset_map": "Reset Map",
        "base_map": "Base Map",
        "satellite": "Satellite",
        "streets": "Streets",
        "terrain": "Terrain",
        "legend": "Legend",
        "help": "Help",
        "about": "About",
        "contact": "Contact",
        "settings": "Settings",
        "logout": "Logout",
        "profile": "Profile",
        "language": "Language",
        "english": "English",
        "bislama": "Bislama",
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark",
        "auto": "Auto",
    },
    "bi": {
        "good_to_farm": "Ples ya i gud blong planem",
        "farm_with_care": "Yu save planem be yu mas lukaotem gud — i gat sampol risk",
        "do_not_farm": "No planem long ples ya",
        "good_to_build": "Ples ya i gud blong bildim",
        "build_with_conditions": "Yu save bildim be yu mas followem ol kondisen",
        "do_not_build": "No bildim long ples ya",
        "run_analysis": "Ronit Analysis",
        "upload_data": "Aploadim Data",
        "select_area": "Droim eria blong yu long mep",
        "analysis": "Analysis",
        "results": "Resultem",
        "download_report": "Daunlod Report",
        "view_map": "Lukim Mep",
        "back": "Bak",
        "next": "Neks",
        "cancel": "Kanselem",
        "save": "Sevim",
        "delete": "Delem",
        "edit": "Editim",
        "create": "Mekem",
        "update": "Apdetim",
        "success": "OK",
        "error": "Eror",
        "warning": "Woning",
        "info": "Informesen",
        "loading": "Loading...",
        "no_data": "I no gat data",
        "select_hazard": "Pik wan hazard taip",
        "select_land_use": "Pik wan lan use taip",
        "hazard_analysis": "Hazard Analysis",
        "land_suitability": "Ples Suitabul Foa Analysis",
        "combined_assessment": "Ol Hazard Tugeta Analysis",
        "agriculture": "Planem",
        "residential": "Stap Ples Bildim",
        "commercial": "Biznez Bildim",
        "critical_infrastructure": "Impotant Stap",
        "flood": "Wota Kam Blong",
        "cyclone": "Saeklon",
        "earthquake": "Gron Sem",
        "landslide": "Gron Slaep",
        "tsunami": "Wota Big Blong Soksok",
        "volcanic": "Volkeino",
        "coastal_erosion": "Sip Gon Daon",
        "drought": "Drae Taem",
        "very_high_risk": "Risk Veri Big Tumas",
        "high_risk": "Risk Big",
        "moderate_risk": "Risk Natingtaing",
        "low_risk": "Risk Liklik",
        "very_low_risk": "Risk Liklik Tumas",
        "area_sq_km": "Eria (km²)",
        "total_population": "Ol Pipol Namba",
        "affected_households": "Famli Namba",
        "critical_facilities": "Impotant Haus",
        "economic_value": "Mani Namba",
        "average_slope": "Gron Slaep (%)",
        "soil_type": "Eart Taip",
        "drainage": "Wota Gon",
        "access_road": "Rot",
        "proximity_town": "Distans Fom Taon (km)",
        "water_access": "Wota",
        "export_pdf": "Mekem PDF",
        "export_geojson": "Mekem GeoJSON",
        "export_shp": "Mekem Shapefile",
        "share_analysis": "Giv Hemi Narafala",
        "print_map": "Printim Mep",
        "zoom_in": "Bigim",
        "zoom_out": "Smolim",
        "fit_bounds": "Fitim Mep",
        "reset_map": "Resetim Mep",
        "base_map": "Mep",
        "satellite": "Satalait",
        "streets": "Rod",
        "terrain": "Gron",
        "legend": "Wot Minin",
        "help": "Help",
        "about": "Aboutem",
        "contact": "Toktok",
        "settings": "Setting",
        "logout": "Goan Out",
        "profile": "Profail Blong Yu",
        "language": "Langwis",
        "english": "Inglish",
        "bislama": "Bislama",
        "theme": "Lukim",
        "light": "Lait",
        "dark": "Dari",
        "auto": "Automatic",
    }
}


def translate(key: str, language: str = "en") -> str:
    """
    Translate a key to the specified language.

    Args:
        key: Translation key (e.g., "good_to_farm")
        language: Language code (default "en" for English, "bi" for Bislama)

    Returns:
        Translated string, or the key itself if translation not found
    """
    try:
        # Validate language
        if language not in TRANSLATIONS:
            logger.warning(f"Unknown language: {language}, falling back to English")
            language = "en"

        # Get translation
        translation = TRANSLATIONS[language].get(key, key)

        # If translation is missing from requested language, fall back to English
        if translation == key and language != "en":
            translation = TRANSLATIONS["en"].get(key, key)

        return translation

    except Exception as e:
        logger.error(f"Error translating key '{key}' to '{language}': {e}")
        return key


def get_supported_languages() -> dict:
    """
    Get list of supported languages.

    Returns:
        Dictionary with language codes as keys and language names as values
    """
    return {
        "en": "English",
        "bi": "Bislama"
    }


def get_language_name(language_code: str) -> str:
    """
    Get the display name for a language code.

    Args:
        language_code: Language code (e.g., "en", "bi")

    Returns:
        Language display name
    """
    names = get_supported_languages()
    return names.get(language_code, language_code)


def translate_dict(data: dict, language: str = "en") -> dict:
    """
    Recursively translate all values in a dictionary that are translation keys.

    Args:
        data: Dictionary with potential translation keys
        language: Language code (default "en")

    Returns:
        Dictionary with translated values
    """
    translated = {}

    for key, value in data.items():
        if isinstance(value, dict):
            translated[key] = translate_dict(value, language)
        elif isinstance(value, list):
            translated[key] = [
                translate_dict(item, language) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and value.startswith("i18n."):
            # If value starts with "i18n.", treat it as a translation key
            translation_key = value[5:]  # Remove "i18n." prefix
            translated[key] = translate(translation_key, language)
        else:
            translated[key] = value

    return translated


def add_translation(key: str, language: str, text: str) -> bool:
    """
    Add or update a translation (for runtime addition of new translations).

    Args:
        key: Translation key
        language: Language code
        text: Translated text

    Returns:
        True if successful, False otherwise
    """
    try:
        if language not in TRANSLATIONS:
            logger.warning(f"Language '{language}' not supported, creating new language dict")
            TRANSLATIONS[language] = {}

        TRANSLATIONS[language][key] = text
        logger.info(f"Added translation: {key} -> {language}")
        return True

    except Exception as e:
        logger.error(f"Error adding translation: {e}")
        return False
