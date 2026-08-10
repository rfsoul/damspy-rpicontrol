(function () {
  const mode = document.getElementById("transport-mode");
  const port = document.getElementById("transport-port");
  const ports = document.getElementById("transport-ports");
  const applyButton = document.getElementById("transport-apply");
  const status = document.getElementById("transport-status");
  if (!mode || !port || !ports || !applyButton || !status) return;

  function show(payload) {
    mode.value = payload.mode;
    port.value = payload.serial_port || "/dev/ttyACM0";
    port.disabled = payload.mode !== "m5";
    ports.replaceChildren();
    (payload.available_serial_ports || []).forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      ports.appendChild(option);
    });
    status.textContent = `${payload.connected ? "Connected" : "Disconnected"}: ${payload.detail}`;
    status.dataset.connected = String(payload.connected);
  }

  async function request(endpoint, options) {
    const response = await fetch(endpoint, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    return payload;
  }

  mode.addEventListener("change", () => {
    port.disabled = mode.value !== "m5";
  });
  applyButton.addEventListener("click", async () => {
    applyButton.disabled = true;
    status.textContent = "Applying connection settings...";
    try {
      show(await request("/api/transport", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({mode: mode.value, serial_port: port.value}),
      }));
    } catch (error) {
      status.textContent = `Disconnected: ${error.message}`;
    } finally {
      applyButton.disabled = false;
    }
  });

  request("/api/transport").then(show).catch((error) => {
    status.textContent = `Disconnected: ${error.message}`;
  });
})();
