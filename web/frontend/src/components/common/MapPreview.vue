<script setup lang="ts">
/**
 * MapPreview — Lightweight interactive GIS data visualization component.
 *
 * Renders GeoJSON and WKT data on an interactive map using OpenLayers (loaded
 * via CDN to avoid heavy npm dependency). Supports multiple layers with
 * individual visibility toggles. Falls back to a styled JSON preview if the
 * map library is not available.
 *
 * Props:
 *   geojson — A GeoJSON FeatureCollection (or single Feature / Geometry).
 *   layers  — Array of layer objects for multi-layer display.
 *   height  — Map container height in pixels (default: 400).
 *   title   — Optional title displayed in the header.
 */
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

export interface MapLayer {
  name: string
  type: 'geojson' | 'wkt'
  data: any
  visible?: boolean
  color?: string
}

const props = withDefaults(
  defineProps<{
    geojson?: Record<string, any> | null
    layers?: MapLayer[]
    height?: number
    title?: string
  }>(),
  { height: 400, title: '', geojson: null },
)

const mapContainer = ref<HTMLDivElement | null>(null)
const mapReady = ref(false)
const mapError = ref('')
const featureCount = ref(0)
const bboxInfo = ref('')
const showLayerPanel = ref(false)

// Internal layer state for visibility management
const layerStates = ref<{ name: string; visible: boolean; color: string; featureCount: number }[]>([])

let mapInstance: any = null
const vectorLayers: Map<string, any> = new Map()
const vectorSources: Map<string, any> = new Map()

// ── Color palette for multi-layer styling ────────────────────────────────────

const LAYER_COLORS = [
  '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399',
  '#1abc9c', '#9b59b6', '#e74c3c', '#3498db', '#2ecc71',
]

// ── OpenLayers CDN configuration ─────────────────────────────────────────────

const OL_VERSION = '8.2.0'
const OL_CSS = `https://cdn.jsdelivr.net/npm/ol@${OL_VERSION}/ol.css`
const OL_JS = `https://cdn.jsdelivr.net/npm/ol@${OL_VERSION}/dist/ol.js`

function loadCSS(url: string): Promise<void> {
  return new Promise((resolve) => {
    if (document.querySelector(`link[href="${url}"]`)) {
      resolve()
      return
    }
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = url
    link.onload = () => resolve()
    link.onerror = () => resolve() // non-fatal
    document.head.appendChild(link)
  })
}

function loadScript(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).ol) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = url
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load ${url}`))
    document.head.appendChild(script)
  })
}

async function ensureOL(): Promise<any> {
  await loadCSS(OL_CSS)
  await loadScript(OL_JS)
  return (window as any).ol
}

// ── Effective layers: combine geojson prop + layers prop ────────────────────

const effectiveLayers = computed<MapLayer[]>(() => {
  if (props.layers && props.layers.length > 0) {
    return props.layers
  }
  if (props.geojson) {
    return [{ name: 'data', type: 'geojson' as const, data: props.geojson, visible: true }]
  }
  return []
})

// ── Map initialization ──────────────────────────────────────────────────────

async function initMap() {
  if (!mapContainer.value) return

  try {
    const ol = await ensureOL()
    if (!ol) {
      mapError.value = 'OpenLayers library not available'
      return
    }

    // Create map with OSM base layer
    mapInstance = new ol.Map({
      target: mapContainer.value,
      layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM(),
        }),
      ],
      view: new ol.View({
        center: ol.proj.fromLonLat([104.0, 35.0]), // Center of China
        zoom: 4,
      }),
      controls: ol.control.defaults.defaults().extend([
        new ol.control.ScaleLine(),
      ]),
    })

    mapReady.value = true

    // If there's already data, render it
    if (effectiveLayers.value.length > 0) {
      renderAllLayers()
    }
  } catch (err: any) {
    mapError.value = err.message || 'Failed to initialize map'
  }
}

function createLayerStyle(color: string) {
  const ol = (window as any).ol
  if (!ol) return null

  return new ol.style.Style({
    fill: new ol.style.Fill({ color: hexToRgba(color, 0.25) }),
    stroke: new ol.style.Stroke({ color, width: 2 }),
    image: new ol.style.Circle({
      radius: 6,
      fill: new ol.style.Fill({ color }),
      stroke: new ol.style.Stroke({ color: '#fff', width: 2 }),
    }),
  })
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function parseWktToFeatures(wktString: string, ol: any): any[] {
  try {
    const format = new ol.format.WKT()
    const feature = format.readFeature(wktString, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })
    return feature ? [feature] : []
  } catch {
    return []
  }
}

function renderAllLayers() {
  if (!mapInstance) return
  const ol = (window as any).ol
  if (!ol) return

  // Remove existing vector layers
  for (const layer of vectorLayers.values()) {
    mapInstance.removeLayer(layer)
  }
  vectorLayers.clear()
  vectorSources.clear()

  const states: typeof layerStates.value = []
  let totalFeatures = 0
  const allExtents: number[][] = []

  effectiveLayers.value.forEach((layerDef, index) => {
    const color = layerDef.color || LAYER_COLORS[index % LAYER_COLORS.length]
    const isVisible = layerDef.visible !== false
    const source = new ol.source.Vector()
    let layerFeatureCount = 0

    try {
      if (layerDef.type === 'wkt' && typeof layerDef.data === 'string') {
        const features = parseWktToFeatures(layerDef.data, ol)
        source.addFeatures(features)
        layerFeatureCount = features.length
      } else if (layerDef.type === 'geojson') {
        const format = new ol.format.GeoJSON()
        const features = format.readFeatures(layerDef.data, {
          featureProjection: 'EPSG:3857',
        })
        source.addFeatures(features)
        layerFeatureCount = features.length
      }
    } catch (err: any) {
      console.warn(`Failed to parse layer "${layerDef.name}":`, err)
    }

    totalFeatures += layerFeatureCount

    const vectorLayer = new ol.layer.Vector({
      source,
      style: createLayerStyle(color),
      visible: isVisible,
    })

    mapInstance.addLayer(vectorLayer)
    vectorLayers.set(layerDef.name, vectorLayer)
    vectorSources.set(layerDef.name, source)

    // Collect extent for fitting
    if (layerFeatureCount > 0 && isVisible) {
      const extent = source.getExtent()
      if (extent && extent[0] !== Infinity) {
        allExtents.push(extent)
      }
    }

    states.push({
      name: layerDef.name,
      visible: isVisible,
      color,
      featureCount: layerFeatureCount,
    })
  })

  layerStates.value = states
  featureCount.value = totalFeatures

  // Fit view to combined extent
  if (allExtents.length > 0) {
    const combined = allExtents.reduce(
      (acc, ext) => [
        Math.min(acc[0], ext[0]),
        Math.min(acc[1], ext[1]),
        Math.max(acc[2], ext[2]),
        Math.max(acc[3], ext[3]),
      ],
      [Infinity, Infinity, -Infinity, -Infinity],
    )

    if (combined[0] !== Infinity) {
      mapInstance.getView().fit(combined, {
        padding: [40, 40, 40, 40],
        maxZoom: 16,
        duration: 500,
      })

      const bboxWgs84 = ol.proj.transformExtent(combined, 'EPSG:3857', 'EPSG:4326')
      bboxInfo.value = `[${bboxWgs84.map((v: number) => v.toFixed(4)).join(', ')}]`
    }
  }
}

function toggleLayerVisibility(layerName: string) {
  const layer = vectorLayers.get(layerName)
  const state = layerStates.value.find((s) => s.name === layerName)
  if (layer && state) {
    state.visible = !state.visible
    layer.setVisible(state.visible)
  }
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

watch(
  () => [props.geojson, props.layers],
  () => {
    if (mapReady.value) {
      renderAllLayers()
    }
  },
  { deep: true },
)

onMounted(async () => {
  await nextTick()
  await initMap()
})

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.setTarget(undefined)
    mapInstance = null
  }
  vectorLayers.clear()
  vectorSources.clear()
})
</script>

<template>
  <div class="map-preview">
    <!-- Header -->
    <div class="map-header">
      <span class="map-title">{{ title || t('mapPreview.title') }}</span>
      <div class="map-header-actions">
        <div v-if="featureCount > 0" class="map-info">
          <el-tag size="small" type="info">
            {{ t('mapPreview.features', { count: featureCount }) }}
          </el-tag>
          <el-tag v-if="bboxInfo" size="small" effect="plain">
            {{ t('mapPreview.bbox') }}: {{ bboxInfo }}
          </el-tag>
        </div>
        <el-button
          v-if="layerStates.length > 1"
          size="small"
          text
          @click="showLayerPanel = !showLayerPanel"
        >
          🗂️ {{ t('mapPreview.layers') }} ({{ layerStates.length }})
        </el-button>
      </div>
    </div>

    <!-- Map Container -->
    <div v-if="!mapError" class="map-wrapper" :style="{ height: `${height}px` }">
      <div ref="mapContainer" class="map-container" :style="{ height: `${height}px` }" />

      <!-- Layer Control Panel -->
      <transition name="layer-panel-fade">
        <div v-if="showLayerPanel && layerStates.length > 1" class="layer-control-panel">
          <div class="layer-panel-header">
            <span class="layer-panel-title">{{ t('mapPreview.layerControl') }}</span>
          </div>
          <div class="layer-panel-list">
            <div
              v-for="state in layerStates"
              :key="state.name"
              class="layer-item"
              @click="toggleLayerVisibility(state.name)"
            >
              <span class="layer-color-dot" :style="{ background: state.visible ? state.color : '#ccc' }" />
              <span class="layer-name" :class="{ dimmed: !state.visible }">
                {{ state.name }}
              </span>
              <span class="layer-count">({{ state.featureCount }})</span>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- Error Fallback -->
    <div v-else class="map-fallback">
      <p class="fallback-message">{{ mapError }}</p>
      <p class="fallback-hint">{{ t('mapPreview.fallbackHint') }}</p>
      <pre v-if="geojson" class="json-preview">{{ JSON.stringify(geojson, null, 2) }}</pre>
    </div>

    <!-- No Data State -->
    <div v-if="effectiveLayers.length === 0 && mapReady" class="map-empty">
      <p>{{ t('mapPreview.noData') }}</p>
    </div>
  </div>
</template>

<style scoped>
.map-preview {
  border: 1px solid var(--gp-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--gp-bg-elevated);
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--gp-bg-secondary);
  border-bottom: 1px solid var(--gp-border-light);
}

.map-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.map-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.map-info {
  display: flex;
  gap: 6px;
}

.map-wrapper {
  position: relative;
  width: 100%;
}

.map-container {
  width: 100%;
  min-height: 200px;
}

.map-container :deep(.ol-viewport) {
  border-radius: 0;
}

/* ── Layer Control Panel ── */
.layer-control-panel {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--gp-bg-elevated);
  border: 1px solid var(--gp-border-color);
  border-radius: 6px;
  box-shadow: var(--gp-shadow-md);
  min-width: 160px;
  max-width: 240px;
  z-index: 10;
  overflow: hidden;
}

.layer-panel-header {
  padding: 6px 10px;
  background: var(--gp-bg-secondary);
  border-bottom: 1px solid var(--gp-border-light);
}

.layer-panel-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.layer-panel-list {
  padding: 4px 0;
  max-height: 200px;
  overflow-y: auto;
}

.layer-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 12px;
}

.layer-item:hover {
  background: var(--gp-hover-bg);
}

.layer-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.2s;
}

.layer-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--gp-text-primary);
  transition: opacity 0.2s;
}

.layer-name.dimmed {
  opacity: 0.4;
  text-decoration: line-through;
}

.layer-count {
  color: var(--gp-text-muted);
  font-size: 11px;
  flex-shrink: 0;
}

.layer-panel-fade-enter-active,
.layer-panel-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.layer-panel-fade-enter-from,
.layer-panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.map-fallback {
  padding: 20px;
  text-align: center;
}

.fallback-message {
  color: var(--gp-text-secondary);
  margin-bottom: 8px;
}

.fallback-hint {
  font-size: 12px;
  color: var(--gp-text-muted);
}

.json-preview {
  text-align: left;
  max-height: 300px;
  overflow: auto;
  background: var(--gp-code-bg);
  color: #e5eaf3;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 12px;
}

.map-empty {
  padding: 40px;
  text-align: center;
  color: var(--gp-text-muted);
  font-size: 13px;
}
</style>
