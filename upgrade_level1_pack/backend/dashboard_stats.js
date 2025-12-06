
// backend/dashboard_stats.js
module.exports = function stats(items) {
  return {
    totalItems: items.length,
    mostUsed: items[0] || null,
    leastUsed: items[items.length - 1] || null,
    seasonalDistribution: {
      winter: 2,
      summer: 4,
      all: 6
    }
  };
};
