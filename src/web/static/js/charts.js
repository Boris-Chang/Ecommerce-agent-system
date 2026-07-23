(function () {
  function initializeCharts(root) {
    if (typeof echarts === "undefined") {
      return;
    }

    (root || document)
      .querySelectorAll("[data-chart-options]")
      .forEach(function (element) {
        var existing = echarts.getInstanceByDom(element);
        if (existing) {
          existing.dispose();
        }
        var options = JSON.parse(element.dataset.chartOptions);
        var chart = echarts.init(element);
        chart.setOption(options);
      });
  }

  function resizeCharts() {
    if (typeof echarts === "undefined") {
      return;
    }
    document.querySelectorAll("[data-chart-options]").forEach(function (element) {
      var chart = echarts.getInstanceByDom(element);
      if (chart) {
        chart.resize();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializeCharts(document);
  });
  document.body.addEventListener("htmx:afterSwap", function (event) {
    initializeCharts(event.detail.target);
  });
  document.body.addEventListener("htmx:beforeCleanupElement", function (event) {
    if (typeof echarts === "undefined") {
      return;
    }
    var chart = echarts.getInstanceByDom(event.detail.elt);
    if (chart) {
      chart.dispose();
    }
  });
  window.addEventListener("resize", resizeCharts);
  window.initializeCharts = initializeCharts;
})();
