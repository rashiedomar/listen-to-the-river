const DATA_ROOT = "./data";

const layerState = {
  roads: true,
  buildings: false,
  places: true,
  core: true,
  extensions: false,
};

const COLORS = {
  water: "#67a8df",
  waterEdge: "#2b6b9d",
  core: "#184f83",
  fringe: "#9ed4f0",
  road: "#7d665b",
  buildingFill: "#ddd5ce",
  buildingStroke: "#7b6d66",
  place: "#3a8f7f",
};

const layerGroups = {};
const layerLoaders = {};
const pendingLayerLoads = {};
let map;

function popupHtml(title, lines) {
  return `
    <div style="min-width:180px">
      <div style="font-family:Fraunces,serif;font-size:1.1rem;margin-bottom:6px;color:#211116">${title}</div>
      ${lines.map((line) => `<div style="font-size:0.92rem;color:#564a46">${line}</div>`).join("")}
    </div>
  `;
}

function buildMap() {
  map = L.map("map", {
    zoomControl: true,
    preferCanvas: true,
    zoomSnap: 0.25,
  });

  map.createPane("roads");
  map.createPane("buildings");
  map.createPane("water");
  map.createPane("places");

  map.getPane("roads").style.zIndex = 420;
  map.getPane("buildings").style.zIndex = 430;
  map.getPane("water").style.zIndex = 450;
  map.getPane("places").style.zIndex = 460;
  map.getPane("water").classList.add("water-pane");
  map.getPane("buildings").classList.add("buildings-pane");
  map.getPane("roads").classList.add("roads-pane");

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);
}

function buildLayerToggle(label, key) {
  const btn = document.createElement("button");
  btn.className = `layer-chip ${layerState[key] ? "active" : ""}`;
  btn.textContent = label;
  btn.addEventListener("click", async () => {
    layerState[key] = !layerState[key];
    btn.classList.toggle("active", layerState[key]);
    if (layerState[key]) {
      await ensureLayerLoaded(key);
    }
    syncLayerVisibility();
  });
  return btn;
}

async function ensureLayerLoaded(key) {
  if (layerGroups[key] || !layerLoaders[key]) {
    return;
  }
  if (!pendingLayerLoads[key]) {
    pendingLayerLoads[key] = layerLoaders[key]().then((layer) => {
      layerGroups[key] = layer;
      return layer;
    });
  }
  await pendingLayerLoads[key];
}

function syncLayerVisibility() {
  Object.entries(layerGroups).forEach(([key, layer]) => {
    if (!layer) return;
    const shouldShow = layerState[key];
    if (shouldShow && !map.hasLayer(layer)) {
      layer.addTo(map);
    }
    if (!shouldShow && map.hasLayer(layer)) {
      map.removeLayer(layer);
    }
  });
}

function loadJson(path) {
  return fetch(path).then((res) => {
    if (!res.ok) throw new Error(`Failed to load ${path}`);
    return res.json();
  });
}

function buildControls(meta) {
  const wrap = document.getElementById("layer-toggles");
  document.querySelector(".title-card .eyebrow").textContent = `${meta.city} · ${meta.focus_dates.peak_date}`;
  const specs = [
    [meta.layer_labels.roads, "roads"],
    [meta.layer_labels.buildings, "buildings"],
    [meta.layer_labels.places, "places"],
    [meta.layer_labels.core, "core"],
    [meta.layer_labels.extensions, "extensions"],
  ];
  specs.forEach(([label, key]) => wrap.appendChild(buildLayerToggle(label, key)));
}

function focusCityView(cityCenter) {
  const feature = cityCenter.features[0];
  const [lng, lat] = feature.geometry.coordinates;
  map.setView([lat, lng], 14.35);
}

function createBuildingsLayer(buildings) {
  return L.geoJSON(buildings, {
    pane: "buildings",
    pointToLayer: (feature, latlng) =>
      L.circleMarker(latlng, {
        radius:
          feature.properties.impact_level === "severe"
            ? 4.6
            : feature.properties.impact_level === "moderate"
              ? 3.8
              : feature.properties.impact_level === "minor"
                ? 3.2
                : 2.4,
        color: COLORS.buildingStroke,
        weight: feature.properties.impact_level === "severe" ? 1 : 0.7,
        fillColor: COLORS.buildingFill,
        fillOpacity: feature.properties.impact_level === "proximity" ? 0.34 : 0.58,
        opacity: 0.88,
      }),
    onEachFeature(feature, layer) {
      layer.bindPopup(
        popupHtml("Building", [
          `Impact: ${feature.properties.impact_level}`,
          `Flooded share: ${(feature.properties.impact_fraction * 100).toFixed(1)}%`,
          `Distance to water: ${feature.properties.distance_to_flood_m.toFixed(0)} m`,
        ]),
      );
    },
  });
}

function buildLayers(data) {
  focusCityView(data.cityCenter);

  L.geoJSON(data.finalMask, {
    pane: "water",
    interactive: false,
    style: {
      className: "flood-final",
      color: COLORS.waterEdge,
      weight: 0.6,
      fillColor: COLORS.water,
      fillOpacity: 0.32,
      opacity: 0.72,
      lineJoin: "round",
    },
  }).addTo(map);

  layerGroups.core = L.geoJSON(data.coreMask, {
    pane: "water",
    interactive: false,
    style: {
      className: "flood-core",
      color: "#0d3f6b",
      weight: 0.4,
      fillColor: COLORS.core,
      fillOpacity: 0.24,
      opacity: 0.7,
      lineJoin: "round",
    },
  }).addTo(map);

  layerGroups.extensions = L.geoJSON(data.extensions, {
    pane: "water",
    interactive: false,
    style: {
      className: "flood-fringe",
      color: "#6eaed8",
      weight: 0.2,
      fillColor: COLORS.fringe,
      fillOpacity: 0.14,
      opacity: 0.42,
      lineJoin: "round",
    },
  });

  layerGroups.roads = L.geoJSON(data.roads, {
    pane: "roads",
    style: (feature) => ({
      color: COLORS.road,
      weight: feature.properties.impact_level === "severe" ? 2.4 : feature.properties.impact_level === "moderate" ? 2 : 1.55,
      opacity: feature.properties.impact_level === "proximity" ? 0.62 : 0.9,
    }),
    onEachFeature(feature, layer) {
      const title = feature.properties.name || "Road";
      layer.bindPopup(
        popupHtml(title, [
          `Impact: ${feature.properties.impact_level}`,
          `Flooded share: ${(feature.properties.impact_fraction * 100).toFixed(1)}%`,
          `Distance to water: ${feature.properties.distance_to_flood_m.toFixed(0)} m`,
        ]),
      );
    },
  }).addTo(map);

  layerGroups.places = L.geoJSON(data.places, {
    pane: "places",
    pointToLayer: (feature, latlng) =>
      L.circleMarker(latlng, {
        radius: feature.properties.impact_level === "severe" ? 6.5 : 5,
        color: "#ffffff",
        weight: 1.2,
        fillColor: COLORS.place,
        fillOpacity: 0.92,
      }),
    onEachFeature(feature, layer) {
      const title = feature.properties.name || "Place";
      layer.bindPopup(
        popupHtml(title, [
          `Impact: ${feature.properties.impact_level}`,
          `Distance to water: ${feature.properties.distance_to_flood_m.toFixed(0)} m`,
        ]),
      );
    },
  }).addTo(map);
}

async function init() {
  const [meta, cityCenter, finalMask, coreMask, extensions, roads, places] = await Promise.all([
    loadJson(`${DATA_ROOT}/story_meta.json`),
    loadJson(`${DATA_ROOT}/city_center.geojson`),
    loadJson(`${DATA_ROOT}/final_story_mask.geojson`),
    loadJson(`${DATA_ROOT}/core_mask.geojson`),
    loadJson(`${DATA_ROOT}/s1_extensions.geojson`),
    loadJson(`${DATA_ROOT}/roads_impacted.geojson`),
    loadJson(`${DATA_ROOT}/places_impacted.geojson`),
  ]);

  buildMap();
  buildControls(meta);
  layerLoaders.buildings = async () => createBuildingsLayer(await loadJson(`${DATA_ROOT}/buildings_impacted.geojson`));
  buildLayers({ cityCenter, finalMask, coreMask, extensions, roads, places });
  syncLayerVisibility();
}

init().catch((error) => {
  console.error(error);
  alert(error.message);
});
