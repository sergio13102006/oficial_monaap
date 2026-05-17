(function () {
  // =========================
  // Inicializar comprobante
  // =========================
  function initComprobante() {
  const modalElement = document.getElementById("modalComprobante");
  const modalTitle = document.getElementById("modalComprobanteTitle");
  const previewBody = document.getElementById("comprobantePreviewBody");
  const btnDescargar = document.getElementById("btnDescargarComprobante");

    if (!modalElement || !previewBody || !btnDescargar) {
      console.error("No se encontraron los elementos del comprobante.");
      return;
    }

    let currentDocId = "";
    let currentExcelUrl = "";
    let currentDownloadName = "comprobante";
    const loadingHTML = `
      <div class="comprobante-loading">
        <div class="spinner-border" role="status"></div>
        <p class="mt-3 mb-0">Cargando vista previa...</p>
      </div>
    `;

    const errorHTML = (message) => `
      <div class="alert alert-danger mb-0">
        <strong>Error:</strong> ${message}
      </div>
    `;

    // =========================
    // Esperar carga de imágenes
    // =========================
    function waitForImages(root) {
      const images = Array.from(root.querySelectorAll("img"));

      return Promise.all(
        images.map((img) => {
          if (img.complete && img.naturalWidth > 0) {
            return Promise.resolve();
          }

          return new Promise((resolve) => {
            const done = () => resolve();
            img.addEventListener("load", done, { once: true });
            img.addEventListener("error", done, { once: true });
          });
        })
      );
    }

    function applyWatermarks(root) {
      root.querySelectorAll(".invoice-watermark-premium[data-watermark-src]").forEach((el) => {
        const src = el.dataset.watermarkSrc;
        if (src) {
          el.style.backgroundImage = `url('${src}')`;
        }
      });
    }

    // =========================
    // Descargar PDF desde la vista previa
    // =========================
    async function descargarPreviewComoPDF() {
      if (typeof html2pdf === "undefined") {
        throw new Error("html2pdf.js no está disponible.");
      }

      const comprobante = previewBody.querySelector(".invoice-sheet-premium");
      if (!comprobante) {
        throw new Error("No se encontró la vista previa del comprobante.");
      }

      const wrapper = document.createElement("div");
      wrapper.style.position = "fixed";
      wrapper.style.left = "-99999px";
      wrapper.style.top = "0";
      wrapper.style.width = "210mm";
      wrapper.style.background = "#ffffff";
      wrapper.style.zIndex = "-1";

      const clone = comprobante.cloneNode(true);
      clone.classList.add("pdf-export-sheet");
      clone.style.margin = "0";
      clone.style.boxShadow = "none";
      clone.style.border = "0";

      wrapper.appendChild(clone);
      document.body.appendChild(wrapper);

      try {
        await waitForImages(clone);
        const filename = currentDocId
          ? `${currentDownloadName}_${currentDocId}.pdf`
          : `${currentDownloadName}.pdf`;
        const opt = {
          margin: [4, 4, 4, 4],
          filename: filename,
          image: { type: "jpeg", quality: 0.98 },
          html2canvas: {
            scale: 2,
            useCORS: true,
            backgroundColor: "#f7f0e8",
            scrollX: 0,
            scrollY: 0,
          },
          jsPDF: {
            unit: "mm",
            format: "a4",
            orientation: "portrait",
          },
          pagebreak: {
            mode: ["avoid-all", "css", "legacy"],
          },
        };
        await html2pdf().set(opt).from(clone).save();
      } finally {
        wrapper.remove();
      }
    }

    // =========================
    // Abrir vista previa en modal
    // =========================
    document.addEventListener("click", async function (event) {
      const trigger = event.target.closest(".js-open-comprobante");
      if (!trigger) return;
      const previewUrl = trigger.dataset.previewUrl;
      const excelUrl = trigger.dataset.excelUrl;
      const modalCustomTitle = trigger.dataset.modalTitle;
      const downloadName = trigger.dataset.downloadName;

      currentDocId = trigger.dataset.compraId || trigger.dataset.devolucionId || "";
      currentExcelUrl = excelUrl || "";
      currentDownloadName = downloadName || "comprobante";

      if (modalTitle) {
        modalTitle.textContent = modalCustomTitle || "Comprobante";
      }
      previewBody.innerHTML = loadingHTML;

      try {
        const response = await fetch(previewUrl, {
          method: "GET",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const text = await response.text();

        let data;
        try {
          data = JSON.parse(text);
        } catch (e) {
          throw new Error("La respuesta no fue JSON válido.");
        }

        if (!response.ok || !data.success) {
          throw new Error(data.message || "No se pudo cargar la vista previa.");
        }

        previewBody.innerHTML = data.html;
        applyWatermarks(previewBody);
      } catch (error) {
        console.error("ERROR FETCH COMPROBANTE:", error);
        previewBody.innerHTML = errorHTML(error.message || "Error inesperado.");
      }
    });

    // =========================
    // Descargar PDF o Excel
    // =========================
        btnDescargar.addEventListener("click", async function () {
      if (!previewBody.querySelector(".invoice-sheet-premium")) {
        Swal.fire({
          icon: "warning",
          title: "Sin comprobante",
          text: "Primero abre un comprobante.",
        });
        return;
      }

      let result;

      if (currentExcelUrl) {
        result = await Swal.fire({
          title: "Descargar comprobante",
          text: "Selecciona el formato",
          icon: "question",
          showCancelButton: true,
          showDenyButton: true,
          confirmButtonText: "PDF",
          denyButtonText: "Excel",
          cancelButtonText: "Cancelar",
          reverseButtons: true,
          buttonsStyling: false,
          customClass: {
            confirmButton: "btn btn-danger me-2",
            denyButton: "btn btn-success me-2",
            cancelButton: "btn btn-secondary",
          },
        });
      } else {
        result = await Swal.fire({
          title: "Descargar comprobante",
          text: "Se descargará en PDF.",
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "PDF",
          cancelButtonText: "Cancelar",
          reverseButtons: true,
          buttonsStyling: false,
          customClass: {
            confirmButton: "btn btn-danger me-2",
            cancelButton: "btn btn-secondary",
          },
        });
      }

      if (result.isConfirmed) {
        try {
          Swal.fire({
            title: "Generando PDF...",
            text: "Espera un momento",
            allowOutsideClick: false,
            didOpen: () => {
              Swal.showLoading();
            },
          });

          await descargarPreviewComoPDF();
          Swal.close();
        } catch (error) {
          Swal.fire({
            icon: "error",
            title: "No se pudo descargar",
            text: error.message || "Error generando el PDF.",
          });
        }
      } else if (result.isDenied) {
        if (!currentExcelUrl) {
          Swal.fire({
            icon: "warning",
            title: "Sin archivo",
            text: "No se encontró la ruta del Excel.",
          });
          return;
        }

        window.location.href = currentExcelUrl;
      }
    });

      }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initComprobante);
  } else {
    initComprobante();
  }
})();
