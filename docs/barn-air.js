/* See the Barn from the Air (2026-10-24; Scott chose "Both" and A, notes/barn-from-the-air-*-2026-10-24.png).
   The barn page shows a still aerial photo with the barn's pin. Fly Over the Barn loads the 3D map (MapLibre, in
   maplibre/, only now) and flies in the way the tested sample does (notes/flyover-sample-roads-2026-10-23.html):
   - lands at zoom 14.5, tilted 60: closer (zoom 16) put the camera only a few hundred metres over the ground and it
     ended up inside it;
   - turns slowly once the 3D ground has loaded, one long easeTo (a step every frame made the camera drift);
   - backs out if the camera comes within 250 m of the ground under it;
   - Road Names fades in and out with no transition: with 3D ground MapLibre 4 keeps the first moment of a fade.
   The map asks for photos from USGS and elevation from AWS only after the button is pressed. */
(function () {
  "use strict";
  const box = document.getElementById("barn-air");
  if (!box) return;
  const go = document.getElementById("air-go"), holder = document.getElementById("air-map");
  const lat = Number(box.dataset.lat), lon = Number(box.dataset.lon), name = box.dataset.name;
  let map = null, spinning = false, lifting = false;

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
    n.append(...kids);
    return n;
  }
  function load(tag, attrs) {
    return new Promise((ok, fail) => { const n = el(tag, attrs); n.onload = ok; n.onerror = fail; document.head.append(n); });
  }

  function turn() {
    if (spinning && map && !map.isMoving()) map.easeTo({ bearing: map.getBearing() + 90, duration: 30000, easing: (t) => t, essential: true });
  }
  function spin() { spinning = true; turn(); }
  function stopSpin() { spinning = false; }

  function flyIn() {
    stopSpin();
    map.stop();
    map.jumpTo({ center: [lon, lat], zoom: 7, pitch: 0, bearing: 0 });
    map.easeTo({ pitch: 45, bearing: 45, zoom: 9, duration: 2500 });
    map.once("moveend", () => {
      map.flyTo({ center: [lon, lat], zoom: 14.5, pitch: 60, bearing: 75, speed: 0.35, curve: 1.5, essential: true });
      map.once("moveend", () => map.once("idle", spin));
    });
  }

  // MapLibre 4 doesn't keep the camera above the ground; back out half a zoom step when it gets within 250 m.
  // queryTerrainElevation gives the ground relative to the ground at the middle of the screen, so add that back.
  function guard() {
    if (!map || lifting) return;
    const cp = map.transform.getCameraPosition(), rel = map.queryTerrainElevation(cp.lngLat);
    if (rel == null || cp.altitude - (map.transform.elevation + rel) >= 250) return;
    const was = spinning;
    lifting = true; spinning = false;
    map.easeTo({ zoom: map.getZoom() - 0.5, pitch: Math.min(map.getPitch(), 60), duration: 800, essential: true });
    map.once("moveend", () => { lifting = false; if (was) setTimeout(spin, 0); });
  }

  // Street View at the middle of what the map shows, facing its way, in a smaller window on a computer (Scott, for
  // My Farm's links: "I don't want them to lose sight of the fact that they are on my site")
  function streetView(e) {
    const c = map.getCenter(), heading = Math.round((map.getBearing() + 360) % 360);
    const url = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${c.lat.toFixed(5)},${c.lng.toFixed(5)}&heading=${heading}`;
    e.currentTarget.href = url;
    if (window.matchMedia("(min-width: 900px)").matches) {
      const w = window.open(url, "streetview", "popup,width=1000,height=700");
      if (w) e.preventDefault();
    }
  }

  function pin() {
    const p = el("div", { class: "air-pin on-map", "aria-hidden": "true" }, el("span", {}, name));
    p.insertAdjacentHTML("beforeend", '<svg width="26" height="34" viewBox="0 0 26 34"><path d="M13 33C13 33 2 20 2 12.5a11 11 0 0 1 22 0C24 20 13 33 13 33z" fill="#e0ac45" stroke="#243b2f" stroke-width="2"/><circle cx="13" cy="12.5" r="4" fill="#243b2f"/></svg>');
    return new maplibregl.Marker({ element: p, anchor: "bottom" }).setLngLat([lon, lat]);
  }

  function start() {
    holder.replaceChildren();
    holder.classList.add("flying");
    const canvas = el("div", { class: "air-canvas" });
    const chip = el("span", { class: "air-chip" }, `Flying over ${name}`);
    const again = el("button", { type: "button", class: "btn small" }, "Fly Again");
    const roads = el("button", { type: "button", class: "btn small secondary", "aria-pressed": "false" }, "Road Names");
    const sv = el("a", { class: "btn small secondary", href: "#", target: "_blank", rel: "noopener" }, "Street View ›");
    holder.append(canvas, chip, el("div", { class: "air-bar" }, again, roads, sv));
    maplibregl.setWorkerUrl("maplibre/maplibre-gl-csp-worker.js");
    map = new maplibregl.Map({
      container: canvas,
      style: {
        version: 8,
        sources: {
          sat: { type: "raster", tileSize: 256, maxzoom: 16, attribution: "Imagery: USDA NAIP via USGS The National Map",
                 tiles: ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"] },
          roads: { type: "raster", tileSize: 256, minzoom: 11, maxzoom: 18, attribution: "Roads: USGS The National Map",
                   tiles: ["https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&f=image"] },
          dem: { type: "raster-dem", tileSize: 256, maxzoom: 14, encoding: "terrarium", attribution: "Terrain: AWS Terrain Tiles",
                 tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"] }
        },
        layers: [{ id: "sat", type: "raster", source: "sat" },
                 { id: "roads", type: "raster", source: "roads", minzoom: 11,
                   paint: { "raster-opacity": 0, "raster-opacity-transition": { duration: 0 }, "raster-fade-duration": 0 } }],
        terrain: { source: "dem", exaggeration: 1.3 },
        sky: {}
      },
      center: [lon, lat], zoom: 7, maxZoom: 18, maxPitch: 75,
      attributionControl: false    // the sources are named under the map; the open credit box covered the buttons on a phone
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.on("moveend", () => { if (spinning) setTimeout(turn, 0); });
    for (const ev of ["mousedown", "touchstart", "wheel"]) map.on(ev, stopSpin);
    map.on("load", () => { pin().addTo(map); flyIn(); });
    setInterval(guard, 300);
    again.addEventListener("click", flyIn);
    roads.addEventListener("click", () => {
      const on = roads.getAttribute("aria-pressed") !== "true";
      roads.setAttribute("aria-pressed", String(on));
      roads.textContent = on ? "✓ Road Names" : "Road Names";
      map.setPaintProperty("roads", "raster-opacity", on ? 0.85 : 0);
    });
    sv.addEventListener("click", streetView);
  }

  go.addEventListener("click", async () => {
    go.disabled = true;
    go.textContent = "Loading the map…";
    try {
      await Promise.all([load("link", { rel: "stylesheet", href: "maplibre/maplibre-gl.css" }),
                         load("script", { src: "maplibre/maplibre-gl-csp.js" })]);
      start();
    } catch (err) {
      go.disabled = false;
      go.textContent = "Fly Over the Barn";
      holder.append(el("p", { class: "air-error" }, "The 3D map couldn't load. Check your connection and try again."));
    }
  });
})();
