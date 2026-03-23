const plugins = [];

try {
  plugins.push(require("autoprefixer"));
} catch (error) {
  // Allow builds to proceed in minimal environments where PostCSS helpers are not installed.
}

module.exports = { plugins };
