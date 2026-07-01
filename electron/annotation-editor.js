(() => {
  const API_BASE = window.desktopApi?.apiBase || "http://127.0.0.1:8765";
  const canvas = document.getElementById("annotationCanvas");
  const stage = document.getElementById("annotationStage");
  const video = document.getElementById("videoPlayer");
  const image = document.getElementById("annotationImagePreview");
  const noteInput = document.getElementById("segmentAnnotationInput");
  const saveButton = document.getElementById("saveAnnotationBtn");
  const deleteButton = document.getElementById("deleteAnnotationBtn");
  const status = document.getElementById("annotationStatus");
  const bindingLabel = document.getElementById("annotationBindingLabel");
  const list = document.getElementById("annotationList");
  const count = document.getElementById("annotationCount");
  const colorInput = document.getElementById("annotationColor");
  const widthInput = document.getElementById("annotationWidth");
  const undoButton = document.getElementById("annotationUndoBtn");
  const redoButton = document.getElementById("annotationRedoBtn");
  const clearButton = document.getElementById("annotationClearBtn");
  if (!canvas || !stage || !video) return;

  const typeLabels = { segment: "片段", brush: "画笔", rectangle: "矩形框" };
  let projectDir = "";
  let projectAnnotations = [];
  let segments = [];
  let selectedSegmentId = "";
  let selectedAnnotationId = "";
  let tool = "select";
  let draftShapes = [];
  let redoShapes = [];
  let activeShape = null;
  let pointerAction = null;
  let selectedDirty = false;
  let imageObjectUrl = "";
  let modelCapabilities = {};
  let modelProfileId = "";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function selectedAnnotation() {
    return projectAnnotations.find((item) => item.id === selectedAnnotationId) || null;
  }

  function currentTargetKind() {
    return image && !image.classList.contains("hidden") ? "image" : "video";
  }

  function currentTime() {
    return currentTargetKind() === "video" && Number.isFinite(video.currentTime) ? video.currentTime : 0;
  }

  function currentVideoRef() {
    try {
      const source = new URL(video.currentSrc);
      return source.searchParams.get("path") || video.currentSrc;
    } catch (_error) {
      return video.currentSrc || "";
    }
  }

  function formatTime(value) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "未绑定时间";
    const seconds = Number(value);
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds - minutes * 60;
    return `${String(minutes).padStart(2, "0")}:${remainder.toFixed(3).padStart(6, "0")}`;
  }

  function annotationBinding(annotation) {
    const segment = annotation.segment_id ? `片段 ${annotation.segment_id}` : "";
    const target = annotation.shape_data?.target_kind === "image" ? "图片区域" : formatTime(annotation.time_start);
    return [segment, target].filter(Boolean).join(" · ");
  }

  function updateBindingLabel() {
    if (!bindingLabel) return;
    const segment = selectedSegmentId && selectedSegmentId !== "final" ? ` · ${selectedSegmentId}` : "";
    bindingLabel.textContent = currentTargetKind() === "image"
      ? `绑定：当前图片区域${segment}`
      : `绑定：当前画面 ${formatTime(currentTime())}${segment}`;
  }

  function updateButtons() {
    const selected = selectedAnnotation();
    const canCreateSegment = tool === "segment" && selectedSegmentId && selectedSegmentId !== "final";
    saveButton.disabled = !projectDir || (!draftShapes.length && !selected && !canCreateSegment);
    deleteButton.disabled = !selected;
    undoButton.disabled = !draftShapes.length;
    redoButton.disabled = !redoShapes.length;
  }

  function setStatus(message) {
    if (status) status.textContent = message;
  }

  function setTool(nextTool) {
    tool = nextTool;
    document.querySelectorAll("[data-annotation-tool]").forEach((button) => {
      button.classList.toggle("active", button.dataset.annotationTool === tool);
    });
    canvas.classList.toggle("select-mode", tool === "select");
    canvas.style.pointerEvents = tool === "segment" ? "none" : "auto";
    if (tool === "segment") {
      setStatus("输入文字后保存片段批注；画布已让出，可操作播放器控件。");
    } else if (tool === "select") {
      setStatus("可选择矩形框并拖动、缩放，或从列表打开批注。");
    } else {
      setStatus("在画面上拖拽创建批注，完成后填写说明并保存。");
    }
    updateButtons();
  }

  function resizeCanvas() {
    const rect = stage.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    draw();
  }

  function pointFromEvent(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    };
  }

  function drawArrow(context, start, end, color, width, canvasWidth, canvasHeight) {
    const sx = start.x * canvasWidth;
    const sy = start.y * canvasHeight;
    const ex = end.x * canvasWidth;
    const ey = end.y * canvasHeight;
    const angle = Math.atan2(ey - sy, ex - sx);
    const head = Math.max(10, width * 3.5);
    context.beginPath();
    context.moveTo(sx, sy);
    context.lineTo(ex, ey);
    context.moveTo(ex, ey);
    context.lineTo(ex - head * Math.cos(angle - Math.PI / 6), ey - head * Math.sin(angle - Math.PI / 6));
    context.moveTo(ex, ey);
    context.lineTo(ex - head * Math.cos(angle + Math.PI / 6), ey - head * Math.sin(angle + Math.PI / 6));
    context.strokeStyle = color;
    context.lineWidth = width;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.stroke();
  }

  function drawShape(context, shape, isSelected = false) {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.width / ratio;
    const height = canvas.height / ratio;
    const color = shape.color || "#fb7185";
    const strokeWidth = Number(shape.width || 4);
    context.save();
    context.scale(ratio, ratio);
    context.strokeStyle = color;
    context.fillStyle = color;
    context.lineWidth = strokeWidth;
    context.lineCap = "round";
    context.lineJoin = "round";
    if (shape.kind === "rectangle") {
      context.strokeRect(shape.x * width, shape.y * height, shape.width_normalized * width, shape.height_normalized * height);
      if (isSelected) {
        const handle = 9;
        const hx = (shape.x + shape.width_normalized) * width;
        const hy = (shape.y + shape.height_normalized) * height;
        context.fillStyle = "#ffffff";
        context.fillRect(hx - handle / 2, hy - handle / 2, handle, handle);
        context.strokeStyle = "#0f172a";
        context.lineWidth = 1;
        context.strokeRect(hx - handle / 2, hy - handle / 2, handle, handle);
      }
    } else if (shape.kind === "arrow" && shape.points?.length >= 2) {
      drawArrow(context, shape.points[0], shape.points[shape.points.length - 1], color, strokeWidth, width, height);
    } else if (shape.points?.length) {
      context.beginPath();
      shape.points.forEach((point, index) => {
        const x = point.x * width;
        const y = point.y * height;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      if (shape.points.length === 1) context.lineTo(shape.points[0].x * width + 0.1, shape.points[0].y * height + 0.1);
      context.stroke();
    }
    context.restore();
  }

  function isVisibleAtCurrentPosition(annotation) {
    if (annotation.id === selectedAnnotationId) return true;
    if (annotation.shape_data?.target_kind === "image") return currentTargetKind() === "image";
    if (currentTargetKind() !== "video") return false;
    if (annotation.segment_id && selectedSegmentId && selectedSegmentId !== "final" && annotation.segment_id !== selectedSegmentId) return false;
    const start = Number(annotation.time_start);
    const end = annotation.time_end === null || annotation.time_end === undefined ? start : Number(annotation.time_end);
    if (!Number.isFinite(start)) return annotation.type === "segment" && annotation.segment_id === selectedSegmentId;
    return currentTime() >= start - 0.35 && currentTime() <= end + 0.35;
  }

  function draw() {
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);
    projectAnnotations.filter(isVisibleAtCurrentPosition).forEach((annotation) => {
      (annotation.shape_data?.shapes || []).forEach((shape) => drawShape(context, shape, annotation.id === selectedAnnotationId));
    });
    draftShapes.forEach((shape) => drawShape(context, shape));
    if (activeShape) drawShape(context, activeShape);
  }

  function shapeBounds(shape) {
    if (shape.kind === "rectangle") {
      return { left: shape.x, top: shape.y, right: shape.x + shape.width_normalized, bottom: shape.y + shape.height_normalized };
    }
    const points = shape.points || [];
    if (!points.length) return null;
    return {
      left: Math.min(...points.map((point) => point.x)),
      top: Math.min(...points.map((point) => point.y)),
      right: Math.max(...points.map((point) => point.x)),
      bottom: Math.max(...points.map((point) => point.y)),
    };
  }

  function hitTest(point) {
    const visible = projectAnnotations.filter(isVisibleAtCurrentPosition).slice().reverse();
    for (const annotation of visible) {
      const shapes = annotation.shape_data?.shapes || [];
      for (let index = shapes.length - 1; index >= 0; index -= 1) {
        const shape = shapes[index];
        const bounds = shapeBounds(shape);
        if (!bounds) continue;
        const padding = 0.025;
        if (point.x >= bounds.left - padding && point.x <= bounds.right + padding && point.y >= bounds.top - padding && point.y <= bounds.bottom + padding) {
          const resize = shape.kind === "rectangle"
            && Math.abs(point.x - bounds.right) < 0.035
            && Math.abs(point.y - bounds.bottom) < 0.05;
          return { annotation, shape, shapeIndex: index, resize };
        }
      }
    }
    return null;
  }

  function selectAnnotation(annotation, { populateNote = true } = {}) {
    selectedAnnotationId = annotation?.id || "";
    selectedDirty = false;
    if (annotation && populateNote) noteInput.value = annotation.text_note || "";
    if (annotation) {
      const firstShape = annotation.shape_data?.shapes?.[0];
      if (firstShape?.color) colorInput.value = firstShape.color;
      if (firstShape?.width) widthInput.value = String(firstShape.width);
    }
    renderList();
    updateButtons();
    draw();
  }

  function beginPointer(event) {
    if (!projectDir && tool !== "select") {
      setStatus("请先生成或加载项目，再创建批注。");
      return;
    }
    const point = pointFromEvent(event);
    if (tool === "select") {
      const hit = hitTest(point);
      if (!hit) {
        selectAnnotation(null, { populateNote: false });
        return;
      }
      selectAnnotation(hit.annotation);
      if (hit.shape.kind === "rectangle") {
        pointerAction = {
          kind: hit.resize ? "resize" : "move",
          shape: hit.shape,
          start: point,
          original: { ...hit.shape },
        };
      }
      canvas.setPointerCapture(event.pointerId);
      return;
    }
    if (!["brush", "arrow", "rectangle"].includes(tool)) return;
    video.pause();
    const base = { color: colorInput.value, width: Number(widthInput.value) };
    if (tool === "rectangle") {
      activeShape = { ...base, kind: "rectangle", x: point.x, y: point.y, width_normalized: 0, height_normalized: 0 };
    } else {
      activeShape = { ...base, kind: tool === "arrow" ? "arrow" : "freehand", points: [point] };
    }
    pointerAction = { kind: "draw", start: point };
    canvas.setPointerCapture(event.pointerId);
    draw();
  }

  function movePointer(event) {
    if (!pointerAction) return;
    const point = pointFromEvent(event);
    if (pointerAction.kind === "draw" && activeShape) {
      if (activeShape.kind === "rectangle") {
        activeShape.x = Math.min(pointerAction.start.x, point.x);
        activeShape.y = Math.min(pointerAction.start.y, point.y);
        activeShape.width_normalized = Math.abs(point.x - pointerAction.start.x);
        activeShape.height_normalized = Math.abs(point.y - pointerAction.start.y);
      } else if (activeShape.kind === "arrow") {
        activeShape.points = [pointerAction.start, point];
      } else {
        activeShape.points.push(point);
      }
    } else if (pointerAction.shape) {
      const shape = pointerAction.shape;
      const original = pointerAction.original;
      if (pointerAction.kind === "resize") {
        shape.width_normalized = Math.max(0.01, Math.min(1 - shape.x, point.x - shape.x));
        shape.height_normalized = Math.max(0.01, Math.min(1 - shape.y, point.y - shape.y));
      } else {
        const dx = point.x - pointerAction.start.x;
        const dy = point.y - pointerAction.start.y;
        shape.x = Math.max(0, Math.min(1 - original.width_normalized, original.x + dx));
        shape.y = Math.max(0, Math.min(1 - original.height_normalized, original.y + dy));
      }
      selectedDirty = true;
    }
    draw();
  }

  async function endPointer(event) {
    if (!pointerAction) return;
    if (pointerAction.kind === "draw" && activeShape) {
      const valid = activeShape.kind !== "rectangle"
        || (activeShape.width_normalized > 0.005 && activeShape.height_normalized > 0.005);
      if (valid) {
        draftShapes.push(activeShape);
        redoShapes = [];
        selectedAnnotationId = "";
        noteInput.focus();
        setStatus("图形已创建；填写文字说明后点击“保存批注”。");
      }
      activeShape = null;
    } else if (selectedDirty && selectedAnnotation()) {
      await saveCurrent();
    }
    pointerAction = null;
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    renderList();
    updateButtons();
    draw();
  }

  function buildPayload(annotationType, shapes) {
    const time = currentTime();
    const isSegment = annotationType === "segment";
    const segmentEnd = Number.isFinite(video.duration) ? video.duration : time;
    return {
      model_profile_id: modelProfileId,
      type: annotationType,
      segment_id: selectedSegmentId && selectedSegmentId !== "final" ? selectedSegmentId : "",
      time_start: currentTargetKind() === "video" ? (isSegment ? 0 : time) : null,
      time_end: currentTargetKind() === "video" ? (isSegment ? segmentEnd : time) : null,
      frame_index: currentTargetKind() === "video" ? Math.round((isSegment ? 0 : time) * 30) : null,
      shape_data: {
        version: 1,
        target_kind: currentTargetKind(),
        target_ref: currentTargetKind() === "image" ? (image.dataset.filename || "uploaded_image") : currentVideoRef(),
        coordinate_space: "normalized",
        shapes,
      },
      text_note: noteInput.value.trim(),
    };
  }

  async function request(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "批注操作失败。");
    return payload;
  }

  async function saveCurrent() {
    if (!projectDir) throw new Error("当前项目路径不可用。");
    if (currentTargetKind() === "image" && !modelCapabilities.image_annotation) {
      throw new Error("当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。");
    }
    const selected = selectedAnnotation();
    if (selected && !draftShapes.length) {
      const payload = { ...selected, project_dir: projectDir, model_profile_id: modelProfileId, text_note: noteInput.value.trim() };
      const result = await request(`${API_BASE}/project/annotations/${encodeURIComponent(selected.id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      projectAnnotations = projectAnnotations.map((item) => item.id === selected.id ? result.annotation : item);
      selectedDirty = false;
      selectAnnotation(result.annotation);
      setStatus("批注已更新并保存到项目文件。");
      return result.annotation;
    }

    const type = tool === "rectangle" || draftShapes.some((shape) => shape.kind === "rectangle") ? "rectangle"
      : tool === "segment" && !draftShapes.length ? "segment" : "brush";
    const payload = { project_dir: projectDir, ...buildPayload(type, draftShapes) };
    const result = await request(`${API_BASE}/project/annotations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    projectAnnotations.push(result.annotation);
    draftShapes = [];
    redoShapes = [];
    selectAnnotation(result.annotation);
    setStatus("批注已保存到项目文件 annotations.json。");
    return result.annotation;
  }

  async function deleteAnnotation(annotationId = selectedAnnotationId) {
    if (!annotationId || !projectDir) return;
    await request(`${API_BASE}/project/annotations/${encodeURIComponent(annotationId)}?project_dir=${encodeURIComponent(projectDir)}`, { method: "DELETE" });
    projectAnnotations = projectAnnotations.filter((item) => item.id !== annotationId);
    if (selectedAnnotationId === annotationId) {
      selectedAnnotationId = "";
      noteInput.value = "";
    }
    renderList();
    updateButtons();
    draw();
    setStatus("批注已删除。");
  }

  function seekToAnnotation(annotation) {
    selectAnnotation(annotation);
    let switchedSegment = false;
    if (annotation.segment_id && annotation.segment_id !== selectedSegmentId) {
      const segmentButton = document.querySelector(`.segment-chip[data-segment-id="${CSS.escape(annotation.segment_id)}"]`);
      if (segmentButton) {
        switchedSegment = true;
        segmentButton.click();
      }
    }
    const seek = () => {
      if (annotation.time_start !== null && annotation.time_start !== undefined && video.duration) {
        video.currentTime = Math.min(Number(annotation.time_start), video.duration || Number(annotation.time_start));
      }
      updateBindingLabel();
      draw();
    };
    if (!switchedSegment && video.readyState >= 1) seek();
    else video.addEventListener("loadedmetadata", seek, { once: true });
    setStatus("已跳转到批注绑定位置。");
  }

  function renderList() {
    count.textContent = `${projectAnnotations.length} 条`;
    if (!projectAnnotations.length) {
      list.innerHTML = '<div class="annotation-empty">当前项目暂无批注。</div>';
      return;
    }
    list.innerHTML = projectAnnotations.slice().reverse().map((annotation) => `
      <article class="annotation-list-item ${annotation.id === selectedAnnotationId ? "active" : ""}" data-annotation-id="${escapeHtml(annotation.id)}">
        <div class="annotation-list-main">
          <div class="annotation-list-title"><span class="annotation-type-badge">${escapeHtml(typeLabels[annotation.type] || annotation.type)}</span><span class="annotation-list-binding">${escapeHtml(annotationBinding(annotation))}</span></div>
          <div class="annotation-list-note">${escapeHtml(annotation.text_note || "（无文字说明）")}</div>
        </div>
        <div class="annotation-list-actions">
          <button data-annotation-action="jump">跳转</button>
          <button data-annotation-action="edit">编辑</button>
          <button data-annotation-action="delete">删除</button>
        </div>
      </article>
    `).join("");
    list.querySelectorAll(".annotation-list-item").forEach((item) => {
      const annotation = projectAnnotations.find((entry) => entry.id === item.dataset.annotationId);
      item.addEventListener("click", (event) => {
        const action = event.target.closest("button")?.dataset.annotationAction || "jump";
        if (action === "delete") deleteAnnotation(annotation.id).catch((error) => setStatus(`删除失败：${error.message}`));
        else if (action === "edit") {
          selectAnnotation(annotation);
          setTool("select");
          noteInput.focus();
          setStatus("正在编辑批注；修改文字、颜色、粗细或矩形位置后保存。");
        } else seekToAnnotation(annotation);
      });
    });
  }

  async function loadAnnotations() {
    if (!projectDir) {
      projectAnnotations = [];
      renderList();
      draw();
      return;
    }
    try {
      const payload = await request(`${API_BASE}/project/annotations?project_dir=${encodeURIComponent(projectDir)}`);
      projectAnnotations = payload.annotations || [];
      selectedAnnotationId = "";
      renderList();
      draw();
      setStatus(`已加载 ${projectAnnotations.length} 条项目批注。`);
    } catch (error) {
      setStatus(`批注加载失败：${error.message}`);
    }
  }

  async function setProject(nextProjectDir, nextSegments = []) {
    segments = nextSegments || [];
    const normalizedProjectDir = nextProjectDir || "";
    const changed = normalizedProjectDir !== projectDir;
    projectDir = normalizedProjectDir;
    updateButtons();
    if (changed) await loadAnnotations();
  }

  function setSelectedSegment(segmentId) {
    selectedSegmentId = segmentId || "";
    updateBindingLabel();
    updateButtons();
    draw();
  }

  function setImagePreview(file) {
    if (file && !(modelCapabilities.vision && modelCapabilities.image_upload && modelCapabilities.multimodal_input && modelCapabilities.image_annotation)) {
      setStatus("当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。");
      return false;
    }
    if (imageObjectUrl) URL.revokeObjectURL(imageObjectUrl);
    if (!file) {
      imageObjectUrl = "";
      image.removeAttribute("src");
      image.classList.add("hidden");
      video.classList.remove("hidden");
    } else {
      imageObjectUrl = URL.createObjectURL(file);
      image.src = imageObjectUrl;
      image.dataset.filename = file.name;
      image.classList.remove("hidden");
      video.classList.add("hidden");
    }
    updateBindingLabel();
    draw();
    return true;
  }

  function setCapabilities(capabilities = {}, profileId = "") {
    modelCapabilities = capabilities || {};
    modelProfileId = profileId || "";
    if (!modelCapabilities.image_annotation && currentTargetKind() === "image") showVideo();
  }

  function showVideo() {
    image.classList.add("hidden");
    video.classList.remove("hidden");
    updateBindingLabel();
    draw();
  }

  document.querySelectorAll("[data-annotation-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.annotationTool)));
  canvas.addEventListener("pointerdown", beginPointer);
  canvas.addEventListener("pointermove", movePointer);
  canvas.addEventListener("pointerup", (event) => endPointer(event).catch((error) => setStatus(`保存失败：${error.message}`)));
  canvas.addEventListener("pointercancel", (event) => endPointer(event).catch(() => {}));
  saveButton.addEventListener("click", () => saveCurrent().catch((error) => setStatus(`保存失败：${error.message}`)));
  deleteButton.addEventListener("click", () => deleteAnnotation().catch((error) => setStatus(`删除失败：${error.message}`)));
  undoButton.addEventListener("click", () => {
    if (draftShapes.length) redoShapes.push(draftShapes.pop());
    draw();
    updateButtons();
  });
  redoButton.addEventListener("click", () => {
    if (redoShapes.length) draftShapes.push(redoShapes.pop());
    draw();
    updateButtons();
  });
  clearButton.addEventListener("click", () => {
    const selected = selectedAnnotation();
    if (draftShapes.length) {
      redoShapes.push(...draftShapes.splice(0));
    } else if (selected?.shape_data?.shapes?.length) {
      selected.shape_data.shapes = [];
      selectedDirty = true;
      setStatus("当前批注图形已清除；点击保存以写入项目。");
    }
    draw();
    updateButtons();
  });
  noteInput.addEventListener("input", () => {
    if (selectedAnnotation()) selectedDirty = true;
    updateButtons();
  });
  colorInput.addEventListener("input", () => {
    const selected = selectedAnnotation();
    if (selected) {
      (selected.shape_data?.shapes || []).forEach((shape) => { shape.color = colorInput.value; });
      selectedDirty = true;
    }
    draftShapes.forEach((shape) => { shape.color = colorInput.value; });
    draw();
  });
  widthInput.addEventListener("input", () => {
    const selected = selectedAnnotation();
    if (selected) {
      (selected.shape_data?.shapes || []).forEach((shape) => { shape.width = Number(widthInput.value); });
      selectedDirty = true;
    }
    draftShapes.forEach((shape) => { shape.width = Number(widthInput.value); });
    draw();
  });
  video.addEventListener("timeupdate", () => { updateBindingLabel(); draw(); });
  video.addEventListener("loadedmetadata", showVideo);
  new ResizeObserver(resizeCanvas).observe(stage);
  window.addEventListener("resize", resizeCanvas);

  window.annotationEditor = {
    setProject,
    setSelectedSegment,
    setImagePreview,
    setCapabilities,
    showVideo,
    saveCurrent,
    ensureSegmentAnnotation: async (text) => {
      noteInput.value = text;
      const selected = selectedAnnotation();
      if (selected && selected.segment_id !== selectedSegmentId) selectAnnotation(null, { populateNote: false });
      const previousTool = tool;
      if (!draftShapes.length && !selectedAnnotation()) setTool("segment");
      const annotation = await saveCurrent();
      setTool(previousTool);
      return annotation;
    },
    reload: loadAnnotations,
  };

  setTool("select");
  resizeCanvas();
  renderList();
  updateBindingLabel();
})();
