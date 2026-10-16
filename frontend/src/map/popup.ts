import type { Checkpoint } from "../api/types";
import { formatConditions, formatMiles, formatTime } from "../domain/format";
import { levelColor } from "../domain/levels";

/** Popup body for a checkpoint, built from text nodes so API strings are never parsed as HTML. */
export function checkpointPopup(checkpoint: Checkpoint): HTMLElement {
  const root = document.createElement("div");
  root.className = "checkpoint-popup";

  const title = line(root, "strong", `${formatMiles(checkpoint.mile)} · ${formatTime(checkpoint.eta)}`);
  title.className = "popup-title";

  const level = line(root, "div", checkpoint.level);
  level.className = "popup-level";
  level.style.setProperty("--level-color", levelColor(checkpoint.level));

  line(root, "div", formatConditions(checkpoint));
  if (checkpoint.reasons.length > 0) line(root, "div", checkpoint.reasons.join("; "));
  return root;
}

function line(parent: HTMLElement, tag: string, text: string): HTMLElement {
  const element = document.createElement(tag);
  element.textContent = text;
  parent.append(element);
  return element;
}
