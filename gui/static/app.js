(() => {
  const body = document.body;
  const toggle = document.querySelector(".menu-toggle");
  const scrim = document.querySelector(".nav-scrim");
  const sidebar = document.querySelector("#primary-sidebar");

  const setMenu = (open) => {
    body.classList.toggle("nav-open", open);
    toggle?.setAttribute("aria-expanded", String(open));
  };

  toggle?.addEventListener("click", () => setMenu(!body.classList.contains("nav-open")));
  scrim?.addEventListener("click", () => setMenu(false));
  sidebar?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenu(false);
  });

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"], button:not([type])');
      if (!button || button.disabled) return;
      button.dataset.originalLabel = button.textContent;
      button.textContent = "Working…";
      button.classList.add("is-loading");
      button.setAttribute("aria-busy", "true");
    });
  });
})();
