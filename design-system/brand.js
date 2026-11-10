/**
 * Constantes y utilidades de marca para previews locales HTML
 */
window.BRAND_NAME = "DentalSaaS";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-brand-name]").forEach((el) => {
    el.textContent = window.BRAND_NAME;
  });
});

