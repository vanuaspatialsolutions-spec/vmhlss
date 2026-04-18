# VMHLSS Frontend - Quick Start Guide

## Installation & Setup (5 minutes)

### 1. Install Dependencies
```bash
cd /sessions/pensive-blissful-curie/mnt/Vanuatu\ DSS/vmhlss/frontend
npm install
```

### 2. Configure Environment
Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and set your API endpoint:
```env
VITE_API_URL=http://localhost:8000/api
VITE_MAPLIBRE_API_KEY=your_optional_key
```

### 3. Start Development Server
```bash
npm run dev
```

Visit: **http://localhost:5173**

## First Time Using the System?

### Default Demo Experience
- All workspaces are functional without backend
- Mock data pre-loaded in Data Dashboard
- MapLibre map centered on Vanuatu
- Demo reports and analysis results available

### Five Workspaces Available

1. **Map & Query** (`/`) - Create analysis areas on map
2. **Data Management** (`/data`) - Upload and manage datasets
3. **Documents** (`/documents`) - Extract knowledge from documents
4. **Georeferencing** (`/georef`) - Georeference historical maps
5. **Reports** (`/reports`) - Generate analysis reports

## Key Features

### Language Support
- Toggle English/Bislama in top-right corner
- All UI text translated
- Selection persists in local storage

### Data Dashboard
- 14 dataset slots (10 required, 4 optional)
- Status: Empty, Passed, Conditional, Failed
- Drag-drop file upload
- 6-stage QA process visualization

### Map Interface
- Draw areas on the map
- 11 layer categories (hazards, suitability, LULC, etc.)
- Switch basemaps (Satellite/OSM/Topographic)
- Color-coded suitability results

### Analysis Workflow
1. Draw area on map
2. Select assessment type (Development/Agriculture/Both)
3. Choose relevant personas
4. Click "Run Analysis"
5. View results with hazard details

## File Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── workspaces/      # 5 main workspace components
│   │   ├── map/             # Map controls and popups
│   │   ├── data/            # Dataset upload and QA
│   │   └── common/          # Shared nav and status bar
│   ├── services/
│   │   └── api.ts           # Backend API client
│   ├── store/
│   │   └── index.ts         # Zustand state stores
│   ├── i18n/
│   │   └── index.ts         # EN/BI translations
│   ├── types/
│   │   └── index.ts         # TypeScript definitions
│   ├── App.tsx              # Main app with routing
│   └── main.tsx             # React entry point
├── package.json             # Dependencies
├── vite.config.ts           # Build config
├── tsconfig.json            # TypeScript config
└── tailwind.config.js       # Tailwind customization
```

## Available Commands

```bash
npm run dev          # Development server (hot reload)
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Check code quality
```

## Database Colors

### Suitability Classes
- **S1** (#1a5c30): Highly suitable - Dark Green
- **S2** (#4aa040): Suitable - Green
- **S3** (#c8a000): Moderate - Yellow
- **S4** (#c85000): Marginal - Orange
- **S5** (#8b2000): Not suitable - Red
- **NS** (#1a1a1a): Not assessed - Black

### Status Indicators
- **✓ Pass** (#10b981): Green
- **✕ Fail** (#ef4444): Red
- **⚠ Conditional** (#f59e0b): Amber
- **◆ Auto-fixed** (#3b82f6): Blue
- **○ Empty** (#d1d5db): Grey

## Troubleshooting

### Port Already in Use
```bash
# Default port is 5173, change with:
npm run dev -- --port 3000
```

### API Connection Issues
1. Check `.env` file has correct VITE_API_URL
2. Ensure backend is running on port 8000
3. Clear browser cache if needed

### Module Not Found
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Errors
```bash
# Rebuild TypeScript
npx tsc --noEmit
```

## Production Build

```bash
# Create optimized build
npm run build

# Output in dist/ directory
# Deploy dist/ folder to your server
```

## API Integration

The frontend automatically connects to your backend API:
- Base URL from `VITE_API_URL` environment variable
- JWT token interceptor for authentication
- Auto-refresh on 401 responses
- Proxy configured in vite.config.ts

## Technology Stack

- **React 18.2** - UI Framework
- **TypeScript 5.3** - Type Safety
- **Vite 5.1** - Build Tool
- **Tailwind CSS 3.4** - Styling
- **MapLibre GL 4.1** - Maps
- **Zustand 4.5** - State Management
- **Axios 1.6** - HTTP Client
- **React Router 6.22** - Navigation

## Next Steps

1. ✓ Install and run frontend
2. → Start backend API on port 8000
3. → Create test user account
4. → Test data upload workflow
5. → Run analysis on demo area
6. → Generate sample report

## Documentation

- **README.md** - Comprehensive documentation
- **IMPLEMENTATION_SUMMARY.md** - Feature checklist and details
- **FILE_MANIFEST.txt** - Complete file listing

## Need Help?

- Check browser console for errors (F12)
- Review network requests (DevTools → Network tab)
- Check API endpoint is accessible
- Verify environment variables are set

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: April 2026
