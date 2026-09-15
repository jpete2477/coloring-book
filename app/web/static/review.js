(function () {
  const script = document.currentScript;
  const bookId = script.dataset.bookId;
  const assetId = script.dataset.assetId;
  const prevId = script.dataset.prevId;
  const nextId = script.dataset.nextId;

  window.submitAction = function (action) {
    const form = document.createElement("form");
    form.method = "post";
    form.action = `/${bookId}/api/assets/${assetId}/${action}`;

    const fields = { notes: "notes" };
    if (action === "approve") {
      Object.assign(fields, { quality: "quality", complexity: "complexity", uniqueness: "uniqueness" });
    }
    for (const [fieldName, elementId] of Object.entries(fields)) {
      const el = document.getElementById(elementId);
      if (el && el.value !== "") {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = fieldName;
        input.value = el.value;
        form.appendChild(input);
      }
    }
    document.body.appendChild(form);
    form.submit();
  };

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    switch (e.key.toLowerCase()) {
      case "a":
        submitAction("approve");
        break;
      case "x":
        submitAction("reject");
        break;
      case "r":
        submitAction("regenerate");
        break;
      case "n":
        if (nextId) window.location = `/${bookId}/review/${nextId}`;
        break;
      case "p":
        if (prevId) window.location = `/${bookId}/review/${prevId}`;
        break;
    }
  });
})();
