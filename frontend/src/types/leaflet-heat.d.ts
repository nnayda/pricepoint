declare module "leaflet.heat" {
  import * as L from "leaflet";
  function heatLayer(
    latlngs: Array<[number, number, number?]>,
    options?: Record<string, unknown>,
  ): L.Layer;
  export default heatLayer;
}
