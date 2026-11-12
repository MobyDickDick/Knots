"use strict";

const $ = id => document.getElementById(id);
const canvas = $("knot-canvas");
const ctx = canvas.getContext("2d");
const background = "#142b2d";
const colors = ["#78b5e0", "#8fcfb1", "#ef956e"];
let record = null;
let generatedRecord = null;
let minimizedRecord = null;
let view = "2d";
let yaw = -0.55;
let pitch = 0.95;
let zoom = 1;
let drag = null;
let busy = false;

const descriptions = {
  trefoil: "Der klassische Kleeblattknoten als geprüftes 5 × 5-Gitterdiagramm.",
  "figure-eight": "Der Achterknoten in einer festen Gitterdarstellung mit sechs Bogenpaaren.",
  torus: "Eine Familie echter Knoten. Die ungerade Zahl q bestimmt den Knotentyp.",
  travel: "Die Überführung wird an jeder Kreuzung einzeln gewählt: mal waagrecht oben, mal senkrecht.",
  ornamental: "Ein Rechteck wächst durch lokale Umwege zu einem abwechslungsreichen Unknoten.",
};

function updateControls() {
  const preset = $("preset").value;
  for (const name of ["travel", "torus", "ornamental"]) {
    $(`${name}-options`).hidden = preset !== name;
  }
  const random = preset === "travel" || preset === "ornamental";
  $("seed").disabled = !random;
  $("random-seed").disabled = !random || busy;
  $("minimize").disabled = busy || !record || minimizedRecord?.optimization.status === "global_minimum";
  $("show-original").disabled = busy;
  $("show-result").disabled = busy;
  $("preset-help").textContent = descriptions[preset];
  $("seed-help").textContent = random
    ? "Gleicher Seed + gleiche Parameter = derselbe Weg."
    : "Referenzdiagramme sind fest; sie benötigen keinen Seed.";
}

function displayName(data) {
  if (data.parameters.preset === "ornamental") return "Ornamentaler Unknoten";
  if (data.name === "T(2,3)") return "Kleeblattknoten · 3₁";
  if (data.name === "4_1") return "Achterknoten · 4₁";
  if (data.name === "0_1") return "Unknoten · 0₁";
  if (data.name === "unknown") return "Gitterkandidat · ungeklärt";
  return data.name;
}

async function generate(event) {
  if (event) event.preventDefault();
  if (busy) return;
  busy = true;
  $("error").hidden = true;
  $("generate").disabled = true;
  $("generate").firstElementChild.textContent = "Wird erzeugt …";
  $("random-seed").disabled = true;
  $("viewer").setAttribute("aria-busy", "true");
  updateControls();
  const options = {
    preset: $("preset").value,
    seed: ["travel", "ornamental"].includes($("preset").value) ? $("seed").value : "2026",
    point_count: Number($("point-count").value),
    crossings: Number($("crossings").value),
    steps: Number($("steps").value),
  };
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Der Knoten konnte nicht erzeugt werden.");
    generatedRecord = data;
    minimizedRecord = null;
    $("optimization-panel").hidden = true;
    $("minimize").textContent = "Minimierung versuchen";
    showRecord(data);
    $("status").textContent = `${displayName(data)} erzeugt: ${data.metrics.length} Punkte, ${data.metrics.crossings} Kreuzungen.`;
  } catch (error) {
    showError(error);
    if (!record) $("valid-badge").textContent = "Keine Konstruktion geladen";
  } finally {
    busy = false;
    $("generate").disabled = false;
    $("generate").firstElementChild.textContent = "Knoten erzeugen";
    $("viewer").setAttribute("aria-busy", "false");
    updateControls();
  }
}

function showRecord(data) {
    record = data;
    $("knot-name").textContent = displayName(data);
    $("valid-badge").textContent = "✓ Geschlossen & geprüft";
    $("metric-length").textContent = data.metrics.length;
    $("metric-crossings").textContent = data.metrics.crossings;
    $("metric-switches").textContent = data.metrics.layer_switches;
    $("metric-determinant").textContent = data.classification.determinant ?? "—";
    $("classification").textContent = data.classification.status === "certified"
      ? "Referenzdiagramm erkannt" : "Knotentyp ungeklärt";
    if (data.parameters.preset === "ornamental") {
      $("classification").textContent = "Unknoten durch Konstruktion";
    }
    $("turtle-code").textContent = data.code;
    let evidence = data.classification.status === "certified"
      ? "Klassifikation durch vollständigen Diagrammvergleich oder reguläre kreuzungsfreie Projektion."
      : "Kein vollständiger Referenztreffer. Eine Determinante allein beweist keinen Knotentyp.";
    if (data.parameters.preset === "ornamental") {
      evidence = "Die Umwege erhalten den Unknotentyp durch Konstruktion. Die Projektion kann entartet sein; dann wird keine Determinante angegeben.";
    }
    if (data.metrics.degeneracies) {
      evidence += ` ${data.metrics.degeneracies} Projektionsentartungen; der räumliche Pfad bleibt gültig.`;
    }
    if (data.optimization) {
      evidence = "Der Knotentyp bleibt durch geometrisch geprüfte, protokollierte Umformungen erhalten. " +
        (data.optimization.status === "global_minimum"
          ? "Vier Schritte sind der kleinste mögliche einfache Gitterzyklus."
          : "Eine globale Minimalität ist nicht bewiesen.");
    } else if (data.parameters.preset === "travel" && data.parameters.crossing_mode === "mixed") {
      evidence += " Freie Kreuzungsführung mit lokalen Überführungen auf einem vierfach verfeinerten Gitter.";
    }
    evidence += " JSON enthält den Startpunkt am Ende erneut; der Turtle-Code startet in (0,0,0) nach Osten.";
    if (["travel", "ornamental"].includes(data.parameters.preset)) {
      evidence += ` Seed: ${data.parameters.seed}.`;
    }
    $("evidence").textContent = evidence;
    for (const id of ["download-svg", "download-json", "download-code", "copy-code"]) $(id).disabled = false;
    $("show-original").setAttribute("aria-pressed", String(data === generatedRecord));
    $("show-result").setAttribute("aria-pressed", String(data === minimizedRecord));
    resetView();
}

function showError(error) {
    $("error").textContent = error instanceof TypeError
      ? "Der lokale Generator ist nicht erreichbar. Bitte start_generator.cmd erneut starten."
      : error.message;
    $("error").hidden = false;
    $("status").textContent = $("error").textContent;
}

async function minimize() {
  if (busy || !record) return;
  const input = minimizedRecord || generatedRecord;
  busy = true;
  $("error").hidden = true;
  $("generate").disabled = true;
  $("minimize").textContent = "Minimierung läuft …";
  $("viewer").setAttribute("aria-busy", "true");
  $("status").textContent = "Der aktuelle Knoten wird verkürzt und auf beide Ebenen verteilt. Ein Versuch dauert etwa acht Sekunden.";
  updateControls();
  try {
    const response = await fetch("/api/minimize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points: input.points, parameters: input.parameters }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Die Minimierung ist fehlgeschlagen.");
    minimizedRecord = data;
    showRecord(data);
    const details = data.optimization;
    const originalLength = generatedRecord.metrics.length;
    const endings = {
      global_minimum: "Minimaler Gitterzyklus erreicht: Weniger als vier Schritte sind nicht möglich.",
      local_minimum: "Keine weitere Verkürzung durch Gitterverdichtung und die unterstützten lokalen Züge gefunden. Das beweist keine kürzestmögliche Darstellung.",
      move_limit: "Zuglimit erreicht. Mit einem weiteren Versuch fortsetzen.",
      time_limit: "Zeitlimit erreicht. Mit einem weiteren Versuch fortsetzen.",
      redistributed: "Ebenenverteilung verbessert. Ein weiterer Versuch kann neue Verkürzungen finden.",
    };
    const compression = details.compression_count ? ` Davon ${details.compression_count} Gitterverdichtung(en).` : "";
    $("optimization-summary").textContent = `${originalLength} → ${data.metrics.length} Punkte · ${originalLength - data.metrics.length} entfernt. Letzter Versuch: ${details.move_count} Umformungen.${compression} ${endings[details.status] || details.status}`;
    const before = generatedRecord.layer_lengths, after = data.layer_lengths;
    $("layer-summary").textContent = `Fadenlänge unten / oben: ${before[0]} / ${before[1]} → ${after[0]} / ${after[1]} Gitterschritte. Kürzere Wege haben Vorrang; bei gleicher Länge wird eine gleichmäßigere Verteilung bevorzugt.`;
    $("optimization-panel").hidden = false;
    $("status").textContent = $("optimization-summary").textContent;
  } catch (error) {
    showError(error);
  } finally {
    busy = false;
    $("generate").disabled = false;
    $("minimize").textContent = minimizedRecord
      ? (minimizedRecord.optimization.status === "global_minimum" ? "Minimum erreicht" : "Weiter minimieren")
      : "Minimierung versuchen";
    $("viewer").setAttribute("aria-busy", "false");
    updateControls();
  }
}

function resetView() {
  yaw = -0.55;
  pitch = 0.95;
  zoom = 1;
  draw();
}

function setView(next) {
  view = next;
  drag = null;
  $("view-2d").setAttribute("aria-pressed", String(next === "2d"));
  $("view-3d").setAttribute("aria-pressed", String(next === "3d"));
  canvas.classList.toggle("is-3d", next === "3d");
  $("interaction-hint").textContent = next === "3d"
    ? "Ziehen oder Pfeiltasten: drehen · Mausrad: zoomen · Ebenenabstand überhöht"
    : "Obere Ebene diagonal um √2/2 versetzt";
  resetView();
}

function draw() {
  const { width, height } = canvas.getBoundingClientRect();
  if (!width || !height) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  if (!record) return;

  const points = record.points;
  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const offset = Math.SQRT1_2;
  const midX = (minX + maxX) / 2, midY = (minY + maxY) / 2;
  const upper = points.some(p => p[2] === 1);
  const radius = Math.hypot((maxX - minX) / 2, (maxY - minY) / 2, 0.9);
  const scale = zoom * (view === "2d"
    ? Math.min((width - 100) / (maxX - minX + (upper ? offset : 0) + 1),
      (height - 190) / (maxY - minY + (upper ? offset : 0) + 1))
    : Math.min(width - 90, height - 170) / (2 * radius + 1));
  const origin = [width / 2, height / 2 - 2];
  function project(p) {
    let x, y, depth;
    if (view === "2d") {
      x = p[0] + p[2] * offset - midX - (upper ? offset / 2 : 0);
      y = p[1] + p[2] * offset - midY - (upper ? offset / 2 : 0);
      depth = p[2];
    } else {
      const px = p[0] - midX, py = p[1] - midY, pz = (p[2] - 0.5) * 1.8;
      x = px * Math.cos(yaw) - py * Math.sin(yaw);
      const turned = px * Math.sin(yaw) + py * Math.cos(yaw);
      y = turned * Math.cos(pitch) + pz * Math.sin(pitch);
      depth = -turned * Math.sin(pitch) + pz * Math.cos(pitch);
    }
    return [origin[0] + x * scale, origin[1] - y * scale, depth];
  }

  // Display grids use the same transform as the actual knot coordinates.
  ctx.lineWidth = 0.6;
  for (const layer of view === "2d" && upper ? [0, 1] : [0]) {
    ctx.strokeStyle = layer ? "#284e47" : "#284347";
    for (let x = minX - 1; x <= maxX + 1; x++) {
      const a = project([x, minY - 1, layer]), b = project([x, maxY + 1, layer]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    for (let y = minY - 1; y <= maxY + 1; y++) {
      const a = project([minX - 1, y, layer]), b = project([maxX + 1, y, layer]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
  }

  const projected = points.map(project);
  const edges = points.slice(0, -1).map((p, i) => {
    const q = points[i + 1], a = projected[i], b = projected[i + 1];
    return { a, b, depth: (a[2] + b[2]) / 2, layer: p[2] !== q[2] ? 2 : p[2] };
  }).sort((a, b) => a.depth - b.depth);
  const thickness = Math.max(2, Math.min(6.5, scale * 0.115));
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const edge of edges) {
    ctx.beginPath(); ctx.moveTo(edge.a[0], edge.a[1]); ctx.lineTo(edge.b[0], edge.b[1]);
    ctx.lineCap = "butt";
    ctx.strokeStyle = background; ctx.lineWidth = thickness + 4; ctx.stroke();
    ctx.lineCap = "round";
    ctx.strokeStyle = colors[edge.layer]; ctx.lineWidth = thickness; ctx.stroke();
  }
  // Mark the exact turtle start once, without suggesting an open endpoint.
  const start = projected[0];
  ctx.beginPath(); ctx.arc(start[0], start[1], thickness + 3, 0, 2 * Math.PI);
  ctx.strokeStyle = "#f4e6bb"; ctx.lineWidth = 1.2; ctx.stroke();

  ctx.font = '10px "Segoe UI", sans-serif';
  let legendX = 25;
  for (const [label, color] of [["z = 0", colors[0]], ["z = 1", colors[1]], ["Wechsel", colors[2]]]) {
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(legendX, 83, 3, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#a7bcb2"; ctx.fillText(label, legendX + 9, 86);
    legendX += label === "Wechsel" ? 90 : 70;
  }
  canvas.setAttribute("aria-label", `${displayName(record)}, ${record.metrics.length} Punkte, ${record.metrics.crossings} Kreuzungen. ${view === "3d" ? "Mit der Maus ziehen oder Pfeiltasten zum Drehen. Mausrad oder Plus und Minus zum Zoomen." : "Zweischichtige Gitterprojektion. Ring markiert den Startpunkt."}`);
}

function download(content, type, extension) {
  if (!record) return;
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `knoten-${record.parameters.preset}-${record.parameters.seed}.${extension}`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("generator-form").addEventListener("submit", generate);
$("minimize").addEventListener("click", minimize);
$("show-original").addEventListener("click", () => generatedRecord && showRecord(generatedRecord));
$("show-result").addEventListener("click", () => minimizedRecord && showRecord(minimizedRecord));
$("preset").addEventListener("change", updateControls);
for (const id of ["point-count", "crossings", "steps"]) {
  $(id).addEventListener("input", () => $(`${id}-value`).textContent = $(id).value);
}
$("random-seed").addEventListener("click", () => {
  const values = new Uint32Array(2);
  crypto.getRandomValues(values);
  $("seed").value = ((BigInt(values[0] & 0x7fffffff) << 32n) | BigInt(values[1])).toString();
  $("status").textContent = "Neuer Seed gewählt. Knoten erzeugen, um ihn anzuwenden.";
});
$("view-2d").addEventListener("click", () => setView("2d"));
$("view-3d").addEventListener("click", () => setView("3d"));
$("reset-view").addEventListener("click", resetView);
$("download-svg").addEventListener("click", () => record && download(record.svg, "image/svg+xml", "svg"));
$("download-json").addEventListener("click", () => {
  if (!record) return;
  const { svg, ...data } = record;
  download(JSON.stringify(data, null, 2) + "\n", "application/json", "json");
});
$("download-code").addEventListener("click", () => record && download(record.code + "\n", "text/plain", "txt"));
$("copy-code").addEventListener("click", async () => {
  if (!record) return;
  try {
    await navigator.clipboard.writeText(record.code);
    $("copy-code").textContent = "Kopiert ✓";
    $("status").textContent = "Turtle-Code kopiert.";
    setTimeout(() => $("copy-code").textContent = "Kopieren", 1800);
  } catch {
    $("status").textContent = "Kopieren nicht möglich. Den Turtle-Code als Datei herunterladen.";
    $("copy-code").textContent = "Bitte herunterladen";
  }
});
canvas.addEventListener("pointerdown", event => {
  if (view !== "3d" || event.button !== 0) return;
  drag = { x: event.clientX, y: event.clientY, pointerId: event.pointerId };
  canvas.setPointerCapture(event.pointerId);
  canvas.focus({ preventScroll: true });
});
canvas.addEventListener("pointermove", event => {
  if (!drag || event.pointerId !== drag.pointerId || view !== "3d") return;
  yaw += (event.clientX - drag.x) * 0.009;
  pitch = Math.max(-Math.PI, Math.min(Math.PI, pitch + (event.clientY - drag.y) * 0.009));
  drag.x = event.clientX; drag.y = event.clientY;
  draw();
});
for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) canvas.addEventListener(name, () => drag = null);
canvas.addEventListener("wheel", event => {
  event.preventDefault();
  zoom = Math.max(0.4, Math.min(3, zoom * Math.exp(-event.deltaY * 0.001)));
  draw();
}, { passive: false });
canvas.addEventListener("keydown", event => {
  if (event.key === "+" || event.key === "=") zoom = Math.min(3, zoom * 1.1);
  else if (event.key === "-") zoom = Math.max(0.4, zoom / 1.1);
  else if (event.key === "Home") { resetView(); event.preventDefault(); return; }
  else if (view === "3d" && event.key.startsWith("Arrow")) {
    if (event.key === "ArrowLeft") yaw -= 0.12;
    else if (event.key === "ArrowRight") yaw += 0.12;
    else if (event.key === "ArrowUp") pitch -= 0.12;
    else if (event.key === "ArrowDown") pitch += 0.12;
    pitch = Math.max(-Math.PI, Math.min(Math.PI, pitch));
  } else return;
  event.preventDefault(); draw();
});
new ResizeObserver(draw).observe(canvas);
updateControls();
generate();
