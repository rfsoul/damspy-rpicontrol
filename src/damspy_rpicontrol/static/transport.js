(function () {
  const mode = document.getElementById("transport-mode");
  const port = document.getElementById("transport-port");
  const applyButton = document.getElementById("transport-apply");
  const status = document.getElementById("transport-status");
  const pathHelp = document.getElementById("transport-path-help");
  const surveyButton = document.getElementById("survey-start");
  if (!mode || !port || !applyButton || !status) return;

  function show(payload) {
    mode.value = payload.mode;
    port.value = payload.mode === "m5" && payload.serial_port
      ? "M5 Gateway detected"
      : "Detected automatically";
    status.textContent = `${payload.connected ? "Connected" : "Disconnected"}: ${payload.detail}`;
    status.dataset.connected = String(payload.connected);
    if (pathHelp) {
      pathHelp.textContent = payload.mode === "m5"
        ? "M5 path: this server → M5 Gateway → ESP-NOW → M5 Node → USB HID → RØDE product."
        : "USB path: this server → USB HID → RØDE product.";
    }
    if (surveyButton) surveyButton.disabled = payload.mode !== "m5";
  }

  async function request(endpoint, options) {
    const response = await fetch(endpoint, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    return payload;
  }

  mode.addEventListener("change", () => {
    port.disabled = true;
    if (pathHelp) {
      pathHelp.textContent = mode.value === "m5"
        ? "M5 path: this server → M5 Gateway → ESP-NOW → M5 Node → USB HID → RØDE product."
        : "USB path: this server → USB HID → RØDE product.";
    }
    if (surveyButton) surveyButton.disabled = mode.value !== "m5";
  });
  applyButton.addEventListener("click", async () => {
    applyButton.disabled = true;
    status.textContent = "Applying connection settings...";
    try {
      show(await request("/api/transport", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({mode: mode.value}),
      }));
    } catch (error) {
      status.textContent = `Disconnected: ${error.message}`;
    } finally {
      applyButton.disabled = false;
    }
  });

  if (surveyButton) {
    surveyButton.addEventListener("click", async () => {
      const warning = "Starting standalone range survey stops normal HID control until the M5 Gateway is reset. Continue?";
      if (!window.confirm(warning)) return;
      surveyButton.disabled = true;
      status.textContent = "Starting standalone range survey...";
      try {
        const payload = await request("/api/m5/survey/start", {method: "POST"});
        status.textContent = payload.detail;
      } catch (error) {
        status.textContent = error.message;
        surveyButton.disabled = mode.value !== "m5";
      }
    });
  }

  request("/api/transport").then(show).catch((error) => {
    status.textContent = `Disconnected: ${error.message}`;
  });
})();
