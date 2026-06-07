(function () {
  "use strict";

  var VIEW = 150;

  function qs(id) {
    return document.getElementById(id);
  }

  var form = qs("pulse-pe-form");
  var picker = qs("pulse-pe-picker");
  var fileSubmit = qs("pulse-pe-avatar-submit");
  var dropzone = qs("pulse-pe-dropzone");
  var stage = qs("pulse-pe-stage");
  var img = qs("pulse-pe-img");
  var cropPanel = qs("pulse-pe-crop");
  var zoomInput = qs("pulse-pe-zoom");

  function showCropPanel() {
    if (cropPanel) cropPanel.classList.add("pulse-pe__crop--visible");
  }

  function hideCropPanel() {
    if (cropPanel) cropPanel.classList.remove("pulse-pe__crop--visible");
  }

  var resetBtn = qs("pulse-pe-reset");
  var replaceBtn = qs("pulse-pe-replace");
  var currentWrap = qs("pulse-pe-current");
  var currentImg = qs("pulse-pe-current-img");
  var clearAvatarInput = qs("pulse-pe-clear-avatar");

  var state = {
    hasNewFile: false,
    zoom: 1,
    panX: 0,
    panY: 0,
    drag: null,
    objectUrl: null,
  };

  function getNaturalSize() {
    return { w: img.naturalWidth, h: img.naturalHeight };
  }

  function baseScale() {
    var s = getNaturalSize();
    if (!s.w || !s.h) return 1;
    return Math.max(VIEW / s.w, VIEW / s.h);
  }

  function displaySize() {
    var s = getNaturalSize();
    var bs = baseScale();
    return { w: s.w * bs * state.zoom, h: s.h * bs * state.zoom };
  }

  function clampPan() {
    var d = displaySize();
    state.panX = Math.min(0, Math.max(VIEW - d.w, state.panX));
    state.panY = Math.min(0, Math.max(VIEW - d.h, state.panY));
  }

  function centerPan() {
    var d = displaySize();
    state.panX = (VIEW - d.w) / 2;
    state.panY = (VIEW - d.h) / 2;
  }

  function layoutImage() {
    if (!state.hasNewFile || !img.naturalWidth) return;
    var d = displaySize();
    clampPan();
    img.style.width = d.w + "px";
    img.style.height = d.h + "px";
    img.style.left = state.panX + "px";
    img.style.top = state.panY + "px";
  }

  function exportCanvas() {
    if (!img.complete || !img.naturalWidth) return null;
    var nW = img.naturalWidth;
    var nH = img.naturalHeight;
    var bs = baseScale();
    var scaleTotal = bs * state.zoom;
    var dispW = nW * scaleTotal;
    var dispH = nH * scaleTotal;
    var ix = (-state.panX / dispW) * nW;
    var iy = (-state.panY / dispH) * nH;
    var sw = (VIEW / dispW) * nW;
    var sh = (VIEW / dispH) * nH;
    ix = Math.max(0, Math.min(ix, nW - 1e-6));
    iy = Math.max(0, Math.min(iy, nH - 1e-6));
    sw = Math.min(sw, nW - ix);
    sh = Math.min(sh, nH - iy);
    var canvas = document.createElement("canvas");
    canvas.width = VIEW;
    canvas.height = VIEW;
    var ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(img, ix, iy, sw, sh, 0, 0, VIEW, VIEW);
    return canvas;
  }

  function getPlaceholder() {
    return qs("pulse-pe-placeholder");
  }

  function ensurePlaceholder() {
    if (getPlaceholder() || !dropzone || !stage) return;
    var div = document.createElement("div");
    div.className = "pulse-pe__dropzone-placeholder";
    div.id = "pulse-pe-placeholder";
    div.innerHTML =
      '<span class="material-symbols-outlined pulse-pe__cam" aria-hidden="true">photo_camera</span>' +
      '<span class="pulse-pe__hint-text">Нажмите для загрузки фото</span>';
    dropzone.insertBefore(div, stage);
  }

  function showPlaceholder() {
    ensurePlaceholder();
    var ph = getPlaceholder();
    if (ph) ph.hidden = false;
  }

  function hidePlaceholder() {
    var ph = getPlaceholder();
    if (ph) ph.hidden = true;
  }

  function openPicker() {
    picker.click();
  }

  function hideCurrentAvatar() {
    currentWrap.hidden = true;
    currentImg.removeAttribute("src");
    currentImg.removeAttribute("alt");
  }

  function setClearAvatar(on) {
    if (clearAvatarInput) clearAvatarInput.value = on ? "1" : "0";
  }

  function applyDefaultCrop() {
    state.zoom = 1;
    zoomInput.value = "1";
    zoomInput.setAttribute("aria-valuenow", "1");
    centerPan();
    layoutImage();
  }

  function clearAvatarUi() {
    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = null;
    }
    state.hasNewFile = false;
    img.removeAttribute("src");
    stage.hidden = true;
    hideCropPanel();
    hideCurrentAvatar();
    showPlaceholder();
    fileSubmit.disabled = true;
    setClearAvatar(true);
  }

  function onFileChosen(file) {
    if (!file || !file.type || !/^image\//.test(file.type)) return;
    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = null;
    }
    state.objectUrl = URL.createObjectURL(file);
    state.hasNewFile = true;
    setClearAvatar(false);
    hideCurrentAvatar();
    hidePlaceholder();
    stage.hidden = false;
    showCropPanel();
    img.onload = function () {
      applyDefaultCrop();
    };
    img.src = state.objectUrl;
  }

  picker.addEventListener("change", function () {
    var f = picker.files && picker.files[0];
    picker.value = "";
    if (f) onFileChosen(f);
  });

  dropzone.addEventListener("click", function () {
    if (!stage.hidden) return;
    openPicker();
  });

  if (replaceBtn) {
    replaceBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      openPicker();
    });
  }

  dropzone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!stage.hidden) return;
      openPicker();
    }
  });

  zoomInput.addEventListener("input", function () {
    state.zoom = parseFloat(zoomInput.value) || 1;
    zoomInput.setAttribute("aria-valuenow", String(state.zoom));
    clampPan();
    layoutImage();
  });

  resetBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    clearAvatarUi();
  });

  function pointerPos(ev) {
    if (ev.touches && ev.touches[0]) return { x: ev.touches[0].clientX, y: ev.touches[0].clientY };
    return { x: ev.clientX, y: ev.clientY };
  }

  function onDragStart(ev) {
    if (!state.hasNewFile || stage.hidden) return;
    ev.preventDefault();
    var p = pointerPos(ev);
    state.drag = { startX: p.x, startY: p.y, pan0X: state.panX, pan0Y: state.panY };
    if (ev.pointerId != null) {
      try {
        stage.setPointerCapture(ev.pointerId);
      } catch (err) {}
    }
  }

  function onDragMove(ev) {
    if (!state.drag) return;
    var p = pointerPos(ev);
    state.panX = state.drag.pan0X + (p.x - state.drag.startX);
    state.panY = state.drag.pan0Y + (p.y - state.drag.startY);
    clampPan();
    layoutImage();
  }

  function onDragEnd(ev) {
    if (!state.drag) return;
    state.drag = null;
    if (ev && ev.pointerId != null) {
      try {
        stage.releasePointerCapture(ev.pointerId);
      } catch (err) {}
    }
  }

  stage.addEventListener("pointerdown", onDragStart);
  window.addEventListener("pointermove", onDragMove);
  window.addEventListener("pointerup", onDragEnd);
  window.addEventListener("pointercancel", onDragEnd);

  var isProcessing = false;
  form.addEventListener("submit", function (e) {
    if (isProcessing) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    isProcessing = true;
    function finishSubmit() {
      form.submit();
    }
    if (state.hasNewFile && img.naturalWidth) {
      setClearAvatar(false);
      var canvas = exportCanvas();
      if (!canvas) {
        fileSubmit.disabled = true;
        finishSubmit();
        return;
      }
      canvas.toBlob(
        function (blob) {
          if (blob) {
            try {
              var dt = new DataTransfer();
              dt.items.add(new File([blob], "avatar.jpg", { type: "image/jpeg" }));
              fileSubmit.files = dt.files;
              fileSubmit.disabled = false;
            } catch (err) {
              fileSubmit.disabled = true;
            }
          } else {
            fileSubmit.disabled = true;
          }
          finishSubmit();
        },
        "image/jpeg",
        0.92
      );
    } else {
      fileSubmit.disabled = true;
      finishSubmit();
    }
  });

  function init() {
    if (!form || !dropzone) return;
    state.hasNewFile = false;
    setClearAvatar(false);
    hideCropPanel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
