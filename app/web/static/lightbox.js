(function () {
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxCaption = document.getElementById("lightbox-caption");
  if (!lightbox) return;

  function open(src, caption) {
    if (!src) return;
    lightboxImg.src = src;
    lightboxCaption.textContent = caption || "";
    lightbox.hidden = false;
  }

  function close() {
    lightbox.hidden = true;
    lightboxImg.src = "";
  }

  document.querySelectorAll(".page-thumb-clickable").forEach((img) => {
    img.addEventListener("click", () => open(img.dataset.fullSrc, img.dataset.caption));
  });

  lightbox.addEventListener("click", close);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });
})();
