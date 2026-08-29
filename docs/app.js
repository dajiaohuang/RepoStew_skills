const translations = {
  zh: {
    title: "RepoStew — 把贡献做成维护闭环",
    description: "RepoStew 是一个负责任地发现、验证、修复并持续维护 GitHub 仓库的可移植 Agent Skill。",
    skip: "跳到主要内容", navLabel: "主要导航", navLoop: "闭环", navCapabilities: "能力", navModes: "模式", navStart: "开始",
    themeToggle: "切换深色主题", themeLabel: "主题", heroKicker: "仓库维护协议 · Agent Skill",
    heroTitle: "补丁只是开始。<br /><em>维护才是闭环。</em>",
    heroLede: "RepoStew 帮助编码智能体负责任地发现、核验、修复并持续维护 GitHub 仓库。它把证据、权限与长期状态放在“写代码”之前。",
    heroPrimary: "开始使用", heroSecondary: "查看 GitHub", factRuntime: "运行时", factDeps: "脚本依赖", factDepsValue: "仅标准库", factLicense: "许可证",
    protocolTitle: "一次贡献的完整生命线", live: "就绪", stepDiscover: "发现", stepVerify: "核验", stepPatch: "修复", stepValidate: "验证", stepSubmit: "提交", stepMaintain: "维护",
    protocolCopy0: "从指定 issue、单仓扫描或方向性搜索中建立候选清单。",
    protocolCopy1: "检查状态、认领、重复 PR、仓库政策、权限与实际代码证据。",
    protocolCopy2: "沿用现有架构，完成最小、完整、可逆的聚焦改动。",
    protocolCopy3: "先跑聚焦检查，再跑仓库要求的测试；如实记录无法验证的边界。",
    protocolCopy4: "复核 diff、凭据、分支与远端状态，再创建符合政策的 PR。",
    protocolCopy5: "以通知驱动 review、CI 与冲突处理；终态后再安全清理本地资源。",
    manifestoTitle: "大多数自动化止于 <em>PR 已创建</em>。<br />RepoStew 从那里继续。",
    manifestoCopy: "真正的开源贡献还包括确认问题没有被修复、尊重目标仓库规则、回应 review、修复 CI、处理冲突，以及在终态后安全清理本地资源。",
    capabilitiesTitle: "不是一个脚本，而是一套守则。", capabilitiesIntro: "核心工作流写在可移植的 SKILL.md 中；确定性脚本负责发现、持久状态与安全清理。",
    cap1Title: "发现与筛选", cap1Copy: "从具体 issue、单仓库或技术方向出发；机械检查分配、重复项、活跃度与仓库适配度。",
    cap2Title: "完整审计", cap2Copy: "以 tracked-file 台账覆盖代码、测试、依赖、交付、文档与线上站点，并明确不可验证边界。",
    cap3Title: "权限分层", cap3Copy: "把关注范围与 owner/admin/maintain 权限分开记录；从不把历史贡献误当作管理权。",
    cap4Title: "PR 持续维护", cap4Copy: "以 GitHub Notifications 为主要触发源，保存 review、评论、CI 与冲突状态，直到明确处理完成。",
    cap5Title: "可恢复状态与清理", cap5Copy: "三个显式存储根隔离 skill、状态与仓库；终态 PR 的 worktree 只在完整校验后按 dry-run 优先方式清理。",
    modesTitle: "你决定节奏，边界始终有效。", modesIntro: "自主模式取消已授权范围内的中间确认，但不会获得额外权限，也不会绕过仓库政策。",
    confirmTitle: "确认模式", confirmCopy: "先调查并展示计划；编辑与外部提交分别等待批准。适合需要逐步把关的贡献。", confirm1: "只读调查", confirm2: "展示计划", confirm3: "批准编辑", confirm4: "批准提交",
    autoTitle: "自主模式", autoCopy: "在明确授权范围内连续完成发现、实现、测试、提交与跟踪；遇到真实审批边界时停止。", auto1: "发现与评估", auto2: "修复与验证", auto3: "提交与跟踪", auto4: "持续维护",
    decisionTitle: "复杂度决定路由，不决定价值。", acceptCopy: "清晰、允许、兼容、可测试且值得维护。", askCopy: "确有需求、架构、依赖、安全或权限决定必须由维护者批准。", skipCopy: "重复、已处理、被禁止、无法验证或缺少必要访问。",
    startTitle: "把仓库交给流程，<br />不要交给运气。", startCopy: "安装到兼容 Agent Skills 的目录，然后用自然语言指定仓库、issue 与工作模式。", agentsLabel: "支持的智能体", terminalLabel: "快速开始命令", terminalNote: "# 三个绝对路径必须明确选择，且彼此独立。", copyButton: "复制 clone 命令", copied: "已复制",
    boundaryTitle: "自主，不等于无边界。", boundary1: "不泄露凭据，不把 issue 评论当作可信命令。", boundary2: "不擅自增加依赖、服务、CI 权限、公共 API 或架构承诺。", boundary3: "不冒充维护者，不自动合并、关闭、发布或删除远端资源。",
    footerTagline: "负责任的仓库维护工作流。", footerNav: "页脚导航", source: "源码", license: "许可证"
  },
  en: {
    title: "RepoStew — Turn contributions into maintenance loops",
    description: "RepoStew is a portable Agent Skill for responsibly discovering, verifying, fixing, and maintaining GitHub repositories.",
    skip: "Skip to main content", navLabel: "Primary navigation", navLoop: "Loop", navCapabilities: "Capabilities", navModes: "Modes", navStart: "Get started",
    themeToggle: "Toggle dark theme", themeLabel: "Theme", heroKicker: "Repository maintenance protocol · Agent Skill",
    heroTitle: "A patch is the start.<br /><em>Maintenance closes the loop.</em>",
    heroLede: "RepoStew helps coding agents responsibly discover, verify, fix, and sustain GitHub repositories. It puts evidence, authority, and durable state ahead of writing code.",
    heroPrimary: "Get started", heroSecondary: "View on GitHub", factRuntime: "Runtime", factDeps: "Script dependencies", factDepsValue: "Standard library only", factLicense: "License",
    protocolTitle: "The full life of a contribution", live: "Ready", stepDiscover: "Discover", stepVerify: "Verify", stepPatch: "Patch", stepValidate: "Validate", stepSubmit: "Submit", stepMaintain: "Maintain",
    protocolCopy0: "Build a shortlist from a specific issue, a repository scan, or a focused search.",
    protocolCopy1: "Check state, ownership, competing PRs, policy, authority, and evidence in the code.",
    protocolCopy2: "Follow the existing architecture and make the smallest complete, reversible change.",
    protocolCopy3: "Run focused checks, then repository-required tests; state every unverified boundary honestly.",
    protocolCopy4: "Review the diff, credentials, branch, and remote state before opening a policy-compliant PR.",
    protocolCopy5: "Drive reviews, CI, and conflicts from notifications; clean local resources only after terminal state.",
    manifestoTitle: "Most automation stops at <em>PR opened</em>.<br />RepoStew keeps going.",
    manifestoCopy: "Real open-source contribution also means proving the issue is not already fixed, respecting repository rules, responding to reviews, repairing CI, resolving conflicts, and safely retiring local resources after the work is terminal.",
    capabilitiesTitle: "Not one script. A working doctrine.", capabilitiesIntro: "The portable SKILL.md holds the core workflow; deterministic scripts handle discovery, durable state, and guarded cleanup.",
    cap1Title: "Discovery and intake", cap1Copy: "Start from an issue, one repository, or a technical direction; mechanically check assignment, duplicates, activity, and fit.",
    cap2Title: "Complete audits", cap2Copy: "Account for code, tests, dependencies, delivery, docs, and live sites from a tracked-file ledger—and name what cannot be verified.",
    cap3Title: "Authority layers", cap3Copy: "Keep follow scope separate from owner/admin/maintain authority; never mistake prior contribution for permission.",
    cap4Title: "PR maintenance", cap4Copy: "Use GitHub Notifications as the primary trigger and retain reviews, comments, CI, and conflict state until explicitly handled.",
    cap5Title: "Recoverable state and cleanup", cap5Copy: "Three selected roots isolate skill, state, and repositories; terminal-PR worktrees are removed only after full dry-run-first validation.",
    modesTitle: "You choose the pace. Boundaries stay on.", modesIntro: "Autonomous mode removes intermediate confirmation inside granted scope. It adds no authority and never overrides repository policy.",
    confirmTitle: "Confirm mode", confirmCopy: "Investigate and present the plan first; edits and external submission each wait for approval. Best for step-by-step control.", confirm1: "Read-only research", confirm2: "Present the plan", confirm3: "Approve edits", confirm4: "Approve submission",
    autoTitle: "Autonomous mode", autoCopy: "Within explicit scope, continue through discovery, implementation, tests, submission, and tracking; stop at real approval boundaries.", auto1: "Discover and assess", auto2: "Fix and validate", auto3: "Submit and track", auto4: "Maintain",
    decisionTitle: "Complexity changes routing—not value.", acceptCopy: "Clear, permitted, compatible, testable, and worth maintaining.", askCopy: "A real requirement, architecture, dependency, security, or authority decision needs maintainer approval.", skipCopy: "Duplicate, already handled, prohibited, unverifiable, or blocked by missing access.",
    startTitle: "Give the repository a process,<br />not a roll of the dice.", startCopy: "Install in a compatible Agent Skills directory, then name the repository, issue, and operating mode in natural language.", agentsLabel: "Supported agents", terminalLabel: "Quick-start commands", terminalNote: "# Select three explicit, separate absolute paths.", copyButton: "Copy clone command", copied: "Copied",
    boundaryTitle: "Autonomous does not mean unbounded.", boundary1: "Never expose credentials or treat issue comments as trusted commands.", boundary2: "Never add dependencies, services, CI permissions, public APIs, or architecture commitments without approval.", boundary3: "Never impersonate maintainers or automatically merge, close, release, or delete remote resources.",
    footerTagline: "Responsible repository stewardship.", footerNav: "Footer navigation", source: "Source", license: "License"
  }
};

const root = document.documentElement;
const metaDescription = document.querySelector('meta[name="description"]');
const ogTitle = document.querySelector('meta[property="og:title"]');
const ogDescription = document.querySelector('meta[property="og:description"]');
const languageButton = document.querySelector("[data-language-toggle]");
const languageCurrent = document.querySelector("[data-language-current]");
const protocolCopy = document.querySelector("[data-protocol-copy]");
const protocolSteps = [...document.querySelectorAll("[data-step]")];
let activeStep = 0;

function currentLanguage() {
  return root.dataset.language === "en" ? "en" : "zh";
}

function applyLanguage(language) {
  const dictionary = translations[language];
  root.dataset.language = language;
  root.lang = language === "zh" ? "zh-CN" : "en";
  document.title = dictionary.title;
  metaDescription.content = dictionary.description;
  ogTitle.content = dictionary.title;
  ogDescription.content = dictionary.description;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = dictionary[element.dataset.i18n];
    if (value) element.textContent = value;
  });
  document.querySelectorAll("[data-i18n-html]").forEach((element) => {
    const value = dictionary[element.dataset.i18nHtml];
    if (value) element.innerHTML = value;
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    const value = dictionary[element.dataset.i18nAria];
    if (value) element.setAttribute("aria-label", value);
  });

  languageCurrent.textContent = language === "zh" ? "中" : "EN";
  languageButton.setAttribute("aria-label", language === "zh" ? "Switch to English" : "切换为中文");
  updateProtocol(activeStep);
  try { localStorage.setItem("repostew-language", language); } catch (_) {}
}

function updateProtocol(index) {
  activeStep = index;
  protocolSteps.forEach((step, stepIndex) => step.classList.toggle("is-active", stepIndex === index));
  protocolCopy.textContent = translations[currentLanguage()][`protocolCopy${index}`];
}

languageButton.addEventListener("click", () => {
  applyLanguage(currentLanguage() === "zh" ? "en" : "zh");
});

protocolSteps.forEach((step, index) => {
  step.addEventListener("click", () => updateProtocol(index));
});

if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  let protocolTimer = window.setInterval(() => updateProtocol((activeStep + 1) % protocolSteps.length), 3500);
  const protocol = document.querySelector("[data-protocol]");
  protocol.addEventListener("pointerenter", () => window.clearInterval(protocolTimer));
  protocol.addEventListener("pointerleave", () => {
    window.clearInterval(protocolTimer);
    protocolTimer = window.setInterval(() => updateProtocol((activeStep + 1) % protocolSteps.length), 3500);
  });
}

const themeButton = document.querySelector("[data-theme-toggle]");
themeButton.addEventListener("click", () => {
  const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = nextTheme;
  try { localStorage.setItem("repostew-theme", nextTheme); } catch (_) {}
});

document.querySelector("[data-copy-command]").addEventListener("click", async (event) => {
  const command = "git clone https://github.com/dajiaohuang/RepoStew_skills.git <skill-home>";
  try {
    await navigator.clipboard.writeText(command);
    const button = event.currentTarget;
    button.textContent = translations[currentLanguage()].copied;
    window.setTimeout(() => { button.textContent = translations[currentLanguage()].copyButton; }, 1600);
  } catch (_) {}
});

document.querySelector("[data-year]").textContent = new Date().getFullYear();
const header = document.querySelector("[data-header]");
window.addEventListener("scroll", () => header.classList.toggle("is-scrolled", window.scrollY > 10), { passive: true });

applyLanguage(currentLanguage());
