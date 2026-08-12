(function () {
  const form = document.getElementById("capture-form");
  const runButton = document.getElementById("run-capture");
  const downloadButton = document.getElementById("download");
  const output = document.getElementById("capture-output");
  let capture = null;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    runButton.disabled = true;
    downloadButton.hidden = true;
    output.textContent = "Running deterministic capture and best-effort cleanup...";
    try {
      const response = await fetch("/api/transport-capture", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          profile: document.getElementById("profile").value,
          transport: document.getElementById("capture-transport").value,
        }),
      });
      const responseText = await response.text();
      let body;
      try {
        body = JSON.parse(responseText);
      } catch (error) {
        throw new Error("HTTP " + response.status + ": " + (responseText || "empty response"));
      }
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
      capture = body;
      const all = [...body.operations, ...body.cleanup_operations];
      const errors = all.filter((operation) => operation.error !== null).length;
      const writes = all.reduce((count, operation) => count + operation.writes.length, 0);
      const reads = all.reduce((count, operation) => count + operation.reads.length, 0);
      output.textContent = JSON.stringify({
        selected_profile: body.selected_profile,
        transport: body.transport,
        physical_usb_device: body.physical_usb_device,
        operations: body.operations.length,
        cleanup_operations: body.cleanup_operations.length,
        writes,
        reads,
        exceptions_recorded: errors,
        download_filename: body.download_filename,
      }, null, 2);
      downloadButton.hidden = false;
    } catch (error) {
      capture = null;
      output.textContent = `Capture request failed: ${error.message}`;
    } finally {
      runButton.disabled = false;
    }
  });

  downloadButton.addEventListener("click", () => {
    if (!capture) return;
    const blob = new Blob([JSON.stringify(capture, null, 2) + "\n"], {type: "application/json"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = capture.download_filename;
    link.click();
    URL.revokeObjectURL(link.href);
  });
})();
