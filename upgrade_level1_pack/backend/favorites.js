
// backend/favorites.js
let favorites = [];

module.exports = {
  addFavorite(itemId) {
    if (!favorites.includes(itemId)) favorites.push(itemId);
    return favorites;
  },
  listFavorites() {
    return favorites;
  },
  removeFavorite(itemId) {
    favorites = favorites.filter(id => id !== itemId);
    return favorites;
  }
};
