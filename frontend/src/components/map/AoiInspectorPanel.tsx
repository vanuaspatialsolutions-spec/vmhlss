/**
 * AoiInspectorPanel — slides in automatically when the user draws a polygon.
 * Only shows analyses that the system can actually generate for this location.
 */

import { useState } from 'react';
import type { AoiInspection, AvailableAnalysis } from '../../hooks/useAoiInspector';

interface Props {
  inspection: AoiInspection;
  onRunAnalysis: (analysisId: string) => void;
  onClearAoi: () => void;
  isProcessing: boolean;
}

const CATEGORY_META: Record<string, { label: string; color: string; badgeColor: string }> = {
  hazard:         { label: 'Hazard',         color: 'bg-red-100 text-red-700',   badgeColor: 'bg-red-600 text-white' },
  suitability:    { label: 'Suitability',    color: 'bg-green-100 text-green-700', badgeColor: 'bg-green-600 text-white' },
  infrastructure: { label: 'Infrastructure', color: 'bg-blue-100 text-blue-700',   badgeColor: 'bg-blue-600 text-white' },
  environment:    { label: 'Environment',    color: 'bg-teal-100 text-teal-700',   badgeColor: 'bg-teal-600 text-white' },
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
          {value.toLocaleString()}{' '}
          <span className="font-normal text-gray-500 text-xs">{unit}</span>
        </div>
      )}
    </div>
  );
}

function PendingCard({ title, icon }: { title: string; icon: string }) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-gray-50 border border-dashed border-gray-300">
      <span className="text-lg shrink-0 opacity-40">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-400">{title}</span>
          <span className="text-[10px] text-gray-400 italic">Checking area data…</span>
        </div>
        <div className="h-2 w-32 bg-gray-200 rounded animate-pulse mt-1" />
      </div>
    </div>
  );
}

function AnalysisCard({ analysis, onRun, isProcessing }: {
  analysis: AvailableAnalysis;
  onRun: () => void;
  isProcessing: boolean;
}) {
  const cat = CATEGORY_META[analysis.category];
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
  const { stats, analyses, osmLoading } = inspection;

  // Separate confirmed-available from pending (still loading OSM data)
  const confirmed = analyses.filter(a => !a.pending);
  const pending   = analyses.filter(a =>  a.pending);

  // Build category tabs only from categories that have confirmed analyses
  const presentCategories = Array.from(new Set(confirmed.map(a => a.category)));
  const showTabs = presentCategories.length > 1;

  const [activeCategory, setActiveCategory] = useState<string>('all');

  const filteredConfirmed = activeCategory === 'all'
    ? confirmed
    : confirmed.filter(a => a.category === activeCategory);

  // Default to first analysis for "Run Full Assessment" button
  const defaultAnalysis = confirmed[0];

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
            {' · '}{stats.perimeterKm.toFixed(1)} km perimeter
          </p>
        </div>
        <button
          onClick={onClearAoi}
          className="text-green-200 hover:text-white text-xs border border-green-500 hover:border-white rounded px-2 py-0.5 transition-colors"
        >
          ✕ Clear
        </button>
      </div>

      {/* ── GIS Feature Counts ── */}
      <div className="px-3 py-3 border-b border-gray-100 shrink-0">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          GIS Features in Area
          {osmLoading && (
            <span className="ml-1 text-gray-400 font-normal normal-case">(loading…)</span>
          )}
        </p>
        <div className="grid grid-cols-2 gap-2">
          <StatCard label="Buildings"      value={stats.buildings}  unit="structures" icon="🏠" loading={osmLoading} />
          <StatCard label="Roads"          value={stats.roadKm}     unit="km"         icon="🛣️" loading={osmLoading} />
          <StatCard label="Rivers/Streams" value={stats.waterwayKm} unit="km"         icon="🌊" loading={osmLoading} />
          <StatCard label="Parks/Reserves" value={stats.parks}      unit="areas"      icon="🌿" loading={osmLoading} />
        </div>
      </div>

      {/* ── Bbox coords ── */}
      <div className="px-3 py-1.5 border-b border-gray-100 shrink-0">
        <p className="text-[10px] text-gray-400 font-mono">
          {stats.bbox[1].toFixed(3)}°S {stats.bbox[0].toFixed(3)}°E →{' '}
          {stats.bbox[3].toFixed(3)}°S {stats.bbox[2].toFixed(3)}°E
        </p>
      </div>

      {/* ── Available Analyses ── */}
      <div className="flex flex-col flex-1 min-h-0">
        <div className="px-3 pt-3 pb-2 shrink-0">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Available for This Area
            {osmLoading && pending.length > 0 && (
              <span className="ml-1 font-normal text-gray-400 normal-case">
                (+{pending.length} checking…)
              </span>
            )}
          </p>

          {/* Category filter tabs — only show if multiple categories present */}
          {showTabs && (
            <div className="flex gap-1 flex-wrap mb-1">
              <button
                onClick={() => setActiveCategory('all')}
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full transition-colors ${
                  activeCategory === 'all'
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                All ({confirmed.length})
              </button>
              {presentCategories.map(cat => {
                const count = confirmed.filter(a => a.category === cat).length;
                const meta = CATEGORY_META[cat];
                return (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full transition-colors ${
                      activeCategory === cat
                        ? meta.badgeColor
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {meta.label} ({count})
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Scrollable analysis list */}
        <div className="overflow-y-auto flex-1 px-2 pb-3 space-y-0.5">
          {filteredConfirmed.length === 0 && !osmLoading && (
            <div className="text-center text-xs text-gray-400 py-6">
              No analyses available for this filter.
            </div>
          )}

          {filteredConfirmed.map(analysis => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              onRun={() => onRunAnalysis(analysis.id)}
              isProcessing={isProcessing}
            />
          ))}

          {/* Pending (OSM-dependent) cards shown only while loading */}
          {osmLoading && pending.map(a => (
            <PendingCard key={a.id} title={a.title} icon={a.icon} />
          ))}
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="px-3 py-2.5 border-t border-gray-100 bg-gray-50 flex gap-2 shrink-0">
        <button
          onClick={() => onRunAnalysis(defaultAnalysis?.id ?? 'development-suitability')}
          disabled={isProcessing || !defaultAnalysis}
          className="flex-1 py-1.5 text-xs font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
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
