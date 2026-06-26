const API_BASE = "http://127.0.0.1:8765";

const elements = {
  imageInput: document.getElementById("imageInput"),
  imageName: document.getElementById("imageName"),
  promptInput: document.getElementById("promptInput"),
  providerInput: document.getElementById("providerInput"),
  qualityInput: document.getElementById("qualityInput"),
  durationInput: document.getElementById("durationInput"),
  maxDurationMinutesInput: document.getElementById("maxDurationMinutesInput"),
  sceneCountModeInput: document.getElementById("sceneCountModeInput"),
  sceneCountInput: document.getElementById("sceneCountInput"),
  compactTimingInput: document.getElementById("compactTimingInput"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  baseUrlInput: document.getElementById("baseUrlInput"),
  modelInput: document.getElementById("modelInput"),
  generateBtn: document.getElementById("generateBtn"),
  outputBtn: document.getElementById("outputBtn"),
  outputDir: document.getElementById("outputDir"),
  logOutput: document.getElementById("logOutput"),
  storyboardView: document.getElementById("storyboardView"),
  codeView: document.getElementById("codeView"),
  repairsView: document.getElementById("repairsView"),
  videoPlayer: document.getElementById("videoPlayer"),
  replayBtn: document.getElementById("replayBtn"),
  pauseTaskBtn: document.getElementById("pauseTaskBtn"),
  resumeTaskBtn: document.getElementById("resumeTaskBtn"),
  stagePreviewList: document.getElementById("stagePreviewList"),
  segmentPreviewList: document.getElementById("segmentPreviewList"),
  audioPreviewList: document.getElementById("audioPreviewList"),
  audioStatus: document.getElementById("audioStatus"),
  projectPath: document.getElementById("projectPath"),
  projectFileList: document.getElementById("projectFileList"),
  projectFileContent: document.getElementById("projectFileContent"),
  quickModeTab: document.getElementById("quickModeTab"),
  workflowModeTab: document.getElementById("workflowModeTab"),
  quickView: document.getElementById("quickView"),
  workflowView: document.getElementById("workflowView"),
  nodeLibrary: document.getElementById("nodeLibrary"),
  workflowCanvas: document.getElementById("workflowCanvas"),
  workflowEdges: document.getElementById("workflowEdges"),
  workflowNodes: document.getElementById("workflowNodes"),
  nodeInspector: document.getElementById("nodeInspector"),
  workflowLog: document.getElementById("workflowLog"),
  workflowVideoPlayer: document.getElementById("workflowVideoPlayer"),
  workflowReplayBtn: document.getElementById("workflowReplayBtn"),
  workflowProjectPath: document.getElementById("workflowProjectPath"),
  workflowSummaryView: document.getElementById("workflowSummaryView"),
  workflowStoryboardView: document.getElementById("workflowStoryboardView"),
  workflowCodeView: document.getElementById("workflowCodeView"),
  loadMathTemplateBtn: document.getElementById("loadMathTemplateBtn"),
  loadImageTemplateBtn: document.getElementById("loadImageTemplateBtn"),
  loadMechanicsTemplateBtn: document.getElementById("loadMechanicsTemplateBtn"),
  validateWorkflowBtn: document.getElementById("validateWorkflowBtn"),
  runWorkflowBtn: document.getElementById("runWorkflowBtn"),
  saveWorkflowBtn: document.getElementById("saveWorkflowBtn"),
  loadWorkflowInput: document.getElementById("loadWorkflowInput"),
  fitWorkflowBtn: document.getElementById("fitWorkflowBtn"),
  editPromptInput: document.getElementById("editPromptInput"),
  applyEditBtn: document.getElementById("applyEditBtn"),
  editStatus: document.getElementById("editStatus"),
  editHistory: document.getElementById("editHistory"),
  promptPanelBtn: document.getElementById("promptPanelBtn"),
  promptModal: document.getElementById("promptModal"),
  closePromptPanelBtn: document.getElementById("closePromptPanelBtn"),
  promptNameList: document.getElementById("promptNameList"),
  promptNameInput: document.getElementById("promptNameInput"),
  promptTemplateInput: document.getElementById("promptTemplateInput"),
  savePromptBtn: document.getElementById("savePromptBtn"),
  reloadPromptBtn: document.getElementById("reloadPromptBtn"),
  promptPanelStatus: document.getElementById("promptPanelStatus"),
  annotationSegmentLabel: document.getElementById("annotationSegmentLabel"),
  segmentAnnotationInput: document.getElementById("segmentAnnotationInput"),
  sendSegmentAnnotationBtn: document.getElementById("sendSegmentAnnotationBtn"),
  annotationStatus: document.getElementById("annotationStatus")
};

let selectedOutputDir = "";
let lastRenderedLogs = "";
let nodeDefinitions = {};
let workflow = null;
let selectedNodeId = null;
let pendingConnection = null;
let dragState = null;
let panState = null;
let currentQuickTaskId = null;
let currentStages = [];
let currentSegments = [];
let lastQuickResult = null;
let editHistory = [];
let promptTemplates = {};
let selectedPromptName = "";
let selectedSegmentId = "";

const categoryLabels = {
  input: "输入",
  image: "图像",
  ai: "AI",
  planning: "规划",
  code: "代码",
  render: "渲染",
  output: "输出",
  comment: "注释",
};

const nodeTypeLabels = {
  InputImageNode: "图片输入",
  PromptInputNode: "提示词",
  ModelConfigNode: "模型配置",
  ImagePreprocessNode: "图像预处理",
  ImageUnderstandNode: "图像理解",
  TeachingPlanNode: "教学规划",
  StoryboardNode: "分镜",
  SubtitleNode: "字幕",
  ManimCodeNode: "Manim 代码",
  RenderNode: "渲染",
  RepairNode: "修复",
  OutputNode: "输出",
  PreviewNode: "预览",
  CommentNode: "注释",
};

function applyDefaultTestSettings() {
  if (!elements.promptInput.value.trim()) {
    elements.promptInput.value = "介绍铁路路基道床的组成、功能、荷载传递、排水、弹性缓冲和施工整形过程。";
  }
  elements.providerInput.value = "deepseek";
  elements.qualityInput.value = "low";
  if (!elements.baseUrlInput.value.trim()) {
    elements.baseUrlInput.value = "https://api.deepseek.com/v1";
  }
  if (!elements.modelInput.value.trim()) {
    elements.modelInput.value = "deepseek-v4-pro";
  }
}

function appendLog(message) {
  const now = new Date().toLocaleTimeString();
  elements.logOutput.textContent += `[${now}] ${message}\n`;
  elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
}

function appendWorkflowLog(message) {
  const now = new Date().toLocaleTimeString();
  elements.workflowLog.textContent += `[${now}] ${message}\n`;
  elements.workflowLog.scrollTop = elements.workflowLog.scrollHeight;
}

async function openPromptPanel() {
  if (!elements.promptModal) return;
  elements.promptModal.classList.remove("hidden");
  await loadPromptTemplates();
}

function closePromptPanel() {
  if (!elements.promptModal) return;
  elements.promptModal.classList.add("hidden");
}

async function loadPromptTemplates() {
  if (!elements.promptNameList) return;
  elements.promptPanelStatus.textContent = "正在读取提示词...";
  const response = await fetch(`${API_BASE}/prompts`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "提示词读取失败。");
  promptTemplates = payload.prompts || {};
  selectedPromptName = selectedPromptName && promptTemplates[selectedPromptName]
    ? selectedPromptName
    : Object.keys(promptTemplates)[0] || "";
  renderPromptTemplateList();
  selectPromptTemplate(selectedPromptName);
  elements.promptPanelStatus.textContent = "提示词已读取。";
}

function renderPromptTemplateList() {
  if (!elements.promptNameList) return;
  elements.promptNameList.innerHTML = Object.keys(promptTemplates).map((name) => `
    <button class="prompt-name-item ${name === selectedPromptName ? "active" : ""}" data-prompt-name="${escapeHtml(name)}">${escapeHtml(name)}</button>
  `).join("");
  elements.promptNameList.querySelectorAll(".prompt-name-item").forEach((button) => {
    button.addEventListener("click", () => selectPromptTemplate(button.dataset.promptName));
  });
}

function selectPromptTemplate(name) {
  selectedPromptName = name || "";
  if (elements.promptNameInput) elements.promptNameInput.value = selectedPromptName;
  if (elements.promptTemplateInput) elements.promptTemplateInput.value = promptTemplates[selectedPromptName] || "";
  renderPromptTemplateList();
}

async function saveSelectedPromptTemplate() {
  if (!selectedPromptName) return;
  promptTemplates[selectedPromptName] = elements.promptTemplateInput.value;
  elements.promptPanelStatus.textContent = "正在保存提示词...";
  const response = await fetch(`${API_BASE}/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompts: promptTemplates })
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "提示词保存失败。");
  promptTemplates = payload.prompts || promptTemplates;
  elements.promptPanelStatus.textContent = "提示词已保存，后续生成立即生效。";
  renderPromptTemplateList();
}

function getWorkflowViewport() {
  if (!workflow) return { x: 0, y: 0, zoom: 1 };
  workflow.viewport = workflow.viewport || { x: 0, y: 0, zoom: 1 };
  workflow.viewport.zoom = workflow.viewport.zoom || 1;
  return workflow.viewport;
}

function labelForNode(definitionOrType) {
  const type = typeof definitionOrType === "string" ? definitionOrType : definitionOrType?.type;
  return nodeTypeLabels[type] || definitionOrType?.label || type || "节点";
}

function renderTaskLogs(logs) {
  const text = logs.join("\n");
  if (text === lastRenderedLogs) return;
  lastRenderedLogs = text;
  elements.logOutput.textContent = text + "\n";
  elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
}

function applyResult(result) {
  lastQuickResult = result;
  elements.projectPath.textContent = `项目：${result.project_dir || "不可用"}`;
  elements.storyboardView.textContent = JSON.stringify(result.storyboard || [], null, 2);
  elements.codeView.textContent = result.manim_code || "";
  elements.repairsView.textContent = [
    `AI 记录：${result.ai_trace_dir || "不可用"}`,
    `修复日志：${result.repair_log_dir || "不可用"}`,
    `渲染日志：${result.render_log_dir || "不可用"}`,
    result.failure_reason || "渲染成功。"
  ].join("\n");

  if (result.video_path) {
    const cacheBuster = Date.now();
    const videoUrl = `${API_BASE}/video?path=${encodeURIComponent(result.video_path)}&t=${cacheBuster}`;
    loadVideo(elements.videoPlayer, videoUrl, appendLog);
    loadVideo(elements.workflowVideoPlayer, videoUrl, appendWorkflowLog);
  } else {
    elements.videoPlayer.pause();
    elements.videoPlayer.removeAttribute("src");
    elements.videoPlayer.load();
  }
  renderAudioStatus(result);
  if (elements.applyEditBtn) {
    elements.applyEditBtn.disabled = !result.project_dir;
    elements.editStatus.textContent = "可整片修改；点击某个片段后可只替换该片段。";
  }
  currentStages = result.stages || [];
  currentSegments = result.segments || [];
  renderStages(currentStages, currentSegments, 3);
  renderSegments(currentSegments, result.video_path);
  renderAudioPreview(result);
  autoLoadFirstSegmentVideo(currentSegments);
  if (result.project_dir) loadProjectFiles(result.project_dir);
  applyWorkflowResult(result);
}

function applyPartialResult(partial) {
  if (!partial) return;
  lastQuickResult = { ...(lastQuickResult || {}), ...partial };
  if (partial.project_dir) elements.projectPath.textContent = `项目：${partial.project_dir}`;
  if (partial.storyboard) elements.storyboardView.textContent = JSON.stringify(partial.storyboard, null, 2);
  currentStages = partial.stages || currentStages;
  currentSegments = partial.segments || currentSegments;
  renderStages(currentStages, currentSegments, detectCurrentStage([]));
  renderSegments(currentSegments, partial.video_path || null);
  renderAudioPreview(partial);
  autoLoadFirstSegmentVideo(currentSegments);
}
function renderAudioStatus(result) {
  if (!elements.audioStatus) return;
  const status = result.tts_status || (result.tts_enabled ? "unknown" : "disabled");
  const audioPath = result.audio_path ? ` ???${result.audio_path}` : "";
  elements.audioStatus.classList.remove("success", "warning");
  if (status === "embedded") {
    elements.audioStatus.textContent = `?????????${audioPath}`;
    elements.audioStatus.classList.add("success");
  } else if (status === "not_embedded" || status === "audio_only") {
    elements.audioStatus.textContent = `???????????????????${audioPath}`;
    elements.audioStatus.classList.add("warning");
  } else if (status === "failed") {
    elements.audioStatus.textContent = `??????????????????${result.tts_error || ""}`;
    elements.audioStatus.classList.add("warning");
  } else {
    elements.audioStatus.textContent = "????????????";
  }
}

function buildDefaultStages(totalDuration = 300) {
  const seconds = Math.round(totalDuration / 3);
  return [
    { stage: 1, title: "第一阶段：大纲脚本", status: "planned", estimated_seconds: seconds, scene_indexes: [] },
    { stage: 2, title: "第二阶段：分镜预览", status: "planned", estimated_seconds: seconds, scene_indexes: [] },
    { stage: 3, title: "第三阶段：拼接导出", status: "planned", estimated_seconds: seconds, scene_indexes: [], is_stitching_stage: true }
  ];
}

function detectCurrentStage(logs) {
  const text = (logs || []).join("\n");
  if (/Stage 3\/3|阶段 3\/3|第三阶段/.test(text)) return 3;
  if (/Stage 2\/3|阶段 2\/3|第二阶段/.test(text)) return 2;
  if (/Stage 1\/3|阶段 1\/3|第一阶段/.test(text)) return 1;
  return 1;
}

function renderStages(stages, segments = [], activeStage = 1) {
  if (!elements.stagePreviewList) return;
  const stageData = stages.length ? stages : buildDefaultStages(Number(elements.durationInput?.value || 300));
  elements.stagePreviewList.innerHTML = stageData.map((stage) => {
    const stageNumber = Number(stage.stage || 1);
    const sceneCount = segments.filter((segment) => Number(segment.stage || 1) === stageNumber).length || (stage.scene_indexes || []).length;
    const classes = ["stage-card"];
    if (stageNumber === activeStage) classes.push("current");
    if (stageNumber < activeStage || stage.status === "stitched") classes.push("done");
    const stitching = stage.is_stitching_stage ? " · 最后拼接" : "";
    return `
      <button class="${classes.join(" ")}" data-stage="${stageNumber}">
        <strong>${escapeHtml(stage.title || `第 ${stageNumber} 阶段`)}</strong>
        <span>${escapeHtml(stage.status || "planned")} · ${stage.estimated_seconds || ""}s · ${sceneCount} 个分镜${stitching}</span>
      </button>
    `;
  }).join("");
  elements.stagePreviewList.querySelectorAll(".stage-card").forEach((button) => {
    button.addEventListener("click", () => {
      const stage = Number(button.dataset.stage || 1);
      renderStages(stageData, currentSegments, stage);
      renderSegments(currentSegments.filter((segment) => Number(segment.stage || 1) === stage), null);
    });
  });
}

function renderSegments(segments, fallbackVideoPath) {
  if (!elements.segmentPreviewList) return;
  const finalVideoPath = fallbackVideoPath || lastQuickResult?.video_path || "";
  const previousTimeline = elements.segmentPreviewList.querySelector(".segment-timeline");
  const previousScrollLeft = previousTimeline ? previousTimeline.scrollLeft : 0;
  if (!segments.length) {
    elements.segmentPreviewList.innerHTML = `
      <button class="compose-chip ${finalVideoPath ? "ready" : ""}" data-video-path="${escapeHtml(finalVideoPath)}">合成<br>视频</button>
      <div class="path-line">暂无片段。等待分镜规划或片段渲染完成。</div>
    `;
    bindComposeVideoButton();
    return;
  }
  elements.segmentPreviewList.innerHTML = `
    <button class="compose-chip ${finalVideoPath ? "ready" : ""} ${selectedSegmentId === "final" ? "active" : ""}" data-video-path="${escapeHtml(finalVideoPath)}">
      合成<br>视频
    </button>
    <div class="segment-timeline">
      ${segments.map((segment, index) => `
        <button class="segment-chip ${segment.id === selectedSegmentId ? "active" : ""} ${escapeHtml(segment.status || "planned")}" data-video-path="${escapeHtml(segment.video_path || "")}" data-segment-id="${escapeHtml(segment.id || "")}" data-segment-index="${index}">
          <strong>${index + 1}</strong>
          <span>${escapeHtml(segment.title || segment.id || "片段")}</span>
        </button>
      `).join("")}
    </div>
  `;
  const timeline = elements.segmentPreviewList.querySelector(".segment-timeline");
  if (timeline) timeline.scrollLeft = previousScrollLeft;
  bindComposeVideoButton();
  elements.segmentPreviewList.querySelectorAll(".segment-chip").forEach((button) => {
    button.addEventListener("click", () => {
      elements.segmentPreviewList.querySelectorAll(".segment-chip, .compose-chip").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      selectedSegmentId = button.dataset.segmentId || "";
      if (elements.editStatus) {
        elements.editStatus.textContent = selectedSegmentId ? `已选择 ${selectedSegmentId}，提交修改将只替换该片段。` : "未选择片段。";
      }
      updateAnnotationSelection(button);
      const videoPath = button.dataset.videoPath;
      if (videoPath) {
        playVideoPath(videoPath, appendLog);
      } else {
        appendLog("该片段尚未生成视频，等待渲染完成或选择其他片段。");
      }
    });
  });
}

function bindComposeVideoButton() {
  const button = elements.segmentPreviewList?.querySelector(".compose-chip");
  if (!button) return;
  button.addEventListener("click", () => {
    const videoPath = button.dataset.videoPath;
    if (!videoPath) {
      appendLog("最终合成视频尚未生成；可以先点击右侧已完成的分镜片段预览。");
      return;
    }
    elements.segmentPreviewList.querySelectorAll(".segment-chip, .compose-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedSegmentId = "final";
    updateAnnotationSelection(null);
    if (elements.editStatus) {
      elements.editStatus.textContent = "正在预览合成视频；点击某个分镜节点后可只替换该片段。";
    }
    playVideoPath(videoPath, appendLog);
  });
}

function updateAnnotationSelection(button) {
  if (!elements.annotationSegmentLabel || !elements.sendSegmentAnnotationBtn) return;
  const segmentId = button?.dataset?.segmentId || (selectedSegmentId && selectedSegmentId !== "final" ? selectedSegmentId : "");
  const segment = currentSegments.find((item) => item.id === segmentId);
  if (!segmentId || !segment) {
    elements.annotationSegmentLabel.textContent = "请选择下方分镜片段";
    elements.sendSegmentAnnotationBtn.disabled = true;
    return;
  }
  elements.annotationSegmentLabel.textContent = `当前片段：${segmentId} · ${segment.title || "未命名"}`;
  elements.sendSegmentAnnotationBtn.disabled = !lastQuickResult?.project_dir;
}

async function submitSegmentAnnotation() {
  const targetSegmentId = selectedSegmentId;
  if (!targetSegmentId || targetSegmentId === "final") {
    elements.annotationStatus.textContent = "请先点击下方某个分镜片段。";
    return;
  }
  const note = elements.segmentAnnotationInput.value.trim();
  if (!note) {
    elements.annotationStatus.textContent = "请先输入标注或修改要求。";
    return;
  }
  if (!lastQuickResult?.project_dir) {
    elements.annotationStatus.textContent = "当前项目路径不可用。";
    return;
  }
  const form = new FormData();
  form.append("source_project_dir", lastQuickResult.project_dir);
  form.append("segment_id", targetSegmentId);
  form.append("provider", elements.providerInput.value);
  form.append("api_key", elements.apiKeyInput.value);
  form.append("base_url", elements.baseUrlInput.value);
  form.append("model", elements.modelInput.value);
  form.append("quality", elements.qualityInput.value);
  form.append("edit_prompt", `用户对当前视频片段的标注与修改要求：${note}\n请只重做这个片段，保留整体教学目标，并显著改变与相邻片段重复的视觉构图。`);
  elements.annotationStatus.textContent = `已提交 ${targetSegmentId} 的修正任务，当前生成不会被暂停。`;
  const response = await fetch(`${API_BASE}/replace_segment_async`, { method: "POST", body: form });
  const task = await response.json();
  if (!response.ok) throw new Error(task.detail || "片段修正任务提交失败。");
  monitorBackgroundTask(task.task_id, `片段修正 ${targetSegmentId}`, targetSegmentId);
}

async function monitorBackgroundTask(taskId, label, targetSegmentId = "") {
  try {
    while (true) {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`);
      const task = await response.json();
      if (!response.ok) throw new Error(task.detail || "后台任务查询失败。");
      if (task.partial_result) {
        applyNonIntrusivePartialResult(task.partial_result);
        await refreshProjectStatus(task.project_dir || task.partial_result?.project_dir || lastQuickResult?.project_dir);
      }
      if (task.state === "succeeded") {
        applyNonIntrusivePartialResult(task.result);
        elements.annotationStatus.textContent = `${label} 完成，片段已更新。`;
        if (selectedSegmentId === targetSegmentId) {
          const updated = currentSegments.find((segment) => segment.id === targetSegmentId);
          if (updated?.video_path) playVideoPath(updated.video_path, appendLog);
        }
        return;
      }
      if (task.state === "failed") {
        throw new Error(task.error || `${label} 失败。`);
      }
      await new Promise((resolve) => setTimeout(resolve, 1800));
    }
  } catch (error) {
    elements.annotationStatus.textContent = `${label} 失败：${error.message}`;
  }
}

function selectedTotalDurationSeconds() {
  const minutes = Number(elements.maxDurationMinutesInput?.value || 0);
  if (minutes > 0) return Math.round(minutes * 60);
  return Number(elements.durationInput?.value || 300);
}

function selectedStoryboardSceneCount() {
  if (elements.sceneCountModeInput?.value !== "manual") return 0;
  return Math.max(6, Math.min(60, Number(elements.sceneCountInput?.value || 15)));
}

function renderAudioPreview(result = {}) {
  if (!elements.audioPreviewList) return;
  const segments = currentSegments.length ? currentSegments : [];
  const audioPaths = result.tts_scene_audio_paths || lastQuickResult?.tts_scene_audio_paths || [];
  const ttsStatus = result.tts_status || lastQuickResult?.tts_status || "pending";
  const count = Math.max(segments.length, audioPaths.length, selectedStoryboardSceneCount() || 0, 1);
  elements.audioPreviewList.innerHTML = Array.from({ length: count }, (_, index) => {
    const hasAudio = Boolean(audioPaths[index]);
    const state = hasAudio ? "ready" : (ttsStatus === "failed" ? "failed" : "pending");
    return `<div class="audio-segment ${state}" title="语音片段 ${index + 1}"><span>${index + 1}</span></div>`;
  }).join("");
}

function applyNonIntrusivePartialResult(partial) {
  if (!partial) return;
  const playingSrc = elements.videoPlayer?.getAttribute("src") || "";
  lastQuickResult = { ...(lastQuickResult || {}), ...partial };
  if (partial.project_dir) elements.projectPath.textContent = `项目：${partial.project_dir}`;
  currentStages = partial.stages || currentStages;
  currentSegments = partial.segments || currentSegments;
  renderStages(currentStages, currentSegments, detectCurrentStage([]));
  renderSegments(currentSegments, partial.video_path || null);
  renderAudioPreview(partial);
  if (playingSrc && elements.videoPlayer && !elements.videoPlayer.getAttribute("src")) {
    elements.videoPlayer.setAttribute("src", playingSrc);
    elements.videoPlayer.load();
  }
}

function playVideoPath(videoPath, logger) {
  const videoUrl = `${API_BASE}/video?path=${encodeURIComponent(videoPath)}&t=${Date.now()}`;
  loadVideo(elements.videoPlayer, videoUrl, logger);
}

function autoLoadFirstSegmentVideo(segments) {
  if (!elements.videoPlayer || elements.videoPlayer.getAttribute("src")) return;
  const firstPlayable = (segments || []).find((segment) => segment.video_path);
  if (!firstPlayable) return;
  selectedSegmentId = firstPlayable.id || selectedSegmentId;
  updateAnnotationSelection(null);
  playVideoPath(firstPlayable.video_path, appendLog);
  if (elements.workflowVideoPlayer) {
    const videoUrl = `${API_BASE}/video?path=${encodeURIComponent(firstPlayable.video_path)}&t=${Date.now()}`;
    loadVideo(elements.workflowVideoPlayer, videoUrl, appendWorkflowLog);
  }
  renderSegments(segments, null);
}

async function loadProjectFiles(projectDir) {
  if (!projectDir || !elements.projectFileList) return;
  try {
    const response = await fetch(`${API_BASE}/project/files?project_dir=${encodeURIComponent(projectDir)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "项目文件读取失败。");
    elements.projectFileList.innerHTML = payload.files.map((file) => `
      <button class="project-file-item" data-full-path="${escapeHtml(file.full_path)}">${escapeHtml(file.path)}</button>
    `).join("");
    elements.projectFileContent.textContent = "请选择左侧项目文件。";
    elements.projectFileList.querySelectorAll(".project-file-item").forEach((button) => {
      button.addEventListener("click", () => loadProjectFile(button.dataset.fullPath));
    });
  } catch (error) {
    elements.projectFileContent.textContent = `项目文件读取失败：${error.message}`;
  }
}

async function loadProjectFile(path) {
  const response = await fetch(`${API_BASE}/project/file?path=${encodeURIComponent(path)}`);
  const payload = await response.json();
  if (!response.ok) {
    elements.projectFileContent.textContent = payload.detail || "文件读取失败。";
    return;
  }
  elements.projectFileContent.textContent = payload.binary ? `二进制文件：${payload.path}` : payload.content;
}

function loadVideo(player, url, logger) {
  if (!player) return;
  player.pause();
  player.removeAttribute("src");
  player.load();
  player.src = url;
  player.load();
  player.currentTime = 0;
  player.play().catch(() => {
    logger("视频已加载，请在播放器中点击播放。");
  });
}

function clearWorkflowResult() {
  elements.workflowVideoPlayer.pause();
  elements.workflowVideoPlayer.removeAttribute("src");
  elements.workflowVideoPlayer.load();
  elements.workflowProjectPath.textContent = "项目：生成中...";
  elements.workflowSummaryView.textContent = "";
  elements.workflowStoryboardView.textContent = "";
  elements.workflowCodeView.textContent = "";
}

function applyWorkflowResult(result) {
  if (!elements.workflowProjectPath) return;
  elements.workflowProjectPath.textContent = `项目：${result.project_dir}`;
  elements.workflowSummaryView.textContent = [
    `成功：${result.success}`,
    `视频：${result.video_path || "未生成"}`,
    `节点输出：${result.workflow_outputs_dir || "不可用"}`,
    `AI 记录：${result.ai_trace_dir || "不可用"}`,
    `渲染日志：${result.render_log_dir || "不可用"}`,
    result.failure_reason ? `失败原因：${result.failure_reason}` : "渲染成功。"
  ].join("\n");
  elements.workflowStoryboardView.textContent = JSON.stringify(result.storyboard || [], null, 2);
  elements.workflowCodeView.textContent = result.manim_code || "";
}

function setMode(mode) {
  const workflowMode = mode === "workflow";
  elements.quickView.classList.toggle("hidden", workflowMode);
  elements.workflowView.classList.toggle("hidden", !workflowMode);
  elements.quickModeTab.classList.toggle("active", !workflowMode);
  elements.workflowModeTab.classList.toggle("active", workflowMode);
  elements.generateBtn.style.display = workflowMode ? "none" : "inline-flex";
  if (workflowMode) renderWorkflow();
}

async function refreshProjectStatus(projectDir) {
  if (!projectDir) return;
  try {
    const response = await fetch(`${API_BASE}/project/status?project_dir=${encodeURIComponent(projectDir)}`);
    const payload = await response.json();
    if (!response.ok) return;
    applyPartialResult({
      ...(payload.summary || {}),
      project_dir: payload.project_dir,
      stages: payload.stages || [],
      segments: payload.segments || []
    });
  } catch (_error) {
    // Non-blocking: task polling still carries logs and final result.
  }
}

async function pollTask(taskId) {
  while (true) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`);
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "任务轮询失败。");

    renderTaskLogs(task.logs || []);
    if (task.partial_result) applyPartialResult(task.partial_result);
    await refreshProjectStatus(task.project_dir || task.partial_result?.project_dir || lastQuickResult?.project_dir);
    renderStages(currentStages, currentSegments, detectCurrentStage(task.logs || []));

    if (task.state === "succeeded") {
      applyResult(task.result);
      appendLog("完成。");
      return;
    }

    if (task.state === "failed") {
      throw new Error(task.error || "生成失败。");
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}
elements.imageInput.addEventListener("change", () => {
  const file = elements.imageInput.files[0];
  elements.imageName.textContent = file ? file.name : "选择图片";
});

elements.outputBtn.addEventListener("click", async () => {
  const dir = await window.desktopApi.selectOutputDir();
  if (dir) {
    selectedOutputDir = dir;
    elements.outputDir.textContent = dir;
    appendLog("已选择输出目录。");
  }
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-view").forEach((item) => item.classList.add("hidden"));
    button.classList.add("active");
    document.getElementById(`${button.dataset.tab}View`).classList.remove("hidden");
  });
});

elements.replayBtn.addEventListener("click", () => {
  elements.videoPlayer.currentTime = 0;
  elements.videoPlayer.play();
});

if (elements.sendSegmentAnnotationBtn) {
  elements.sendSegmentAnnotationBtn.addEventListener("click", async () => {
    try {
      elements.sendSegmentAnnotationBtn.disabled = true;
      await submitSegmentAnnotation();
    } catch (error) {
      elements.annotationStatus.textContent = `提交失败：${error.message}`;
    } finally {
      updateAnnotationSelection(null);
    }
  });
}

elements.pauseTaskBtn.addEventListener("click", async () => {
  if (!currentQuickTaskId) return;
  await fetch(`${API_BASE}/tasks/${currentQuickTaskId}/pause`, { method: "POST" });
  elements.pauseTaskBtn.disabled = true;
  elements.resumeTaskBtn.disabled = false;
  appendLog("已请求暂停。当前阶段结束后会暂停。");
});

elements.resumeTaskBtn.addEventListener("click", async () => {
  if (!currentQuickTaskId) return;
  await fetch(`${API_BASE}/tasks/${currentQuickTaskId}/resume`, { method: "POST" });
  elements.pauseTaskBtn.disabled = false;
  elements.resumeTaskBtn.disabled = true;
  appendLog("已继续生成。");
});

elements.workflowReplayBtn.addEventListener("click", () => {
  elements.workflowVideoPlayer.currentTime = 0;
  elements.workflowVideoPlayer.play();
});

document.querySelectorAll(".workflow-result-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".workflow-result-tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".workflow-result-view").forEach((item) => item.classList.add("hidden"));
    button.classList.add("active");
    document.getElementById(`workflow${button.dataset.workflowResultTab[0].toUpperCase()}${button.dataset.workflowResultTab.slice(1)}View`).classList.remove("hidden");
  });
});

elements.quickModeTab.addEventListener("click", () => setMode("quick"));
elements.workflowModeTab.addEventListener("click", () => setMode("workflow"));
if (elements.maxDurationMinutesInput) {
  elements.maxDurationMinutesInput.addEventListener("change", () => {
    const seconds = selectedTotalDurationSeconds();
    if (elements.durationInput) elements.durationInput.value = String(seconds);
    renderStages(currentStages, currentSegments, detectCurrentStage([]));
    renderAudioPreview(lastQuickResult || {});
  });
}
if (elements.durationInput) {
  elements.durationInput.addEventListener("change", () => {
    if (elements.maxDurationMinutesInput) {
      elements.maxDurationMinutesInput.value = String(Math.round(Number(elements.durationInput.value || 300) / 60));
    }
  });
}
if (elements.sceneCountModeInput) {
  elements.sceneCountModeInput.addEventListener("change", () => {
    if (elements.sceneCountInput) elements.sceneCountInput.disabled = elements.sceneCountModeInput.value !== "manual";
    renderAudioPreview(lastQuickResult || {});
  });
  if (elements.sceneCountInput) elements.sceneCountInput.disabled = elements.sceneCountModeInput.value !== "manual";
}
if (elements.sceneCountInput) {
  elements.sceneCountInput.addEventListener("change", () => renderAudioPreview(lastQuickResult || {}));
}
if (elements.promptPanelBtn) {
  elements.promptPanelBtn.addEventListener("click", () => {
    openPromptPanel().catch((error) => {
      appendLog(`提示词面板打开失败：${error.message}`);
    });
  });
}
if (elements.closePromptPanelBtn) {
  elements.closePromptPanelBtn.addEventListener("click", closePromptPanel);
}
if (elements.reloadPromptBtn) {
  elements.reloadPromptBtn.addEventListener("click", () => {
    loadPromptTemplates().catch((error) => {
      elements.promptPanelStatus.textContent = `读取失败：${error.message}`;
    });
  });
}
if (elements.savePromptBtn) {
  elements.savePromptBtn.addEventListener("click", () => {
    saveSelectedPromptTemplate().catch((error) => {
      elements.promptPanelStatus.textContent = `保存失败：${error.message}`;
    });
  });
}

elements.generateBtn.addEventListener("click", async () => {
  elements.generateBtn.disabled = true;
  elements.logOutput.textContent = "";
  elements.storyboardView.textContent = "";
  elements.codeView.textContent = "";
  elements.repairsView.textContent = "";
  elements.projectFileList.innerHTML = "";
  elements.projectFileContent.textContent = "";
  if (elements.audioStatus) {
    elements.audioStatus.textContent = "???????";
    elements.audioStatus.classList.remove("success", "warning");
  }
  if (elements.applyEditBtn) elements.applyEditBtn.disabled = true;
  if (elements.editStatus) elements.editStatus.textContent = "?????????????";
  const totalDurationSeconds = selectedTotalDurationSeconds();
  currentStages = buildDefaultStages(totalDurationSeconds);
  currentSegments = [];
  selectedSegmentId = "";
  updateAnnotationSelection(null);
  if (elements.segmentAnnotationInput) elements.segmentAnnotationInput.value = "";
  if (elements.annotationStatus) elements.annotationStatus.textContent = "不会阻止当前生成任务。";
  renderStages(currentStages, currentSegments, 1);
  elements.segmentPreviewList.innerHTML = '<div class="path-line">等待生成片段...</div>';
  renderAudioPreview({});
  elements.videoPlayer.pause();
  elements.videoPlayer.removeAttribute("src");
  elements.videoPlayer.load();
  elements.projectPath.textContent = "项目：生成中...";
  lastRenderedLogs = "";
  currentQuickTaskId = null;
  elements.pauseTaskBtn.disabled = true;
  elements.resumeTaskBtn.disabled = true;
  appendLog("正在提交生成任务。");

  try {
    const health = await fetch(`${API_BASE}/health`);
    if (!health.ok) throw new Error("本地后端未就绪。");

    const form = new FormData();
    const image = elements.imageInput.files[0];
    if (image) form.append("image", image);
    form.append("prompt", elements.promptInput.value);
    form.append("provider", elements.providerInput.value);
    form.append("quality", elements.qualityInput.value);
    form.append("total_duration_seconds", String(totalDurationSeconds));
    form.append("storyboard_scene_count", String(selectedStoryboardSceneCount()));
    form.append("compact_timing", elements.compactTimingInput?.checked ? "true" : "false");
    form.append("api_key", elements.apiKeyInput.value);
    form.append("base_url", elements.baseUrlInput.value);
    form.append("model", elements.modelInput.value);
    form.append("output_dir", selectedOutputDir);

    const response = await fetch(`${API_BASE}/generate_async`, { method: "POST", body: form });
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "任务提交失败。");

    elements.projectPath.textContent = `项目：${task.project_dir}`;
    currentQuickTaskId = task.task_id;
    elements.pauseTaskBtn.disabled = false;
    elements.resumeTaskBtn.disabled = true;
    appendLog(`任务已创建：${task.task_id}`);
    await pollTask(task.task_id);
  } catch (error) {
    appendLog(`错误：${error.message}`);
  } finally {
    elements.generateBtn.disabled = false;
    elements.pauseTaskBtn.disabled = true;
    elements.resumeTaskBtn.disabled = true;
  }
});


if (elements.applyEditBtn) {
  elements.applyEditBtn.addEventListener("click", async () => {
    if (!lastQuickResult?.project_dir) return;
    const editPrompt = elements.editPromptInput.value.trim();
    if (!editPrompt) {
      elements.editStatus.textContent = "请输入修改要求。";
      return;
    }
    elements.applyEditBtn.disabled = true;
    elements.generateBtn.disabled = true;
    const replacingSegment = Boolean(selectedSegmentId && selectedSegmentId !== "final");
    elements.editStatus.textContent = replacingSegment ? `正在替换片段 ${selectedSegmentId}...` : "正在整片重新生成...";
    editHistory.push(`${replacingSegment ? "替换片段" : "整片修改"} ${editHistory.length + 1}：${editPrompt}`);
    elements.editHistory.textContent = editHistory.join("\n");
    try {
      const form = new FormData();
      form.append("provider", elements.providerInput.value);
      form.append("quality", elements.qualityInput.value);
      form.append("api_key", elements.apiKeyInput.value);
      form.append("base_url", elements.baseUrlInput.value);
      form.append("model", elements.modelInput.value);
      form.append("edit_prompt", editPrompt);

      const endpoint = replacingSegment ? "replace_segment_async" : "regenerate_async";
      form.append("source_project_dir", lastQuickResult.project_dir);
      if (replacingSegment) {
        form.append("segment_id", selectedSegmentId);
      } else {
        form.append("total_duration_seconds", String(selectedTotalDurationSeconds()));
        form.append("storyboard_scene_count", String(selectedStoryboardSceneCount()));
        form.append("compact_timing", elements.compactTimingInput?.checked ? "true" : "false");
        form.append("output_dir", selectedOutputDir);
      }

      const response = await fetch(`${API_BASE}/${endpoint}`, { method: "POST", body: form });
      const task = await response.json();
      if (!response.ok) throw new Error(task.detail || "修改任务提交失败。");
      currentQuickTaskId = task.task_id;
      elements.projectPath.textContent = `项目：${task.project_dir}`;
      elements.editStatus.textContent = `修改任务已提交：${task.task_id}`;
      appendLog(`修改任务已提交：${task.task_id}`);
      await pollTask(task.task_id);
      elements.editPromptInput.value = "";
      selectedSegmentId = "";
    } catch (error) {
      elements.editStatus.textContent = `修改失败：${error.message}`;
      appendLog(`修改失败：${error.message}`);
    } finally {
      elements.generateBtn.disabled = false;
      elements.applyEditBtn.disabled = !lastQuickResult?.project_dir;
    }
  });
}
applyDefaultTestSettings();

async function initializeWorkflowEditor() {
  try {
    const definitionsResponse = await fetch(`${API_BASE}/workflow/node-definitions`);
    const definitionsPayload = await definitionsResponse.json();
    nodeDefinitions = Object.fromEntries(definitionsPayload.nodes.map((definition) => [definition.type, definition]));
    renderNodeLibrary(definitionsPayload.nodes);
    await loadWorkflowTemplate("math_function");
  } catch (error) {
    appendWorkflowLog(`初始化工作流编辑器失败：${error.message}`);
  }
}

function renderNodeLibrary(definitions) {
  const groups = {};
  definitions.forEach((definition) => {
    groups[definition.category] = groups[definition.category] || [];
    groups[definition.category].push(definition);
  });
  elements.nodeLibrary.innerHTML = Object.entries(groups).map(([category, items]) => `
    <div class="library-group">
      <div class="library-group-title">${categoryLabels[category] || category}</div>
      ${items.map((item) => `<button class="library-node" data-node-type="${item.type}">${labelForNode(item)}</button>`).join("")}
    </div>
  `).join("");
  elements.nodeLibrary.querySelectorAll(".library-node").forEach((button) => {
    button.addEventListener("click", () => addWorkflowNode(button.dataset.nodeType));
  });
}

async function loadWorkflowTemplate(templateId) {
  const response = await fetch(`${API_BASE}/workflow/templates/${templateId}`);
  const loaded = await response.json();
  if (!response.ok) throw new Error(loaded.detail || "Template load failed.");
  workflow = loaded;
  selectedNodeId = null;
  pendingConnection = null;
  appendWorkflowLog(`已加载模板：${workflow.workflow_name}`);
  renderWorkflow();
}

function addWorkflowNode(nodeType) {
  if (!workflow) return;
  const definition = nodeDefinitions[nodeType];
  const id = `${nodeType}_${Date.now().toString(36)}`;
  workflow.nodes.push({
    id,
    type: nodeType,
    label: labelForNode(definition),
    position: { x: 140 + workflow.nodes.length * 18, y: 120 + workflow.nodes.length * 18 },
    params: structuredClone(definition.default_params || {}),
    status: "idle"
  });
  selectedNodeId = id;
  renderWorkflow();
}

function renderWorkflow() {
  if (!workflow || !elements.workflowNodes) return;
  elements.workflowNodes.innerHTML = "";
  workflow.nodes.forEach((node) => {
    const definition = nodeDefinitions[node.type] || {};
    const viewport = getWorkflowViewport();
    const nodeEl = document.createElement("div");
    nodeEl.className = `workflow-node node-category-${definition.category || "comment"}${node.id === selectedNodeId ? " selected" : ""}`;
    nodeEl.style.left = "0";
    nodeEl.style.top = "0";
    nodeEl.style.transform = `translate(${viewport.x + node.position.x * viewport.zoom}px, ${viewport.y + node.position.y * viewport.zoom}px) scale(${viewport.zoom})`;
    nodeEl.style.transformOrigin = "top left";
    nodeEl.dataset.nodeId = node.id;
    nodeEl.innerHTML = `
      <div class="workflow-node-header">
        <span class="workflow-node-title">${node.label || labelForNode(definition)}</span>
        <span class="workflow-node-status">${node.status || "idle"}</span>
      </div>
      <div class="workflow-node-body">
        <div class="port-list">
          ${(definition.inputs || []).map((port) => renderPort(node.id, port, "input")).join("")}
        </div>
        <div class="port-list">
          ${(definition.outputs || []).map((port) => renderPort(node.id, port, "output")).join("")}
        </div>
      </div>
    `;
    elements.workflowNodes.appendChild(nodeEl);
    nodeEl.addEventListener("click", (event) => {
      if (event.target.closest(".port")) return;
      selectedNodeId = node.id;
      renderWorkflow();
    });
    nodeEl.querySelector(".workflow-node-header").addEventListener("pointerdown", (event) => startNodeDrag(event, node.id));
    nodeEl.querySelectorAll(".port").forEach((portEl) => {
      portEl.addEventListener("click", (event) => {
        event.stopPropagation();
        handlePortClick(portEl.dataset.nodeId, portEl.dataset.portName, portEl.dataset.portKind);
      });
    });
  });
  renderEdges();
  renderInspector();
}

function renderPort(nodeId, port, kind) {
  const pending = pendingConnection && pendingConnection.nodeId === nodeId && pendingConnection.portName === port.name;
  return `
    <div class="port ${pending ? "pending" : ""}" data-node-id="${nodeId}" data-port-name="${port.name}" data-port-kind="${kind}" title="${port.type}">
      ${kind === "input" ? '<span class="port-dot"></span>' : ""}
      <span>${port.name}</span>
      <span>(${port.type})</span>
      ${kind === "output" ? '<span class="port-dot"></span>' : ""}
    </div>
  `;
}

function renderEdges() {
  const rect = elements.workflowCanvas.getBoundingClientRect();
  elements.workflowEdges.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);
  elements.workflowEdges.innerHTML = "";
  if (!workflow) return;
  const viewport = getWorkflowViewport();
  workflow.edges.forEach((edge) => {
    const source = workflow.nodes.find((node) => node.id === edge.source);
    const target = workflow.nodes.find((node) => node.id === edge.target);
    if (!source || !target) return;
    const start = {
      x: viewport.x + (source.position.x + 220) * viewport.zoom,
      y: viewport.y + (source.position.y + 58) * viewport.zoom,
    };
    const end = {
      x: viewport.x + target.position.x * viewport.zoom,
      y: viewport.y + (target.position.y + 58) * viewport.zoom,
    };
    const mid = Math.max(40, Math.abs(end.x - start.x) / 2);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("class", "workflow-edge");
    path.setAttribute("d", `M ${start.x} ${start.y} C ${start.x + mid} ${start.y}, ${end.x - mid} ${end.y}, ${end.x} ${end.y}`);
    elements.workflowEdges.appendChild(path);
  });
}

function handlePortClick(nodeId, portName, kind) {
  if (kind === "output") {
    pendingConnection = { nodeId, portName };
    renderWorkflow();
    return;
  }
  if (!pendingConnection) return;
  const source = pendingConnection.nodeId;
  const sourceHandle = pendingConnection.portName;
  const id = `e_${source}_${sourceHandle}_${nodeId}_${portName}_${Date.now().toString(36)}`;
  workflow.edges.push({ id, source, sourceHandle, target: nodeId, targetHandle: portName });
  pendingConnection = null;
  appendWorkflowLog(`已连接 ${source}.${sourceHandle} -> ${nodeId}.${portName}`);
  renderWorkflow();
}

function startNodeDrag(event, nodeId) {
  event.preventDefault();
  event.stopPropagation();
  const node = workflow.nodes.find((item) => item.id === nodeId);
  dragState = {
    nodeId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: node.position.x,
    startY: node.position.y,
  };
  window.addEventListener("pointermove", moveNodeDrag);
  window.addEventListener("pointerup", stopNodeDrag, { once: true });
}

function moveNodeDrag(event) {
  if (!dragState) return;
  const node = workflow.nodes.find((item) => item.id === dragState.nodeId);
  const viewport = getWorkflowViewport();
  node.position.x = Math.max(0, dragState.startX + (event.clientX - dragState.startClientX) / viewport.zoom);
  node.position.y = Math.max(0, dragState.startY + (event.clientY - dragState.startClientY) / viewport.zoom);
  renderWorkflow();
}

function stopNodeDrag() {
  window.removeEventListener("pointermove", moveNodeDrag);
  dragState = null;
}

function renderInspector() {
  const node = workflow?.nodes.find((item) => item.id === selectedNodeId);
  if (!node) {
    elements.nodeInspector.innerHTML = '<div class="inspector-empty">请选择节点</div>';
    return;
  }
  const definition = nodeDefinitions[node.type];
  const params = node.params || {};
  elements.nodeInspector.innerHTML = `
    <div class="inspector-section">
      <h3>${labelForNode(definition)}</h3>
      <div class="path-line">${node.id}</div>
      <p>${definition.description}</p>
    </div>
    <div class="inspector-section">
      <h3>参数</h3>
      ${Object.entries({ ...(definition.default_params || {}), ...params }).map(([key, value]) => renderParamControl(key, value)).join("") || '<div class="path-line">无参数</div>'}
    </div>
    <div class="inspector-section">
      <h3>输入端口</h3>
      ${(definition.inputs || []).map((port) => `<div class="port-doc">${port.name}: ${port.type}${port.required ? " 必填" : ""}</div>`).join("") || '<div class="path-line">无输入端口</div>'}
    </div>
    <div class="inspector-section">
      <h3>输出端口</h3>
      ${(definition.outputs || []).map((port) => `<div class="port-doc">${port.name}: ${port.type}</div>`).join("") || '<div class="path-line">无输出端口</div>'}
    </div>
    <button id="deleteSelectedNodeBtn" class="secondary">删除节点</button>
  `;
  elements.nodeInspector.querySelectorAll("[data-param-key]").forEach((input) => {
    input.addEventListener("input", () => {
      const active = workflow.nodes.find((item) => item.id === selectedNodeId);
      active.params[input.dataset.paramKey] = input.value;
    });
  });
  elements.nodeInspector.querySelector("#deleteSelectedNodeBtn").addEventListener("click", deleteSelectedNode);
}

function renderParamControl(key, value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const control = text.length > 60
    ? `<textarea data-param-key="${key}">${escapeHtml(text)}</textarea>`
    : `<input data-param-key="${key}" value="${escapeHtml(text)}" />`;
  return `<label>${key}${control}</label>`;
}

function deleteSelectedNode() {
  if (!selectedNodeId || !workflow) return;
  workflow.nodes = workflow.nodes.filter((node) => node.id !== selectedNodeId);
  workflow.edges = workflow.edges.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId);
  selectedNodeId = null;
  renderWorkflow();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function validateWorkflow() {
  const response = await fetch(`${API_BASE}/workflow/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(workflow)
  });
  const result = await response.json();
  appendWorkflowLog(result.valid ? "工作流验证通过。" : "工作流验证失败。");
  (result.issues || []).forEach((issue) => appendWorkflowLog(`${issue.severity}: ${issue.message}`));
  if (result.execution_order?.length) appendWorkflowLog(`执行顺序：${result.execution_order.join(" -> ")}`);
  return result.valid;
}

async function runWorkflow() {
  elements.runWorkflowBtn.disabled = true;
  elements.workflowLog.textContent = "";
  clearWorkflowResult();
  try {
    const valid = await validateWorkflow();
    if (!valid) return;
    const url = new URL(`${API_BASE}/workflow/run_async`);
    url.searchParams.set("provider", elements.providerInput.value || "deepseek");
    url.searchParams.set("base_url", elements.baseUrlInput.value || "https://api.deepseek.com/v1");
    url.searchParams.set("model", elements.modelInput.value || "deepseek-v4-pro");
    url.searchParams.set("quality", elements.qualityInput.value || "low");
    url.searchParams.set("output_dir", selectedOutputDir);
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(workflow)
    });
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "工作流运行失败。");
    appendWorkflowLog(`任务已创建：${task.task_id}`);
    await pollWorkflowTask(task.task_id);
  } catch (error) {
    appendWorkflowLog(`错误：${error.message}`);
  } finally {
    elements.runWorkflowBtn.disabled = false;
  }
}

async function pollWorkflowTask(taskId) {
  let last = "";
  while (true) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`);
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "任务轮询失败。");
    const logs = (task.logs || []).join("\n");
    if (logs !== last) {
      last = logs;
      elements.workflowLog.textContent = logs + "\n";
      elements.workflowLog.scrollTop = elements.workflowLog.scrollHeight;
    }
    if (task.state === "succeeded") {
      applyResult(task.result);
      appendWorkflowLog("工作流运行完成。");
      return;
    }
    if (task.state === "failed") throw new Error(task.error || "工作流失败。");
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

function saveWorkflowJson() {
  const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${workflow.workflow_name || "workflow"}.json`.replaceAll(" ", "_");
  anchor.click();
  URL.revokeObjectURL(url);
}

elements.loadMathTemplateBtn.addEventListener("click", () => loadWorkflowTemplate("math_function"));
elements.loadImageTemplateBtn.addEventListener("click", () => loadWorkflowTemplate("image_problem"));
elements.loadMechanicsTemplateBtn.addEventListener("click", () => loadWorkflowTemplate("mechanics_beam"));
elements.validateWorkflowBtn.addEventListener("click", validateWorkflow);
elements.runWorkflowBtn.addEventListener("click", runWorkflow);
elements.saveWorkflowBtn.addEventListener("click", saveWorkflowJson);
elements.fitWorkflowBtn.addEventListener("click", () => {
  if (!workflow) return;
  workflow.viewport = { x: 20, y: 20, zoom: 0.85 };
  workflow.nodes.forEach((node, index) => {
    node.position.x = 80 + (index % 5) * 260;
    node.position.y = 80 + Math.floor(index / 5) * 170;
  });
  renderWorkflow();
});
elements.loadWorkflowInput.addEventListener("change", async () => {
  const file = elements.loadWorkflowInput.files[0];
  if (!file) return;
  workflow = JSON.parse(await file.text());
  selectedNodeId = null;
  appendWorkflowLog(`已加载工作流文件：${file.name}`);
  renderWorkflow();
});

initializeWorkflowEditor();

elements.workflowCanvas.addEventListener("pointerdown", (event) => {
  if (event.target.closest(".workflow-node")) return;
  const viewport = getWorkflowViewport();
  panState = {
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: viewport.x,
    startY: viewport.y,
  };
  elements.workflowCanvas.classList.add("panning");
  window.addEventListener("pointermove", moveCanvasPan);
  window.addEventListener("pointerup", stopCanvasPan, { once: true });
});

function moveCanvasPan(event) {
  if (!panState || !workflow) return;
  const viewport = getWorkflowViewport();
  viewport.x = panState.startX + event.clientX - panState.startClientX;
  viewport.y = panState.startY + event.clientY - panState.startClientY;
  renderWorkflow();
}

function stopCanvasPan() {
  window.removeEventListener("pointermove", moveCanvasPan);
  elements.workflowCanvas.classList.remove("panning");
  panState = null;
}

elements.workflowCanvas.addEventListener("wheel", (event) => {
  if (!workflow) return;
  event.preventDefault();
  const rect = elements.workflowCanvas.getBoundingClientRect();
  const viewport = getWorkflowViewport();
  const oldZoom = viewport.zoom;
  const factor = event.deltaY < 0 ? 1.1 : 0.9;
  const newZoom = Math.min(1.8, Math.max(0.35, oldZoom * factor));
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const worldX = (mouseX - viewport.x) / oldZoom;
  const worldY = (mouseY - viewport.y) / oldZoom;
  viewport.zoom = newZoom;
  viewport.x = mouseX - worldX * newZoom;
  viewport.y = mouseY - worldY * newZoom;
  renderWorkflow();
}, { passive: false });






