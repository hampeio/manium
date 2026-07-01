const API_BASE = window.desktopApi?.apiBase || "http://127.0.0.1:8765";

const elements = {
  imageInput: document.getElementById("imageInput"),
  imageName: document.getElementById("imageName"),
  promptInput: document.getElementById("promptInput"),
  providerInput: document.getElementById("providerInput"),
  settingsBtn: document.getElementById("settingsBtn"),
  settingsModal: document.getElementById("settingsModal"),
  closeSettingsBtn: document.getElementById("closeSettingsBtn"),
  imageUploadBox: document.getElementById("imageUploadBox"),
  visionCapabilityHint: document.getElementById("visionCapabilityHint"),
  modelCapabilitySummary: document.getElementById("modelCapabilitySummary"),
  modelProfileList: document.getElementById("modelProfileList"),
  modelProfileName: document.getElementById("modelProfileName"),
  modelProviderName: document.getElementById("modelProviderName"),
  modelBaseUrl: document.getElementById("modelBaseUrl"),
  modelApiKey: document.getElementById("modelApiKey"),
  modelNameSetting: document.getElementById("modelNameSetting"),
  modelMaxTokens: document.getElementById("modelMaxTokens"),
  modelTemperature: document.getElementById("modelTemperature"),
  modelTopP: document.getElementById("modelTopP"),
  newModelProfileBtn: document.getElementById("newModelProfileBtn"),
  saveModelProfileBtn: document.getElementById("saveModelProfileBtn"),
  deleteModelProfileBtn: document.getElementById("deleteModelProfileBtn"),
  defaultModelProfileBtn: document.getElementById("defaultModelProfileBtn"),
  probeModelProfileBtn: document.getElementById("probeModelProfileBtn"),
  modelSettingsStatus: document.getElementById("modelSettingsStatus"),
  audioProfileList: document.getElementById("audioProfileList"),
  audioProfileName: document.getElementById("audioProfileName"),
  audioProviderName: document.getElementById("audioProviderName"),
  audioBaseUrl: document.getElementById("audioBaseUrl"),
  audioApiKey: document.getElementById("audioApiKey"),
  audioModelName: document.getElementById("audioModelName"),
  audioResponseMode: document.getElementById("audioResponseMode"),
  audioTextField: document.getElementById("audioTextField"),
  audioModelField: document.getElementById("audioModelField"),
  audioHeaders: document.getElementById("audioHeaders"),
  audioParameters: document.getElementById("audioParameters"),
  audioResponseField: document.getElementById("audioResponseField"),
  newAudioProfileBtn: document.getElementById("newAudioProfileBtn"),
  saveAudioProfileBtn: document.getElementById("saveAudioProfileBtn"),
  deleteAudioProfileBtn: document.getElementById("deleteAudioProfileBtn"),
  defaultAudioProfileBtn: document.getElementById("defaultAudioProfileBtn"),
  testAudioProfileBtn: document.getElementById("testAudioProfileBtn"),
  audioSettingsStatus: document.getElementById("audioSettingsStatus"),
  exportConfigsBtn: document.getElementById("exportConfigsBtn"),
  exportSecretsInput: document.getElementById("exportSecretsInput"),
  importConfigsInput: document.getElementById("importConfigsInput"),
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
  originalSegmentPreviewBtn: document.getElementById("originalSegmentPreviewBtn"),
  correctedSegmentPreviewBtn: document.getElementById("correctedSegmentPreviewBtn"),
  overallPreviewBtn: document.getElementById("overallPreviewBtn"),
  composeOverallBtn: document.getElementById("composeOverallBtn"),
  composeStatus: document.getElementById("composeStatus"),
  pauseTaskBtn: document.getElementById("pauseTaskBtn"),
  resumeTaskBtn: document.getElementById("resumeTaskBtn"),
  rootFolderBtn: document.getElementById("rootFolderBtn"),
  rootFolderPanel: document.getElementById("rootFolderPanel"),
  rootFolderPath: document.getElementById("rootFolderPath"),
  rootVideoList: document.getElementById("rootVideoList"),
  stagePreviewList: document.getElementById("stagePreviewList"),
  segmentPreviewList: document.getElementById("segmentPreviewList"),
  audioPreviewList: document.getElementById("audioPreviewList"),
  audioStatus: document.getElementById("audioStatus"),
  projectPath: document.getElementById("projectPath"),
  projectFileList: document.getElementById("projectFileList"),
  projectFileContent: document.getElementById("projectFileContent"),
  projectRootBtn: document.getElementById("projectRootBtn"),
  changeProjectRootBtn: document.getElementById("changeProjectRootBtn"),
  projectRootPath: document.getElementById("projectRootPath"),
  quickModeTab: document.getElementById("quickModeTab"),
  workflowModeTab: document.getElementById("workflowModeTab"),
  styleModeTab: document.getElementById("styleModeTab"),
  quickView: document.getElementById("quickView"),
  workflowView: document.getElementById("workflowView"),
  styleView: document.getElementById("styleView"),
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
  stylePresetSelect: document.getElementById("stylePresetSelect"),
  styleLibraryList: document.getElementById("styleLibraryList"),
  styleNameInput: document.getElementById("styleNameInput"),
  styleDescriptionInput: document.getElementById("styleDescriptionInput"),
  stylePromptInput: document.getElementById("stylePromptInput"),
  styleSceneCountInput: document.getElementById("styleSceneCountInput"),
  styleSpeedInput: document.getElementById("styleSpeedInput"),
  styleVersionSelect: document.getElementById("styleVersionSelect"),
  styleAnalysisView: document.getElementById("styleAnalysisView"),
  styleProjectInput: document.getElementById("styleProjectInput"),
  styleImportInput: document.getElementById("styleImportInput"),
  saveStylePresetBtn: document.getElementById("saveStylePresetBtn"),
  applyStylePresetBtn: document.getElementById("applyStylePresetBtn"),
  exportStylePresetBtn: document.getElementById("exportStylePresetBtn"),
  rollbackStylePresetBtn: document.getElementById("rollbackStylePresetBtn"),
  styleLibraryStatus: document.getElementById("styleLibraryStatus"),
  annotationSegmentLabel: document.getElementById("annotationSegmentLabel"),
  segmentAnnotationInput: document.getElementById("segmentAnnotationInput"),
  sendSegmentAnnotationBtn: document.getElementById("sendSegmentAnnotationBtn"),
  annotationStatus: document.getElementById("annotationStatus"),
  taskProgressPanel: document.getElementById("taskProgressPanel"),
  taskStateLabel: document.getElementById("taskStateLabel"),
  taskProgressText: document.getElementById("taskProgressText"),
  taskProgressBar: document.getElementById("taskProgressBar"),
  taskCurrentStep: document.getElementById("taskCurrentStep"),
  taskRemainingSteps: document.getElementById("taskRemainingSteps"),
  workflowTaskStateLabel: document.getElementById("workflowTaskStateLabel"),
  workflowTaskProgressText: document.getElementById("workflowTaskProgressText"),
  workflowTaskProgressBar: document.getElementById("workflowTaskProgressBar"),
  workflowTaskCurrentStep: document.getElementById("workflowTaskCurrentStep"),
  customNodeInput: document.getElementById("customNodeInput"),
  workflowTutorialBtn: document.getElementById("workflowTutorialBtn"),
  segmentCodeLabel: document.getElementById("segmentCodeLabel"),
  segmentCodeInput: document.getElementById("segmentCodeInput"),
  copySegmentCodeBtn: document.getElementById("copySegmentCodeBtn"),
  uploadSegmentCodeInput: document.getElementById("uploadSegmentCodeInput"),
  renderSegmentCodeBtn: document.getElementById("renderSegmentCodeBtn"),
  segmentTimingPolicy: document.getElementById("segmentTimingPolicy"),
  segmentManualDuration: document.getElementById("segmentManualDuration"),
  segmentSyncStatus: document.getElementById("segmentSyncStatus"),
  segmentCodeHistory: document.getElementById("segmentCodeHistory"),
  restoreSegmentCodeBtn: document.getElementById("restoreSegmentCodeBtn"),
  segmentCodeStatus: document.getElementById("segmentCodeStatus")
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
let currentRootDir = "";
let currentProjectDir = "";
let currentSegmentCodeInfo = null;
let modelProfiles = [];
let defaultModelProfileId = "";
let editingModelProfileId = "";
let audioProfiles = [];
let defaultAudioProfileId = "";
let editingAudioProfileId = "";
let styleLibrary = [];
let selectedStyleId = "";

const categoryLabels = {
  input: "输入",
  image: "图像",
  ai: "AI",
  planning: "规划",
  code: "代码",
  render: "渲染",
  output: "输出",
  comment: "注释",
  reference: "参考素材",
  control: "控制",
  logic: "逻辑",
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
  VideoInputNode: "视频上传",
  StyleReferenceNode: "风格参考",
  CharacterReferenceNode: "角色参考",
  SceneReferenceNode: "场景参考",
  CameraMotionNode: "镜头运动",
  DurationControlNode: "时长控制",
  ResolutionNode: "分辨率设置",
  ConditionNode: "条件判断",
  BranchNode: "多分支",
  MergeNode: "合并",
};

const promptNameLabels = {
  SYSTEM_PROMPT: "系统提示词",
  PLAN_AND_CODE_PROMPT: "规划与代码提示词",
  GENERATION_STRATEGY_PROMPT: "生成策略提示词",
  STORYBOARD_BATCH_PROMPT: "分镜批次提示词",
  CODE_FROM_PLAN_PROMPT: "完整代码生成提示词",
  SEGMENT_CODE_PROMPT: "片段代码生成提示词",
  REPAIR_PROMPT: "自动修复提示词"
};

const statusLabels = {
  idle: "等待",
  planned: "已规划",
  queued: "排队中",
  running: "进行中",
  rendered: "已渲染",
  replaced: "已替换",
  success: "成功",
  succeeded: "成功",
  completed: "已完成",
  failed: "失败",
  skipped: "已跳过",
  stopped: "已停止",
  paused: "已暂停",
  stalled: "已卡住",
  interrupted: "后台已中断",
  waiting_input: "等待输入",
  stitched: "已拼接",
  awaiting_compose: "等待手动合成",
  pending: "等待中"
};

function statusLabel(status) {
  return statusLabels[status] || status || "未知状态";
}

async function loadStyleLibrary(preferredId = "") {
  const response = await fetch(`${API_BASE}/style-library`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "风格库读取失败。");
  styleLibrary = payload.styles || [];
  selectedStyleId = preferredId || selectedStyleId;
  if (selectedStyleId && !styleLibrary.some((item) => item.id === selectedStyleId)) selectedStyleId = "";
  elements.stylePresetSelect.innerHTML = '<option value="">不使用风格预设</option>' + styleLibrary.map((item) =>
    `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · v${item.active_version}</option>`
  ).join("");
  elements.stylePresetSelect.value = selectedStyleId;
  elements.styleLibraryList.innerHTML = styleLibrary.map((item) =>
    `<button class="prompt-name-item ${item.id === selectedStyleId ? "active" : ""}" data-style-id="${escapeHtml(item.id)}">${escapeHtml(item.name)} · v${item.active_version}</button>`
  ).join("") || '<div class="path-line">风格库为空。</div>';
  elements.styleLibraryList.querySelectorAll("[data-style-id]").forEach((button) => {
    button.addEventListener("click", () => selectStyle(button.dataset.styleId));
  });
  if (selectedStyleId) selectStyle(selectedStyleId);
}

function selectStyle(styleId) {
  selectedStyleId = styleId;
  const style = styleLibrary.find((item) => item.id === styleId);
  if (!style) return;
  const preset = style.preset || {};
  elements.styleNameInput.value = style.name || "";
  elements.styleDescriptionInput.value = preset.style_description || style.description || "";
  elements.stylePromptInput.value = preset.prompt_preset || "";
  elements.styleSceneCountInput.value = preset.scene_count || 1;
  elements.styleSpeedInput.value = preset.animation_speed || "";
  elements.styleAnalysisView.textContent = JSON.stringify({ analysis: style.analysis, example_code: preset.example_code || "" }, null, 2);
  elements.styleVersionSelect.innerHTML = (style.versions || []).map((item) =>
    `<option value="${item.version}" ${item.version === style.active_version ? "selected" : ""}>版本 ${item.version} · ${escapeHtml(item.created_at || "")}</option>`
  ).join("");
  elements.stylePresetSelect.value = styleId;
  elements.styleLibraryList.querySelectorAll("[data-style-id]").forEach((button) => button.classList.toggle("active", button.dataset.styleId === styleId));
}

function applySelectedStyle() {
  const style = styleLibrary.find((item) => item.id === (elements.stylePresetSelect.value || selectedStyleId));
  if (!style) return;
  selectedStyleId = style.id;
  if (elements.sceneCountModeInput && elements.sceneCountInput) {
    elements.sceneCountModeInput.value = "manual";
    elements.sceneCountInput.disabled = false;
    elements.sceneCountInput.value = String(style.preset?.scene_count || elements.sceneCountInput.value);
  }
  elements.styleLibraryStatus.textContent = `已选择“${style.name}”，生成时会自动注入风格预设。`;
}

async function learnStyleFromFiles(files) {
  if (!files.length) return;
  const form = new FormData();
  [...files].forEach((file) => form.append("files", file));
  form.append("style_name", elements.styleNameInput.value.trim() || "自动学习风格");
  form.append("description", elements.styleDescriptionInput.value.trim());
  form.append("existing_style_id", selectedStyleId);
  form.append("model_profile_id", elements.providerInput.value || "");
  form.append("use_ai", "true");
  elements.styleLibraryStatus.textContent = "正在提取工程证据，并调用当前模型 API 学习风格...";
  const response = await fetch(`${API_BASE}/style-library/analyze`, { method: "POST", body: form });
  const style = await response.json();
  if (!response.ok) throw new Error(style.detail || "工程分析失败。");
  await loadStyleLibrary(style.id);
  const modelStatus = style.analysis?.model_analysis?.status;
  elements.styleLibraryStatus.textContent = modelStatus === "success"
    ? `AI 学习完成：${style.name} v${style.active_version} · ${style.analysis.model_analysis.model}`
    : `模型调用失败，已保留本地分析结果：${style.analysis?.model_analysis?.message || "未知错误"}`;
}

async function saveStylePreset() {
  if (!selectedStyleId) throw new Error("请先学习或选择一个风格。");
  const payload = {
    name: elements.styleNameInput.value.trim(),
    style_description: elements.styleDescriptionInput.value.trim(),
    prompt_preset: elements.stylePromptInput.value,
    scene_count: Number(elements.styleSceneCountInput.value || 1),
    animation_speed: elements.styleSpeedInput.value.trim(),
  };
  const response = await fetch(`${API_BASE}/style-library/${selectedStyleId}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  const style = await response.json();
  if (!response.ok) throw new Error(style.detail || "保存失败。");
  await loadStyleLibrary(style.id);
  elements.styleLibraryStatus.textContent = `已保存为版本 ${style.active_version}。`;
}

function updateTaskProgress(task, workflowMode = false) {
  const prefix = workflowMode ? "workflowTask" : "task";
  const stateLabel = elements[`${prefix}StateLabel`];
  const progressText = elements[`${prefix}ProgressText`];
  const progressBar = elements[`${prefix}ProgressBar`];
  const currentStep = elements[`${prefix}CurrentStep`];
  const percent = Math.max(0, Math.min(100, Number(task?.progress_percent || 0)));
  if (stateLabel) stateLabel.textContent = `当前状态：${statusLabel(task?.state || "queued")}`;
  if (progressText) progressText.textContent = `${percent}%`;
  if (progressBar) progressBar.value = percent;
  if (currentStep) currentStep.textContent = task?.error ? `${task.current_step || "失败"}：${task.error}` : (task?.current_step || "等待后台更新");
  if (!workflowMode && elements.taskRemainingSteps) {
    const remaining = task?.remaining_steps || [];
    elements.taskRemainingSteps.textContent = remaining.length ? `剩余阶段：${remaining.join("、")}` : "全部阶段已完成。";
  }
  elements.taskProgressPanel?.classList.toggle("is-failed", ["failed", "stalled", "interrupted"].includes(task?.state));
}

function applyDefaultTestSettings() {
  if (!elements.promptInput.value.trim()) {
    elements.promptInput.value = "介绍铁路路基道床的组成、功能、荷载传递、排水、弹性缓冲和施工整形过程。";
  }
  elements.qualityInput.value = "low";
}

function currentModelProfile() {
  return modelProfiles.find((profile) => profile.id === elements.providerInput.value) || null;
}

function hasModelCapability(name) {
  return Boolean(currentModelProfile()?.capabilities?.[name]);
}

function applyActiveModelProfile() {
  const profile = currentModelProfile();
  if (!profile) return;
  elements.baseUrlInput.value = profile.api_base_url || "";
  elements.modelInput.value = profile.model_name || "";
  elements.apiKeyInput.value = "";
  elements.apiKeyInput.placeholder = profile.api_key_configured ? "已配置（在设置中修改）" : "未配置";
  const capabilities = profile.capabilities || {};
  const visionReady = Boolean(capabilities.vision && capabilities.image_upload && capabilities.multimodal_input);
  elements.imageInput.disabled = !visionReady;
  elements.imageUploadBox?.classList.toggle("capability-disabled", !visionReady);
  elements.visionCapabilityHint.textContent = visionReady
    ? "当前模型支持 Vision：可上传、分析并批注图片。"
    : "当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。";
  const labels = {
    text_generation: "文本", vision: "Vision", image_upload: "图片上传", multimodal_input: "多模态",
    image_annotation: "图片批注", function_calling: "Function Calling", json_output: "JSON",
    streaming: "Streaming", audio: "音频",
  };
  elements.modelCapabilitySummary.innerHTML = Object.entries(labels).map(([key, label]) =>
    `<span class="capability-badge ${capabilities[key] ? "enabled" : ""}">${label}</span>`
  ).join("");
  window.currentModelProfileId = profile.id;
  window.currentModelCapabilities = capabilities;
  window.annotationEditor?.setCapabilities(capabilities, profile.id);
  if (Object.keys(nodeDefinitions).length) renderNodeLibrary(Object.values(nodeDefinitions));
  if (!visionReady && elements.imageInput.files?.length) {
    elements.imageInput.value = "";
    elements.imageName.textContent = "选择图片";
    window.annotationEditor?.setImagePreview(null);
  }
}

async function loadModelProfiles(preferredId = "") {
  const response = await fetch(`${API_BASE}/model-configs`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "模型配置读取失败。");
  modelProfiles = payload.profiles || [];
  defaultModelProfileId = payload.default_id || modelProfiles[0]?.id || "";
  elements.providerInput.innerHTML = modelProfiles.map((profile) =>
    `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.name)} · ${escapeHtml(profile.model_name)}</option>`
  ).join("");
  elements.providerInput.value = preferredId && modelProfiles.some((item) => item.id === preferredId)
    ? preferredId : defaultModelProfileId;
  applyActiveModelProfile();
  renderModelProfileList();
}

function renderModelProfileList() {
  if (!elements.modelProfileList) return;
  elements.modelProfileList.innerHTML = modelProfiles.map((profile) =>
    `<option value="${escapeHtml(profile.id)}">${profile.id === defaultModelProfileId ? "★ " : ""}${escapeHtml(profile.name)} · ${escapeHtml(profile.model_name)}</option>`
  ).join("");
  if (editingModelProfileId) elements.modelProfileList.value = editingModelProfileId;
}

function editModelProfile(profileId) {
  editingModelProfileId = profileId || "";
  const profile = modelProfiles.find((item) => item.id === profileId);
  elements.modelProfileName.value = profile?.name || "";
  elements.modelProviderName.value = profile?.provider_name || "openai-compatible";
  elements.modelBaseUrl.value = profile?.api_base_url || "";
  elements.modelApiKey.value = "";
  elements.modelApiKey.placeholder = profile?.api_key_configured ? "已配置；留空保留" : "输入 API Key";
  elements.modelNameSetting.value = profile?.model_name || "";
  elements.modelMaxTokens.value = profile?.parameters?.max_tokens || 8192;
  elements.modelTemperature.value = profile?.parameters?.temperature ?? 0.25;
  elements.modelTopP.value = profile?.parameters?.top_p ?? 1;
  document.querySelectorAll("[data-model-capability]").forEach((input) => {
    input.checked = Boolean(profile?.capabilities?.[input.dataset.modelCapability]);
  });
  elements.modelSettingsStatus.textContent = profile
    ? `能力来源：${profile.capability_source || "manual"}；${profile.probe?.message || "尚未探测。"}`
    : "正在创建新模型配置。";
  renderModelProfileList();
}

function modelProfilePayload() {
  const capabilities = {};
  document.querySelectorAll("[data-model-capability]").forEach((input) => {
    capabilities[input.dataset.modelCapability] = input.checked;
  });
  return {
    id: editingModelProfileId || undefined,
    name: elements.modelProfileName.value.trim(),
    provider_name: elements.modelProviderName.value.trim() || "openai-compatible",
    api_base_url: elements.modelBaseUrl.value.trim(),
    api_key: elements.modelApiKey.value,
    model_name: elements.modelNameSetting.value.trim(),
    capabilities,
    capability_source: "manual",
    parameters: {
      max_tokens: Number(elements.modelMaxTokens.value || 8192),
      temperature: Number(elements.modelTemperature.value || 0.25),
      top_p: Number(elements.modelTopP.value || 1),
    },
  };
}

async function saveModelProfile() {
  elements.modelSettingsStatus.textContent = "正在保存模型配置...";
  const response = await fetch(`${API_BASE}/model-configs`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(modelProfilePayload()),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "模型配置保存失败。");
  editingModelProfileId = payload.profile.id;
  await loadModelProfiles(elements.providerInput.value || payload.profile.id);
  editModelProfile(editingModelProfileId);
  elements.modelSettingsStatus.textContent = "模型配置已保存。";
}

async function loadAudioProfiles(preferredId = "") {
  const response = await fetch(`${API_BASE}/audio-configs`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "音频配置读取失败。");
  audioProfiles = payload.profiles || [];
  defaultAudioProfileId = payload.default_id || "";
  editingAudioProfileId = preferredId && audioProfiles.some((item) => item.id === preferredId) ? preferredId : (editingAudioProfileId || defaultAudioProfileId);
  elements.audioProfileList.innerHTML = audioProfiles.map((profile) =>
    `<option value="${escapeHtml(profile.id)}">${profile.id === defaultAudioProfileId ? "★ " : ""}${escapeHtml(profile.name)} · ${escapeHtml(profile.model_name || profile.provider_name)}</option>`
  ).join("");
  if (editingAudioProfileId) elements.audioProfileList.value = editingAudioProfileId;
  const active = audioProfiles.find((item) => item.id === defaultAudioProfileId);
  if (elements.audioStatus) elements.audioStatus.textContent = active
    ? `配音 API：${active.provider_name} / ${active.model_name || "未指定模型"} · 最近状态 ${active.last_call_status}`
    : "配音 API：未配置，将生成无旁白视频";
}

function editAudioProfile(profileId) {
  editingAudioProfileId = profileId || "";
  const profile = audioProfiles.find((item) => item.id === profileId);
  elements.audioProfileName.value = profile?.name || "";
  elements.audioProviderName.value = profile?.provider_name || "";
  elements.audioBaseUrl.value = profile?.api_base_url || "";
  elements.audioApiKey.value = "";
  elements.audioApiKey.placeholder = profile?.api_key_configured ? "已配置；留空保留" : "输入 API Key";
  elements.audioModelName.value = profile?.model_name || "";
  elements.audioResponseMode.value = profile?.response_mode || "binary";
  elements.audioTextField.value = profile?.text_field || "text";
  elements.audioModelField.value = profile?.model_field || "model";
  elements.audioHeaders.value = JSON.stringify(profile?.request_headers || {}, null, 2);
  elements.audioParameters.value = JSON.stringify(profile?.request_parameters || {}, null, 2);
  elements.audioResponseField.value = profile?.response_audio_field || "audio";
  elements.audioSettingsStatus.textContent = profile
    ? `是否已配置：是；Provider：${profile.provider_name}；模型：${profile.model_name || "未指定"}；连通性：${profile.probe?.status || "never"}；最近调用：${profile.last_call_status} ${profile.last_call_message || ""}`
    : "正在创建新音频配置；未保存时系统会自动跳过旁白。";
}

function parseJsonInput(value, label) {
  try { return JSON.parse(value || "{}"); }
  catch (error) { throw new Error(`${label}不是有效 JSON：${error.message}`); }
}

async function saveAudioProfile() {
  const payload = {
    id: editingAudioProfileId || undefined,
    name: elements.audioProfileName.value.trim(), provider_name: elements.audioProviderName.value.trim(),
    api_base_url: elements.audioBaseUrl.value.trim(), api_key: elements.audioApiKey.value,
    model_name: elements.audioModelName.value.trim(), response_mode: elements.audioResponseMode.value,
    text_field: elements.audioTextField.value.trim() || "text", model_field: elements.audioModelField.value.trim() || "model",
    request_headers: parseJsonInput(elements.audioHeaders.value, "请求 Header"),
    request_parameters: parseJsonInput(elements.audioParameters.value, "请求参数"),
    response_audio_field: elements.audioResponseField.value.trim() || "audio", enabled: true,
  };
  const response = await fetch(`${API_BASE}/audio-configs`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "音频配置保存失败。");
  editingAudioProfileId = result.profile.id;
  await loadAudioProfiles(editingAudioProfileId);
  editAudioProfile(editingAudioProfileId);
  elements.audioSettingsStatus.textContent = "音频配置已保存。";
}

async function initializeConfigurations() {
  try {
    await Promise.all([loadModelProfiles(), loadAudioProfiles()]);
  } catch (error) {
    appendLog(`配置初始化失败：${error.message}`);
    elements.visionCapabilityHint.textContent = "模型能力读取失败，图片功能已停用。";
    elements.imageInput.disabled = true;
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
    <button class="prompt-name-item ${name === selectedPromptName ? "active" : ""}" data-prompt-name="${escapeHtml(name)}">${escapeHtml(promptNameLabels[name] || name)}</button>
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
  currentProjectDir = result.project_dir || currentProjectDir;
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
  window.annotationEditor?.setProject(currentProjectDir, currentSegments);
  updateCompositionControls(result);
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
  currentProjectDir = partial.project_dir || currentProjectDir;
  if (partial.project_dir) elements.projectPath.textContent = `项目：${partial.project_dir}`;
  if (partial.storyboard) elements.storyboardView.textContent = JSON.stringify(partial.storyboard, null, 2);
  currentStages = partial.stages || currentStages;
  currentSegments = partial.segments || currentSegments;
  window.annotationEditor?.setProject(currentProjectDir, currentSegments);
  updateCompositionControls(lastQuickResult || partial);
  renderStages(currentStages, currentSegments, detectCurrentStage([]));
  renderSegments(currentSegments, partial.video_path || null);
  renderAudioPreview(partial);
  autoLoadFirstSegmentVideo(currentSegments);
}
function renderAudioStatus(result) {
  if (!elements.audioStatus) return;
  const status = result.tts_status || (result.tts_enabled ? "unknown" : "disabled");
  const audioPath = result.audio_path ? ` 路径：${result.audio_path}` : "";
  elements.audioStatus.classList.remove("success", "warning");
  if (status === "embedded") {
    elements.audioStatus.textContent = `配音已嵌入视频。${audioPath}`;
    elements.audioStatus.classList.add("success");
  } else if (status === "not_embedded" || status === "audio_only") {
    elements.audioStatus.textContent = `配音已生成，但未嵌入视频。${audioPath}`;
    elements.audioStatus.classList.add("warning");
  } else if (status === "failed") {
    elements.audioStatus.textContent = `配音生成失败：${result.tts_error || "未知错误"}`;
    elements.audioStatus.classList.add("warning");
  } else {
    elements.audioStatus.textContent = "配音：尚未生成";
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
        <span>${escapeHtml(statusLabel(stage.status || "planned"))} · ${stage.estimated_seconds || ""} 秒 · ${sceneCount} 个分镜${stitching}</span>
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
      <button class="compose-chip ${finalVideoPath ? "ready" : ""}" data-video-path="${escapeHtml(finalVideoPath)}">总体<br>预览</button>
      <div class="path-line">暂无片段。等待分镜规划或片段渲染完成。</div>
    `;
    bindComposeVideoButton();
    return;
  }
  elements.segmentPreviewList.innerHTML = `
    <button class="compose-chip ${finalVideoPath ? "ready" : ""} ${selectedSegmentId === "final" ? "active" : ""}" data-video-path="${escapeHtml(finalVideoPath)}">
      总体<br>预览
    </button>
    <div class="segment-timeline">
      ${segments.map((segment, index) => `
        <button class="segment-chip ${segment.id === selectedSegmentId ? "active" : ""} ${escapeHtml(segment.status || "planned")}" data-video-path="${escapeHtml(segment.preview_video_path || segment.video_path || "")}" data-original-video-path="${escapeHtml(segment.original_preview_path || segment.original_video_path || segment.video_path || "")}" data-corrected-video-path="${escapeHtml(segment.corrected_preview_path || segment.corrected_video_path || "")}" data-segment-id="${escapeHtml(segment.id || "")}" data-segment-index="${index}">
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
      const selectedSegment = currentSegments.find((segment) => segment.id === selectedSegmentId);
      updateSegmentPreviewControls(selectedSegment);
      loadSelectedSegmentCode(selectedSegmentId);
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
    clearSegmentCodeEditor("总体视频没有独立的单段 Manim 代码，请选择一个分镜。");
    updateSegmentPreviewControls(null);
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
  window.annotationEditor?.setSelectedSegment(segmentId);
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
  const savedAnnotation = await window.annotationEditor?.ensureSegmentAnnotation(note);
  const isImageAnnotation = savedAnnotation?.shape_data?.target_kind === "image";
  if (isImageAnnotation && !(hasModelCapability("vision") && hasModelCapability("image_upload") && hasModelCapability("multimodal_input") && hasModelCapability("image_annotation"))) {
    elements.annotationStatus.textContent = "当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。";
    return;
  }
  const form = new FormData();
  form.append("source_project_dir", lastQuickResult.project_dir);
  form.append("segment_id", targetSegmentId);
  form.append("model_profile_id", elements.providerInput.value);
  form.append("api_key", elements.apiKeyInput.value);
  form.append("base_url", elements.baseUrlInput.value);
  form.append("model", elements.modelInput.value);
  form.append("quality", elements.qualityInput.value);
  form.append("use_project_image", isImageAnnotation ? "true" : "false");
  form.append("edit_prompt", `用户对当前视频片段的标注与修改要求：${note}\n结构化批注：${JSON.stringify(savedAnnotation || {})}\n请只重做这个片段，保留整体教学目标，并显著改变与相邻片段重复的视觉构图。`);
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
      updateTaskProgress(task);
      if (task.partial_result) {
        applyNonIntrusivePartialResult(task.partial_result);
        await refreshProjectStatus(task.project_dir || task.partial_result?.project_dir || lastQuickResult?.project_dir);
      }
      if (task.state === "succeeded") {
        applyNonIntrusivePartialResult(task.result);
        elements.annotationStatus.textContent = `${label} 完成，片段已更新。`;
        if (selectedSegmentId === targetSegmentId) {
          const updated = currentSegments.find((segment) => segment.id === targetSegmentId);
          const updatedPreview = updated?.corrected_preview_path || updated?.preview_video_path || updated?.video_path;
          if (updatedPreview) playVideoPath(updatedPreview, appendLog);
        }
        return;
      }
      if (["failed", "stalled", "interrupted"].includes(task.state)) {
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
    const hasAudio = Boolean(segments[index]?.audio_path || audioPaths[index]);
    const state = hasAudio ? "ready" : (ttsStatus === "failed" ? "failed" : "pending");
    return `<div class="audio-segment ${state}" title="语音片段 ${index + 1}"><span>${index + 1}</span></div>`;
  }).join("");
}

function applyNonIntrusivePartialResult(partial) {
  if (!partial) return;
  const playingSrc = elements.videoPlayer?.getAttribute("src") || "";
  lastQuickResult = { ...(lastQuickResult || {}), ...partial };
  currentProjectDir = partial.project_dir || currentProjectDir;
  if (partial.project_dir) elements.projectPath.textContent = `项目：${partial.project_dir}`;
  currentStages = partial.stages || currentStages;
  currentSegments = partial.segments || currentSegments;
  window.annotationEditor?.setProject(currentProjectDir, currentSegments);
  updateCompositionControls(lastQuickResult);
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
  window.annotationEditor?.showVideo();
  loadVideo(elements.videoPlayer, videoUrl, logger);
}

function updateSegmentPreviewControls(segment) {
  const originalPath = segment?.original_preview_path || segment?.original_video_path || segment?.video_path || "";
  const correctedPath = segment?.corrected_preview_path || segment?.corrected_video_path || "";
  if (elements.originalSegmentPreviewBtn) {
    elements.originalSegmentPreviewBtn.disabled = !originalPath;
    elements.originalSegmentPreviewBtn.dataset.videoPath = originalPath;
  }
  if (elements.correctedSegmentPreviewBtn) {
    elements.correctedSegmentPreviewBtn.disabled = !correctedPath;
    elements.correctedSegmentPreviewBtn.dataset.videoPath = correctedPath;
  }
}

function clearSegmentCodeEditor(message = "请先选择一个分镜片段。") {
  currentSegmentCodeInfo = null;
  if (elements.segmentCodeLabel) elements.segmentCodeLabel.textContent = message;
  if (elements.segmentCodeInput) elements.segmentCodeInput.value = "";
  if (elements.copySegmentCodeBtn) elements.copySegmentCodeBtn.disabled = true;
  if (elements.renderSegmentCodeBtn) elements.renderSegmentCodeBtn.disabled = true;
  if (elements.segmentCodeHistory) elements.segmentCodeHistory.innerHTML = '<option value="">历史版本</option>';
  if (elements.restoreSegmentCodeBtn) elements.restoreSegmentCodeBtn.disabled = true;
  if (elements.segmentSyncStatus) elements.segmentSyncStatus.textContent = "视频时长：-- · 音频时长：-- · 对齐状态：--";
}

async function loadSelectedSegmentCode(segmentId) {
  const projectDir = currentProjectDir || lastQuickResult?.project_dir || "";
  if (!segmentId || segmentId === "final" || !projectDir) {
    clearSegmentCodeEditor();
    return;
  }
  elements.segmentCodeStatus.textContent = `正在读取 ${segmentId} 的代码...`;
  try {
    const response = await fetch(`${API_BASE}/project/segment-code?project_dir=${encodeURIComponent(projectDir)}&segment_id=${encodeURIComponent(segmentId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "读取片段代码失败。");
    if (selectedSegmentId !== segmentId) return;
    currentSegmentCodeInfo = payload;
    elements.segmentCodeLabel.textContent = `当前编辑：${payload.segment_id} · ${payload.title || "未命名"} · 代码版本 v${payload.code_revision}`;
    elements.segmentCodeInput.value = payload.code || "";
    elements.copySegmentCodeBtn.disabled = false;
    elements.renderSegmentCodeBtn.disabled = false;
    elements.segmentTimingPolicy.value = payload.timing_policy || "auto_audio";
    elements.segmentManualDuration.disabled = elements.segmentTimingPolicy.value !== "manual";
    elements.segmentManualDuration.value = payload.manual_duration || payload.audio_duration || payload.video_duration || "";
    const alignedText = payload.aligned ? "已对齐" : (payload.needs_audio_stretch ? "需要自动适配" : "未对齐");
    elements.segmentSyncStatus.textContent = `Manim 视频时长：${Number(payload.video_duration || 0).toFixed(2)} 秒 · 音频时长：${Number(payload.audio_duration || 0).toFixed(2)} 秒 · ${alignedText}`;
    elements.segmentCodeHistory.innerHTML = '<option value="">历史版本</option>' + (payload.history || []).map((item, index) =>
      `<option value="${index}">v${item.revision} · ${escapeHtml(item.saved_at || "")}</option>`
    ).join("");
    elements.restoreSegmentCodeBtn.disabled = true;
    elements.segmentCodeStatus.textContent = "修改和重渲染只影响当前片段，不会自动合成总体视频。";
  } catch (error) {
    clearSegmentCodeEditor(`片段 ${segmentId} 的代码暂不可用。`);
    elements.segmentCodeStatus.textContent = `读取失败：${error.message}`;
  }
}

async function submitSegmentCodeRender() {
  const projectDir = currentProjectDir || lastQuickResult?.project_dir || "";
  const segmentId = selectedSegmentId;
  if (!projectDir || !segmentId || segmentId === "final") throw new Error("请先选择一个分镜片段。");
  const code = elements.segmentCodeInput.value;
  if (!code.trim()) throw new Error("Manim 代码不能为空。");
  const form = new FormData();
  form.append("project_dir", projectDir);
  form.append("segment_id", segmentId);
  form.append("manim_code", code);
  form.append("quality", elements.qualityInput.value || "low");
  form.append("timing_policy", elements.segmentTimingPolicy.value);
  form.append("manual_duration", elements.segmentManualDuration.value || "0");
  elements.renderSegmentCodeBtn.disabled = true;
  elements.segmentCodeStatus.textContent = `正在校验并重渲染 ${segmentId}...`;
  const response = await fetch(`${API_BASE}/render_segment_code_async`, { method: "POST", body: form });
  const task = await response.json();
  if (!response.ok) throw new Error(task.detail || "提交代码渲染任务失败。");
  await pollSegmentCodeTask(task.task_id, segmentId, projectDir);
}

async function pollSegmentCodeTask(taskId, segmentId, projectDir) {
  while (true) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`);
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "片段渲染状态查询失败。");
    updateTaskProgress(task);
    const latestLog = (task.logs || []).at(-1);
    if (latestLog) elements.segmentCodeStatus.textContent = latestLog;
    if (task.partial_result) applyNonIntrusivePartialResult(task.partial_result);
    if (task.state === "succeeded") {
      await refreshProjectStatus(projectDir);
      await loadSelectedSegmentCode(segmentId);
      const updated = currentSegments.find((item) => item.id === segmentId);
      const preview = updated?.corrected_preview_path || updated?.preview_video_path || updated?.video_path;
      if (preview) playVideoPath(preview, appendLog);
      elements.segmentCodeStatus.textContent = `${segmentId} 已重渲染并刷新预览；总体视频等待手动合成。`;
      return;
    }
    if (["failed", "stalled", "interrupted"].includes(task.state)) {
      throw new Error(task.error || "当前片段渲染失败。");
    }
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
}

function updateCompositionControls(result = {}) {
  const projectDir = result.project_dir || currentProjectDir || lastQuickResult?.project_dir || "";
  const segmentsReady = currentSegments.length > 0 && currentSegments.every((segment) => segment.video_path);
  const composed = Boolean(result.video_path) && !["awaiting_user", "stale"].includes(result.compose_status);
  if (elements.composeOverallBtn) elements.composeOverallBtn.disabled = !projectDir || !segmentsReady;
  if (elements.overallPreviewBtn) {
    elements.overallPreviewBtn.disabled = !composed;
    elements.overallPreviewBtn.dataset.videoPath = composed ? result.video_path : "";
  }
  if (!elements.composeStatus) return;
  if (result.compose_status === "stale") {
    elements.composeStatus.textContent = "局部片段已更新；原总体视频已失效，请确认后手动重新合成。";
  } else if (composed) {
    elements.composeStatus.textContent = "总体视频已按全部最新片段完成合成。";
  } else if (segmentsReady) {
    elements.composeStatus.textContent = "片段已就绪。系统不会自动合成；需要时请点击“合成总体视频”。";
  } else {
    elements.composeStatus.textContent = "总体视频仅在全部片段就绪并点击“合成总体视频”后生成。";
  }
}

async function submitManualComposition() {
  const projectDir = currentProjectDir || lastQuickResult?.project_dir || "";
  if (!projectDir) throw new Error("当前项目路径不可用。");
  const form = new FormData();
  form.append("project_dir", projectDir);
  elements.composeOverallBtn.disabled = true;
  elements.composeStatus.textContent = "正在检查片段音画时长并合成总体视频...";
  const response = await fetch(`${API_BASE}/compose_project_async`, { method: "POST", body: form });
  const task = await response.json();
  if (!response.ok) throw new Error(task.detail || "总体视频合成任务提交失败。");
  while (true) {
    const taskResponse = await fetch(`${API_BASE}/tasks/${task.task_id}`);
    const taskState = await taskResponse.json();
    if (!taskResponse.ok) throw new Error(taskState.detail || "合成任务查询失败。");
    const latestLog = (taskState.logs || []).at(-1);
    if (latestLog) elements.composeStatus.textContent = latestLog;
    if (taskState.state === "succeeded") {
      applyResult(taskState.result);
      elements.composeStatus.textContent = "总体视频合成完成，已切换到总体视频预览。";
      return;
    }
    if (taskState.state === "failed") throw new Error(taskState.error || "总体视频合成失败。");
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
}

async function loadRootFolder() {
  if (!elements.rootFolderPanel || !elements.rootVideoList) return;
  elements.rootFolderPanel.classList.remove("hidden");
  elements.rootVideoList.innerHTML = '<div class="path-line">正在加载成品视频...</div>';
  const requestedRoot = selectedOutputDir || "";
  const response = await fetch(`${API_BASE}/projects/root?root_dir=${encodeURIComponent(requestedRoot)}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "根文件夹读取失败。");
  currentRootDir = payload.root_dir || requestedRoot;
  elements.rootFolderPath.textContent = currentRootDir;
  renderRootVideos(payload.projects || []);
}

function renderRootVideos(projects) {
  if (!elements.rootVideoList) return;
  if (!projects.length) {
    elements.rootVideoList.innerHTML = '<div class="root-folder-empty">根文件夹中暂无已完成的视频。</div>';
    return;
  }
  elements.rootVideoList.innerHTML = projects.map((project) => `
    <button class="root-video-item" data-project-dir="${escapeHtml(project.project_dir)}">
      <span class="root-video-title">${escapeHtml(project.title || project.name || "未命名项目")}</span>
      <span class="root-video-meta">${escapeHtml(project.name || "")} · ${formatFileSize(project.size || 0)}</span>
    </button>
  `).join("");
  elements.rootVideoList.querySelectorAll(".root-video-item").forEach((button) => {
    button.addEventListener("click", async () => {
      elements.rootVideoList.querySelectorAll(".root-video-item").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      await switchToRootProject(button.dataset.projectDir);
    });
  });
}

async function switchToRootProject(projectDir) {
  elements.projectPath.textContent = `项目：正在加载 ${projectDir}`;
  const response = await fetch(`${API_BASE}/project/status?project_dir=${encodeURIComponent(projectDir)}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "项目内容加载失败。");
  const result = {
    ...(payload.summary || {}),
    project_dir: payload.project_dir,
    stages: payload.stages || [],
    segments: payload.segments || []
  };
  applyResult(result);
  appendLog(`已切换到根文件夹项目：${projectDir}`);
}

function formatFileSize(bytes) {
  if (!bytes) return "0 MB";
  return `${(Number(bytes) / 1024 / 1024).toFixed(1)} MB`;
}

function autoLoadFirstSegmentVideo(segments) {
  if (!elements.videoPlayer || elements.videoPlayer.getAttribute("src")) return;
  const firstPlayable = (segments || []).find((segment) => segment.preview_video_path || segment.video_path);
  if (!firstPlayable) return;
  selectedSegmentId = firstPlayable.id || selectedSegmentId;
  updateAnnotationSelection(null);
  updateSegmentPreviewControls(firstPlayable);
  playVideoPath(firstPlayable.preview_video_path || firstPlayable.video_path, appendLog);
  if (elements.workflowVideoPlayer) {
    const videoUrl = `${API_BASE}/video?path=${encodeURIComponent(firstPlayable.preview_video_path || firstPlayable.video_path)}&t=${Date.now()}`;
    loadVideo(elements.workflowVideoPlayer, videoUrl, appendWorkflowLog);
  }
  renderSegments(segments, null);
}

async function loadProjectFiles(projectDir) {
  if (!elements.projectFileList || !elements.projectFileContent) return;
  if (!projectDir) {
    await loadProjectRootFiles();
    return;
  }
  currentProjectDir = projectDir;
  elements.projectFileList.innerHTML = '<div class="project-files-state">正在读取项目文件...</div>';
  elements.projectFileContent.textContent = "正在加载...";
  try {
    const response = await fetch(`${API_BASE}/project/files?project_dir=${encodeURIComponent(projectDir)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "项目文件读取失败。");
    if (!payload.files?.length) {
      elements.projectFileList.innerHTML = '<div class="project-files-state">该项目文件夹为空。</div>';
      elements.projectFileContent.textContent = `项目路径：${payload.project_dir || projectDir}`;
      return;
    }
    elements.projectFileList.innerHTML = renderProjectFileGroups(payload.files);
    elements.projectFileContent.textContent = `项目已加载：${payload.project_dir || projectDir}\n共 ${payload.files.length} 个文件。\n请选择左侧文件查看内容。`;
    elements.projectFileList.querySelectorAll(".project-file-item").forEach((button) => {
      button.addEventListener("click", () => loadProjectFile(button.dataset.fullPath));
    });
  } catch (error) {
    elements.projectFileList.innerHTML = '<div class="project-files-state error">项目文件加载失败。</div>';
    elements.projectFileContent.textContent = `项目文件读取失败：${error.message}`;
  }
}

function renderProjectFileGroups(files) {
  const groupDefinitions = [
    { id: "core", label: "核心文件", open: true, match: (path) => !path.includes("/") },
    { id: "outputs", label: "成品与输出", open: true, match: (path) => /^(outputs|stitched)\//.test(path) },
    { id: "inputs", label: "输入素材", open: true, match: (path) => /^inputs\//.test(path) },
    { id: "audio", label: "配音文件", open: false, match: (path) => /^audio\//.test(path) },
    { id: "segments", label: "分镜片段", open: false, match: (path) => /^segments\//.test(path) },
    { id: "ai", label: "模型调用记录", open: false, match: (path) => /^ai_traces\//.test(path) },
    { id: "logs", label: "日志与修复", open: false, match: (path) => /^(logs|repairs|workflow_outputs|media)\//.test(path) },
    { id: "other", label: "其他文件", open: false, match: () => true }
  ];
  const groups = new Map(groupDefinitions.map((group) => [group.id, []]));
  files.forEach((file) => {
    const definition = groupDefinitions.find((group) => group.match(file.path));
    groups.get(definition.id).push(file);
  });
  return groupDefinitions
    .filter((group) => groups.get(group.id).length)
    .map((group) => {
      const groupFiles = groups.get(group.id);
      return `
        <details class="project-file-group" ${group.open ? "open" : ""}>
          <summary>${escapeHtml(group.label)} <span>${groupFiles.length}</span></summary>
          <div class="project-file-group-items">
            ${groupFiles.map((file) => `
              <button class="project-file-item" data-full-path="${escapeHtml(file.full_path)}">
                ${escapeHtml(shortProjectFileName(file.path, group.id))}
              </button>
            `).join("")}
          </div>
        </details>
      `;
    }).join("");
}

function shortProjectFileName(path, groupId) {
  if (groupId === "core" || groupId === "other") return path;
  const firstSlash = path.indexOf("/");
  return firstSlash >= 0 ? path.slice(firstSlash + 1) : path;
}

async function loadProjectRootFiles() {
  if (!elements.projectFileList || !elements.projectFileContent) return;
  elements.projectFileList.innerHTML = '<div class="project-files-state">正在读取根目录...</div>';
  elements.projectFileContent.textContent = "正在加载项目列表...";
  const requestedRoot = currentRootDir || selectedOutputDir || "";
  try {
    const response = await fetch(
      `${API_BASE}/projects/root?root_dir=${encodeURIComponent(requestedRoot)}&include_unfinished=true`
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "根目录读取失败。");
    currentRootDir = payload.root_dir || requestedRoot;
    currentProjectDir = "";
    if (elements.projectRootPath) elements.projectRootPath.textContent = currentRootDir;
    const projects = payload.projects || [];
    if (!projects.length) {
      elements.projectFileList.innerHTML = '<div class="project-files-state">根目录中暂无项目。</div>';
      elements.projectFileContent.textContent = `根目录：${currentRootDir}`;
      return;
    }
    elements.projectFileList.innerHTML = projects.map((project) => `
      <button class="project-folder-item" data-project-dir="${escapeHtml(project.project_dir)}">
        <strong>${escapeHtml(project.title || project.name || "未命名项目")}</strong>
        <span>${escapeHtml(project.name || "")} · ${escapeHtml(project.status || "未知状态")}</span>
        <span class="project-load-label">加载项目${project.video_path ? "并预览视频" : ""}</span>
      </button>
    `).join("");
    elements.projectFileContent.textContent = `根目录中共有 ${projects.length} 个项目。\n请选择左侧项目查看文件。`;
    elements.projectFileList.querySelectorAll(".project-folder-item").forEach((button) => {
      button.addEventListener("click", async () => {
        currentProjectDir = button.dataset.projectDir || "";
        elements.projectFileContent.textContent = "正在加载项目和中心预览...";
        try {
          await switchToRootProject(currentProjectDir);
        } catch (error) {
          elements.projectFileContent.textContent = `项目加载失败：${error.message}`;
          appendLog(`项目加载失败：${error.message}`);
        }
      });
    });
  } catch (error) {
    elements.projectFileList.innerHTML = '<div class="project-files-state error">根目录加载失败。</div>';
    elements.projectFileContent.textContent = `根目录读取失败：${error.message}`;
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
  const styleMode = mode === "style";
  elements.quickView.classList.toggle("hidden", workflowMode || styleMode);
  elements.workflowView.classList.toggle("hidden", !workflowMode);
  elements.styleView.classList.toggle("hidden", !styleMode);
  elements.quickModeTab.classList.toggle("active", !workflowMode && !styleMode);
  elements.workflowModeTab.classList.toggle("active", workflowMode);
  elements.styleModeTab.classList.toggle("active", styleMode);
  elements.generateBtn.style.display = workflowMode || styleMode ? "none" : "inline-flex";
  if (workflowMode) renderWorkflow();
  if (styleMode) loadStyleLibrary(selectedStyleId).catch((error) => elements.styleLibraryStatus.textContent = error.message);
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

    updateTaskProgress(task);
    renderTaskLogs(task.logs || []);
    if (task.partial_result) applyPartialResult(task.partial_result);
    await refreshProjectStatus(task.project_dir || task.partial_result?.project_dir || lastQuickResult?.project_dir);
    renderStages(currentStages, currentSegments, detectCurrentStage(task.logs || []));

    if (task.state === "succeeded") {
      applyResult(task.result);
      appendLog("完成。");
      return;
    }

    if (["failed", "stalled", "interrupted"].includes(task.state)) {
      throw new Error(task.error || "生成失败。");
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}
elements.imageInput.addEventListener("change", () => {
  const file = elements.imageInput.files[0];
  if (file && !(hasModelCapability("vision") && hasModelCapability("image_upload") && hasModelCapability("multimodal_input"))) {
    elements.imageInput.value = "";
    elements.imageName.textContent = "选择图片";
    window.annotationEditor?.setImagePreview(null);
    elements.visionCapabilityHint.textContent = "当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。";
    return;
  }
  elements.imageName.textContent = file ? file.name : "选择图片";
  window.annotationEditor?.setImagePreview(file || null);
});

elements.providerInput.addEventListener("change", applyActiveModelProfile);
elements.settingsBtn?.addEventListener("click", async () => {
  elements.settingsModal?.classList.remove("hidden");
  await Promise.all([loadModelProfiles(elements.providerInput.value), loadAudioProfiles()]);
  editModelProfile(elements.providerInput.value);
  editAudioProfile(editingAudioProfileId || defaultAudioProfileId);
});
elements.closeSettingsBtn?.addEventListener("click", () => elements.settingsModal?.classList.add("hidden"));
elements.modelProfileList?.addEventListener("change", () => editModelProfile(elements.modelProfileList.value));
elements.newModelProfileBtn?.addEventListener("click", () => editModelProfile(""));
elements.saveModelProfileBtn?.addEventListener("click", () => saveModelProfile().catch((error) => { elements.modelSettingsStatus.textContent = `保存失败：${error.message}`; }));
elements.deleteModelProfileBtn?.addEventListener("click", async () => {
  if (!editingModelProfileId) return;
  const response = await fetch(`${API_BASE}/model-configs/${encodeURIComponent(editingModelProfileId)}`, { method: "DELETE" });
  const payload = await response.json();
  if (!response.ok) { elements.modelSettingsStatus.textContent = `删除失败：${payload.detail}`; return; }
  editingModelProfileId = "";
  await loadModelProfiles();
  editModelProfile(elements.providerInput.value);
});
elements.defaultModelProfileBtn?.addEventListener("click", async () => {
  if (!editingModelProfileId) return;
  const response = await fetch(`${API_BASE}/model-configs/${encodeURIComponent(editingModelProfileId)}/default`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) { elements.modelSettingsStatus.textContent = `设置失败：${payload.detail}`; return; }
  await loadModelProfiles(editingModelProfileId);
  editModelProfile(editingModelProfileId);
  elements.modelSettingsStatus.textContent = "已设为默认模型。";
});
elements.probeModelProfileBtn?.addEventListener("click", async () => {
  if (!editingModelProfileId) return;
  elements.modelSettingsStatus.textContent = "正在探测文本、Vision、JSON、Function Calling 与 Streaming，请稍候...";
  const response = await fetch(`${API_BASE}/model-configs/${encodeURIComponent(editingModelProfileId)}/probe`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) { elements.modelSettingsStatus.textContent = `探测失败：${payload.detail}`; return; }
  await loadModelProfiles(elements.providerInput.value);
  editModelProfile(editingModelProfileId);
});

elements.audioProfileList?.addEventListener("change", () => editAudioProfile(elements.audioProfileList.value));
elements.newAudioProfileBtn?.addEventListener("click", () => editAudioProfile(""));
elements.saveAudioProfileBtn?.addEventListener("click", () => saveAudioProfile().catch((error) => { elements.audioSettingsStatus.textContent = `保存失败：${error.message}`; }));
elements.deleteAudioProfileBtn?.addEventListener("click", async () => {
  if (!editingAudioProfileId) return;
  const response = await fetch(`${API_BASE}/audio-configs/${encodeURIComponent(editingAudioProfileId)}`, { method: "DELETE" });
  const payload = await response.json();
  if (!response.ok) { elements.audioSettingsStatus.textContent = `删除失败：${payload.detail}`; return; }
  editingAudioProfileId = "";
  await loadAudioProfiles();
  editAudioProfile(defaultAudioProfileId);
});
elements.defaultAudioProfileBtn?.addEventListener("click", async () => {
  if (!editingAudioProfileId) return;
  const response = await fetch(`${API_BASE}/audio-configs/${encodeURIComponent(editingAudioProfileId)}/default`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) { elements.audioSettingsStatus.textContent = `设置失败：${payload.detail}`; return; }
  await loadAudioProfiles(editingAudioProfileId);
  editAudioProfile(editingAudioProfileId);
});
elements.testAudioProfileBtn?.addEventListener("click", async () => {
  if (!editingAudioProfileId) return;
  elements.audioSettingsStatus.textContent = "正在测试音频接口...";
  const response = await fetch(`${API_BASE}/audio-configs/${encodeURIComponent(editingAudioProfileId)}/test`, { method: "POST" });
  const payload = await response.json();
  elements.audioSettingsStatus.textContent = response.ok && payload.success ? payload.message : `测试失败：${payload.error || payload.detail || payload.message}`;
  await loadAudioProfiles(editingAudioProfileId);
});
elements.exportConfigsBtn?.addEventListener("click", async () => {
  const response = await fetch(`${API_BASE}/configurations?include_secrets=${elements.exportSecretsInput?.checked ? "true" : "false"}`);
  const payload = await response.json();
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = "manim-provider-configs.json"; anchor.click(); URL.revokeObjectURL(url);
});
elements.importConfigsInput?.addEventListener("change", async () => {
  const file = elements.importConfigsInput.files[0]; if (!file) return;
  try {
    const response = await fetch(`${API_BASE}/configurations/import`, { method: "POST", headers: { "Content-Type": "application/json" }, body: await file.text() });
    const payload = await response.json(); if (!response.ok) throw new Error(payload.detail || "导入失败。");
    await Promise.all([loadModelProfiles(), loadAudioProfiles()]);
    elements.modelSettingsStatus.textContent = "配置导入完成。";
  } catch (error) { elements.modelSettingsStatus.textContent = `导入失败：${error.message}`; }
  finally { elements.importConfigsInput.value = ""; }
});

elements.copySegmentCodeBtn?.addEventListener("click", async () => {
  await navigator.clipboard.writeText(elements.segmentCodeInput.value || "");
  elements.segmentCodeStatus.textContent = `已复制 ${selectedSegmentId || "当前片段"} 的 Manim 代码。`;
});

elements.uploadSegmentCodeInput?.addEventListener("change", async () => {
  const file = elements.uploadSegmentCodeInput.files[0];
  if (!file) return;
  elements.segmentCodeInput.value = await file.text();
  elements.segmentCodeStatus.textContent = `已载入 ${file.name}，点击“保存并重渲染当前片段”后生效。`;
  elements.uploadSegmentCodeInput.value = "";
});

elements.segmentTimingPolicy?.addEventListener("change", () => {
  elements.segmentManualDuration.disabled = elements.segmentTimingPolicy.value !== "manual";
});

elements.segmentCodeHistory?.addEventListener("change", () => {
  elements.restoreSegmentCodeBtn.disabled = elements.segmentCodeHistory.value === "";
});

elements.restoreSegmentCodeBtn?.addEventListener("click", () => {
  const index = Number(elements.segmentCodeHistory.value);
  const historical = currentSegmentCodeInfo?.history?.[index];
  if (!historical?.code) return;
  elements.segmentCodeInput.value = historical.code;
  elements.segmentCodeStatus.textContent = `已载入历史版本 v${historical.revision}；重新渲染后才会成为当前版本。`;
});

elements.renderSegmentCodeBtn?.addEventListener("click", async () => {
  try {
    await submitSegmentCodeRender();
  } catch (error) {
    elements.segmentCodeStatus.textContent = `重渲染失败：${error.message}`;
  } finally {
    elements.renderSegmentCodeBtn.disabled = !selectedSegmentId || selectedSegmentId === "final";
  }
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
  button.addEventListener("click", async () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-view").forEach((item) => item.classList.add("hidden"));
    button.classList.add("active");
    document.getElementById(`${button.dataset.tab}View`).classList.remove("hidden");
    if (button.dataset.tab === "files") {
      await loadProjectFiles(currentProjectDir || lastQuickResult?.project_dir || "");
    }
  });
});

elements.replayBtn.addEventListener("click", () => {
  elements.videoPlayer.currentTime = 0;
  elements.videoPlayer.play();
});

if (elements.originalSegmentPreviewBtn) {
  elements.originalSegmentPreviewBtn.addEventListener("click", () => {
    const path = elements.originalSegmentPreviewBtn.dataset.videoPath;
    if (path) playVideoPath(path, appendLog);
  });
}

if (elements.correctedSegmentPreviewBtn) {
  elements.correctedSegmentPreviewBtn.addEventListener("click", () => {
    const path = elements.correctedSegmentPreviewBtn.dataset.videoPath;
    if (path) playVideoPath(path, appendLog);
  });
}

if (elements.overallPreviewBtn) {
  elements.overallPreviewBtn.addEventListener("click", () => {
    const path = elements.overallPreviewBtn.dataset.videoPath;
    if (path) playVideoPath(path, appendLog);
  });
}

if (elements.composeOverallBtn) {
  elements.composeOverallBtn.addEventListener("click", () => {
    submitManualComposition().catch((error) => {
      elements.composeStatus.textContent = `总体视频合成失败：${error.message}`;
      updateCompositionControls(lastQuickResult || {});
    });
  });
}

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

if (elements.rootFolderBtn) {
  elements.rootFolderBtn.addEventListener("click", () => {
    loadRootFolder().catch((error) => {
      elements.rootFolderPanel?.classList.remove("hidden");
      if (elements.rootVideoList) elements.rootVideoList.innerHTML = `<div class="root-folder-empty">加载失败：${escapeHtml(error.message)}</div>`;
      appendLog(`根文件夹加载失败：${error.message}`);
    });
  });
}

if (elements.projectRootBtn) {
  elements.projectRootBtn.addEventListener("click", () => loadProjectRootFiles());
}

if (elements.changeProjectRootBtn) {
  elements.changeProjectRootBtn.addEventListener("click", async () => {
    const dir = await window.desktopApi.selectOutputDir();
    if (!dir) return;
    selectedOutputDir = dir;
    currentRootDir = dir;
    elements.outputDir.textContent = dir;
    await loadProjectRootFiles();
    appendLog(`根目录已更改为：${dir}`);
  });
}

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
elements.styleModeTab.addEventListener("click", () => setMode("style"));
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
  if (elements.imageInput.files[0] && !(hasModelCapability("vision") && hasModelCapability("image_upload") && hasModelCapability("multimodal_input"))) {
    appendLog("当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。");
    return;
  }
  elements.generateBtn.disabled = true;
  elements.logOutput.textContent = "";
  elements.storyboardView.textContent = "";
  elements.codeView.textContent = "";
  elements.repairsView.textContent = "";
  elements.projectFileList.innerHTML = "";
  elements.projectFileContent.textContent = "生成任务创建后将在这里显示项目文件。";
  currentProjectDir = "";
  lastQuickResult = null;
  if (elements.audioStatus) {
    elements.audioStatus.textContent = "配音：正在等待视频生成";
    elements.audioStatus.classList.remove("success", "warning");
  }
  if (elements.applyEditBtn) elements.applyEditBtn.disabled = true;
  if (elements.editStatus) elements.editStatus.textContent = "视频生成完成后可提交修改要求。";
  const totalDurationSeconds = selectedTotalDurationSeconds();
  currentStages = buildDefaultStages(totalDurationSeconds);
  currentSegments = [];
  selectedSegmentId = "";
  window.annotationEditor?.setProject("", []);
  updateSegmentPreviewControls(null);
  updateCompositionControls({});
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
    const activeStyle = styleLibrary.find((item) => item.id === elements.stylePresetSelect?.value);
    const styledPrompt = activeStyle?.preset?.prompt_preset
      ? `${activeStyle.preset.prompt_preset}\n\n本次课程主题与要求：\n${elements.promptInput.value}`
      : elements.promptInput.value;
    form.append("prompt", styledPrompt);
    form.append("model_profile_id", elements.providerInput.value);
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
      form.append("model_profile_id", elements.providerInput.value);
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
initializeConfigurations();
loadStyleLibrary().catch((error) => appendLog(`风格库读取失败：${error.message}`));

elements.stylePresetSelect?.addEventListener("change", applySelectedStyle);
elements.applyStylePresetBtn?.addEventListener("click", () => {
  applySelectedStyle();
  setMode("quick");
});
elements.styleProjectInput?.addEventListener("change", () => {
  learnStyleFromFiles(elements.styleProjectInput.files)
    .catch((error) => elements.styleLibraryStatus.textContent = `学习失败：${error.message}`)
    .finally(() => { elements.styleProjectInput.value = ""; });
});
elements.saveStylePresetBtn?.addEventListener("click", () => {
  saveStylePreset().catch((error) => elements.styleLibraryStatus.textContent = `保存失败：${error.message}`);
});
elements.exportStylePresetBtn?.addEventListener("click", () => {
  const style = styleLibrary.find((item) => item.id === selectedStyleId);
  if (!style) return;
  const blob = new Blob([JSON.stringify(style, null, 2)], { type: "application/json" });
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = `${style.name || "manim-style"}.json`;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
});
elements.styleImportInput?.addEventListener("change", async () => {
  try {
    const file = elements.styleImportInput.files[0];
    if (!file) return;
    const response = await fetch(`${API_BASE}/style-library/import`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: await file.text()
    });
    const style = await response.json();
    if (!response.ok) throw new Error(style.detail || "导入失败。");
    await loadStyleLibrary(style.id);
  } catch (error) {
    elements.styleLibraryStatus.textContent = `导入失败：${error.message}`;
  } finally {
    elements.styleImportInput.value = "";
  }
});
elements.rollbackStylePresetBtn?.addEventListener("click", async () => {
  if (!selectedStyleId || !elements.styleVersionSelect.value) return;
  try {
    const response = await fetch(`${API_BASE}/style-library/${selectedStyleId}/rollback/${elements.styleVersionSelect.value}`, { method: "POST" });
    const style = await response.json();
    if (!response.ok) throw new Error(style.detail || "回退失败。");
    await loadStyleLibrary(style.id);
    elements.styleLibraryStatus.textContent = `已回退到版本 ${style.active_version}。`;
  } catch (error) {
    elements.styleLibraryStatus.textContent = `回退失败：${error.message}`;
  }
});

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
  const imageNodeTypes = new Set(["InputImageNode", "ImagePreprocessNode", "ImageUnderstandNode"]);
  const visionReady = hasModelCapability("vision") && hasModelCapability("image_upload") && hasModelCapability("multimodal_input");
  const groups = {};
  definitions.forEach((definition) => {
    groups[definition.category] = groups[definition.category] || [];
    groups[definition.category].push(definition);
  });
  elements.nodeLibrary.innerHTML = Object.entries(groups).map(([category, items]) => `
    <div class="library-group">
      <div class="library-group-title">${categoryLabels[category] || category}</div>
      ${items.map((item) => `<button class="library-node" data-node-type="${item.type}" ${imageNodeTypes.has(item.type) && !visionReady ? "disabled title=\"当前模型不支持 Vision\"" : ""}>${labelForNode(item)}</button>`).join("")}
    </div>
  `).join("");
  elements.nodeLibrary.querySelectorAll(".library-node").forEach((button) => {
    button.addEventListener("click", () => addWorkflowNode(button.dataset.nodeType));
  });
}

async function loadWorkflowTemplate(templateId) {
  const response = await fetch(`${API_BASE}/workflow/templates/${templateId}`);
  const loaded = await response.json();
  if (!response.ok) throw new Error(loaded.detail || "模板加载失败。");
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
        <span class="workflow-node-status">${statusLabel(node.status || "idle")}</span>
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
      active.status = "idle";
      const affected = new Set([active.id]);
      let changed = true;
      while (changed) {
        changed = false;
        workflow.edges.forEach((edge) => {
          if (affected.has(edge.source) && !affected.has(edge.target)) {
            affected.add(edge.target);
            changed = true;
          }
        });
      }
      workflow.nodes.forEach((item) => {
        if (affected.has(item.id)) item.status = "idle";
      });
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
  (result.issues || []).forEach((issue) => appendWorkflowLog(`${statusLabel(issue.severity)}：${issue.message}`));
  if (result.execution_order?.length) appendWorkflowLog(`执行顺序：${result.execution_order.join(" → ")}`);
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
    url.searchParams.set("model_profile_id", elements.providerInput.value);
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
    updateTaskProgress(task, true);
    const logs = (task.logs || []).join("\n");
    if (logs !== last) {
      last = logs;
      elements.workflowLog.textContent = logs + "\n";
      elements.workflowLog.scrollTop = elements.workflowLog.scrollHeight;
    }
    if (task.state === "succeeded") {
      const states = task.result?.workflow_node_states || {};
      workflow.nodes.forEach((node) => {
        if (states[node.id]?.status) node.status = states[node.id].status;
      });
      renderWorkflow();
      applyResult(task.result);
      appendWorkflowLog("工作流运行完成。");
      return;
    }
    if (["failed", "stalled", "interrupted"].includes(task.state)) throw new Error(task.error || "工作流失败。");
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
elements.loadImageTemplateBtn.addEventListener("click", () => {
  if (!(hasModelCapability("vision") && hasModelCapability("image_upload") && hasModelCapability("multimodal_input"))) {
    appendWorkflowLog("当前所选模型不支持图片理解（Vision）能力，请切换至支持读图的模型后再使用该功能。");
    return;
  }
  loadWorkflowTemplate("image_problem");
});
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

elements.customNodeInput?.addEventListener("change", async () => {
  const file = elements.customNodeInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    const response = await fetch(`${API_BASE}/workflow/custom-nodes`, { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "自定义节点上传失败。");
    nodeDefinitions[payload.node.type] = payload.node;
    renderNodeLibrary(Object.values(nodeDefinitions));
    appendWorkflowLog(`自定义节点“${payload.node.label}”已加入节点库。`);
  } catch (error) {
    appendWorkflowLog(`自定义节点上传失败：${error.message}`);
  } finally {
    elements.customNodeInput.value = "";
  }
});

elements.workflowTutorialBtn?.addEventListener("click", () => {
  appendWorkflowLog("节点工作流教程：WORKFLOW_TUTORIAL.md。基础流程：输入节点 → 规划/控制节点 → Manim 代码 → 渲染 → 输出。");
  elements.workflowLog?.scrollIntoView({ behavior: "smooth", block: "center" });
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






