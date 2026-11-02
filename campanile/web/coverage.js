// DEVELOPED BY CARROTSTUDIO software house
// The coverage test: from where the phone is, how hard it is for a message to reach the
// Campanile and come back. A measurement that can't get through stays on the phone and goes
// once back in range: the holes are what matter most.
import { el, secondsText, showResult, speedText, verdictLabel } from "/common.js";
import { lang, t, tn, translatePage } from "/i18n.js";

translatePage();

const PINGS = 20;
const FIRST = 3; // pings that all get lost: nothing gets through here, no need to wait for more
const GAP = 100; // ms between pings: under the 20 requests a second nginx allows a phone
const PING_WAIT = 2000; // ms: a ping slower than this counts as lost
const SAMPLE_WAIT = 30_000; // ms for the 256 kB piece
const SEND_WAIT = 5000; // ms for saving one result
const PAGE_WAIT = 30_000; // ms for the home page, or the test post: past it, not opened
// What a phone downloads to open the home page, as the page itself asks for it (a test keeps
// the list in step with index.html and its imports).
const HOME = [
  "/", "/favicon.svg", "/style.css", "/index.js", "/common.js", "/i18n.js", "/strings.js",
  "/api/notices", "/api/status",
];
const POST_CHARS = 4000; // a long post, all its fields filled in
const MAX_AGO = 86_400; // seconds the Campanile accepts a result late
const PENDING_KEY = "campanile-coverage-pending-v1";
const MAX_PENDING = 50;

const form = document.getElementById("cov-form");
const result = document.getElementById("cov-result");
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// Out of range a request may hang for a minute: each one has its own deadline. null means
// nothing came back, from no network or a deadline passed.
async function ask(path, wait, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), wait);
  const headers = { "Accept-Language": lang };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const started = performance.now();
  try {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: controller.signal,
    });
    const data = await response.arrayBuffer();
    return { ok: response.ok, status: response.status, ms: performance.now() - started, data };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// The Campanile answered no (the test off, too many measurements): its words, not a measure.
function refusal(answer) {
  let message = t("error.status", { status: answer.status });
  try {
    message = JSON.parse(new TextDecoder().decode(answer.data)).error || message;
  } catch {
    // not JSON
  }
  const error = new Error(message);
  error.status = answer.status;
  return error;
}

// The home page, opened as a phone opens it: every file at once, done when the last arrives.
async function openHome() {
  const started = performance.now();
  const answers = await Promise.all(HOME.map((path) => ask(path, PAGE_WAIT)));
  return answers.every((a) => a?.ok) ? Math.round(performance.now() - started) : null;
}

// A post sent as the board sends one; the Campanile reads it and drops it.
async function sendPost() {
  const answer = await ask("/api/coverage/send", PAGE_WAIT, { text: "x".repeat(POST_CHARS) });
  return answer?.ok ? Math.round(answer.ms) : null;
}

async function measure(place) {
  let reached = false;
  for (let i = 0; i < FIRST && !reached; i++) {
    const answer = await ask("/api/coverage/ping", PING_WAIT);
    if (answer && !answer.ok) throw refusal(answer);
    reached = answer !== null;
  }
  if (!reached) {
    return { place, sent: FIRST, lost: FIRST, median_ms: null, worst_ms: null, kbps: null,
      page_ms: null, send_ms: null };
  }
  const times = [];
  for (let i = 1; i <= PINGS; i++) {
    showResult(result, t("cov.running", { n: i, total: PINGS }));
    const ping = await ask(`/api/coverage/ping?n=${i}`, PING_WAIT);
    if (ping?.ok) times.push(ping.ms);
    await sleep(GAP);
  }
  showResult(result, t("cov.home"));
  const page = await openHome();
  showResult(result, t("cov.sending"));
  const send = await sendPost();
  showResult(result, t("cov.sample"));
  const sample = await ask(`/api/coverage/sample?n=${Date.now()}`, SAMPLE_WAIT);
  times.sort((a, b) => a - b);
  return {
    place,
    sent: PINGS,
    lost: PINGS - times.length,
    median_ms: times.length ? Math.round(times[Math.floor(times.length / 2)]) : null,
    worst_ms: times.length ? Math.round(times[times.length - 1]) : null,
    kbps: sample?.ok ? Math.round((sample.data.byteLength * 8) / sample.ms) : null, // bits a ms
    page_ms: page,
    send_ms: send,
  };
}

// The verdict, or null when it didn't get through. Throws when the Campanile refused it.
async function save(numbers, ago = 0) {
  const answer = await ask("/api/coverage", SEND_WAIT, ago ? { ...numbers, ago } : numbers);
  if (answer === null) return null;
  if (!answer.ok) throw refusal(answer);
  return JSON.parse(new TextDecoder().decode(answer.data)).verdict;
}

// What waits to be sent: on the phone, so a reload doesn't lose it (in memory where it can't).
function loadPending() {
  try {
    const kept = JSON.parse(localStorage.getItem(PENDING_KEY));
    return Array.isArray(kept) ? kept : [];
  } catch {
    return [];
  }
}
const pending = loadPending();
function keepPending() {
  pending.splice(0, Math.max(0, pending.length - MAX_PENDING));
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  } catch {
    // no storage: they wait in this page only
  }
}

function showPending(sent) {
  const line = document.getElementById("cov-pending");
  const parts = [];
  if (sent) parts.push(tn("cov.late", sent));
  if (pending.length) parts.push(tn("cov.pending", pending.length));
  line.textContent = parts.join(" ");
  line.classList.toggle("hidden", !parts.length);
}

// Back in range: what waited goes first, oldest first, each one placed when it was taken.
async function flush() {
  let sent = 0;
  while (pending.length) {
    const ago = Math.min(MAX_AGO, Math.max(0, Math.round((Date.now() - pending[0].at) / 1000)));
    let verdict;
    try {
      verdict = await save(pending[0].numbers, ago);
    } catch (error) {
      if (error.status === 404) break; // the test is off: they wait for it to be on again
      verdict = "refused"; // one the Campanile won't take: dropped, so it doesn't block the rest
    }
    if (verdict === null) break; // still out of range
    pending.shift();
    keepPending();
    sent++;
  }
  showPending(sent);
}

const pageText = (ms) => (ms === null ? t("cov.opened.none") : t("cov.opened", { s: secondsText(ms) }));
const sendText = (ms) => (ms === null ? t("cov.send.none") : t("cov.send", { s: secondsText(ms) }));

function show(m, verdict, note) {
  const rtt = m.median_ms === null ? t("cov.rtt.none") : t("cov.rtt", { ms: m.median_ms, worst: m.worst_ms });
  document.getElementById("cov-list").prepend(el("article", { class: "post" },
    el("strong", { text: `${m.place} · ${verdictLabel(verdict)}` }),
    el("div", { class: "meta", text: rtt }),
    el("div", { class: "meta", text: t("cov.lost", { lost: m.lost, sent: m.sent }) }),
    el("div", { class: "meta", text: pageText(m.page_ms) }),
    el("div", { class: "meta", text: sendText(m.send_ms) }),
    el("div", { class: "meta", text: t("cov.speed", { speed: speedText(m.kbps) }) }),
    el("div", { class: "meta", text: note }),
  ));
  document.getElementById("cov-mine").classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const numbers = await measure(document.getElementById("place").value.trim());
    showResult(result, t("cov.saving"));
    let verdict;
    try {
      verdict = await save(numbers);
    } catch (error) {
      show(numbers, "bad", t("cov.notsaved", { error: error.message }));
      showResult(result, "");
      return;
    }
    if (verdict === null) {
      pending.push({ numbers, at: Date.now() });
      keepPending();
      show(numbers, "bad", t("cov.queued"));
      showPending(0);
    } else {
      show(numbers, verdict, t("cov.saved"));
      await flush();
    }
    showResult(result, "");
  } catch (error) {
    showResult(result, error.message, true);
  } finally {
    button.disabled = false;
  }
});

showPending(0);
flush(); // what waited from an earlier visit goes as soon as the page opens in range
