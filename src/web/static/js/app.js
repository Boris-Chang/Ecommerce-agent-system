document.addEventListener("DOMContentLoaded", function () {
  document.documentElement.classList.add("js-ready");
  document.querySelectorAll(".sku-expand-row").forEach(function (row) {
    row.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        row.click();
      }
    });
  });
});
