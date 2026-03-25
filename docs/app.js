function setCopyFeedback(button, copyText, status) {
  const baseLabel = "Copy";
  if (!button || !copyText) return;

  if (status === "ok") {
    button.classList.add("copied");
    copyText.textContent = "Copied";
    window.setTimeout(function () {
      button.classList.remove("copied");
      copyText.textContent = baseLabel;
    }, 1600);
    return;
  }

  copyText.textContent = "Failed";
  window.setTimeout(function () {
    copyText.textContent = baseLabel;
  }, 1600);
}

function legacyCopyText(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.select();
  const ok = document.execCommand("copy");
  document.body.removeChild(textArea);
  return ok;
}

function copyBibTeX() {
  const bibtexElement = document.getElementById("bibtex-code");
  const button = document.querySelector(".copy-bibtex-btn");
  const copyText = button ? button.querySelector(".copy-text") : null;
  if (!bibtexElement || !button || !copyText) return;

  const content = bibtexElement.textContent.trim();
  if (!content) return;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(content)
      .then(function () {
        setCopyFeedback(button, copyText, "ok");
      })
      .catch(function () {
        setCopyFeedback(button, copyText, legacyCopyText(content) ? "ok" : "failed");
      });
    return;
  }

  setCopyFeedback(button, copyText, legacyCopyText(content) ? "ok" : "failed");
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function syncScrollTopButton() {
  const scrollButton = document.querySelector(".scroll-to-top");
  if (!scrollButton) return;

  if (window.pageYOffset > 300) {
    scrollButton.classList.add("visible");
  } else {
    scrollButton.classList.remove("visible");
  }
}

window.addEventListener("scroll", syncScrollTopButton);

document.addEventListener("DOMContentLoaded", function () {
  syncScrollTopButton();
});
