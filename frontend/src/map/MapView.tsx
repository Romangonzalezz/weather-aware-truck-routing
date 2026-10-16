import { type GeoJSONSource, Map as MapLibreMap, NavigationControl, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { Corridor, Plan, Route } from "../api/types";
import { checkpointFeatures, corridorFeatures, routeBounds, routeFeatures } from "./geojson";
import { heatmapRadius, heatmapWeight } from "./heatmap";
import { addTripLayers, LAYERS, SOURCES, STYLE_URL, styleSelectedRoute } from "./layers";
import { checkpointPopup } from "./popup";

const US_CENTER: [number, number] = [-97, 39];
const FIT_PADDING = 60;

interface Props {
  plan?: Plan;
  selectedRouteId?: string;
  corridor?: Corridor;
  hour: number;
  heatmapVisible: boolean;
}

function setData(map: MapLibreMap, source: string, data: Parameters<GeoJSONSource["setData"]>[0]) {
  (map.getSource(source) as GeoJSONSource).setData(data);
}

export function MapView({ plan, selectedRouteId, corridor, hour, heatmapVisible }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap>(undefined);
  const [ready, setReady] = useState(false);
  const selectedRoute: Route | undefined = plan?.routes.find((route) => route.id === selectedRouteId) ?? plan?.routes[0];
  const hovered = useRef<Route | undefined>(undefined);
  hovered.current = selectedRoute;

  useEffect(() => {
    const map = new MapLibreMap({ container: container.current!, style: STYLE_URL, center: US_CENTER, zoom: 3.4 });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      addTripLayers(map);
      attachCheckpointPopup(map, () => hovered.current);
      setReady(true);
    });
    return () => {
      setReady(false);
      map.remove();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    setData(map, SOURCES.routes, routeFeatures(plan?.routes ?? []));
    if (plan) map.fitBounds(routeBounds(plan.routes), { padding: FIT_PADDING, duration: 800 });
  }, [ready, plan]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    setData(map, SOURCES.checkpoints, checkpointFeatures(selectedRoute));
    styleSelectedRoute(map, selectedRoute?.id);
  }, [ready, selectedRoute]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    setData(map, SOURCES.corridor, corridor ? corridorFeatures(corridor) : { type: "FeatureCollection", features: [] });
    if (corridor) map.setPaintProperty(LAYERS.heat, "heatmap-radius", heatmapRadius(corridor.spacing_deg));
  }, [ready, corridor]);

  // The only work a slider tick does: swap which precomputed score the heatmap reads.
  useEffect(() => {
    if (ready) mapRef.current?.setPaintProperty(LAYERS.heat, "heatmap-weight", heatmapWeight(hour));
  }, [ready, hour]);

  useEffect(() => {
    if (ready) mapRef.current?.setLayoutProperty(LAYERS.heat, "visibility", heatmapVisible ? "visible" : "none");
  }, [ready, heatmapVisible]);

  return <div className="map" ref={container} role="region" aria-label="Map of routes, checkpoints and weather" />;
}

function attachCheckpointPopup(map: MapLibreMap, currentRoute: () => Route | undefined) {
  const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12 });
  map.on("mousemove", LAYERS.checkpoints, (event) => {
    const feature = event.features?.[0];
    const checkpoint = currentRoute()?.checkpoints[feature?.properties.index];
    if (!feature || !checkpoint) return;
    map.getCanvas().style.cursor = "pointer";
    popup.setLngLat([checkpoint.lon, checkpoint.lat]).setDOMContent(checkpointPopup(checkpoint)).addTo(map);
  });
  map.on("mouseleave", LAYERS.checkpoints, () => {
    map.getCanvas().style.cursor = "";
    popup.remove();
  });
}
