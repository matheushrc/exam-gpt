document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".md-preview").forEach((el) => {
    const source = el.dataset.source || el.textContent || "";
    el.innerHTML = marked.parse(source);
    if (typeof renderMathInElement === "function") {
      renderMathInElement(el, {
        delimiters: [{ left: "$", right: "$", display: false }],
      });
    }
  });

  document.querySelectorAll(".expandable").forEach((el) => {
    el.addEventListener("focus", () => {
      el.rows = 10;
    });
    el.addEventListener("blur", () => {
      el.rows = 3;
    });
  });
});
