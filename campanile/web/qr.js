// DEVELOPED BY CARROTSTUDIO software house
// A QR code drawn as SVG: the Campanile's address on the sign, the coverage test's on the
// admin page.
import qrcode from "/vendor/qrcode.mjs";

const SVG = "http://www.w3.org/2000/svg";

export function drawQr(container, text) {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const modules = qr.getModuleCount();
  const margin = 4;
  const side = modules + margin * 2;
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${side} ${side}`);
  svg.setAttribute("shape-rendering", "crispEdges");
  const background = document.createElementNS(SVG, "rect");
  background.setAttribute("width", side);
  background.setAttribute("height", side);
  background.setAttribute("fill", "#fff");
  svg.append(background);
  let d = "";
  for (let row = 0; row < modules; row++) {
    for (let col = 0; col < modules; col++) {
      if (qr.isDark(row, col)) d += `M${col + margin} ${row + margin}h1v1h-1z`;
    }
  }
  const dots = document.createElementNS(SVG, "path");
  dots.setAttribute("d", d);
  dots.setAttribute("fill", "#000");
  svg.append(dots);
  container.replaceChildren(svg);
}
