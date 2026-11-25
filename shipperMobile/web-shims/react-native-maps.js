// Web stand-in for react-native-maps (native-only): an OpenStreetMap embed.
// shortcut: no markers/route line on web, add a Leaflet map if needed.
import React, { forwardRef, useImperativeHandle } from 'react';
import { View } from 'react-native';

export const PROVIDER_DEFAULT = null;
export const Marker = () => null;
export const Polyline = () => null;
export const UrlTile = () => null;

const MapView = forwardRef(({ style, initialRegion }, ref) => {
  useImperativeHandle(ref, () => ({
    getCamera: () => Promise.resolve({ zoom: 15 }),
    animateCamera: () => {},
  }));
  const { latitude: lat = 10.78, longitude: lng = 106.7 } = initialRegion || {};
  const d = 0.01;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - d},${lat - d},${lng + d},${lat + d}&layer=mapnik&marker=${lat},${lng}`;
  return (
    <View style={style}>
      <iframe title="map" src={src} style={{ border: 0, width: '100%', height: '100%' }} />
    </View>
  );
});

export default MapView;
