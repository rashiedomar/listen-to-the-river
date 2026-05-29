const DATA_ROOT = "./data";

const layerState = {
  roads: true,
  buildings: true,
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
let map;
let waterRenderer;

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
    preferCanvas: false,
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

  waterRenderer = L.svg({ pane: "water", padding: 0.4 });

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);
}

function ensureWaterDefs() {
  const svg = document.querySelector("#map .leaflet-pane.water-pane svg");
  if (!svg || svg.querySelector("#waterPatternMain")) {
    return;
  }

  const ns = "http://www.w3.org/2000/svg";
  const defs = document.createElementNS(ns, "defs");
  defs.innerHTML = `
    <filter id="waterSoftBlur" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3.8" />
    </filter>
    <filter id="waterEdgeBlur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="1.5" />
    </filter>
    <pattern id="waterPatternMain" patternUnits="userSpaceOnUse" width="96" height="96">
      <rect width="96" height="96" fill="#7fbfe8"></rect>
      <path d="M-6 22 C10 8, 26 8, 42 22 S74 36, 92 22" fill="none" stroke="#eef8ff" stroke-opacity="0.44" stroke-width="2.2" stroke-linecap="round"/>
      <path d="M-4 56 C12 44, 28 44, 46 56 S78 68, 98 56" fill="none" stroke="#d7eefc" stroke-opacity="0.36" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M-8 82 C8 70, 26 70, 42 82 S74 96, 98 82" fill="none" stroke="#f7fbff" stroke-opacity="0.25" stroke-width="1.4" stroke-linecap="round"/>
      <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="24 12" dur="18s" repeatCount="indefinite" />
    </pattern>
    <pattern id="waterPatternCore" patternUnits="userSpaceOnUse" width="86" height="86">
      <rect width="86" height="86" fill="#3f88bf"></rect>
      <path d="M-8 20 C12 5, 30 5, 50 20 S84 34, 100 18" fill="none" stroke="#d8f1ff" stroke-opacity="0.42" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M-6 54 C12 42, 30 42, 48 54 S80 68, 92 52" fill="none" stroke="#a9d3ef" stroke-opacity="0.38" stroke-width="1.5" stroke-linecap="round"/>
      <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="20 8" dur="14s" repeatCount="indefinite" />
    </pattern>
    <pattern id="waterPatternFringe" patternUnits="userSpaceOnUse" width="112" height="112">
      <rect width="112" height="112" fill="#b5def2"></rect>
      <path d="M-8 26 C16 10, 38 10, 60 26 S104 42, 126 26" fill="none" stroke="#f9fdff" stroke-opacity="0.34" stroke-width="2" stroke-linecap="round"/>
      <path d="M-8 72 C16 58, 38 58, 58 72 S102 84, 122 72" fill="none" stroke="#d7eefb" stroke-opacity="0.24" stroke-width="1.5" stroke-linecap="round"/>
      <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="26 10" dur="22s" repeatCount="indefinite" />
    </pattern>
  `;
  svg.prepend(defs);
}

function buildLayerToggle(label, key) {
  const btn = document.createElement("button");
  btn.className = `layer-chip ${layerState[key] ? "active" : ""}`;
  btn.textContent = label;
  btn.addEventListener("click", () => {
    layerState[key] = !layerState[key];
    btn.classList.toggle("active", layerState[key]);
    syncLayerVisibility();
  });
  return btn;
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

function buildLayers(data) {
  focusCityView(data.cityCenter);

  const waterGlow = L.geoJSON(data.finalMask, {
    pane: "water",
    interactive: false,
    renderer: waterRenderer,
    style: {
      className: "flood-glow",
      color: "#7fc1ea",
      weight: 0,
      fillColor: COLORS.water,
      fillOpacity: 0.22,
      opacity: 0,
    },
  }).addTo(map);

  L.geoJSON(data.finalMask, {
    pane: "water",
    interactive: false,
    renderer: waterRenderer,
    style: {
      className: "flood-final",
      color: COLORS.waterEdge,
      weight: 0.6,
      fillColor: COLORS.water,
      fillOpacity: 0.22,
      opacity: 0.65,
      lineJoin: "round",
    },
  }).addTo(map);

  layerGroups.core = L.geoJSON(data.coreMask, {
    pane: "water",
    interactive: false,
    renderer: waterRenderer,
    style: {
      className: "flood-core",
      color: "#0d3f6b",
      weight: 0.35,
      fillColor: COLORS.core,
      fillOpacity: 0.25,
      opacity: 0.65,
      lineJoin: "round",
    },
  }).addTo(map);

  layerGroups.extensions = L.geoJSON(data.extensions, {
    pane: "water",
    interactive: false,
    renderer: waterRenderer,
    style: {
      className: "flood-fringe",
      color: "#6eaed8",
      weight: 0.2,
      fillColor: COLORS.fringe,
      fillOpacity: 0.16,
      opacity: 0.5,
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

  layerGroups.buildings = L.geoJSON(data.buildings, {
    pane: "buildings",
    style: (feature) => ({
      color: COLORS.buildingStroke,
      weight: feature.properties.impact_level === "severe" ? 0.85 : 0.55,
      fillColor: COLORS.buildingFill,
      fillOpacity: feature.properties.impact_level === "proximity" ? 0.2 : 0.36,
      opacity: 0.78,
    }),
    onEachFeature(feature, layer) {
      const title = feature.properties.name || "Building";
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

  ensureWaterDefs();
}

async function init() {
  const [meta, cityCenter, finalMask, coreMask, extensions, roads, buildings, places] = await Promise.all([
    loadJson(`${DATA_ROOT}/story_meta.json`),
    loadJson(`${DATA_ROOT}/city_center.geojson`),
    loadJson(`${DATA_ROOT}/final_story_mask.geojson`),
    loadJson(`${DATA_ROOT}/core_mask.geojson`),
    loadJson(`${DATA_ROOT}/s1_extensions.geojson`),
    loadJson(`${DATA_ROOT}/roads_impacted.geojson`),
    loadJson(`${DATA_ROOT}/buildings_impacted.geojson`),
    loadJson(`${DATA_ROOT}/places_impacted.geojson`),
  ]);

  buildMap();
  buildControls(meta);
  buildLayers({ cityCenter, finalMask, coreMask, extensions, roads, buildings, places });
  syncLayerVisibility();
}

init().catch((error) => {
  console.error(error);
  alert(error.message);
});
