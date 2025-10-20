const API_BASE = "/api";
let videoEl;
let employeeId = null;
let collected = [];

async function loadModels() {
    const base = "https://cdn.jsdelivr.net/npm/face-api.js/models";
    await faceapi.nets.tinyFaceDetector.loadFromUri(base);
    await faceapi.nets.faceLandmark68Net.loadFromUri(base);
    await faceapi.nets.faceRecognitionNet.loadFromUri(base);
}

function setStatus(t) {
    document.getElementById("statusText").textContent =
        t;
}

async function startCam() {
    videoEl = document.getElementById("video");
    const stream = await navigator.mediaDevices.getUserMedia({video: true});
    videoEl.srcObject = stream;
    await new Promise(r => videoEl.onloadedmetadata = r);
}

async function createEmployee(name) {
    const res = await fetch(`${API_BASE}/employees/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"}, body:
            JSON.stringify({name})
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json(); // {id, name}
}

async function captureEmbedding() {
    const det = await faceapi.detectSingleFace(videoEl, new
    faceapi.TinyFaceDetectorOptions({inputSize: 320}))
        .withFaceLandmarks().withFaceDescriptor();
    if (!det) {
        setStatus("No se detecta rostro");
        return;
    }
    collected.push(Array.from(det.descriptor));
    setStatus(`Muestras: ${collected.length}`);
}

async function finishEnrollment() {
    const res = await fetch(`${API_BASE}/employees/${employeeId}/embeddings/`,
        {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({descriptors: collected})
        });
    if (!res.ok) throw new Error(await res.text());
    setStatus("Embeddings guardados");
    collected = [];
}

async function init() {
    setStatus("Cargando modelos...");
    await loadModels();
    setStatus("Listo");
    document.getElementById("startBtn").onclick = async () => {
        await startCam();
        document.getElementById("captureBtn").disabled = false;
    };
    document.getElementById("createEmpBtn").onclick = async () => {
        const name = document.getElementById("empName").value.trim();
        if (!name) return setStatus("Ingresa un nombre");
        const emp = await createEmployee(name);
        employeeId = emp.id;
        setStatus(`Empleado creado: ${emp.name} (ID ${emp.id})`);
        document.getElementById("finishBtn").disabled = false;
    };
    document.getElementById("captureBtn").onclick = captureEmbedding;
    document.getElementById("finishBtn").onclick = finishEnrollment;
}

window.addEventListener("DOMContentLoaded", init);