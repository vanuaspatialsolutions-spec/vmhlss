/**
 * HazardAnalysisPanel — comprehensive multi-hazard results panel.
 *
 * Methodology from:
 *   Kim et al. (2025) Multi-Hazard Susceptibility Mapping Using ML (Remote Sensing)
 *   Sharma & Miyazaki (2019) Multi-Hazard Risk AHP (GI4DM / ISPRS Archives)
 *
 * Tabs: Overview | Hazards | AHP & Feature Charts | Model Performance
 */

import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line,
} from 'recharts';
import type { Analysis } from '../../types/index';
import type {
  HazardSusceptibilityScore,
  ModelPerformanceMetric,
  AHPCriterionWeight,
  FeatureImportanceEntry,
  CoverageStatRow,
  EnhancedAnalysisData,
} from '../../services/localEngine';

type EnhancedAnalysis = Analysis & EnhancedAnalysisData;

interface Props {
  analysis: EnhancedAnalysis;
  onClearAoi:     () => void;
  onRunAnalysis:  (analysisId: string) => void;
  onGoToReports:  () => void;
  isProcessing:   boolean;
}

type Tab = 'overview' | 'hazards' | 'charts' | 'model';

// ── Helpers ────────────────────────────────────────────────────────────────

const LEVEL_COLORS = {
  Low:         { bg: '#dcfce7', text: '#166534', bar: '#16a34a' },
  Moderate:    { bg: '#fef9c3', text: '#854d0e', bar: '#ca8a04' },
  High:        { bg: '#ffedd5', text: '#9a3412', bar: '#ea580c' },
  'Very High': { bg: '#fee2e2', text: '#991b1b', bar: '#dc2626' },
} as const;

const CLASS_COLORS: Record<string, { color: string; bg: string; label: string }> = {
  S1: { color: '#166534', bg: '#dcfce7', label: 'Highly Suitable'        },
  S2: { color: '#16a34a', bg: '#bbf7d0', label: 'Moderately Suitable'    },
  S3: { color: '#ca8a04', bg: '#fef9c3', label: 'Marginally Suitable'    },
  S4: { color: '#ea580c', bg: '#ffedd5', label: 'Currently Unsuitable'   },
  S5: { color: '#991b1b', bg: '#fee2e2', label: 'Permanently Unsuitable' },
};

/** Generate synthetic ROC curve data from AUC (Paper 1 Figure approach) */
function rocCurveData(rocAuc: number): { fpr: number; tpr: number }[] {
  const pts: { fpr: number; tpr: number }[] = [{ fpr: 0, tpr: 0 }];
  for (let i = 1; i <= 20; i++) {
    const fpr = i / 20;
    // Bow the curve proportional to AUC
    const tpr = Math.min(1, fpr + (2 * rocAuc - 1) * Math.sqrt(fpr * (1 - fpr)) * 2.5);
    pts.push({ fpr, tpr: Math.max(fpr, tpr) });
  }
  pts.push({ fpr: 1, tpr: 1 });
  return pts;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function HazardCard({ h }: { h: HazardSusceptibilityScore }) {
  const c = LEVEL_COLORS[h.level];
  return (
    <div
      className="rounded-xl border p-3 flex flex-col gap-1.5"
      style={{ borderColor: c.bar + '55', background: c.bg }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-base">{h.icon}</span>
          <span className="text-xs font-bold text-gray-800">{h.name}</span>
        </div>
        <span
          className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-full"
          style={{ background: c.bar, color: '#fff' }}
        >
          {h.level.toUpperCase().replace(' ', '\u00A0')}
        </span>
      </div>
      {/* Score bar */}
      <div className="h-1.5 rounded-full bg-white/60 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${h.score}%`, background: c.bar }}
        />
      </div>
      <p className="text-[10px] leading-snug" style={{ color: c.text }}>{h.description}</p>
      <span className="text-[10px] font-mono self-end" style={{ color: c.text }}>
        Score: {h.score}/100
      </span>
    </div>
  );
}

function OverviewTab({ analysis }: { analysis: EnhancedAnalysis }) {
  const total   = analysis.results?.length ?? 0;
  const stats   = (analysis as EnhancedAnalysis).coverageStats as CoverageStatRow[] | undefined ?? [];
  const areaKm2 = (analysis as EnhancedAnalysis).aoiAreaKm2 ?? 0;
  const suitablePct = stats
    .filter(s => s.cls === 'S1' || s.cls === 'S2')
    .reduce((sum, s) => sum + s.pct, 0);
  const topHazardLevel = (analysis as EnhancedAnalysis).hazardSusceptibility?.[0]?.level ?? 'High';

  return (
    <div className="space-y-3 px-3 py-3">
      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Grid Cells',  value: total,                        unit: 'pts' },
          { label: 'Area',        value: areaKm2.toFixed(1),           unit: 'km²' },
          { label: 'S1+S2 Zone',  value: `${suitablePct}%`,            unit: 'suitable' },
        ].map(k => (
          <div key={k.label} className="bg-green-50 rounded-lg p-2 text-center">
            <div className="text-lg font-extrabold text-green-800 leading-none">{k.value}</div>
            <div className="text-[9px] text-green-600 mt-0.5">{k.unit}</div>
            <div className="text-[9px] text-gray-500">{k.label}</div>
          </div>
        ))}
      </div>

      {/* Suitability breakdown — Paper 2 coverage table style */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
          Suitability Classification (FAO S1–S5)
        </p>
        <div className="space-y-1.5">
          {Object.entries(CLASS_COLORS).map(([cls, { color, bg, label }]) => {
            const row = stats.find(s => s.cls === cls);
            const count   = row?.count   ?? analysis.results?.filter(r => r.suitabilityClass === cls).length ?? 0;
            const pct     = row?.pct     ?? Math.round((count / Math.max(total, 1)) * 100);
            const areaVal = row?.areaKm2 ?? parseFloat((areaKm2 * count / Math.max(total, 1)).toFixed(2));
            if (count === 0) return null;
            return (
              <div key={cls} className="flex items-center gap-2">
                <span
                  className="text-[10px] font-bold w-7 text-center rounded py-0.5 shrink-0"
                  style={{ color, background: bg }}
                >
                  {cls}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs text-gray-700 truncate">{label}</span>
                    <span className="text-[10px] text-gray-400 ml-1 shrink-0">
                      {areaVal} km² · {pct}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, background: color }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Key finding callout — Paper 2 style impact statement */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-800">
        <span className="font-bold">📋 Key Finding: </span>
        {suitablePct >= 60
          ? `${suitablePct}% of the area shows S1/S2 (high/moderate) suitability. ${topHazardLevel === 'Very High' || topHazardLevel === 'High' ? 'Cyclone and earthquake hazards require mitigation measures in development plans.' : 'Hazard risk is manageable with standard engineering controls.'}`
          : `Only ${suitablePct}% meets S1/S2 suitability thresholds. Multi-hazard AHP analysis (Paper 2 methodology) indicates ${100 - suitablePct}% of cells require hazard mitigation or are unsuitable for the intended land use.`
        }
      </div>

      {/* AHP note */}
      <p className="text-[9px] text-gray-400 italic leading-snug">
        Classification uses FAO land suitability framework with AHP-weighted multi-hazard
        criteria (Sharma &amp; Miyazaki 2019). Multi-hazard consideration reduces suitable
        area by ~14% compared to general AHP (no-hazard baseline).
      </p>
    </div>
  );
}

function HazardsTab({ hazards }: { hazards: HazardSusceptibilityScore[] }) {
  return (
    <div className="px-3 py-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
        Hazard Susceptibility Levels
        <span className="normal-case font-normal text-gray-400 ml-1">
          (Low → Moderate → High → Very High)
        </span>
      </p>
      <div className="grid grid-cols-2 gap-2">
        {hazards.map(h => <HazardCard key={h.hazardId} h={h} />)}
      </div>
      <p className="text-[9px] text-gray-400 italic mt-2 leading-snug">
        Susceptibility levels derived from Vanuatu geographic proximity to hazard
        sources (Kim et al. 2025 methodology: XGB/RF models + AHP expert weighting).
      </p>
    </div>
  );
}

function ChartsTab({
  ahpWeights,
  featureImportance,
}: {
  ahpWeights: AHPCriterionWeight[];
  featureImportance: FeatureImportanceEntry[];
}) {
  const [selectedHazard, setSelectedHazard] = useState('cyclone-risk');

  const HAZARD_OPTIONS = [
    { id: 'cyclone-risk',          label: '🌀 Cyclone'    },
    { id: 'flood-risk',            label: '🌊 Flood'      },
    { id: 'volcanic-hazard',       label: '🌋 Volcanic'   },
    { id: 'earthquake-hazard',     label: '📳 Earthquake' },
    { id: 'landslide-risk',        label: '🏔️ Landslide'  },
    { id: 'tsunami-vulnerability', label: '🌊 Tsunami'    },
  ];

  // Paper 2 Figure 3/6/9/11 — AHP criteria weight comparison
  const ahpChartData = ahpWeights.map(w => ({
    name: w.criterion.length > 10 ? w.criterion.slice(0, 9) + '…' : w.criterion,
    'General AHP':    parseFloat((w.generalAhp * 100).toFixed(1)),
    'Multi-Haz. AHP': parseFloat((w.multiHazardAhp * 100).toFixed(1)),
  }));

  // Paper 1 Table 6 — feature importance for selected hazard
  const featData = featureImportance
    .filter(f => f.hazardId === selectedHazard)
    .sort((a, b) => b.importance - a.importance)
    .map(f => ({
      name:       f.feature.length > 18 ? f.feature.slice(0, 17) + '…' : f.feature,
      importance: parseFloat((f.importance * 100).toFixed(1)),
    }));

  return (
    <div className="px-3 py-3 space-y-4">

      {/* AHP Weight Comparison — Paper 2 methodology */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
          AHP Criteria Weights (%)
        </p>
        <p className="text-[9px] text-gray-400 mb-2">
          Shift from General AHP to Multi-Hazard AHP (Sharma &amp; Miyazaki 2019, Fig. 3)
        </p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart
            data={ahpChartData}
            margin={{ top: 4, right: 4, bottom: 20, left: -10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 8, fill: '#6b7280' }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              tick={{ fontSize: 8, fill: '#6b7280' }}
              domain={[0, 32]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v: number) => [`${v}%`]}
              contentStyle={{ fontSize: 10, borderRadius: 6 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 9, paddingTop: 4 }}
              iconSize={8}
            />
            <Bar dataKey="General AHP"    fill="#0ea5e9" radius={[2, 2, 0, 0]} maxBarSize={18} />
            <Bar dataKey="Multi-Haz. AHP" fill="#f97316" radius={[2, 2, 0, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Feature Importance — Paper 1 Table 6 */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            Feature Importance (%)
          </p>
          <select
            value={selectedHazard}
            onChange={e => setSelectedHazard(e.target.value)}
            className="text-[9px] border border-gray-200 rounded px-1 py-0.5 bg-white text-gray-700"
          >
            {HAZARD_OPTIONS.map(o => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        </div>
        <p className="text-[9px] text-gray-400 mb-1.5">
          Key predictive variables (Kim et al. 2025, RF/XGB variable importance)
        </p>
        <ResponsiveContainer width="100%" height={130}>
          <BarChart
            layout="vertical"
            data={featData}
            margin={{ top: 2, right: 20, bottom: 2, left: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 8, fill: '#6b7280' }}
              domain={[0, 50]}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fontSize: 8, fill: '#4b5563' }}
              width={90}
            />
            <Tooltip
              formatter={(v: number) => [`${v}%`, 'Importance']}
              contentStyle={{ fontSize: 10, borderRadius: 6 }}
            />
            <Bar
              dataKey="importance"
              fill="#10b981"
              radius={[0, 2, 2, 0]}
              maxBarSize={12}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ModelTab({ metrics }: { metrics: ModelPerformanceMetric[] }) {
  const [rocHazard, setRocHazard] = useState('cyclone-risk');
  const selected = metrics.find(m => m.hazardId === rocHazard) ?? metrics[0];

  const rocData = selected ? rocCurveData(selected.rocAuc) : [];
  const diagData = [{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }];

  const MODEL_COLOR: Record<string, string> = {
    XGB: '#7c3aed', RF: '#0ea5e9', AHP: '#f97316',
  };

  return (
    <div className="px-3 py-3 space-y-3">

      {/* Performance metrics table — Paper 1 Table 5 style */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
          Model Performance Metrics
        </p>
        <p className="text-[9px] text-gray-400 mb-1.5">
          Adapted from Kim et al. (2025) Table 5 — RF/XGB/AHP accuracy metrics
        </p>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-[9px] border-collapse">
            <thead>
              <tr className="bg-green-700 text-white">
                {['Hazard', 'Model', 'Acc', 'Prec', 'Rec', 'F1', 'AUC'].map(h => (
                  <th key={h} className="px-1.5 py-1.5 text-left font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metrics.map((m, i) => (
                <tr
                  key={m.hazardId}
                  className={`${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} cursor-pointer hover:bg-green-50 transition-colors`}
                  onClick={() => setRocHazard(m.hazardId)}
                >
                  <td className="px-1.5 py-1 font-medium text-gray-800 truncate max-w-[70px]">{m.name}</td>
                  <td className="px-1.5 py-1">
                    <span
                      className="font-bold px-1 py-0.5 rounded text-white text-[8px]"
                      style={{ background: MODEL_COLOR[m.model] }}
                    >
                      {m.model}
                    </span>
                  </td>
                  <td className="px-1.5 py-1 text-gray-700">{m.accuracy.toFixed(2)}</td>
                  <td className="px-1.5 py-1 text-gray-700">{m.precision.toFixed(2)}</td>
                  <td className="px-1.5 py-1 text-gray-700">{m.recall.toFixed(2)}</td>
                  <td className="px-1.5 py-1 text-gray-700">{m.f1Score.toFixed(2)}</td>
                  <td className="px-1.5 py-1 font-semibold text-green-700">{m.rocAuc.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[9px] text-gray-400 mt-1">Click a row to view its ROC curve below.</p>
      </div>

      {/* ROC Curve — Paper 1 Figure 4 style */}
      {selected && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            ROC Curve — {selected.name}
          </p>
          <p className="text-[9px] text-gray-400 mb-1.5">
            Model: <span className="font-bold" style={{ color: MODEL_COLOR[selected.model] }}>{selected.model}</span>
            &nbsp;· AUC = <span className="font-bold text-green-700">{selected.rocAuc.toFixed(3)}</span>
          </p>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart margin={{ top: 4, right: 8, bottom: 20, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis
                dataKey="fpr"
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={{ fontSize: 8, fill: '#6b7280' }}
                label={{ value: 'FPR', position: 'insideBottom', offset: -12, fontSize: 9, fill: '#6b7280' }}
              />
              <YAxis
                type="number"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(1)}
                tick={{ fontSize: 8, fill: '#6b7280' }}
                label={{ value: 'TPR', angle: -90, position: 'insideLeft', offset: 12, fontSize: 9, fill: '#6b7280' }}
              />
              <Tooltip
                formatter={(v: number) => [v.toFixed(3)]}
                contentStyle={{ fontSize: 9, borderRadius: 6 }}
              />
              {/* Diagonal reference (random classifier) */}
              <Line
                data={diagData}
                dataKey="tpr"
                stroke="#d1d5db"
                strokeDasharray="4 3"
                dot={false}
                strokeWidth={1}
                name="Random"
              />
              {/* Model ROC curve */}
              <Line
                data={rocData}
                dataKey="tpr"
                stroke={MODEL_COLOR[selected.model]}
                dot={false}
                strokeWidth={2}
                name={`${selected.model} (AUC=${selected.rocAuc.toFixed(3)})`}
              />
              <Legend wrapperStyle={{ fontSize: 9 }} iconSize={8} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── Main panel ──────────────────────────────────────────────────────────────

export default function HazardAnalysisPanel({
  analysis,
  onClearAoi,
  onRunAnalysis,
  onGoToReports,
  isProcessing,
}: Props) {
  const [tab, setTab] = useState<Tab>('overview');

  const enh = analysis as EnhancedAnalysis;
  const hazards = enh.hazardSusceptibility ?? [];
  const metrics = enh.modelPerformance ?? [];
  const weights = enh.ahpWeights ?? [];
  const features = enh.featureImportance ?? [];
  const total   = analysis.results?.length ?? 0;
  const areaKm2 = enh.aoiAreaKm2 ?? 0;

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview',   icon: '📊' },
    { id: 'hazards',  label: 'Hazards',    icon: '⚠️' },
    { id: 'charts',   label: 'Charts',     icon: '📈' },
    { id: 'model',    label: 'Model Info', icon: '🔬' },
  ];

  return (
    <div
      className="flex flex-col bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
      style={{ width: 368, maxHeight: 'calc(100vh - 100px)' }}
    >
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-green-800 via-green-700 to-emerald-600 px-4 py-3 flex items-center justify-between shrink-0">
        <div>
          <h3 className="text-white font-bold text-sm flex items-center gap-1.5">
            🇻🇺 Multi-Hazard Land Suitability
          </h3>
          <p className="text-green-200 text-xs mt-0.5">
            {total} cells · {areaKm2.toFixed(1)} km² · AHP composite
          </p>
        </div>
        <button
          onClick={onClearAoi}
          className="text-green-200 hover:text-white text-xs border border-green-500 hover:border-white rounded px-2 py-0.5 transition-colors"
        >
          ✕ Clear
        </button>
      </div>

      {/* ── Tab Bar ── */}
      <div className="flex border-b border-gray-200 shrink-0 bg-gray-50">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-2 text-[10px] font-semibold flex flex-col items-center gap-0.5 transition-colors ${
              tab === t.id
                ? 'text-green-700 border-b-2 border-green-600 bg-white -mb-px'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
            }`}
          >
            <span className="text-sm leading-none">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ── */}
      <div className="overflow-y-auto flex-1 min-h-0">
        {tab === 'overview' && <OverviewTab analysis={enh} />}
        {tab === 'hazards'  && <HazardsTab  hazards={hazards} />}
        {tab === 'charts'   && (
          <ChartsTab ahpWeights={weights} featureImportance={features} />
        )}
        {tab === 'model'    && <ModelTab metrics={metrics} />}
      </div>

      {/* ── Footer ── */}
      <div className="px-3 py-2.5 border-t border-gray-100 bg-gray-50 flex flex-col gap-2 shrink-0">
        <div className="flex gap-2">
          <button
            onClick={onGoToReports}
            className="flex-1 py-1.5 px-3 bg-green-600 text-white rounded-lg font-semibold text-xs hover:bg-green-700 active:scale-95 transition-all flex items-center justify-center gap-1.5"
          >
            📄 Generate Report
          </button>
          <button
            onClick={() => onRunAnalysis('development-suitability')}
            disabled={isProcessing}
            className="flex-1 py-1.5 px-3 bg-blue-600 text-white rounded-lg font-semibold text-xs hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed active:scale-95 transition-all flex items-center justify-center gap-1.5"
          >
            {isProcessing ? (
              <><span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> Running…</>
            ) : (
              '▶ Re-run Analysis'
            )}
          </button>
        </div>
        <button
          onClick={onClearAoi}
          className="w-full py-1 px-3 text-gray-500 text-xs hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
        >
          ✕ Clear and Draw New Area
        </button>
      </div>
    </div>
  );
}
