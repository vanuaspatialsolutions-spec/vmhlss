# VMHLSS Frontend

Vanuatu Multi-Hazard Land Suitability System (VMHLSS) - Frontend Application

## Overview

A production-ready TypeScript/React frontend for the VMHLSS decision support system. Provides intuitive interfaces for land suitability assessment, data management, and hazard analysis across Vanuatu.

## Features

### Workspaces

1. **WS-01: Map & Query Workspace** (`/`)
   - Interactive MapLibre GL map with Vanuatu-centered view
   - Draw Area of Interest (AOI) with polygon and rectangle tools
   - Assessment type selection (Development/Agriculture/Both)
   - Persona selection for tailored analysis
   - Layer toggle panel (hazards, CHI, suitability, LULC, boundaries, KB points)
   - Real-time analysis results with color-coded suitability classes
   - Interactive result popups showing CHI score, confidence, top hazard factors

2. **WS-02: Data Dashboard** (`/data`)
   - 14 dataset slot cards (10 Phase 1, 4 Phase 2)
   - Drag-and-drop file upload with progress tracking
   - 6-stage QA process visualization
   - Auto-fix tracking and fix report display
   - Status indicators: empty (grey), passed (green), conditional (amber), failed (red)
   - Dataset replacement workflow

3. **WS-03: Document Workspace** (`/documents`)
   - Document upload and extraction
   - Knowledge base record generation
   - Confidence scoring for extractions
   - Multi-format support (PDF, Word, TXT)

4. **WS-04: Georeferencing Workspace** (`/georef`)
   - Scanned map image upload
   - Ground Control Point (GCP) management
   - Affine transformation computation
   - Digitised feature confirmation

5. **WS-05: Reports Workspace** (`/reports`)
   - Multiple report types (5 templates)
   - Format selection (PDF, HTML, GeoJSON, CSV)
   - Report generation and download
   - Report sharing capabilities

### Common Features

- **Top Navigation Bar**: Workspace tabs, logo, language toggle (EN/BI)
- **Status Bar**: Slots completion count, KB records count, last analysis date, data quality score
- **Bilingual Support**: Full English/Bislama interface
- **Responsive Design**: Mobile, tablet, and desktop optimized

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── workspaces/
│   │   │   ├── MapQueryWorkspace.tsx
│   │   │   ├── DataDashboard.tsx
│   │   │   ├── DocumentWorkspace.tsx
│   │   │   ├── GeoreferencingWorkspace.tsx
│   │   │   └── ReportsWorkspace.tsx
│   │   ├── map/
│   │   │   ├── MapLayerPanel.tsx
│   │   │   ├── QueryPanel.tsx
│   │   │   └── ResultsPopup.tsx
│   │   ├── data/
│   │   │   ├── DataSlotCard.tsx
│   │   │   ├── UploadPanel.tsx
│   │   │   └── QAProgressBar.tsx
│   │   └── common/
│   │       ├── TopNavBar.tsx
│   │       └── StatusBar.tsx
│   ├── services/
│   │   └── api.ts (Axios API client)
│   ├── store/
│   │   └── index.ts (Zustand stores)
│   ├── i18n/
│   │   └── index.ts (Translation system)
│   ├── types/
│   │   └── index.ts (TypeScript definitions)
│   ├── App.tsx (Router and layout)
│   ├── main.tsx (React 18 entry point)
│   └── index.css (Tailwind + custom styles)
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── postcss.config.js
├── index.html
├── .env.example
└── README.md
```

## Tech Stack

- **Framework**: React 18.2
- **Language**: TypeScript 5.3
- **Build**: Vite 5.1
- **Styling**: Tailwind CSS 3.4
- **State Management**: Zustand 4.5
- **Maps**: MapLibre GL 4.1
- **HTTP Client**: Axios 1.6
- **Data Fetching**: React Query 5.18
- **File Upload**: React Dropzone 14.2
- **Charts**: Recharts 2.12
- **Routing**: React Router 6.22

## Installation

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Update API URL in .env
VITE_API_URL=http://localhost:8000/api
VITE_MAPLIBRE_API_KEY=your_key_here
```

## Development

```bash
# Start development server (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

The app will be available at `http://localhost:5173`.

## API Integration

The frontend connects to the VMHLSS backend API at `localhost:8000/api`.

### Key API Endpoints

**Auth**
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`

**Datasets**
- `GET /datasets/slots`
- `POST /datasets/upload`
- `GET /datasets/uploads/:id/qa-status`
- `POST /datasets/uploads/:id/field-mapping`

**Analysis**
- `POST /analysis/run`
- `GET /analysis/:id`
- `GET /analysis/history`

**Documents**
- `POST /documents/upload`
- `GET /documents/:id/extractions`

**Knowledge Base**
- `GET /knowledge-base/query`
- `POST /knowledge-base/records`

**Georeferencing**
- `POST /georef/upload-map`
- `GET /georef/:mapImageId/gcps`
- `POST /georef/:mapImageId/compute`

**Reports**
- `POST /reports/generate`
- `GET /reports/:id/download`

**Dashboard**
- `GET /dashboard/metrics`

## State Management

### Zustand Stores

1. **authStore**: User, token, language
2. **analysisStore**: Current AOI, analysis, assessment type, personas
3. **datasetStore**: Slots, uploads, QA reports
4. **uiStore**: Active workspace, layer visibility, sidebar state
5. **mapStore**: Map center, zoom, basemap, AOI geometry

## Internationalization

Bilingual support (English/Bislama) with full UI coverage:
- Workspace names
- Suitability class labels (S1-NS)
- Button labels and instructions
- Dashboard and analysis terminology

Switch language via toggle in top navigation bar. Selection persists in localStorage.

## Styling

### Color Palette

**Suitability Classes**:
- S1 (Highly Suitable): #1a5c30 (dark green)
- S2 (Suitable): #4aa040 (green)
- S3 (Moderate): #c8a000 (yellow)
- S4 (Marginal): #c85000 (orange)
- S5 (Not Suitable): #8b2000 (red)
- NS (Not Assessed): #1a1a1a (black)

**Status Indicators**:
- Pass: #10b981 (emerald)
- Fail: #ef4444 (red)
- Conditional: #f59e0b (amber)
- Auto-fixed: #3b82f6 (blue)
- Empty: #d1d5db (grey)

## Type Safety

Comprehensive TypeScript definitions for all data structures:
- User, Auth, Tokens
- DatasetSlots, QA Stages, Field Mappings
- Analysis, Results, Suitability Classes
- Knowledge Base Records
- Reports, Georeferencing
- GeoJSON geometries

All components are fully typed with no implicit `any` types.

## Performance

- Vite for fast development and optimized builds
- Code splitting via React Router
- Lazy loading of workspace components
- Optimized re-renders with Zustand selectors
- Tailwind CSS purging for minimal CSS output
- MapLibre layer management with visibility toggling

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Environment Variables

```env
# Backend API URL
VITE_API_URL=http://localhost:8000/api

# MapLibre/Maptiler API key (for basemap tiles)
VITE_MAPLIBRE_API_KEY=your_key_here
```

## Build Output

Production build generates:
- Minified JavaScript bundles
- Optimized CSS with Tailwind purging
- Source maps for debugging
- Static assets

Output in `dist/` directory, ready for deployment.

## License

Proprietary - Vanuatu Government, Department of Climate Change

## Support

For issues or questions:
1. Check the API connectivity in browser DevTools Network tab
2. Review component console for detailed error messages
3. Verify all required environment variables are set
4. Ensure backend API is running and accessible

---

Built with ❤️ for Vanuatu's resilience and sustainable development.
