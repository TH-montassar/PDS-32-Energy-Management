// ==================== CONFIGURATION ====================
const API_BASE = window.location.origin + "/api";
let powerChart, environmentChart;

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 Dashboard initializing...");
  initCharts();
  fetchAllData();

  // Auto-refresh every 5 seconds
  setInterval(fetchAllData, 5000);
});

// ==================== INITIALIZE CHARTS ====================
function initCharts() {
  // Power Chart
  const powerCtx = document.getElementById("powerChart").getContext("2d");
  powerChart = new Chart(powerCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Puissance (W)",
          data: [],
          borderColor: "#667eea",
          backgroundColor: "rgba(102, 126, 234, 0.1)",
          fill: true,
          tension: 0.4,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Puissance (W)",
          },
        },
        x: {
          title: {
            display: true,
            text: "Temps",
          },
        },
      },
    },
  });

  // Environment Chart
  const envCtx = document.getElementById("environmentChart").getContext("2d");
  environmentChart = new Chart(envCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Température (°C)",
          data: [],
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          yAxisID: "y",
          tension: 0.4,
          borderWidth: 2,
        },
        {
          label: "Humidité (%)",
          data: [],
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          yAxisID: "y1",
          tension: 0.4,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
      },
      scales: {
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: "Température (°C)",
          },
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Humidité (%)",
          },
          grid: {
            drawOnChartArea: false,
          },
        },
      },
    },
  });

  console.log("✓ Charts initialized");
}

// ==================== FETCH ALL DATA ====================
async function fetchAllData() {
  try {
    await Promise.all([
      fetchCurrentEnergy(),
      fetchCurrentSensors(),
      fetchCurrentPresence(),
      fetchActuatorsStatus(),
      fetchAnalytics(),
      fetchEnergyHistory(),
      fetchAlerts(),
      updateLiveStatus(),
    ]);

    updateLastUpdateTime();
  } catch (error) {
    console.error("❌ Error fetching data:", error);
  }
}

// ==================== API CALLS ====================
// ... après fetchAlerts() ...

async function updateLiveStatus() {
  try {
    // Utilise directement API_BASE + le chemin
    const response = await fetch(`${API_BASE}/status/live`);
    const data = await response.json();

    const container = document.getElementById("deviceStatusContainer");
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");

    // DEBUG : Ajoute ce log pour voir ce que le JS reçoit vraiment
    console.log("Statut reçu du serveur:", data);

    if (data.status === "online") {
      container.style.backgroundColor = "#10b981"; // Vert
      text.innerText = "LIVE";
      dot.classList.add("pulse-dot");
    } else {
      container.style.backgroundColor = "#ef4444"; // Rouge
      text.innerText = "DOWN";
      dot.classList.remove("pulse-dot");
    }
    text.style.color = "#ffffff";
    dot.style.backgroundColor = "#ffffff";
  } catch (err) {
    console.error("Erreur Fetch Statut:", err);
  }
}
async function fetchCurrentEnergy() {
  try {
    const response = await fetch(`${API_BASE}/energy/current`);
    if (!response.ok) return;

    const data = await response.json();

    document.getElementById("currentPower").innerHTML = `${data.power.toFixed(
      2
    )}<span class="metric-unit">W</span>`;
    document.getElementById(
      "currentCurrent"
    ).innerHTML = `${data.current.toFixed(
      2
    )}<span class="metric-unit">A</span>`;
    document.getElementById(
      "totalEnergy"
    ).innerHTML = `${data.energy_total.toFixed(
      3
    )}<span class="metric-unit">kWh</span>`;
    document.getElementById("currentCost").innerHTML = `${data.cost.toFixed(
      3
    )}<span class="metric-unit">TND</span>`;

    highlightElement("currentPower");
  } catch (error) {
    console.error("Error fetching energy:", error);
  }
}

async function fetchCurrentSensors() {
  try {
    const response = await fetch(`${API_BASE}/sensors/current`);
    if (!response.ok) return;

    const data = await response.json();

    document.getElementById(
      "temperature"
    ).innerHTML = `${data.temperature.toFixed(
      1
    )}<span class="metric-unit">°C</span>`;
    document.getElementById("humidity").innerHTML = `${data.humidity.toFixed(
      1
    )}<span class="metric-unit">%</span>`;
    document.getElementById(
      "lightLevel"
    ).innerHTML = `${data.light_level}<span class="metric-unit">%</span>`;
  } catch (error) {
    console.error("Error fetching sensors:", error);
  }
}

async function fetchCurrentPresence() {
  try {
    const response = await fetch(`${API_BASE}/presence/current`);
    if (!response.ok) return;

    const data = await response.json();

    const indicator = document.getElementById("presenceIndicator");
    const text = document.getElementById("presenceText");

    if (data.presence) {
      indicator.className = "status-indicator status-on";
      text.textContent = "Détectée";
      text.style.color = "#10b981";
    } else {
      indicator.className = "status-indicator status-off";
      text.textContent = "Absente";
      text.style.color = "#ef4444";
    }
  } catch (error) {
    console.error("Error fetching presence:", error);
  }
}

async function fetchActuatorsStatus() {
  try {
    const response = await fetch(`${API_BASE}/actuators/status`);
    if (!response.ok) return;

    const data = await response.json();

    updateRelayStatus("relay1", data.relay1);
    updateRelayStatus("relay2", data.relay2);
    updateRelayStatus("window", data.window || false);

    const autoStatus = document.getElementById("autoModeStatus");
    if (data.auto_mode) {
      autoStatus.innerHTML =
        '<span style="color: #10b981; font-weight: bold;">✓ ACTIF</span>';
    } else {
      autoStatus.innerHTML =
        '<span style="color: #ef4444; font-weight: bold;">✗ INACTIF</span>';
    }
  } catch (error) {
    console.error("Error fetching actuators:", error);
  }
}

function updateRelayStatus(relayId, state) {
  const indicator = document.getElementById(`${relayId}Indicator`);
  const status = document.getElementById(`${relayId}Status`);

  if (state) {
    indicator.className = "status-indicator status-on";
    status.innerHTML =
      '<span style="color: #10b981; font-weight: bold;">ON</span>';
  } else {
    indicator.className = "status-indicator status-off";
    status.innerHTML =
      '<span style="color: #ef4444; font-weight: bold;">OFF</span>';
  }
}

async function fetchAnalytics() {
  try {
    const response = await fetch(`${API_BASE}/analytics/consumption`);
    if (!response.ok) return;

    const data = await response.json();

    document.getElementById(
      "todayEnergy"
    ).innerHTML = `${data.today.energy.toFixed(
      3
    )}<span class="metric-unit">kWh</span>`;
    document.getElementById("todayCost").innerHTML = `${data.today.cost.toFixed(
      3
    )}<span class="metric-unit">TND</span>`;
    document.getElementById(
      "monthlyEstimate"
    ).innerHTML = `${data.monthly_estimate.toFixed(
      2
    )}<span class="metric-unit">TND</span>`;
    document.getElementById(
      "potentialSavings"
    ).innerHTML = `${data.potential_savings.toFixed(
      3
    )}<span class="metric-unit">TND</span>`;

    document.getElementById(
      "avgPower"
    ).innerHTML = `${data.average_power.toFixed(
      2
    )}<span class="metric-unit">W</span>`;
    document.getElementById("peakPower").innerHTML = `${data.peak.power.toFixed(
      2
    )}<span class="metric-unit">W</span>`;

    if (data.peak.time) {
      const time = new Date(data.peak.time).toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      });
      document.getElementById("peakTime").textContent = time;
    }

    // Comparison
    const diff = data.today.energy - data.yesterday.energy;
    const percentage =
      data.yesterday.energy > 0
        ? ((diff / data.yesterday.energy) * 100).toFixed(1)
        : 0;
    const comparisonEl = document.getElementById("comparison");

    if (diff > 0) {
      comparisonEl.innerHTML = `<span style="color: #ef4444;">+${percentage}%</span>`;
    } else {
      comparisonEl.innerHTML = `<span style="color: #10b981;">${percentage}%</span>`;
    }
  } catch (error) {
    console.error("Error fetching analytics:", error);
  }
}

async function fetchEnergyHistory() {
  try {
    const response = await fetch(`${API_BASE}/energy/history?hours=24`);
    if (!response.ok) return;

    const data = await response.json();

    if (data.length === 0) return;

    const labels = data.map((item) => {
      const date = new Date(item.timestamp);
      return date.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      });
    });

    const powers = data.map((item) => item.power);

    powerChart.data.labels = labels;
    powerChart.data.datasets[0].data = powers;
    powerChart.update("none");
  } catch (error) {
    console.error("Error fetching history:", error);
  }
}

async function fetchAlerts() {
  try {
    const response = await fetch(`${API_BASE}/alerts`);
    if (!response.ok) return;

    const alerts = await response.json();

    const container = document.getElementById("alertsContainer");

    if (alerts.length === 0) {
      container.innerHTML =
        '<div class="alert alert-info">✓ Aucune alerte active</div>';
      return;
    }

    container.innerHTML = "";
    alerts.slice(0, 5).forEach((alert) => {
      const alertDiv = document.createElement("div");
      alertDiv.className = `alert alert-${alert.severity.toLowerCase()}`;
      const time = new Date(alert.timestamp).toLocaleString("fr-FR");

      alertDiv.innerHTML = `
                    <div class="alert-message">
                        <strong>${getAlertIcon(alert.severity)} ${
        alert.message
      }</strong>
                        <div class="alert-time">${time}</div>
                    </div>
                    ${
                      !alert.resolved
                        ? `<button class="btn-resolve" onclick="resolveAlert(${alert.id})">Résoudre</button>`
                        : '<span style="color: #10b981; font-weight: bold;">✓ Résolu</span>'
                    }
                `;

      container.appendChild(alertDiv);
    });
  } catch (error) {
    console.error("Error fetching alerts:", error);
  }
}

function getAlertIcon(severity) {
  switch (severity.toUpperCase()) {
    case "CRITICAL":
      return "🔴";
    case "WARNING":
      return "⚠️";
    case "INFO":
      return "ℹ️";
    default:
      return "📋";
  }
}

// ==================== CONTROL FUNCTIONS ====================

async function controlRelay(command) {
  try {
    const response = await fetch(`${API_BASE}/control/relay`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
      throw new Error("Command failed");
    }

    const result = await response.json();
    console.log("✓ Command sent:", result);

    showNotification(`Commande "${command}" envoyée avec succès`, "success");

    // Update immediately
    setTimeout(fetchActuatorsStatus, 1000);
  } catch (error) {
    console.error("❌ Error sending command:", error);
    showNotification("Erreur lors de l'envoi de la commande", "error");
  }
}

async function resolveAlert(alertId) {
  try {
    await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: "PUT",
    });

    fetchAlerts();
    showNotification("Alerte résolue", "success");
  } catch (error) {
    console.error("Error resolving alert:", error);
  }
}

// ==================== UTILITY FUNCTIONS ====================

function updateLastUpdateTime() {
  const now = new Date().toLocaleTimeString("fr-FR");
  document.getElementById(
    "lastUpdate"
  ).textContent = `Dernière mise à jour: ${now}`;
}

function highlightElement(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.closest(".metric").classList.add("highlight");
    setTimeout(() => {
      element.closest(".metric").classList.remove("highlight");
    }, 500);
  }
}

function showNotification(message, type) {
  // Create toast element
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    background: ${type === "success" ? "#10b981" : "#ef4444"};
    color: white;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    z-index: 9999;
    animation: slideInRight 0.3s ease;
  `;

  const icon = type === "success" ? "✓" : "✗";
  toast.textContent = `${icon} ${message}`;

  document.body.appendChild(toast);

  // Remove after 3 seconds
  setTimeout(() => {
    toast.style.animation = "slideOutRight 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
