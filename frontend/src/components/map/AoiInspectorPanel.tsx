/**
 * AoiInspectorPanel — slides in automatically when the user draws a polygon.
 * Shows area stats from OSM layers and lists all available analyses.
 */

import { useState } from 'react';
import type { AoiInspection, AvailableAnalysis } from '../../hooks/useAoiInspector';

interface Props {
  inspection: AoiInspection;
  onRunAnalysis: (analysisId: string) => void;
  onClearAoi: () => void;
  isProcessing: boolean;
}

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  hazard:         { label: 'Hazard',         color: 'bg-red-100 text-red-700' },
  suitability:    { label: 'Suitability',    color: 'bg-green-100 text-green-700' },
  infrastructure: { label: 'Infrastructure', color: 'bg-blue-100 text-blue-700' },
  environment:    { label: 'Environment',    color: 'bg-teal-100 text-teal-700' },
};

function StatCard({ label, value, unit, icon, loading }: {
  label: string; value: number | null; unit: string; icon: string; loading?: boolean;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-2.5 flex flex-col gap-0.5">
      <div className="flex items-center gap-1 text-gray-500 text-xs">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      {loading || value === null ? (
        <div className="h-5 w-16 bg-gray-200 rounded animate-pulse mt-0.5" />
      ) : (
        <div className="font-bold text-gray-900 text-sm">
          {value.toLocaleString()} <span className="font-normal text-gray-500 text-xs">{unit}</span>
        </div>
      )}
    </div>
  );
}

function AnalysisCard({ analysis, onRun, isProcessing }: {
  analysis: AvailableAnalysis;
  onRun: () => void;
  isProcessing: boolean;
}) {
  const cat = CATEGORY_LABELS[analysis.category];
  return (
    <div className="flex items-start gap-2 p-2.5 rounded-lg hover:bg-gray-50 group transition-colors border border-transparent hover:border-gray-200">
      <span className="text-lg mt-0.5 shrink-0">{analysis.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-medium text-gray-900 text-sm">{analysis.title}</span>
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${cat.color}`}>
            {cat.label}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5 leading-snug">{analysis.description}</p>
        {analysis.note && (
          <p className="text-[10px] text-amber-600 mt-0.5">{analysis.note}</p>
        )}
      </div>
      <button
        onClick={onRun}
        disabled={isProcessing}
        className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity px-2.5 py-1 text-xs font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        Run
      </button>
    </div>
  );
}

export default function AoiInspectorPanel({ inspection, onRunAnalysis, onClearAoi, isProcessing }: Props) {
  const { stats, analyses } = inspection;
  const [activeCategory, setActiveCategory] = useState<string>('all');

  const categories = ['all', 'hazard', 'suitability', 'infrastructure', 'environment'];
  const filtered = activeCategory === 'all'
    ? analyses
    : analyses.filter(a => a.category === activeCategory);

  const osmLoading = stats.buildings === null;

  return (
    <div
      className="flex flex-col bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
      style={{ width: 340, maxHeight: 'calc(100vh - 120px)' }}
    >
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-green-700 to-green-600 px-4 py-3 flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-white font-bold text-sm">📍 Area Inspector</h2>
          <p className="text-green-200 text-xs mt-0.5">
            {stats.areaSqKm < 1
              ? `${(stats.areaSqKm * 100).toFixed(1)} ha`
              : `${stats.areaSqKm.toFixed(2)} km²`}
            {' · '}
            {stats.perimeterKm.toFixed(1)} km perimeter
          </p>
        </div>
        <button
          onClick={onClearAoi}
          className="text-green-200 hover:text-white text-xs border border-green-500 hover:border-white rounded px-2 py-0.5 transition-colors"
        >
          ✕ Clear
        </button>
      </div>

      {/* ── OSM Layer Counts ── */}
      <div className="px-3 py-3 border-b border-gray-100 shrink-0">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          GIS Features in Area
          {osmLoading && <span className="ml-1 text-gray-400 font-normal normal-case">(loading…)</span>}
        </p>
        <div className="grid grid-cols-2 gap-2">
          <StatCard label="Buildings"      value={stats.buildings}   unit="structures" icon="🏠" loading={osmLoading} />
          <StatCard label="Roads"          value={stats.roadKm}      unit="km"         icon="🛣️" loading={osmLoading} />
          <StatCard label="Rivers/Streams" value={stats.waterwayKm}  unit="km"         icon="🌊" loading={osmLoading} />
          <StatCard label="Parks/Reserves" value={stats.parks}       unit="areas"      icon="🌿" loading={osmLoading} />
        </div>
      </div>

      {/* ── Bbox coords ── */}
      <div className="px-3 py-2 border-b border-gray-100 shrink-0">
        <p className="text-[10px] text-gray-400 font-mono">
          Bounds: {stats.bbox[1].toFixed(3)}°S, {stats.bbox[0].toFixed(3)}°E →{' '}
          {stats.bbox[3].toFixed(3)}°S, {stats.bbox[2].toFixed(3)}°E
        </p>
      </div>

      {/* ── Available Analyses ── */}
      <div className="flex flex-col flex-1 min-h-0">
        <div className="px-3 pt-3 pb-2 shrink-0">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Available Analyses · {filtered.length}
          </p>
          {/* Category filter tabs */}
          <div className="flex gap-1 flex-wrap">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize transition-colors ${
                  activeCategory === cat
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat === 'all' ? `All (${analyses.length})` : CATEGORY_LABELS[cat]?.label}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable analysis list */}
        <div className="overflow-y-auto flex-1 px-2 pb-3 space-y-0.5">
          {filtered.map(analysis => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              onRun={() => onRunAnalysis(analysis.id)}
              isProcessing={isProcessing}
            />
          ))}
        </div>
      </div>

      {/* ── Footer quick actions ── */}
      <div className="px-3 py-2.5 border-t border-gray-100 bg-gray-50 flex gap-2 shrink-0">
        <button
          onClick={() => onRunAnalysis('development-suitability')}
          disabled={isProcessing}
          className="flex-1 py-1.5 text-xs font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 transition-colors"
        >
          {isProcessing ? (
            <span className="flex items-center justify-center gap-1">
              <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running…
            </span>
          ) : (
            '▶ Run Full Assessment'
          )}
        </button>
        <button
          onClick={onClearAoi}
          className="px-3 py-1.5 text-xs font-semibold text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
