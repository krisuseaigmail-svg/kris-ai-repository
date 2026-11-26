import { useEffect, useMemo, useRef, useState } from "react";
import {
  SCENARIOS,
  type LogEntry,
  type ModelState,
  type NodeKey,
  type ScenarioId,
  deriveState,
  initialState,
  stepTurn,
} from "./model";

const NODE_ORDER: NodeKey[] = ["structure", "conduct", "performance"];

function makeLog(turn: number, text: string): LogEntry {
  return {
    id: `${turn}-${Math.random().toString(36).slice(2, 9)}`,
    turn,
    text,
  };
}

function App() {
  const [scenarioId, setScenarioId] = useState<ScenarioId>("platform");
  const [state, setState] = useState<ModelState>(() => initialState("platform"));
  const [activeNode, setActiveNode] = useState<NodeKey>("structure");
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([
    makeLog(0, "闭环待命：调节杠杆后，点「推动一圈」观察绩效如何回灌结构。"),
  ]);
  const timerRef = useRef<number | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  const scenario = SCENARIOS[scenarioId];

  const nodeCopy = useMemo(
    () => ({
      structure: {
        kicker: "Structure",
        title: "结构",
        body: scenario.structureLabel,
        value: state.structure,
      },
      conduct: {
        kicker: "Conduct",
        title: "行为",
        body: scenario.conductLabel,
        value: state.conduct,
      },
      performance: {
        kicker: "Performance",
        title: "绩效",
        body: scenario.performanceLabel,
        value: state.performance,
      },
    }),
    [scenario, state],
  );

  function advanceTurn() {
    const prev = stateRef.current;
    const { state: next, log } = stepTurn(prev);
    stateRef.current = next;
    setState(next);
    setActiveNode((node) => {
      const idx = NODE_ORDER.indexOf(node);
      return NODE_ORDER[(idx + 1) % NODE_ORDER.length];
    });
    setLogs((old) => [makeLog(next.turn, log), ...old].slice(0, 8));
  }

  useEffect(() => {
    if (!running) {
      if (timerRef.current) window.clearInterval(timerRef.current);
      timerRef.current = null;
      return;
    }

    timerRef.current = window.setInterval(() => {
      advanceTurn();
    }, 1400);

    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [running]);

  function switchScenario(id: ScenarioId) {
    setRunning(false);
    setScenarioId(id);
    const next = initialState(id);
    stateRef.current = next;
    setState(next);
    setActiveNode("structure");
    setLogs([
      makeLog(
        0,
        `已切换到「${SCENARIOS[id].label}」：经典 SCP 是 S→C→P；正向反馈补上 P→S 的回灌。`,
      ),
    ]);
  }

  function updateLever(
    key: "barrier" | "differentiation" | "reinvestment",
    value: number,
  ) {
    setRunning(false);
    setState((prev) => {
      const patched = { ...prev, [key]: value };
      const derived = deriveState(
        patched.barrier,
        patched.differentiation,
        patched.reinvestment,
        prev.momentum,
      );
      const next = { ...derived, turn: prev.turn };
      stateRef.current = next;
      return next;
    });
  }

  function pushOnce() {
    setRunning(false);
    advanceTurn();
  }

  function resetModel() {
    setRunning(false);
    const next = initialState(scenarioId);
    stateRef.current = next;
    setState(next);
    setActiveNode("structure");
    setLogs([makeLog(0, "模型已重置。试着提高再投入，观察飞轮是否加速。")]);
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-orb" aria-hidden="true" />
        <h1 className="brand">
          SC<span>P</span>
        </h1>
        <h2>把结构—行为—绩效拧成正向反馈飞轮</h2>
        <p className="hero-lead">
          经典 SCP 解释市场怎么约束企业；正向反馈补上最后一环：强绩效如何抬高壁垒，再改写下一轮行为。
        </p>
        <div className="cta-row">
          <a className="btn btn-primary" href="#lab">
            进入飞轮实验台
          </a>
          <a className="btn btn-ghost" href="#examples">
            看三条闭环
          </a>
        </div>
      </header>

      <section className="section" id="lab">
        <div className="section-head">
          <h3>飞轮实验台</h3>
          <p>
            调节三个杠杆，观察 Structure → Conduct → Performance，以及绩效回灌结构的动量。正反馈放大方向——可以加速增长，也可以放大衰退。
          </p>
        </div>

        <div className="scenario-row" role="tablist" aria-label="场景">
          {(Object.keys(SCENARIOS) as ScenarioId[]).map((id) => (
            <button
              key={id}
              type="button"
              className={`chip${scenarioId === id ? " active" : ""}`}
              onClick={() => switchScenario(id)}
            >
              {SCENARIOS[id].label}
            </button>
          ))}
        </div>

        <div className="flywheel">
          <div className="loop-stage" aria-live="polite">
            <svg className="loop-svg" viewBox="0 0 100 100" aria-hidden="true">
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="4"
                  markerHeight="4"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#1f7a5c" />
                </marker>
              </defs>
              <path
                d="M 28 28 C 48 8, 78 18, 78 38"
                fill="none"
                stroke="#1f7a5c"
                strokeWidth="0.7"
                markerEnd="url(#arrow)"
                opacity="0.55"
              />
              <path
                d="M 78 42 C 86 62, 68 82, 52 78"
                fill="none"
                stroke="#1f7a5c"
                strokeWidth="0.7"
                markerEnd="url(#arrow)"
                opacity="0.55"
              />
              <path
                d="M 48 78 C 28 78, 16 58, 24 36"
                fill="none"
                stroke="#d97706"
                strokeWidth="0.85"
                strokeDasharray="2 1.4"
                markerEnd="url(#arrow)"
                opacity="0.8"
              />
            </svg>

            <div className={`node s${activeNode === "structure" ? " active" : ""}`}>
              <span className="node-kicker">{nodeCopy.structure.kicker}</span>
              <h4>{nodeCopy.structure.title}</h4>
              <p>{nodeCopy.structure.body}</p>
              <div className="node-meter">
                <span style={{ width: `${nodeCopy.structure.value}%` }} />
              </div>
            </div>

            <div className={`node c${activeNode === "conduct" ? " active" : ""}`}>
              <span className="node-kicker">{nodeCopy.conduct.kicker}</span>
              <h4>{nodeCopy.conduct.title}</h4>
              <p>{nodeCopy.conduct.body}</p>
              <div className="node-meter">
                <span style={{ width: `${nodeCopy.conduct.value}%` }} />
              </div>
            </div>

            <div className={`node p${activeNode === "performance" ? " active" : ""}`}>
              <span className="node-kicker">{nodeCopy.performance.kicker}</span>
              <h4>{nodeCopy.performance.title}</h4>
              <p>{nodeCopy.performance.body}</p>
              <div className="node-meter">
                <span style={{ width: `${nodeCopy.performance.value}%` }} />
              </div>
            </div>

            <div className="feedback-badge">{scenario.feedbackLabel}</div>
          </div>

          <aside className="panel">
            <h4>{scenario.label}</h4>
            <p className="hint">{scenario.blurb}</p>

            <div className="stats">
              <div className="stat">
                <label>结构强度</label>
                <strong>{Math.round(state.structure)}</strong>
              </div>
              <div className="stat">
                <label>行为力度</label>
                <strong>{Math.round(state.conduct)}</strong>
              </div>
              <div className="stat">
                <label>飞轮动量</label>
                <strong>{Math.round(state.momentum)}</strong>
              </div>
            </div>

            <label className="control">
              <header>
                <span>{scenario.levers.barrier}</span>
                <span>{Math.round(state.barrier)}</span>
              </header>
              <input
                type="range"
                min={0}
                max={100}
                value={state.barrier}
                onChange={(e) => updateLever("barrier", Number(e.target.value))}
              />
            </label>

            <label className="control">
              <header>
                <span>{scenario.levers.differentiation}</span>
                <span>{Math.round(state.differentiation)}</span>
              </header>
              <input
                type="range"
                min={0}
                max={100}
                value={state.differentiation}
                onChange={(e) =>
                  updateLever("differentiation", Number(e.target.value))
                }
              />
            </label>

            <label className="control">
              <header>
                <span>{scenario.levers.reinvestment}</span>
                <span>{Math.round(state.reinvestment)}</span>
              </header>
              <input
                type="range"
                min={0}
                max={100}
                value={state.reinvestment}
                onChange={(e) =>
                  updateLever("reinvestment", Number(e.target.value))
                }
              />
            </label>

            <div className="cta-row">
              <button type="button" className="btn btn-primary" onClick={pushOnce}>
                推动一圈
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setRunning((v) => !v)}
              >
                {running ? "暂停自动" : "自动飞轮"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={resetModel}>
                重置
              </button>
            </div>

            <div className="log" aria-label="飞轮日志">
              {logs.map((item) => (
                <div className="log-item" key={item.id}>
                  <time>T{item.turn}</time>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </section>

      <section className="section" id="examples">
        <div className="section-head">
          <h3>三条可验证的闭环</h3>
          <p>
            真正的正向反馈不是把优点排成圆圈，而是每一环的输出必须成为下一环可验证的输入。
          </p>
        </div>
        <div className="examples">
          {(Object.keys(SCENARIOS) as ScenarioId[]).map((id) => {
            const item = SCENARIOS[id];
            return (
              <article className="example" key={id}>
                <h4>{item.label}</h4>
                <p>{item.blurb}</p>
                <div className="chain">
                  {item.chain.map((line) => (
                    <div key={line}>
                      <span>→</span> {line}
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <p className="footer-note">
        SCP（Structure–Conduct–Performance）源自哈佛学派产业组织分析。本页把后期补上的反馈箭头做成可交互飞轮：绩效改善抬高壁垒与差异化，再约束下一轮行为——这就是「SCP 正向反馈模型」的核心。
      </p>
    </div>
  );
}

export default App;
