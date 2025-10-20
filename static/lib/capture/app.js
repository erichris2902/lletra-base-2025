// Configuración
const API_BASE = "/rh/employee/";
const CONFIDENCE_THRESHOLD = 0.6;
const MARGIN_TOP2 = 0.12;
const VOTE_WINDOW = 7;
const COOLDOWN_MS = 2 * 60 * 1000;
let videoEl, canvasEl, ctx;
let running = false;
let labeledDescriptors = null;
let lastCheckByEmployee = new Map();
let votes = [];
let recognitionStartTime = null; // 👈 agregado

// Carga modelos y embeddings
async function loadModels() {
    const base = `${window.location.origin}/static/lib/capture/weights`;
    console.log("Loading models from", base);
    await faceapi.nets.tinyFaceDetector.loadFromUri(base);
    await faceapi.nets.faceLandmark68Net.loadFromUri(base);
    await faceapi.nets.faceRecognitionNet.loadFromUri(base);

    await faceapi.nets.faceExpressionNet.loadFromUri(base);
}

async function loadLabeledDescriptors() {
    const res = await fetch(`/rh/capture/embeddings`);
    const data = await res.json();

    return data.map(p => {
        let descriptors = [];

        for (let d of p.descriptors) {
            // Si el descriptor viene como string (ej. "[[...]]"), conviértelo
            if (typeof d === "string") {
                try {
                    const parsed = JSON.parse(d);
                    // algunos vienen como [[...]] en lugar de [...]
                    if (Array.isArray(parsed[0])) {
                        parsed.forEach(sub => descriptors.push(new Float32Array(sub)));
                    } else {
                        descriptors.push(new Float32Array(parsed));
                    }
                } catch (e) {
                    console.warn("⚠️ No se pudo parsear descriptor:", d, e);
                }
            } else if (Array.isArray(d)) {
                // ya es array real
                descriptors.push(new Float32Array(d));
            }
        }

        return new faceapi.LabeledFaceDescriptors(
            `${p.employee_id}::${p.name}`,
            descriptors
        );
    });
}

function setStatus(t) {
    document.getElementById("statusText").textContent = t;
}

async function startCamera() {
    videoEl = document.getElementById("video");
    canvasEl = document.getElementById("overlay");
    ctx = canvasEl.getContext("2d");
    const stream = await navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: "user"
        }, audio: false
    });
    videoEl.srcObject = stream;
    await new Promise(r => videoEl.onloadedmetadata = r);
    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;
}

function cosineSim(a, b) {
    if (!a || !b || a.length === 0 || b.length === 0) return 0;
    // Si alguno no tiene la longitud estándar, cancela comparación
    if (a.length !== b.length) {
        console.warn("⚠️ Descriptor size mismatch:", a.length, b.length);
        return 0;
    }

    let dot = 0, na = 0, nb = 0;
    for (let i = 0; i < a.length; i++) {
        const va = a[i];
        const vb = b[i];
        if (typeof va !== "number" || typeof vb !== "number") {
            console.warn("⚠️ Invalid embedding values at index", i, va, vb);
            return 0;
        }
        dot += va * vb;
        na += va * va;
        nb += vb * vb;
    }

    if (na === 0 || nb === 0) return 0;
    return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

function bestMatch(descriptor, labeled) {
    // Retorna top1 y top2 por similitud coseno
    let scores = [];
    for (const ld of labeled) {
        for (const d of ld.descriptors) {
            scores.push({label: ld.label, score: cosineSim(descriptor, d)});
        }
    }
    scores.sort((x, y) => y.score - x.score);
    const top1 = scores[0];
    const top2 = scores[1] || {score: 0, label: ""};
    return {top1, top2};

}

async function sendAttendance(employeeId, name, confidence, snapshotBlob, emotion) {
    const now = Date.now();
    const last = lastCheckByEmployee.get(employeeId) || 0;
    const COOLDOWN_MS = 5 * 60 * 1000; // ⏱️ 5 minutos

    // Evita duplicar registros dentro del cooldown
    if (now - last < COOLDOWN_MS) {
        const remaining = ((COOLDOWN_MS - (now - last)) / 1000).toFixed(0);
        console.log(`⏳ Esperando ${remaining}s para volver a registrar a ${name}`);
        setStatus(`⏳ ${name} ya fue registrado. Espera ${remaining}s...`);
        return;
    }

    const form = new FormData();
    form.append("employee_id", employeeId);
    form.append("action", "add_attendance");
    form.append("confidence", confidence.toFixed(3));
    form.append("emotion", emotion || "unknown");
    form.append("csrfmiddlewaretoken", csrfToken);
    if (snapshotBlob) form.append("snapshot", snapshotBlob, `snap_${Date.now()}.jpg`);

    // Envío con AJAX
    submit_with_ajax(`${API_BASE}`, form,
        function (data) {
            lastCheckByEmployee.set(employeeId, now); // 🧠 Registra el último tiempo
            setStatus(`✅ Asistencia registrada: ${name} (${(confidence * 100).toFixed(1)}%)`);
            const msg = `Asistencia registrada para ${name}.`;
            speakMessage(msg);
            Swal.fire({
                icon: 'success',
                title: 'Asistencia registrada',
                html: `<b>${name}</b><br>Confianza: ${(confidence * 100).toFixed(1)}%<br>Estado de ánimo: <b>${emotion}</b>`,
                timer: 2500,
                showConfirmButton: false
            });
        },
        function (err) {
            console.error("❌ Attendance error:", err);
            setStatus("Error enviando asistencia");
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: err.error || 'No se pudo registrar la asistencia'
            });
        }, require_confirmation=false
    );
}

function similarityToConfidence(sim) {
    if (typeof sim !== 'number' || isNaN(sim)) return 0; // 👈 evita NaN
    const min = 0.3;
    const max = 0.9;
    const conf = (sim - min) / (max - min);
    return Math.max(0, Math.min(1, conf));
}

function takeSnapshot() {
    const temp = document.createElement("canvas");
    temp.width = canvasEl.width;
    temp.height = canvasEl.height;
    temp.getContext("2d").drawImage(videoEl, 0, 0, temp.width, temp.height);
    return new Promise(resolve => temp.toBlob(b => resolve(b), "image/jpeg",
        0.85));
}

async function loop() {
    if (!running) return;
    const useTiny = new faceapi.TinyFaceDetectorOptions({
        inputSize: 320,
        scoreThreshold: 0.5
    });
    const detections = await faceapi.detectAllFaces(videoEl, useTiny)
        .withFaceLandmarks()
        .withFaceDescriptors()
        .withFaceExpressions(); // ← Agregado
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    faceapi.draw.drawDetections(canvasEl, detections);
    if (detections.length > 0 && labeledDescriptors &&
        labeledDescriptors.length) {
        for (const det of detections) {
            const {descriptor, detection, expressions} = det;
            const {top1, top2} = bestMatch(descriptor, labeledDescriptors);
            const [employeeId, name] = top1.label.split("::");

            // Emoción dominante
            const sorted = Object.entries(expressions)
                .sort((a, b) => b[1] - a[1]);
            const [mainExpression, confidence] = sorted[0];

            // Votación temporal
            votes.push({employeeId, name, score: top1.score, alt: top2.score});
            if (votes.length > VOTE_WINDOW) votes.shift();
            // Decisión cuando hay suficientes votos
            if (votes.length === VOTE_WINDOW) {
                // Agrupa por empleado para calcular promedio
                const byEmp = votes.reduce((acc, v) => {
                    acc[v.employeeId] = acc[v.employeeId] || [];
                    acc[v.employeeId].push(v.score);
                    return acc;
                }, {});

                // Encuentra el empleado con mayor promedio
                let bestEmp = null, bestAvg = 0, bestAltAvg = 0;
                for (const [eid, arr] of Object.entries(byEmp)) {
                    const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
                    if (avg > bestAvg) {
                        bestEmp = eid;
                        bestAvg = avg;
                    }
                }

                // Calcula promedio del segundo mejor
                bestAltAvg =
                    votes.filter(v => v.employeeId === bestEmp)
                        .reduce((a, b) => a + b.alt, 0) /
                    votes.filter(v => v.employeeId === bestEmp).length;

                // --- 🔥 Nueva lógica de confianza / tiempo ---
                const highConfidence = bestAvg >= 0.98;

                if (!recognitionStartTime && bestAvg >= CONFIDENCE_THRESHOLD) {
                    recognitionStartTime = Date.now();
                    setStatus(`Reconociendo a ${votes[0].name}...`);
                    console.log("Reconociendo a", votes[0].name);
                }

                const sustainedRecognition = recognitionStartTime && (Date.now() - recognitionStartTime >= 3000);
                if (bestAvg < CONFIDENCE_THRESHOLD) {
                    recognitionStartTime = null;
                }

                if ((highConfidence || sustainedRecognition)) {
                    const snap = await takeSnapshot();
                    const v = votes.find(x => x.employeeId === bestEmp);
                    await sendAttendance(bestEmp, v.name, bestAvg, snap, mainExpression);
                    votes = [];
                    recognitionStartTime = null; // reinicia después del envío
                } else if (!highConfidence) {
                    setStatus("Rostro detectado, pero no confiable");
                    console.log("Rostro detectado, pero no confiable");
                }
            }
            // Dibuja etiqueta
            const box = detection.box;
            ctx.font = "16px sans-serif";
            ctx.fillStyle = "rgba(0,0,0,0.5)";
            ctx.fillRect(box.x, box.y - 22, 160, 20);
            ctx.fillRect(box.x, box.y - 42, 180, 20);
            ctx.fillStyle = "#fff";
            const simScore = typeof top1?.score === 'number' ? top1.score : 0;
            const confPercent = (similarityToConfidence(simScore) * 100).toFixed(1);
            ctx.fillText(`${name || "Desconocido"} ${confPercent}%`,
                box.x + 4, box.y - 6);
            ctx.fillText(`😊 ${mainExpression} (${(confidence * 100).toFixed(0)}%)`,
                box.x + 4, box.y - 26);

        }
    } else {
        votes = []; // si no hay detecciones, resetea
    }
    requestAnimationFrame(loop);
}

async function init() {
    setStatus("Cargando modelos...");
    await loadModels();
    setStatus("Descargando embeddings...");
    labeledDescriptors = await loadLabeledDescriptors();
    setStatus(`Listo. Personas: ${labeledDescriptors.length}`);
    document.getElementById("startBtn").onclick = async () => {
        await startCamera();
        running = true;
        document.getElementById("stopBtn").disabled = false;
        loop();
    };
    document.getElementById("stopBtn").onclick = () => {
        running = false;
        const s = videoEl.srcObject;
        if (s)
            s.getTracks().forEach(t => t.stop());
        document.getElementById("stopBtn").disabled = true;
        setStatus("Detenido");
    };
}

window.addEventListener("DOMContentLoaded", init);