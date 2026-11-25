const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);
const upstream = config.resolver.resolveRequest;

// react-native-maps is native-only; swap in a web shim when bundling for web.
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === 'web' && moduleName === 'react-native-maps') {
    return { type: 'sourceFile', filePath: path.resolve(__dirname, 'web-shims/react-native-maps.js') };
  }
  return (upstream || context.resolveRequest)(context, moduleName, platform);
};

module.exports = config;
