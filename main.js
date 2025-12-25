const API_BASE = "http://127.0.0.1:8000";

async function loadWeather() {
  const name = document.getElementById("name").value || "Chennai";
  const lat = parseFloat(document.getElementById("lat").value);
  const lon = parseFloat(document.getElementById("lon").value);

  document.getElementById("error").textContent = "";
  document.getElementById("status").textContent = "Loading...";

  try {
    const url = `${API_BASE}/full?lat=${lat}&lon=${lon}&name=${encodeURIComponent(name)}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    document.getElementById("status").textContent = "";

    renderCurrent(data);
    renderToday(data);
    renderTomorrow(data);
    renderHourly("today-hourly", data.today?.hourly || []);
    renderHourly("tomorrow-hourly", data.tomorrow?.hourly || []);
    renderAir(data);
    renderCharts(data);
  } catch (err) {
    document.getElementById("status").textContent = "";
    document.getElementById("error").textContent = "Failed to load weather: " + err;
  }
}

function renderCurrent(data) {
  const c = data.current || {};
  const loc = data.location || {};
  const el = document.getElementById("current");
  el.innerHTML = `
    <h2>${loc.name || ""}</h2>
    <div>${c.time || ""}</div>
    <p>
      <strong>${c.temp_c?.toFixed?.(1) ?? "–"} °C</strong>
      &nbsp;(${c.precip_status || ""})
    </p>
    <div class="small">
      Feels like: ${c.feels_like_c?.toFixed?.(1) ?? "–"} °C ·
      Humidity: ${c.humidity ?? "–"}% ·
      Wind: ${c.wind_kph ?? "–"} km/h ·
      Last precip: ${c.precip_mm_last ?? 0} mm
    </div>
  `;
}

function renderToday(data) {
  const t = data.today?.summary || {};
  const el = document.getElementById("today");
  el.innerHTML = `
    <h3>Today</h3>
    <div>${t.date || ""}</div>
    <p>Max: ${t.max_c ?? "–"} °C · Min: ${t.min_c ?? "–"} °C</p>
    <div class="small">${t.status || ""}</div>
  `;
}

function renderTomorrow(data) {
  const t = data.tomorrow?.summary || {};
  const el = document.getElementById("tomorrow");
  const ml = data.tomorrow?.ml_max_temp_c;
  el.innerHTML = `
    <h3>Tomorrow</h3>
    <div>${t.date || ""}</div>
    <p>
      Provider max: ${t.max_c != null ? t.max_c.toFixed(3) : "–"} °C<br/>
      Your model max: ${ml != null ? ml.toFixed(6) : "–"} °C
    </p>
    <div class="small">${t.status || ""}</div>
  `;
}

function renderHourly(containerId, list) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  list.forEach((h) => {
    const div = document.createElement("div");
    const time = (h.time || "").slice(11, 16);
    div.className = "hour-item";
    div.innerHTML = `
      <div class="hour-time">${time}</div>
      <div class="hour-temp">${(h.temp_c ?? NaN).toFixed ? h.temp_c.toFixed(1) : "–"} °C</div>
      <div class="hour-label">Status:</div>
      <div class="hour-value">${h.status || "–"}</div>
      <div class="hour-label">Precipitation:</div>
      <div class="hour-value">${h.precip_mm != null ? h.precip_mm.toFixed(2) + " mm" : "–"}</div>
      <div class="hour-label">Chance:</div>
      <div class="hour-value">${h.precip_prob != null ? h.precip_prob + " %" : "–"}</div>
      <div class="hour-label">Humidity:</div>
      <div class="hour-value">${h.humidity != null ? h.humidity + " %" : "–"}</div>
      <div class="hour-label">Wind:</div>
      <div class="hour-value">${h.wind_kph != null ? h.wind_kph.toFixed(1) + " km/h" : "–"}</div>
    `;
    container.appendChild(div);
  });
}


function renderAir(data) {
  const aq = data.air_quality || {};
  const el = document.getElementById("air");
  if (!aq.time) {
    el.innerHTML = "<h3>Air quality</h3><div class='small'>No data</div>";
    return;
  }
  el.innerHTML = `
    <h3>Air quality</h3>
    <div class="small">${aq.time}</div>
    <p>US AQI: ${aq.us_aqi ?? "–"} · PM2.5: ${aq.pm2_5 ?? "–"} µg/m³</p>
  `;
}

let tempChart, rainChart, windChart, humidityChart;

function renderCharts(data) {
  const todayHours = data.today?.hourly || [];
  const tomorrowHours = data.tomorrow?.hourly || [];

  const labelsToday = todayHours.map(h => h.time);
  const labelsTomorrow = tomorrowHours.map(h => h.time);

  const tempToday = todayHours.map(h => h.temp_c);
  const tempTomorrow = tomorrowHours.map(h => h.temp_c);
  const rainToday = todayHours.map(h => h.precip_mm);
  const rainTomorrow = tomorrowHours.map(h => h.precip_mm);
  const windToday = todayHours.map(h => h.wind_kph);
  const windTomorrow = tomorrowHours.map(h => h.wind_kph);
  const humToday = todayHours.map(h => h.humidity);
  const humTomorrow = tomorrowHours.map(h => h.humidity);

  const tempTomorrowModel = (data.tomorrow?.ml_hourly_temp || []).map(x => x ?? null);

  if (tempChart) tempChart.destroy();
  if (rainChart) rainChart.destroy();
  if (windChart) windChart.destroy();
  if (humidityChart) humidityChart.destroy();

  const tempCtx = document.getElementById("tempChart").getContext("2d");
  tempChart = new Chart(tempCtx, {
    type: "line",
    data: {
      labels: labelsToday.concat(labelsTomorrow),
      datasets: [
        {
          label: "Today temp (API)",
          data: tempToday.concat(new Array(tempTomorrow.length).fill(null)),
          borderColor: "rgba(54, 162, 235, 1)",
          tension: 0.2
        },
        {
          label: "Tomorrow temp (API)",
          data: new Array(tempToday.length).fill(null).concat(tempTomorrow),
          borderColor: "rgba(255, 159, 64, 1)",
          tension: 0.2
        },
        {
          label: "Tomorrow temp (model)",
          data: new Array(tempToday.length).fill(null).concat(tempTomorrowModel),
          borderColor: "rgba(255, 99, 132, 1)",
          borderDash: [5, 5],
          tension: 0.2
        }
      ]
    }
  });

  const rainCtx = document.getElementById("rainChart").getContext("2d");
  rainChart = new Chart(rainCtx, {
    type: "line",
    data: {
      labels: labelsToday.concat(labelsTomorrow),
      datasets: [
        {
          label: "Today rain (mm)",
          data: rainToday.concat(new Array(rainTomorrow.length).fill(null)),
          borderColor: "rgba(75, 192, 192, 1)",
          tension: 0.2
        },
        {
          label: "Tomorrow rain (mm)",
          data: new Array(rainToday.length).fill(null).concat(rainTomorrow),
          borderColor: "rgba(153, 102, 255, 1)",
          tension: 0.2
        }
      ]
    }
  });

  const windCtx = document.getElementById("windChart").getContext("2d");
  windChart = new Chart(windCtx, {
    type: "line",
    data: {
      labels: labelsToday.concat(labelsTomorrow),
      datasets: [
        {
          label: "Today wind (km/h)",
          data: windToday.concat(new Array(windTomorrow.length).fill(null)),
          borderColor: "rgba(201, 203, 207, 1)",
          tension: 0.2
        },
        {
          label: "Tomorrow wind (km/h)",
          data: new Array(windToday.length).fill(null).concat(windTomorrow),
          borderColor: "rgba(99, 255, 132, 1)",
          tension: 0.2
        }
      ]
    }
  });

  const humCtx = document.getElementById("humidityChart").getContext("2d");
  humidityChart = new Chart(humCtx, {
    type: "line",
    data: {
      labels: labelsToday.concat(labelsTomorrow),
      datasets: [
        {
          label: "Today humidity (%)",
          data: humToday.concat(new Array(humTomorrow.length).fill(null)),
          borderColor: "rgba(255, 206, 86, 1)",
          tension: 0.2
        },
        {
          label: "Tomorrow humidity (%)",
          data: new Array(humToday.length).fill(null).concat(humTomorrow),
          borderColor: "rgba(54, 162, 235, 1)",
          tension: 0.2
        }
      ]
    }
  });
}

// auto-load Chennai when page opens
// Auto-load when page opens and refresh periodically
window.addEventListener("load", () => {
  loadWeather();                          // initial load
  setInterval(loadWeather, 1000 * 60 * 60);  // refresh every 1 hour
});

