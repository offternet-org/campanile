// DEVELOPED BY CARROTSTUDIO software house
import { api } from "/common.js";
import { drawQr } from "/qr.js";
import { showEmergency, translatePage } from "/i18n.js";

translatePage();

const NETWORK_KEY = "campanile-network-name";

function readNetwork() {
  try { return localStorage.getItem(NETWORK_KEY); } catch { return null; }
}

function saveNetwork(value) {
  try { localStorage.setItem(NETWORK_KEY, value); } catch { /* only on screen then */ }
}

async function start() {
  const input = document.getElementById("network-name");
  const printed = document.getElementById("printed-network");
  input.value = readNetwork() || input.value;
  const update = () => {
    printed.textContent = input.value.trim() || "…";
    saveNetwork(input.value);
  };
  input.addEventListener("input", update);
  update();
  document.getElementById("print").addEventListener("click", () => window.print());

  let address = `${location.origin}/`;
  try {
    const status = await api("/api/status");
    if (status.address) address = status.address;
    showEmergency(status.emergency);
  } catch {
    // fall back to the page's own address
  }
  document.getElementById("address-text").textContent = address.replace(/\/$/, "");
  drawQr(document.getElementById("qr"), address);
}

start();
