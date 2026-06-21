document.addEventListener("DOMContentLoaded", () => {
  const cameraBtn = document.getElementById("camera-btn");
  const cameraPreview = document.getElementById("camera-preview");
  const cameraFeed = document.getElementById("camera-feed");
  const captureBtn = document.getElementById("capture-btn");
  const fileInput = document.getElementById("file-input");
  const previewGrid = document.getElementById("preview-grid");
  const uploadSubmit = document.getElementById("upload-submit");

  let stream = null;
  const capturedImages = []; // [{ blob, url }]
  const pendingFiles = []; // [File]

  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function updateSubmitState() {
    if (!uploadSubmit) return;
    uploadSubmit.disabled = capturedImages.length + pendingFiles.length === 0;
  }

  function renderPreviews() {
    if (!previewGrid) return;
    previewGrid.innerHTML = "";

    capturedImages.forEach((item, index) => {
      const div = document.createElement("div");
      div.className = "preview-item";

      const img = document.createElement("img");
      img.src = item.url;
      div.appendChild(img);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.dataset.index = String(index);
      removeBtn.textContent = "✕";
      removeBtn.addEventListener("click", () => {
        const idx = Number(removeBtn.dataset.index);
        URL.revokeObjectURL(capturedImages[idx].url);
        capturedImages.splice(idx, 1);
        renderPreviews();
      });
      div.appendChild(removeBtn);

      previewGrid.appendChild(div);
    });

    pendingFiles.forEach((file, index) => {
      const div = document.createElement("div");
      div.className = "preview-item";

      const url = URL.createObjectURL(file);
      const img = document.createElement("img");
      img.src = url;
      div.appendChild(img);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.dataset.index = String(index);
      removeBtn.textContent = "✕";
      removeBtn.addEventListener("click", () => {
        const idx = Number(removeBtn.dataset.index);
        URL.revokeObjectURL(url);
        pendingFiles.splice(idx, 1);
        renderPreviews();
      });
      div.appendChild(removeBtn);

      previewGrid.appendChild(div);
    });

    updateSubmitState();
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
  }

  if (cameraBtn) {
    cameraBtn.addEventListener("click", async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (cameraFeed) {
          cameraFeed.srcObject = stream;
        }
        if (cameraPreview) {
          cameraPreview.hidden = false;
        }
      } catch (err) {
        alert("Nao foi possivel acessar a camera. Verifique as permissoes.");
      }
    });
  }

  if (captureBtn) {
    captureBtn.addEventListener("click", () => {
      if (!cameraFeed || !cameraFeed.videoWidth) return;

      const canvas = document.createElement("canvas");
      canvas.width = cameraFeed.videoWidth;
      canvas.height = cameraFeed.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(cameraFeed, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        (blob) => {
          if (!blob) return;
          const url = URL.createObjectURL(blob);
          capturedImages.push({ blob, url });
          renderPreviews();
        },
        "image/jpeg",
        0.9
      );
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      Array.from(fileInput.files || []).forEach((file) => {
        pendingFiles.push(file);
      });
      fileInput.value = "";
      renderPreviews();
    });
  }

  async function uploadFiles() {
    const formData = new FormData();

    pendingFiles.forEach((file) => {
      formData.append("files", file, file.name);
    });

    capturedImages.forEach((item, index) => {
      formData.append("files", item.blob, `photo_${index}.jpg`);
    });

    const response = await fetch("/upload/", {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (response.redirected) {
      window.location.href = response.url;
      return;
    }

    const html = await response.text();
    document.open();
    document.write(html);
    document.close();
  }

  if (uploadSubmit) {
    uploadSubmit.addEventListener("click", async () => {
      if (capturedImages.length + pendingFiles.length === 0) return;

      stopCamera();

      const originalText = uploadSubmit.textContent;
      uploadSubmit.disabled = true;
      uploadSubmit.textContent = "Enviando...";

      try {
        await uploadFiles();
      } catch (err) {
        uploadSubmit.disabled = false;
        uploadSubmit.textContent = originalText;
        alert("Falha ao enviar os arquivos. Tente novamente.");
      }
    });
  }
});
