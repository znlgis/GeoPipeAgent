<script setup lang="ts">
/**
 * MapPreview — Lightweight interactive GIS data visualization component.
 *
 * Renders GeoJSON data on an interactive map using OpenLayers (loaded via CDN
 * to avoid heavy npm dependency). Falls back to a styled JSON preview if the
 * map library is not available.
 *
 * Props:
 *   geojson — A GeoJSON FeatureCollection (or single Feature / Geometry).
 *   height  — Map container height in pixels (default: 400).
 */
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    geojson: Record<string, any> | null
    height?: number
    title?: string
  }>(),
  { height: 400, title: '' },
)

const mapContainer = ref<HTMLDivElement | null>(null)
const mapReady = ref(false)
const mapError = ref('')
const featureCount = ref(0)
const bboxInfo = ref('')

let mapInstance: any = null
let vectorSource: any = null

// ── Dynamically load OpenLayers from CDN ────────────────────────────────────

const OL_CSS = 'https://cdn.jsdelivr.net/npm/ol@8.2.0/ol.css'
const OL_JS = 'https://cdn.jsdelivr.net/npm/ol@8.2.0/dist/ol.js'

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

// ── Map initialization ──────────────────────────────────────────────────────

async function initMap() {
  if (!mapContainer.value) return

  try {
    const ol = await ensureOL()
    if (!ol) {
      mapError.value = 'OpenLayers library not available'
      return
    }

    // Create vector source
    vectorSource = new ol.source.Vector()

    // Style function for features
    const defaultStyle = new ol.style.Style({
      fill: new ol.style.Fill({ color: 'rgba(64, 158, 255, 0.25)' }),
      stroke: new ol.style.Stroke({ color: '#409eff', width: 2 }),
      image: new ol.style.Circle({
        radius: 6,
        fill: new ol.style.Fill({ color: '#409eff' }),
        stroke: new ol.style.Stroke({ color: '#fff', width: 2 }),
      }),
    })

    const vectorLayer = new ol.layer.Vector({
      source: vectorSource,
      style: defaultStyle,
    })

    // Create map
    mapInstance = new ol.Map({
      target: mapContainer.value,
      layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM(),
        }),
        vectorLayer,
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
    if (props.geojson) {
      renderGeoJSON(props.geojson)
    }
  } catch (err: any) {
    mapError.value = err.message || 'Failed to initialize map'
  }
}

function renderGeoJSON(data: Record<string, any>) {
  if (!vectorSource || !mapInstance) return

  const ol = (window as any).ol
  if (!ol) return

  vectorSource.clear()

  try {
    const format = new ol.format.GeoJSON()
    const features = format.readFeatures(data, {
      featureProjection: 'EPSG:3857',
    })

    vectorSource.addFeatures(features)
    featureCount.value = features.length

    // Fit view to features
    if (features.length > 0) {
      const extent = vectorSource.getExtent()
      if (extent && extent[0] !== Infinity) {
        mapInstance.getView().fit(extent, {
          padding: [40, 40, 40, 40],
          maxZoom: 16,
          duration: 500,
        })

        // Calculate bbox info in WGS84
        const bboxWgs84 = ol.proj.transformExtent(extent, 'EPSG:3857', 'EPSG:4326')
        bboxInfo.value = `[${bboxWgs84.map((v: number) => v.toFixed(4)).join(', ')}]`
      }
    }
  } catch (err: any) {
    mapError.value = err.message || 'Invalid GeoJSON data'
  }
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

watch(
  () => props.geojson,
  (newData) => {
    if (newData && mapReady.value) {
      renderGeoJSON(newData)
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
})
</script>

<template>
  <div class="map-preview">
    <!-- Header -->
    <div class="map-header">
      <span class="map-title">{{ title || t('mapPreview.title') }}</span>
      <div v-if="featureCount > 0" class="map-info">
        <el-tag size="small" type="info">
          {{ t('mapPreview.features', { count: featureCount }) }}
        </el-tag>
        <el-tag v-if="bboxInfo" size="small" effect="plain">
          {{ t('mapPreview.bbox') }}: {{ bboxInfo }}
        </el-tag>
      </div>
    </div>

    <!-- Map Container -->
    <div
      v-if="!mapError"
      ref="mapContainer"
      class="map-container"
      :style="{ height: `${height}px` }"
    />

    <!-- Error Fallback -->
    <div v-else class="map-fallback">
      <p class="fallback-message">{{ mapError }}</p>
      <p class="fallback-hint">{{ t('mapPreview.fallbackHint') }}</p>
      <pre v-if="geojson" class="json-preview">{{ JSON.stringify(geojson, null, 2) }}</pre>
    </div>

    <!-- No Data State -->
    <div v-if="!geojson && mapReady" class="map-empty">
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

.map-info {
  display: flex;
  gap: 6px;
}

.map-container {
  width: 100%;
  min-height: 200px;
}

.map-container :deep(.ol-viewport) {
  border-radius: 0;
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
