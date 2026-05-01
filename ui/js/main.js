(function () {
  // Backward compatibility: keep loading existing monolith while preparing modular migration.
  // Use absolute-from-root path to avoid resolving as /js/app.js.
  const script = document.createElement('script');
  script.src = '/app.js';
  script.defer = true;
  document.body.appendChild(script);
})();
