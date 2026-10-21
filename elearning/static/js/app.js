/* LearnHub front-end helpers (no framework). */
(function () {
  "use strict";

  // Auto-dismiss toasts after a few seconds.
  document.querySelectorAll(".toast-stack .alert").forEach(function (el, i) {
    setTimeout(function () {
      el.classList.add("fade");
      el.classList.remove("show");
      setTimeout(function () { el.remove(); }, 300);
    }, 4200 + i * 400);
  });

  // Confirm destructive forms.
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Mark lesson complete without a full page reload.
  var completeForm = document.getElementById("complete-lesson-form");
  if (completeForm) {
    completeForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = completeForm.querySelector("button[type=submit]");
      btn.disabled = true;
      fetch(completeForm.action, {
        method: "POST",
        headers: { "X-CSRFToken": completeForm.querySelector("[name=csrfmiddlewaretoken]").value, "X-Requested-With": "fetch" },
        credentials: "same-origin",
      })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
        .then(function (data) {
          var bar = document.querySelector("[data-progress-bar]");
          var label = document.querySelector("[data-progress-label]");
          if (bar) { bar.style.width = data.progress + "%"; bar.setAttribute("aria-valuenow", data.progress); if (data.progress >= 100) bar.classList.add("bg-success"); }
          if (label) label.textContent = data.progress + "% complete";
          var item = document.querySelector(".learn-sidebar .item.active");
          if (item) { item.classList.add("done"); var ico = item.querySelector(".ico i"); if (ico) ico.className = "bi bi-check-circle-fill"; }
          completeForm.outerHTML = '<div class="d-inline-flex align-items-center gap-2 text-success fw-semibold"><i class="bi bi-check-circle-fill"></i> Completed</div>' +
            (completeForm.dataset.nextUrl ? ' <a class="btn btn-primary ms-3" href="' + completeForm.dataset.nextUrl + '">Continue <i class="bi bi-arrow-right"></i></a>' : "");
        })
        .catch(function () { btn.disabled = false; completeForm.submit(); });
    });
  }

  // Simple card-number formatting on checkout.
  var card = document.querySelector("input[name=card_number]");
  if (card) {
    card.addEventListener("input", function () {
      var v = card.value.replace(/\D/g, "").slice(0, 16);
      card.value = v.replace(/(.{4})/g, "$1 ").trim();
    });
  }
  var expiry = document.querySelector("input[name=expiry]");
  if (expiry) {
    expiry.addEventListener("input", function () {
      var v = expiry.value.replace(/\D/g, "").slice(0, 4);
      expiry.value = v.length > 2 ? v.slice(0, 2) + "/" + v.slice(2) : v;
    });
  }
})();
