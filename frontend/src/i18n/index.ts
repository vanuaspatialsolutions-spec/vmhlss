import type { Language, TranslationKeys } from '../types/index';

type Translation = Partial<TranslationKeys>;

const translations: Record<Language, Translation> = {
  en: {
    // Common UI
    'common.loading': 'Loading...',
    'common.error': 'An error occurred',
    'common.success': 'Success',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.close': 'Close',
    'common.next': 'Next',
    'common.previous': 'Previous',
    'common.export': 'Export',
    'common.import': 'Import',
    'common.download': 'Download',
    'common.upload': 'Upload',
    'common.language': 'Language',

    // Workspaces
    'workspace.mapquery': 'Map & Query',
    'workspace.data': 'Data Management',
    'workspace.documents': 'Documents',
    'workspace.georef': 'Georeferencing',
    'workspace.reports': 'Reports',

    // Suitability Classes - Agriculture
    'suitability.s1.ag': 'Good to farm',
    'suitability.s2.ag': 'Farm with care — some risks present',
    'suitability.s3.ag': 'Farm with caution — moderate risks',
    'suitability.s4.ag': 'Not recommended for farming',
    'suitability.s5.ag': 'Do not farm here',
    'suitability.ns.ag': 'Not suitable',

    // Suitability Classes - Development
    'suitability.s1.dev': 'Suitable for development',
    'suitability.s2.dev': 'Can build with conditions',
    'suitability.s3.dev': 'Build with caution — mitigation required',
    'suitability.s4.dev': 'Not recommended for development',
    'suitability.s5.dev': 'Do not build here',
    'suitability.ns.dev': 'Not suitable',

    // Map Query Workspace
    'mapquery.drawarea': 'Draw Area of Interest',
    'mapquery.selectarea': 'Draw your area of interest on the map',
    'mapquery.assessmenttype': 'Assessment Type',
    'mapquery.development': 'Development',
    'mapquery.agriculture': 'Agriculture',
    'mapquery.both': 'Both',
    'mapquery.personas': 'Personas to Include',
    'mapquery.runanalysis': 'Run Analysis',
    'mapquery.layers': 'Layers',
    'mapquery.hazard': 'Hazards',
    'mapquery.suitability': 'Suitability',
    'mapquery.lulc': 'Land Use / Land Cover',
    'mapquery.boundaries': 'Administrative Boundaries',
    'mapquery.knowledge': 'Knowledge Base Points',
    'mapquery.chi': 'CHI Index',
    'mapquery.results': 'Results',
    'mapquery.processing': 'Processing analysis...',
    'mapquery.clickresult': 'Click on result cells for details',
    'mapquery.export': 'Export Results',

    // Data Dashboard
    'dashboard.slots': 'Data Slots',
    'dashboard.phase1': 'Phase 1 — Core Data',
    'dashboard.phase2': 'Phase 2 — Optional Enhancements',
    'dashboard.upload': 'Upload Data',
    'dashboard.status': 'Status',
    'dashboard.formats': 'Accepted Formats',
    'dashboard.minimum': 'Minimum Standard',
    'dashboard.recommended': 'Recommended Source',
    'dashboard.dragdrop': 'Drag and drop files here or click to browse',
    'dashboard.qaprocess': 'Quality Assurance Process',
    'dashboard.processing': 'Processing...',
    'dashboard.passed': 'Passed',
    'dashboard.failed': 'Failed',
    'dashboard.autofixed': 'Auto-fixed',
    'dashboard.replace': 'Replace Dataset',
    'dashboard.fixes': 'Applied Fixes',

    // Status bar
    'status.slots': 'Slots Complete',
    'status.kbrecords': 'Knowledge Base Records',
    'status.lastanalysis': 'Last Analysis',
  },
  bi: {
    // Common UI
    'common.loading': 'Hem i laodim...',
    'common.error': 'Wanem error i kam',
    'common.success': 'Gud tumas',
    'common.cancel': 'Kansel',
    'common.save': 'Sevm',
    'common.delete': 'Kilim',
    'common.edit': 'Mekem cheinj',
    'common.close': 'Klosim',
    'common.next': 'Neks',
    'common.previous': 'Bak',
    'common.export': 'Exportim',
    'common.import': 'Importim',
    'common.download': 'Daunlodum',
    'common.upload': 'Aploadim',
    'common.language': 'Wae blong toktok',

    // Workspaces
    'workspace.mapquery': 'Mep mo Ask',
    'workspace.data': 'Data Manajim',
    'workspace.documents': 'Dokumens',
    'workspace.georef': 'Geo Refrans',
    'workspace.reports': 'Ripots',

    // Suitability Classes - Agriculture
    'suitability.s1.ag': 'Ples ya i gud blong planem',
    'suitability.s2.ag': 'Yu save planem be yu mas lukaotem gud — i gat sampol risk',
    'suitability.s3.ag': 'Planem be mas kaeful — i gat smol risk',
    'suitability.s4.ag': 'No gud fo planem',
    'suitability.s5.ag': 'No planem long ples ya',
    'suitability.ns.ag': 'No gud',

    // Suitability Classes - Development
    'suitability.s1.dev': 'Ples ya i gud blong bildim',
    'suitability.s2.dev': 'Yu save bildim be yu mas followem ol kondisen',
    'suitability.s3.dev': 'Bildim be mas kaeful — i nid fixim',
    'suitability.s4.dev': 'No gud fo bildim',
    'suitability.s5.dev': 'No bildim long ples ya',
    'suitability.ns.dev': 'No gud',

    // Map Query Workspace
    'mapquery.drawarea': 'Droim Area blong Check',
    'mapquery.selectarea': 'Droim eria blong yu long mep',
    'mapquery.assessmenttype': 'Wanem Kaen Check',
    'mapquery.development': 'Bildim',
    'mapquery.agriculture': 'Planem',
    'mapquery.both': 'Ol Tu',
    'mapquery.personas': 'Pipl blong Inkludem',
    'mapquery.runanalysis': 'Ronit Check',
    'mapquery.layers': 'Layaz',
    'mapquery.hazard': 'Denja',
    'mapquery.suitability': 'Gud Pis',
    'mapquery.lulc': 'Wae Ol Ting Stanap',
    'mapquery.boundaries': 'Baunari',
    'mapquery.knowledge': 'Save Poen',
    'mapquery.chi': 'CHI Score',
    'mapquery.results': 'Answas',
    'mapquery.processing': 'Hem i mekem check...',
    'mapquery.clickresult': 'Klik long answas blong lukaot detels',
    'mapquery.export': 'Skem Answas',

    // Data Dashboard
    'dashboard.slots': 'Data Slots',
    'dashboard.phase1': 'Fase 1 — Main Data',
    'dashboard.phase2': 'Fase 2 — Sampol Narafala',
    'dashboard.upload': 'Aploadim Data',
    'dashboard.status': 'Wetem Stap',
    'dashboard.formats': 'Kaen Failim',
    'dashboard.minimum': 'Minimum Standard',
    'dashboard.recommended': 'Gud Pis fo Kasem',
    'dashboard.dragdrop': 'Dragim failim ya o klik fo lukukaot',
    'dashboard.qaprocess': 'Check Gud Gud Process',
    'dashboard.processing': 'Mekem...',
    'dashboard.passed': 'Okei',
    'dashboard.failed': 'No gud',
    'dashboard.autofixed': 'Hem fixim hiselfem',
    'dashboard.replace': 'Changemet Data',
    'dashboard.fixes': 'Fixim Ol Samting',

    // Status bar
    'status.slots': 'Slots Redy',
    'status.kbrecords': 'Save Numba',
    'status.lastanalysis': 'Las Check',
  },
};

export const useTranslation = (language: Language) => {
  const t = (key: string): string => {
    const value = translations[language][key as keyof Translation];
    return value || key;
  };

  return { t, language };
};

export const getTranslation = (language: Language, key: string): string => {
  const value = translations[language][key as keyof Translation];
  return value || key;
};
