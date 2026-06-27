const WORKSPACE_ID = 1;
const VARTOPO_CENTER = [42.658, 23.285];
const API = {
  workspace: `/map/workspaces/${WORKSPACE_ID}`,
  layers: `/map/workspaces/${WORKSPACE_ID}/layers`,
  observations: `/map/workspaces/${WORKSPACE_ID}/observations.geojson`,
  createObservation: `/map/workspaces/${WORKSPACE_ID}/observations`,
};

const familyColors = {
  poaceae: "#82c91e",
  fabaceae: "#2f9e44",
  asteraceae: "#fab005",
  amaranthaceae: "#f08c00",
  default: "#4263eb",
};

const statusColors = {
  beneficial: "#2f9e44",
  neutral: "#f2c94c",
  monitor: "#f08c00",
  aggressive: "#d9480f",
};

let observations = { type: "FeatureCollection", features: [] };
let filteredObservations = observations;
let availableMonths = [];
let activeMonth = "all";
let colorMode = "status";
let pendingLayer = null;

const map = L.map("map", {
  zoomControl: false,
}).setView(VARTOPO_CENTER, 15);

L.control.zoom({ position: "bottomright" }).addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 20,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const drawnItems = L.featureGroup().addTo(map);
const markerCluster = L.markerClusterGroup({
  showCoverageOnHover: false,
  maxClusterRadius: 42,
});
const predictionLayer = L.layerGroup();
const terrainLayer = L.layerGroup();
const moistureLayer = L.layerGroup();
const disturbanceLayer = L.layerGroup();
const experimentLayer = L.layerGroup();
const pathsLayer = L.layerGroup();
const gridLayer = L.layerGroup();
let heatLayer = L.heatLayer([], {
  radius: 28,
  blur: 18,
  maxZoom: 18,
  gradient: {
    0.2: "#2f9e44",
    0.45: "#f2c94c",
    0.7: "#f08c00",
    1: "#d9480f",
  },
});

const layerGroups = {
  observations: markerCluster,
  predicted_weeds: predictionLayer,
  terrain: terrainLayer,
  moisture: moistureLayer,
  disturbance: disturbanceLayer,
  experiment_plots: experimentLayer,
  walking_paths: pathsLayer,
  grid: gridLayer,
  heatmap: heatLayer,
};

const fallbackLayers = [
  { name: "Observations", layer_type: "observations", visible_by_default: true },
  { name: "Predicted weeds", layer_type: "predicted_weeds", visible_by_default: true },
  { name: "Terrain", layer_type: "terrain", visible_by_default: true },
  { name: "Moisture", layer_type: "moisture", visible_by_default: true },
  { name: "Disturbance", layer_type: "disturbance", visible_by_default: true },
  { name: "Experiment plots", layer_type: "experiment_plots", visible_by_default: true },
  { name: "Walking paths", layer_type: "walking_paths", visible_by_default: true },
  { name: "Grid", layer_type: "grid", visible_by_default: false },
  { name: "Heatmap", layer_type: "heatmap", visible_by_default: false },
];

const drawControl = new L.Control.Draw({
  position: "topleft",
  draw: {
    circle: false,
    circlemarker: false,
    marker: true,
    polygon: {
      allowIntersection: false,
      showArea: true,
    },
    rectangle: true,
    polyline: true,
  },
  edit: {
    featureGroup: drawnItems,
  },
});
map.addControl(drawControl);

const dialog = document.querySelector("#observationDialog");
const form = document.querySelector("#observationForm");
const layerList = document.querySelector("#layerList");
const timeSlider = document.querySelector("#timeSlider");
const timeLabel = document.querySelector("#timeLabel");

document.querySelector("#refreshButton").addEventListener("click", loadAll);
document.querySelector("#cancelObservation").addEventListener("click", () => {
  pendingLayer = null;
  dialog.close();
});

document.querySelectorAll("[data-color-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    colorMode = button.dataset.colorMode;
    document.querySelectorAll("[data-color-mode]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderObservations();
  });
});

timeSlider.addEventListener("input", () => {
  const index = Number(timeSlider.value);
  activeMonth = index === 0 ? "all" : availableMonths[index - 1];
  timeLabel.value = activeMonth === "all" ? "All dates" : formatMonthLabel(activeMonth);
  applyTimeFilter();
});

map.on(L.Draw.Event.CREATED, (event) => {
  pendingLayer = event.layer;
  form.reset();
  form.elements.observed_at.value = new Date().toISOString().slice(0, 10);
  form.elements.coverage_percent.value = 50;
  form.elements.confidence.value = 80;
  form.elements.density_class.value = "medium";
  dialog.showModal();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!pendingLayer) {
    dialog.close();
    return;
  }

  const payload = observationPayloadFromForm(new FormData(form), pendingLayer);
  const response = await fetch(API.createObservation, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    window.alert("Observation could not be saved.");
    return;
  }

  drawnItems.addLayer(pendingLayer);
  pendingLayer = null;
  dialog.close();
  await loadObservations();
});

function observationPayloadFromForm(formData, layer) {
  const feature = layer.toGeoJSON();
  const photoUrl = String(formData.get("photo_url") || "").trim();
  const thumbnailUrl = String(formData.get("thumbnail_url") || "").trim();
  const confidencePercent = Number(formData.get("confidence") || 0);
  const photos = photoUrl
    ? [
        {
          url: photoUrl,
          thumbnail_url: thumbnailUrl || photoUrl,
          taken_at: new Date().toISOString(),
        },
      ]
    : [];

  const payload = {
    observed_at: formData.get("observed_at"),
    species: formData.get("species"),
    confidence: Math.min(Math.max(confidencePercent / 100, 0), 1),
    coverage_percent: Number(formData.get("coverage_percent") || 0),
    density_class: formData.get("density_class"),
    geometry_geojson: JSON.stringify(feature.geometry),
    notes: formData.get("notes") || null,
    photos,
  };

  if (feature.geometry.type === "Point") {
    payload.longitude = feature.geometry.coordinates[0];
    payload.latitude = feature.geometry.coordinates[1];
  }

  return payload;
}

async function loadAll() {
  await Promise.all([loadWorkspace(), loadLayers(), loadObservations()]);
}

async function loadWorkspace() {
  const response = await fetch(API.workspace);
  if (!response.ok) return;
  const workspace = await response.json();
  document.querySelector("#workspaceLabel").textContent = workspace.location_label || workspace.name;
  if (workspace.center_latitude && workspace.center_longitude) {
    map.setView([workspace.center_latitude, workspace.center_longitude], workspace.default_zoom || 15);
  }
}

async function loadLayers() {
  let layers = fallbackLayers;
  const response = await fetch(API.layers);
  if (response.ok) {
    layers = await response.json();
  }
  renderLayerToggles(mergeClientLayers(layers));
}

function mergeClientLayers(serverLayers) {
  const known = new Set(serverLayers.map((layer) => layer.layer_type));
  return [
    ...serverLayers,
    ...fallbackLayers.filter((layer) => !known.has(layer.layer_type)),
  ];
}

function renderLayerToggles(layers) {
  layerList.replaceChildren();
  layers.forEach((layer) => {
    const group = layerGroups[layer.layer_type];
    if (!group) return;

    const label = document.createElement("label");
    label.className = "layer-toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(layer.visible_by_default);
    input.addEventListener("change", () => {
      if (input.checked) {
        group.addTo(map);
        renderOptionalLayer(layer.layer_type);
      } else {
        map.removeLayer(group);
      }
    });

    label.append(input, document.createTextNode(layer.name));
    layerList.append(label);

    if (input.checked) {
      group.addTo(map);
    }
  });
}

async function loadObservations() {
  const response = await fetch(API.observations);
  if (!response.ok) return;
  observations = await response.json();
  configureTimeSlider();
  applyTimeFilter();
}

function configureTimeSlider() {
  availableMonths = [
    ...new Set(
      observations.features
        .map((feature) => feature.properties?.observed_at)
        .filter(Boolean)
        .map((dateText) => dateText.slice(0, 7)),
    ),
  ].sort();
  timeSlider.max = String(availableMonths.length);
  if (!availableMonths.includes(activeMonth)) {
    activeMonth = "all";
    timeSlider.value = "0";
    timeLabel.value = "All dates";
  }
}

function applyTimeFilter() {
  filteredObservations = {
    type: "FeatureCollection",
    features:
      activeMonth === "all"
        ? observations.features
        : observations.features.filter((feature) =>
            feature.properties?.observed_at?.startsWith(activeMonth),
          ),
  };
  renderObservations();
}

function renderObservations() {
  markerCluster.clearLayers();
  filteredObservations.features.forEach((feature) => {
    const layer = L.geoJSON(feature, {
      pointToLayer: (_feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 8,
          weight: 2,
          color: "#ffffff",
          fillColor: colorForFeature(feature),
          fillOpacity: 0.92,
        }),
      style: () => ({
        color: colorForFeature(feature),
        weight: 2,
        fillOpacity: 0.22,
      }),
      onEachFeature: (item, itemLayer) => {
        itemLayer.bindPopup(popupHtml(item));
      },
    });
    markerCluster.addLayer(layer);
  });
  if (map.hasLayer(heatLayer)) {
    renderHeatmap();
  }
  if (map.hasLayer(predictionLayer)) {
    renderPredictionLayer();
  }
  if (map.hasLayer(gridLayer)) {
    renderGridLayer();
  }
}

function renderOptionalLayer(layerType) {
  if (layerType === "heatmap") {
    renderHeatmap();
  }
  if (layerType === "predicted_weeds") {
    renderPredictionLayer();
  }
  if (layerType === "grid") {
    renderGridLayer();
  }
}

function renderHeatmap() {
  const points = filteredObservations.features
    .map((feature) => {
      const center = featureCenter(feature);
      if (!center) return null;
      const coverage = Number(feature.properties?.coverage_percent || 20);
      return [center.lat, center.lng, Math.min(Math.max(coverage / 100, 0.15), 1)];
    })
    .filter(Boolean);

  heatLayer.setLatLngs(points);
}

function renderPredictionLayer() {
  predictionLayer.clearLayers();
  const pressure = filteredObservations.features
    .map((feature) => {
      const center = featureCenter(feature);
      if (!center) return null;
      const coverage = Number(feature.properties?.coverage_percent || 20);
      return L.circle(center, {
        radius: 35 + coverage * 2.2,
        color: "#d9480f",
        weight: 1,
        fillColor: "#f08c00",
        fillOpacity: Math.min(coverage / 160, 0.45),
      }).bindPopup(`Weed pressure ${Math.round(coverage)} / 100`);
    })
    .filter(Boolean);
  pressure.forEach((layer) => predictionLayer.addLayer(layer));
}

function renderGridLayer() {
  gridLayer.clearLayers();
  const bounds = map.getBounds().pad(0.12);
  const cellMeters = gridCellSize(bounds);
  const latStep = cellMeters / 111320;
  const lngStep = cellMeters / (111320 * Math.cos((VARTOPO_CENTER[0] * Math.PI) / 180));

  for (let lat = bounds.getSouth(); lat < bounds.getNorth(); lat += latStep) {
    for (let lng = bounds.getWest(); lng < bounds.getEast(); lng += lngStep) {
      const cellBounds = [
        [lat, lng],
        [lat + latStep, lng + lngStep],
      ];
      const stats = gridStats(cellBounds);
      const fillOpacity = stats.count ? Math.min(stats.coverage / 180, 0.36) : 0.025;
      L.rectangle(cellBounds, {
        color: "#5f3dc4",
        weight: 1,
        fillColor: "#9775fa",
        fillOpacity,
      })
        .bindPopup(gridPopup(stats))
        .addTo(gridLayer);
    }
  }
}

function gridCellSize(bounds) {
  const latMeters = Math.abs(bounds.getNorth() - bounds.getSouth()) * 111320;
  const lngMeters =
    Math.abs(bounds.getEast() - bounds.getWest()) *
    111320 *
    Math.cos((VARTOPO_CENTER[0] * Math.PI) / 180);
  const estimatedCells = (latMeters / 25) * (lngMeters / 25);
  if (estimatedCells <= 1600) {
    return 25;
  }
  return Math.ceil(Math.sqrt((latMeters * lngMeters) / 1600) / 5) * 5;
}

function gridStats(cellBounds) {
  const bounds = L.latLngBounds(cellBounds);
  const features = filteredObservations.features.filter((feature) => {
    const center = featureCenter(feature);
    return center && bounds.contains(center);
  });
  const species = new Set(features.map((feature) => feature.properties?.species).filter(Boolean));
  const coverage = features.reduce(
    (total, feature) => total + Number(feature.properties?.coverage_percent || 0),
    0,
  );
  const dates = features
    .map((feature) => feature.properties?.observed_at)
    .filter(Boolean)
    .sort();
  return {
    count: features.length,
    richness: species.size,
    coverage: features.length ? coverage / features.length : 0,
    lastVisit: dates.at(-1) || "None",
  };
}

function gridPopup(stats) {
  return `
    <div class="observation-popup">
      <h3>Grid cell</h3>
      <dl>
        <dt>Species richness</dt><dd>${stats.richness}</dd>
        <dt>Weed density</dt><dd>${Math.round(stats.coverage)} / 100</dd>
        <dt>Last visit</dt><dd>${escapeHtml(stats.lastVisit)}</dd>
        <dt>Predicted emergence</dt><dd>${stats.count ? "Active" : "Unobserved"}</dd>
      </dl>
    </div>
  `;
}

function popupHtml(feature) {
  const properties = feature.properties || {};
  const photos = properties.photos || [];
  const photo = photos[0];
  const image = photo
    ? `<a href="${escapeAttribute(photo.url)}" target="_blank" rel="noreferrer">
        <img class="popup-photo" src="${escapeAttribute(photo.thumbnail_url || photo.url)}" alt="" />
      </a>`
    : "";

  return `
    <div class="observation-popup">
      ${image}
      <h3>${escapeHtml(properties.species || "Unknown species")}</h3>
      <dl>
        <dt>Coverage</dt><dd>${formatPercent(properties.coverage_percent)}</dd>
        <dt>Density</dt><dd>${escapeHtml(properties.density_class || "Unknown")}</dd>
        <dt>Confidence</dt><dd>${formatConfidence(properties.confidence)}</dd>
        <dt>Photo</dt><dd>${photos.length || (properties.photo_reference ? 1 : 0)}</dd>
        <dt>Notes</dt><dd>${escapeHtml(properties.notes || "None")}</dd>
        <dt>Date</dt><dd>${escapeHtml(properties.observed_at || "Unknown")}</dd>
      </dl>
    </div>
  `;
}

function featureCenter(feature) {
  const geometry = feature.geometry;
  if (!geometry) return null;
  if (geometry.type === "Point") {
    return L.latLng(geometry.coordinates[1], geometry.coordinates[0]);
  }
  const layer = L.geoJSON(feature);
  return layer.getBounds().getCenter();
}

function colorForFeature(feature) {
  if (colorMode === "family") {
    return familyColor(feature.properties?.species || "");
  }
  return statusColor(feature);
}

function statusColor(feature) {
  const species = String(feature.properties?.species || "").toLowerCase();
  const coverage = Number(feature.properties?.coverage_percent || 0);
  const density = feature.properties?.density_class;
  if (species.includes("clover") || species.includes("trifolium") || species.includes("vetch")) {
    return statusColors.beneficial;
  }
  if (coverage >= 60 || density === "high" || species.includes("urtica")) {
    return statusColors.aggressive;
  }
  if (coverage >= 20 || density === "medium") {
    return statusColors.monitor;
  }
  return statusColors.neutral;
}

function familyColor(species) {
  const value = species.toLowerCase();
  if (value.includes("poa") || value.includes("lolium") || value.includes("grass")) {
    return familyColors.poaceae;
  }
  if (value.includes("trifolium") || value.includes("vicia") || value.includes("clover")) {
    return familyColors.fabaceae;
  }
  if (value.includes("taraxacum") || value.includes("cirsium") || value.includes("aster")) {
    return familyColors.asteraceae;
  }
  if (value.includes("amaranthus") || value.includes("chenopodium")) {
    return familyColors.amaranthaceae;
  }
  return familyColors.default;
}

function formatPercent(value) {
  if (value === null || value === undefined) return "Unknown";
  return `${Math.round(Number(value))}%`;
}

function formatConfidence(value) {
  if (value === null || value === undefined) return "Unknown";
  return `${Math.round(Number(value) * 100)}%`;
}

function formatMonthLabel(month) {
  const date = new Date(`${month}-01T00:00:00`);
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

map.on("moveend", () => {
  if (map.hasLayer(gridLayer)) {
    renderGridLayer();
  }
});

loadAll();
setTimeout(() => map.invalidateSize(), 100);
