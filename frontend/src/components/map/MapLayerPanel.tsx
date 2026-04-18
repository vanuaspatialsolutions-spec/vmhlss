import { useAuthStore, useUIStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';

const layerGroups = [
  {
    category: 'hazard',
    label: 'mapquery.hazard',
    layers: [
      { id: 'cyclone', label: 'Cyclone Risk' },
      { id: 'tsunami', label: 'Tsunami Risk' },
      { id: 'volcanic', label: 'Volcanic Risk' },
      { id: 'flood', label: 'Flood Risk' },
      { id: 'earthquake', label: 'Earthquake Risk' },
      { id: 'landslide', label: 'Landslide Risk' },
    ],
  },
  {
    category: 'suitability',
    label: 'mapquery.suitability',
    layers: [
      { id: 'suitability', label: 'Suitability Results' },
      { id: 'chi', label: 'CHI Index' },
    ],
  },
  {
    category: 'lulc',
    label: 'mapquery.lulc',
    layers: [{ id: 'lulc', label: 'Land Use / Land Cover' }],
  },
  {
    category: 'admin',
    label: 'mapquery.boundaries',
    layers: [{ id: 'boundaries', label: 'Administrative Boundaries' }],
  },
  {
    category: 'kb',
    label: 'mapquery.knowledge',
    layers: [{ id: 'knowledgeBase', label: 'Knowledge Base Points' }],
  },
];

export default function MapLayerPanel() {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { mapLayers, toggleLayer } = useUIStore();

  return (
    <div className="p-4">
      <h3 className="font-bold text-gray-900 mb-4">{t('mapquery.layers')}</h3>

      <div className="space-y-4">
        {layerGroups.map((group) => (
          <div key={group.category}>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              {t(group.label)}
            </h4>
            <div className="space-y-2 ml-2">
              {group.layers.map((layer) => (
                <label key={layer.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={mapLayers[layer.id] || false}
                    onChange={() => toggleLayer(layer.id)}
                    className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="text-sm text-gray-700">{layer.label}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
