function updateDashboard(symbol) {
  fetch(`/coin-data/${symbol}/`)
    .then(response => response.json())
    .then(data => {
      // Update overview cards
      document.querySelector("#marketCap").innerText = `$${data.market_cap}`;
      document.querySelector("#volume24h").innerText = `$${data.volume_24h}`;
      document.querySelector("#btcDominance").innerText = `${data.btc_dominance}%`;
      document.querySelector("#fearGreed").innerText = data.fear_greed;

      // Update chart
      Highcharts.chart('bitcoinChart', {
        chart: { type: 'line', backgroundColor: 'transparent', height: 320 },
        title: { text: null },
        credits: { enabled: false },
        xAxis: { categories: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'] },
        yAxis: { title: { text: null } },
        series: [{
          name: `${data.name} Price`,
          data: data.price_history,
          color: '#14b8a6'
        }]
      });
    });
}

// Add click event to top coins and watchlist items
document.querySelectorAll('.coin-row').forEach(row => {
  row.addEventListener('click', () => {
    let symbol = row.dataset.symbol;
    updateDashboard(symbol);
  });
});
