import React, { useState } from 'react';
import LoadingSpinner from '../shared/LoadingSpinner';

type PersonaType = 'developer' | 'agriculture' | 'farmer' | 'gis' | 'engineer';

interface PersonaCardProps {
  personaType: PersonaType;
  content?: string;
  isLoading?: boolean;
  language?: 'en' | 'bi';
}

const PERSONA_CONFIG: Record<PersonaType, { icon: string; title: string; color: string }> = {
  developer:   { icon: '🏗️', title: 'Property Developer',      color: 'bg-blue-50 border-blue-200' },
  agriculture: { icon: '🌱', title: 'Agriculture Expert',       color: 'bg-green-50 border-green-200' },
  farmer:      { icon: '👨‍🌾', title: 'Farmer (EN + Bislama)',   color: 'bg-yellow-50 border-yellow-200' },
  gis:         { icon: '🗺️', title: 'GIS Analyst',              color: 'bg-purple-50 border-purple-200' },
  engineer:    { icon: '⚙️', title: 'Civil / Geotech Engineer', color: 'bg-orange-50 border-orange-200' },
};

// Split farmer persona into EN / Bislama sections
function splitFarmerContent(content: string) {
  const biIndex = content.toLowerCase().indexOf('bislama');
  if (biIndex === -1) return { en: content, bi: '' };
  return { en: content.slice(0, biIndex).trim(), bi: content.slice(biIndex).trim() };
}

export const PersonaCard: React.FC<PersonaCardProps> = ({
  personaType,
  content,
  isLoading = false,
  language: _language = 'en',
}) => {
  const [expanded, setExpanded] = useState(true);
  const [biExpanded, setBiExpanded] = useState(false);
  const cfg = PERSONA_CONFIG[personaType];

  const farmer = personaType === 'farmer' && content
    ? splitFarmerContent(content)
    : null;

  return (
    <div className={`rounded-lg border ${cfg.color} overflow-hidden`}>
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="flex items-center gap-2 font-semibold text-gray-800">
          <span className="text-xl">{cfg.icon}</span>
          {cfg.title}
        </span>
        <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Body */}
      {expanded && (
        <div className="px-4 pb-4 text-sm text-gray-700">
          {isLoading ? (
            <LoadingSpinner message="AI expert analysing..." size="sm" />
          ) : content ? (
            farmer ? (
              <div className="space-y-3">
                {/* English */}
                <div>
                  <p className="font-medium text-gray-500 mb-1 text-xs uppercase tracking-wide">English</p>
                  <p className="whitespace-pre-wrap leading-relaxed">{farmer.en}</p>
                </div>
                {/* Bislama toggle */}
                {farmer.bi && (
                  <div>
                    <button
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 mb-1"
                      onClick={() => setBiExpanded(!biExpanded)}
                    >
                      🌏 {biExpanded ? 'Hide' : 'Show'} Bislama
                    </button>
                    {biExpanded && (
                      <p className="whitespace-pre-wrap leading-relaxed text-gray-600 italic">
                        {farmer.bi}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
            )
          ) : (
            <p className="text-gray-400 italic">
              Select this persona and run analysis to generate advice.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default PersonaCard;
