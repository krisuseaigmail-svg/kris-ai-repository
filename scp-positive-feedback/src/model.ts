export type ScenarioId = "platform" | "content" | "saas";

export type NodeKey = "structure" | "conduct" | "performance";

export interface Scenario {
  id: ScenarioId;
  label: string;
  blurb: string;
  structureLabel: string;
  conductLabel: string;
  performanceLabel: string;
  feedbackLabel: string;
  levers: {
    barrier: string;
    differentiation: string;
    reinvestment: string;
  };
  chain: [string, string, string, string];
}

export interface ModelState {
  barrier: number;
  differentiation: number;
  reinvestment: number;
  structure: number;
  conduct: number;
  performance: number;
  momentum: number;
  turn: number;
}

export interface LogEntry {
  id: string;
  turn: number;
  text: string;
}

export const SCENARIOS: Record<ScenarioId, Scenario> = {
  platform: {
    id: "platform",
    label: "电商平台",
    blurb: "供给密度抬高转化，转化带来规模，规模再反哺供给与议价。",
    structureLabel: "供给密度 · 网络效应 · 切换成本",
    conductLabel: "补贴策略 · 撮合效率 · 品类扩张",
    performanceLabel: "GMV · 毛利率 · 复购",
    feedbackLabel: "绩效 → 壁垒",
    levers: {
      barrier: "进入壁垒（物流/资金/品牌）",
      differentiation: "差异化（品类与体验）",
      reinvestment: "利润再投入强度",
    },
    chain: [
      "结构：更多优质商家与履约能力",
      "行为：更敢投流量、更敢做品类扩张",
      "绩效：GMV 与复购上升",
      "回灌：规模优势抬高进入壁垒",
    ],
  },
  content: {
    id: "content",
    label: "内容社区",
    blurb: "创作者密度决定内容质量，质量拉来用户，用户再吸引创作者。",
    structureLabel: "创作者密度 · 分发算法 · 社区氛围",
    conductLabel: "激励规则 · 推荐权重 · 创作工具",
    performanceLabel: "日活 · 停留时长 · 广告单价",
    feedbackLabel: "绩效 → 结构",
    levers: {
      barrier: "网络效应强度",
      differentiation: "内容垂类差异",
      reinvestment: "创作者激励再投入",
    },
    chain: [
      "结构：创作者与用户双边密度抬升",
      "行为：加大激励与推荐倾斜",
      "绩效：时长与广告效率改善",
      "回灌：数据与社群壁垒更难复制",
    ],
  },
  saas: {
    id: "saas",
    label: "SaaS 产品",
    blurb: "产品深度带来粘性，粘性提高续费率，续费支撑更深的产品投入。",
    structureLabel: "切换成本 · 集成生态 · 数据沉淀",
    conductLabel: "定价包装 · 客户成功 · 研发节奏",
    performanceLabel: "NRR · 毛利 · 获客效率",
    feedbackLabel: "绩效 → 护城河",
    levers: {
      barrier: "切换成本与集成深度",
      differentiation: "工作流差异化",
      reinvestment: "研发与客户成功再投入",
    },
    chain: [
      "结构：数据与集成形成切换成本",
      "行为：提高客成投入与产品深度",
      "绩效：续费与扩展收入上升",
      "回灌：资金与口碑继续加厚护城河",
    ],
  },
};

export function clamp(n: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, n));
}

export function deriveState(
  barrier: number,
  differentiation: number,
  reinvestment: number,
  momentum = 0,
): Omit<ModelState, "turn"> {
  const structure = clamp(0.55 * barrier + 0.35 * differentiation + 0.1 * momentum);
  const conduct = clamp(0.45 * structure + 0.4 * reinvestment + 0.15 * differentiation);
  const performance = clamp(0.5 * conduct + 0.25 * structure + 0.25 * reinvestment);
  const nextMomentum = clamp(momentum * 0.72 + performance * 0.28);
  return {
    barrier,
    differentiation,
    reinvestment,
    structure,
    conduct,
    performance,
    momentum: nextMomentum,
  };
}

export function stepTurn(prev: ModelState): { state: ModelState; log: string } {
  // Positive feedback: strong performance raises barriers & differentiation over time.
  const feedback = (prev.performance - 50) * 0.12 + prev.momentum * 0.04;
  const barrier = clamp(prev.barrier + feedback * 0.55);
  const differentiation = clamp(prev.differentiation + feedback * 0.35);
  const reinvestment = clamp(prev.reinvestment + (prev.performance > 60 ? 1.2 : -0.6));
  const derived = deriveState(barrier, differentiation, reinvestment, prev.momentum);
  const state: ModelState = { ...derived, turn: prev.turn + 1 };

  const direction = feedback >= 0 ? "强化" : "削弱";
  const log = `第 ${state.turn} 圈：绩效 ${Math.round(prev.performance)} → 结构${direction}（壁垒 ${Math.round(barrier)} · 差异 ${Math.round(differentiation)}），动量 ${Math.round(state.momentum)}。`;
  return { state, log };
}

export function initialState(scenario: ScenarioId = "platform"): ModelState {
  const seed =
    scenario === "platform"
      ? { barrier: 48, differentiation: 42, reinvestment: 55 }
      : scenario === "content"
        ? { barrier: 40, differentiation: 58, reinvestment: 50 }
        : { barrier: 55, differentiation: 46, reinvestment: 62 };
  return { ...deriveState(seed.barrier, seed.differentiation, seed.reinvestment), turn: 0 };
}
