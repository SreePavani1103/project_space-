/* =========================================================
   SKILL SYNTH AI — analyze.js
   Analysis form handler with drag-drop, loading animation
   ========================================================= */

(function () {
    "use strict";

    // Load roles into selector
    async function loadRoles() {
        try {
            const resp = await fetch("/api/roles");
            const data = await resp.json();
            const select = document.getElementById("targetRoleSelect");
            if (data.roles) {
                data.roles.forEach((r) => {
                    const opt = document.createElement("option");
                    opt.value = r.name;
                    opt.textContent = `${r.name} (${r.skills_count} skills)`;
                    select.appendChild(opt);
                });
            }
        } catch (e) {
            console.warn("Failed to load roles:", e);
        }
    }

    // Role selector → input sync
    const roleSelect = document.getElementById("targetRoleSelect");
    const roleInput = document.getElementById("targetRole");
    if (roleSelect && roleInput) {
        roleSelect.addEventListener("change", () => {
            if (roleSelect.value) roleInput.value = roleSelect.value;
        });
    }

    // File upload UI
    const fileInput = document.getElementById("resume");
    const zone = document.getElementById("fileUploadZone");
    const content = zone?.querySelector(".file-upload__content");
    const selected = zone?.querySelector(".file-upload__selected");
    const fileName = zone?.querySelector(".file-upload__name");
    const removeBtn = zone?.querySelector(".file-upload__remove");

    if (fileInput && zone) {
        // Drag & drop
        zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
        zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
        zone.addEventListener("drop", (e) => {
            e.preventDefault();
            zone.classList.remove("drag-over");
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                showFile(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener("change", () => {
            if (fileInput.files.length) showFile(fileInput.files[0]);
        });

        removeBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            fileInput.value = "";
            content.style.display = "";
            selected.style.display = "none";
        });
    }

    function showFile(file) {
        if (content && selected && fileName) {
            content.style.display = "none";
            selected.style.display = "flex";
            fileName.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        }
    }

    // Loading steps animation
    function animateLoader() {
        const steps = document.querySelectorAll(".loader-step");
        let i = 0;
        const interval = setInterval(() => {
            if (i < steps.length) {
                steps[i].classList.add("active");
                if (i === steps.length - 1) {
                    steps[i].classList.add("pulsing");
                }
                i++;
            }
        }, 3000);
        return interval;
    }

    // Form submission
    const form = document.getElementById("analyzeForm");
    const loader = document.getElementById("analysisLoader");
    const errorDiv = document.getElementById("analyzeError");

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("analyzeBtn");
            const originalBtnText = btn ? btn.innerHTML : "";
            errorDiv.style.display = "none";

            // Validate
            const targetRole = roleInput.value.trim();
            if (!targetRole) {
                errorDiv.textContent = "Please select or type a target role.";
                errorDiv.style.display = "block";
                return;
            }

            // Show loader, disable button
            if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Analyzing...'; }
            form.style.display = "none";
            loader.style.display = "flex";
            const loaderInterval = animateLoader();

            // BUG 9 FIX: centralised function to restore form state on any error
            function restoreForm(errMsg) {
                clearInterval(loaderInterval);
                loader.style.display = "none";
                form.style.display = "";
                if (btn) { btn.disabled = false; btn.innerHTML = originalBtnText; }
                errorDiv.textContent = errMsg;
                errorDiv.style.display = "block";
            }

            try {
                const formData = new FormData(form);
                const resp = await fetch("/api/analyze", {
                    method: "POST",
                    body: formData,
                });
                const data = await resp.json();

                if (data.job_id) {
                    pollStatus(data.job_id, loaderInterval, restoreForm);
                } else if (data.error) {
                    restoreForm(data.error);
                } else {
                    restoreForm("Failed to start analysis.");
                }
            } catch (err) {
                restoreForm(err.message);
            }
        });
    }

    // BUG 3 FIX: 'stopped' flag prevents recursive setTimeout from firing
    // after an error has already been shown and the form restored.
    async function pollStatus(jobId, loaderInterval, restoreForm) {
        let stopped = false;

        async function doPoll() {
            if (stopped) return;
            try {
                const resp = await fetch(`/api/status/${jobId}`);
                if (!resp.ok) throw new Error(`Server returned ${resp.status}`);
                const data = await resp.json();

                if (data.status === "finished" && data.report_id) {
                    stopped = true;
                    clearInterval(loaderInterval);
                    window.location.href = `/dashboard/report/${data.report_id}`;
                } else if (data.status === "failed") {
                    stopped = true;
                    restoreForm(data.error || "Analysis task failed.");
                } else {
                    // Update progress text in loader UI
                    if (data.progress) {
                        const title = document.querySelector(".loader-card h2");
                        if (title) title.textContent = data.progress;
                    }
                    // Schedule next poll only if not stopped
                    if (!stopped) setTimeout(doPoll, 1500);
                }
            } catch (err) {
                if (!stopped) {
                    stopped = true;
                    restoreForm(err.message);
                }
            }
        }

        doPoll();
    }

    // Init
    loadRoles();
})();
