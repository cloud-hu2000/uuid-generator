(() => {
  "use strict";

  const language = document.documentElement.lang === "zh-CN" ? "zh" : "en";
  const messages = {
    en: {
      invalid: "Enter a whole number between 1 and 100.",
      unsupported: "This browser cannot generate UUIDs. Update it or use a current version of Chrome, Edge, Safari, or Firefox.",
      generationFailed: "Could not generate UUIDs. Please try again or update your browser.",
      generated: (count) => `${count} ${count === 1 ? "UUID" : "UUIDs"} generated. Ready to copy.`,
      copy: "Copy",
      copyAll: "Copy all",
      copyLabel: (index) => `Copy UUID ${index}`,
      copied: "Copied!",
      copiedAll: "Copied! All UUIDs are on your clipboard.",
      copyFailed: "Copy failed. Select the results below and copy them manually.",
    },
    zh: {
      invalid: "请输入 1 到 100 之间的整数。",
      unsupported: "当前浏览器不支持生成 UUID。请更新浏览器，或使用最新版 Chrome、Edge、Safari、Firefox。",
      generationFailed: "生成失败，请重试或更新浏览器。",
      generated: (count) => `已生成 ${count} 个 UUID，可以复制了。`,
      copy: "复制",
      copyAll: "复制全部",
      copyLabel: (index) => `复制第 ${index} 个 UUID`,
      copied: "已复制",
      copiedAll: "已复制全部 UUID。",
      copyFailed: "复制失败，请选中下方结果后手动复制。",
    },
  }[language];

  const form = document.getElementById("generator-form");
  const quantity = document.getElementById("quantity");
  const quantityError = document.getElementById("quantity-error");
  const results = document.getElementById("results");
  const resultCount = document.getElementById("result-count");
  const emptyState = document.getElementById("empty-state");
  const copyAll = document.getElementById("copy-all");
  const status = document.getElementById("status");
  const manualCopy = document.getElementById("manual-copy");
  const manualText = document.getElementById("manual-text");
  const copyTimers = new WeakMap();
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  let values = [];
  let generation = 0;

  function setStatus(message, state = "neutral") {
    status.textContent = message;
    status.dataset.state = state;
  }

  function resetCopyButton(button, label) {
    window.clearTimeout(copyTimers.get(button));
    button.querySelector("[data-copy-label]").textContent = label;
  }

  async function copyText(text, button, isBatch) {
    const currentGeneration = generation;
    const originalLabel = isBatch ? messages.copyAll : messages.copy;
    resetCopyButton(button, originalLabel);
    button.disabled = true;
    try {
      if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
        throw new Error("Clipboard unavailable");
      }
      await navigator.clipboard.writeText(text);
      // A pending copy belongs to the list visible when the user clicked.
      if (currentGeneration !== generation) return;
      manualCopy.hidden = true;
      manualText.value = "";
      setStatus(isBatch ? messages.copiedAll : messages.copied, "success");
      button.querySelector("[data-copy-label]").textContent = messages.copied;
      copyTimers.set(button, window.setTimeout(() => resetCopyButton(button, originalLabel), 2000));
    } catch {
      if (currentGeneration !== generation) return;
      setStatus(messages.copyFailed, "error");
      manualText.value = text;
      manualCopy.hidden = false;
      manualText.focus();
      manualText.select();
    } finally {
      if (currentGeneration === generation) button.disabled = false;
    }
  }

  function render(nextValues) {
    const fragment = document.createDocumentFragment();
    nextValues.forEach((value, index) => {
      const row = document.createElement("li");
      row.className = "result-row";
      const number = document.createElement("span");
      number.className = "row-number";
      number.setAttribute("aria-hidden", "true");
      number.textContent = String(index + 1).padStart(2, "0");
      const code = document.createElement("code");
      code.className = "uuid-value";
      code.textContent = value;
      const button = document.createElement("button");
      button.className = "copy-button";
      button.type = "button";
      button.setAttribute("aria-label", messages.copyLabel(index + 1));
      const label = document.createElement("span");
      label.dataset.copyLabel = "";
      label.textContent = messages.copy;
      button.append(label);
      button.addEventListener("click", () => copyText(value, button, false));
      row.append(number, code, button);
      fragment.append(row);
    });
    results.replaceChildren(fragment);
    results.scrollTop = 0;
    results.hidden = false;
    emptyState.hidden = true;
    resultCount.textContent = String(nextValues.length);
    copyAll.disabled = false;
    resetCopyButton(copyAll, messages.copyAll);
    manualCopy.hidden = true;
    manualText.value = "";
  }

  quantity.addEventListener("input", () => {
    quantity.removeAttribute("aria-invalid");
    quantityError.textContent = "";
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const input = quantity.value.trim();
    const count = Number(input);
    if (!/^\d+$/.test(input) || !Number.isInteger(count) || count < 1 || count > 100) {
      quantityError.textContent = messages.invalid;
      quantity.setAttribute("aria-invalid", "true");
      quantity.focus();
      return;
    }
    quantity.removeAttribute("aria-invalid");
    quantityError.textContent = "";
    if (!window.crypto || typeof window.crypto.randomUUID !== "function") {
      setStatus(messages.unsupported, "error");
      return;
    }
    try {
      const unique = new Set();
      let attempts = 0;
      // Bound retries so an unexpected random generator failure cannot hang the page.
      while (unique.size < count && attempts < count * 20) {
        const value = window.crypto.randomUUID().toLowerCase();
        if (!uuidPattern.test(value)) throw new Error("Invalid UUID");
        unique.add(value);
        attempts += 1;
      }
      if (unique.size !== count) throw new Error("Could not create a unique batch");
      const nextValues = [...unique];
      generation += 1;
      values = nextValues;
      render(nextValues);
      setStatus(messages.generated(count), "success");
    } catch {
      setStatus(messages.generationFailed, "error");
    }
  });

  copyAll.addEventListener("click", () => {
    if (values.length) copyText(values.join("\n"), copyAll, true);
  });
})();
