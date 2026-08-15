(function () {
  const thread = document.querySelector("[data-msg-thread]");
  if (thread) {
    thread.scrollTop = thread.scrollHeight;
  }

  const input = document.querySelector("[data-msg-input]");
  if (!input) return;

  const maxPx = 7.5 * 16;

  function resize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, maxPx) + "px";
    input.style.overflowY = input.scrollHeight > maxPx ? "auto" : "hidden";
  }

  input.addEventListener("input", resize);
  resize();

  input.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    const form = input.closest("form");
    if (form && input.value.trim()) form.requestSubmit();
  });
})();
