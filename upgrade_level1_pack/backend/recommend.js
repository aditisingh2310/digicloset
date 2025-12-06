
// backend/recommend.js
module.exports = function recommend(items) {
  // Simple rule-based recommendation
  if (items.length < 2) {
    return { suggestion: "Add more items to get outfit recommendations!" };
  }
  return {
    outfit: [items[0], items[1]],
    message: "Pair these items for a simple, stylish outfit."
  };
};
