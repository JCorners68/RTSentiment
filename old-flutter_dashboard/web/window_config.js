// Set the initial window size
window.addEventListener('load', function() {
  // Set window size to 1200x800 (smaller than default)
  if (window.chrome) {
    const width = 1200;
    const height = 800;
    window.resizeTo(width, height);
  }
});
