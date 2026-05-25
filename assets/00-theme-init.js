// Apply persisted theme before paint to avoid a flash of wrong mode.
// File is prefixed "00-" so Dash loads it first from assets/.
(function () {
  try {
    var saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
