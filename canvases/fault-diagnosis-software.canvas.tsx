import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Swatch,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type TabId = "define" | "arch" | "engine" | "product" | "build";

const TABS: { id: TabId; label: string }[] = [
  { id: "define", label: "功能定义" },
  { id: "arch", label: "系统架构" },
  { id: "engine", label: "诊断引擎" },
  { id: "product", label: "产品模块" },
  { id: "build", label: "实现路径" },
];

export default function FaultDiagnosisSoftware() {
  const [tab, setTab] = useCanvasState<TabId>("diag-sw-tab", "define");

  return (
    <Stack gap={22}>
      <Stack gap={8}>
        <H1>故障诊断功能 · 软件实现方案</H1>
        <Text tone="secondary">
          把上一份「先隔离层次、再取证定责」落成产品能力。诊断不是再做一块大屏，而是围绕故障工单自动收口影响面、给出 L1/L2/L3 假设、挂上证据、输出可执行建议。
        </Text>
      </Stack>

      <Callout tone="info" title="做功能时的一句话">
        监控负责发现，诊断负责隔离和定责，处置负责修复。软件上先做「可解释的隔离引擎 + 诊断工作台」，不要先做黑盒智能根因。
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value="工单" label="诊断的一等对象" />
        <Stat value="拓扑+变更" label="和指标同等重要的输入" />
        <Stat value="假设" label="输出层次与置信度，不是一句根因" />
        <Stat value="只读探针" label="MVP 不自动改配置/换件" />
      </Grid>

      <Row gap={8} wrap>
        {TABS.map((item) => (
          <span key={item.id}>
            <Pill
              active={tab === item.id}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </Pill>
          </span>
        ))}
      </Row>

      <Divider />

      {tab === "define" && <DefineSection />}
      {tab === "arch" && <ArchSection />}
      {tab === "engine" && <EngineSection />}
      {tab === "product" && <ProductSection />}
      {tab === "build" && <BuildSection />}
    </Stack>
  );
}

function DefineSection() {
  return (
    <Stack gap={18}>
      <Stack gap={8}>
        <H2>这个功能到底交付什么</H2>
        <Text>
          用户报障或告警触发后，系统在 30 分钟目标内给出：影响范围、更像哪一层、依据是什么、建议做什么。人确认后进入处置和复盘。设备侧工艺故障可复用同一引擎，但规则包分开，不和产品自身诊断混在一个工单里。
        </Text>
      </Stack>

      <Table
        headers={["能力", "监控大盘", "诊断功能"]}
        rows={[
          ["核心问题", "现在正不正常", "坏在哪一层、凭什么"],
          ["主对象", "指标、设备、服务", "故障工单（Incident）"],
          ["输出", "红绿状态、趋势", "假设 + 证据链 + 建议动作"],
          ["成功标准", "发现得快", "隔离得准、能对外讲清"],
        ]}
      />

      <Stack gap={8}>
        <H3>必须能处理的三类故障</H3>
        <Grid columns={3} gap={12}>
          <Card>
            <CardHeader>可用性</CardHeader>
            <CardBody>
              <Text size="small">
                整柜中断、登录失败、防火墙不通、节点反复重启。
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>性能</CardHeader>
            <CardBody>
              <Text size="small">
                查询变慢、采集积压、交换口拥塞、中间件饱和。
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>数据正确性</CardHeader>
            <CardBody>
              <Text size="small">
                现场有数中心无数、查询到旧数、计算结果偏差。分析产品必须单列，不能只看进程存活。
              </Text>
            </CardBody>
          </Card>
        </Grid>
      </Stack>

      <Callout tone="warning" title="MVP 明确不做">
        不自动改防火墙策略、不自动升级固件、不用大模型直接给「根因结论」。先保证每条结论都能展开成检查项和原始信号，才能对客户和厂商讲得通。
      </Callout>
    </Stack>
  );
}

function ArchLayer({
  title,
  desc,
}: {
  title: string;
  desc: string;
}) {
  const t = useHostTheme();
  return (
    <div
      style={{
        border: `1px solid ${t.stroke.secondary}`,
        borderRadius: 8,
        padding: "12px 14px",
        background: t.fill.tertiary,
      }}
    >
      <Stack gap={4}>
        <Text weight="semibold">{title}</Text>
        <Text size="small" tone="secondary">
          {desc}
        </Text>
      </Stack>
    </div>
  );
}

function ArchSection() {
  const t = useHostTheme();
  return (
    <Stack gap={18}>
      <Stack gap={8}>
        <H2>四层软件结构</H2>
        <Text tone="secondary">
          现场集群与中心平台共用同一套模型；采集在边缘完成，关联和隔离在中心（或站点控制节点）执行。
        </Text>
      </Stack>

      <Stack gap={8}>
        <ArchLayer
          title="1. 采集层"
          desc="服务器 BMC/Redfish、交换机 SNMP/Syslog、防火墙策略与会话、主机指标、应用黄金信号、中间件导出器、部署/配置/固件变更事件。"
        />
        <div
          style={{
            height: 10,
            borderLeft: `2px solid ${t.stroke.primary}`,
            marginLeft: 18,
          }}
        />
        <ArchLayer
          title="2. 信号与拓扑层"
          desc="统一时间轴、CMDB/拓扑（站点-机柜-设备-服务-三方件）、版本基线、变更流。诊断质量取决于这一层，而不是规则写得多花哨。"
        />
        <div
          style={{
            height: 10,
            borderLeft: `2px solid ${t.stroke.primary}`,
            marginLeft: 18,
          }}
        />
        <ArchLayer
          title="3. 诊断引擎"
          desc="影响面收口、层次探针、变更关联、已知问题匹配、假设排序、只读剧本执行。"
        />
        <div
          style={{
            height: 10,
            borderLeft: `2px solid ${t.stroke.primary}`,
            marginLeft: 18,
          }}
        />
        <ArchLayer
          title="4. 诊断工作台"
          desc="故障工单、拓扑着色、证据时间轴、建议动作、诊断包导出、对外口径生成。"
        />
      </Stack>

      <Stack gap={8}>
        <H2>核心对象模型</H2>
        <Text size="small" tone="secondary">
          实现时就按这些对象建表/建主题，避免做成「告警列表 + 跳转大盘」。
        </Text>
        <Table
          headers={["对象", "含义", "关键字段"]}
          rows={[
            [
              "Entity",
              "可被诊断的实体",
              "类型（server/switch/fw/service/middleware）、站点、版本、角色",
            ],
            [
              "Signal",
              "原始或派生信号",
              "时间、实体、层（L1/L2/L3）、严重度、来源",
            ],
            [
              "Change",
              "变更事件",
              "发布、配置、防火墙策略、固件、证书；操作者与窗口",
            ],
            [
              "Incident",
              "一次故障",
              "影响面、开始/恢复时间、当前层次结论、状态机",
            ],
            [
              "Hypothesis",
              "一条假设",
              "层、组件、置信度、支持证据、反对证据、状态",
            ],
            [
              "Evidence",
              "证据条目",
              "信号快照、日志片段、事件码、变更单号、缺陷号",
            ],
            [
              "Check",
              "探针/剧本步骤",
              "只读、超时、所属层、通过/失败/不确定",
            ],
          ]}
          striped
        />
      </Stack>

      <Stack gap={8}>
        <H3>工单状态机</H3>
        <Table
          headers={["状态", "系统做什么", "人做什么"]}
          rows={[
            ["New", "接入告警或人工开单", "确认是否误报"],
            ["Scoping", "按拓扑计算爆炸半径", "校正影响面"],
            ["Probing", "按 L1→L3→L2 跑只读检查", "可跳过或加跑"],
            ["Hypothesized", "给出分层假设与置信度", "采纳/否定/转层"],
            ["Acting", "给出建议，记录执行", "回滚、换件、开厂商单"],
            ["Resolved", "生成证据包与口径", "复盘入库"],
          ]}
          rowTone={["info", "info", "warning", "warning", "success", "success"]}
        />
      </Stack>
    </Stack>
  );
}

function EngineSection() {
  return (
    <Stack gap={18}>
      <Stack gap={8}>
        <H2>引擎怎么隔离层次</H2>
        <Text>
          不要把上一份判定表写成代码里的一长串 if。做成数据化规则包：现象 + 拓扑约束 + 变更约束 → 倾向层次。规则可版本化、可回放、可对客户解释。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H3>推荐流水线（固定顺序）</H3>
        <Table
          headers={["步骤", "输入", "输出", "实现要点"]}
          rows={[
            [
              "1. 症状抽取",
              "告警、健康检查、用户描述",
              "标准化 Symptom",
              "映射到少量症状码，如 NODE_DOWN、NO_NEW_DATA、QUERY_STALE",
            ],
            [
              "2. 影响面",
              "拓扑 + 同类信号",
              "受影响实体集合",
              "同交换机、同柜、同服务、同站点分别聚合，取最小能解释的范围",
            ],
            [
              "3. 变更关联",
              "变更流与故障窗口",
              "可疑变更列表",
              "前后 2 小时窗口；自研发布、防火墙策略、固件、证书分开打标",
            ],
            [
              "4. 层次探针",
              "L1/L3/L2 检查清单",
              "每层通过/失败/未知",
              "默认 L1 连通性 → L3 底座 → L2 自研；有强变更信号可跳转但必须补快检",
            ],
            [
              "5. 假设排序",
              "探针结果 + 规则包",
              "Top 假设及置信度",
              "同时保留反对证据；置信度不够就停在「层已知、组件未知」",
            ],
            [
              "6. 已知问题匹配",
              "版本矩阵 + 缺陷库",
              "可能的缺陷号",
              "型号+版本+症状命中才展示，避免乱推 CVE",
            ],
          ]}
          striped
        />
      </Stack>

      <CollapsibleSection
        title="第一批规则包（直接来自隔离判定表）"
        leading={<Swatch color="blue" />}
        defaultOpen
      >
        <Table
          headers={["症状 / 现象", "规则倾向", "软件上怎么落地"]}
          rows={[
            [
              "单节点宕 + BMC 硬件事件",
              "L1",
              "探针读 BMC 事件；有 ECC/磁盘/温度码则锁定硬件假设",
            ],
            [
              "同交换机多节点同时中断",
              "L1 交换/链路/供电",
              "按拓扑聚合；禁止拆成 N 个主机工单",
            ],
            [
              "仅某功能失败，主机网络正常",
              "L2，核验 L3 中间件",
              "控制面/数据面分开探针，中间件健康作为前置",
            ],
            [
              "紧随自研发布",
              "优先 L2",
              "Change 类型=app_release 提升 L2 权重，仍跑 L1/L3 快检",
            ],
            [
              "内核 panic / 中间件 hang / 证书过期",
              "L3",
              "应用错误只作为表象证据，不单独定自研代码",
            ],
            [
              "现场有数、中心无数",
              "回传链路 / 接入 / 队列",
              "对拍两端数据新鲜度，再查防火墙策略与队列积压",
            ],
            [
              "服务存活但结果错误或过期",
              "L2 计算或 L3 副本/索引",
              "必须有「数据新鲜度/对账」探针，不能只看进程 up",
            ],
          ]}
          striped
        />
      </CollapsibleSection>

      <Stack gap={8}>
        <H3>置信度怎么给（对外可讲）</H3>
        <Table
          headers={["结果", "条件", "界面怎么展示"]}
          rows={[
            [
              "层已锁定",
              "该层探针失败，另外两层快检通过",
              "「更像硬件/软件/三方件」+ 高置信",
            ],
            [
              "组件已锁定",
              "层锁定且单一实体能解释爆炸半径",
              "给出组件名、事件码或变更单",
            ],
            [
              "仅范围已知",
              "多实体同时异常，证据冲突",
              "停在影响面，不编造根因",
            ],
            [
              "证据不足",
              "关键探针超时或无带外数据",
              "列出缺什么数据，而不是给 50% 瞎猜",
            ],
          ]}
        />
      </Stack>

      <Callout tone="neutral" title="探针必须插件化">
        L1/L2/L3 检查做成 Check Plugin：输入实体、输出通过/失败/未知 + 证据。现场无 BMC、无 SNMP 时允许「未知」，引擎要能在数据缺失下降级，而不是报错中断。
      </Callout>
    </Stack>
  );
}

function ProductSection() {
  return (
    <Stack gap={18}>
      <Stack gap={8}>
        <H2>工作台做成哪些页面</H2>
        <Text tone="secondary">
          给值班和现场用，不给领导看大屏。领导口径从工单一键生成。
        </Text>
      </Stack>

      <Table
        headers={["模块", "用户动作", "系统回馈", "优先级"]}
        rows={[
          [
            "开单 / 告警转工单",
            "从告警一键开单或手工报障",
            "带上初始症状、相关实体、最近变更",
            "P0",
          ],
          [
            "影响面视图",
            "看站点/机柜/设备/服务着色",
            "最小能解释的范围，可手工增删",
            "P0",
          ],
          [
            "层次预判条",
            "看 L1/L2/L3 倾向",
            "三层各自通过/失败/未知，可点进探针",
            "P0",
          ],
          [
            "证据时间轴",
            "沿时间核对信号与变更",
            "硬件事件、指标断崖、发布、策略变更对齐",
            "P0",
          ],
          [
            "检查项执行",
            "一键跑只读探针或跳过",
            "每步留下原始结果，可复现",
            "P0",
          ],
          [
            "建议与闭环",
            "采纳建议、填处置、关单",
            "回滚/换件/开厂商单/加白名单，分临时和永久",
            "P1",
          ],
          [
            "诊断包导出",
            "给客户或厂商",
            "时间线、影响面、层次结论、证据、缺陷号",
            "P1",
          ],
          [
            "已知问题库",
            "按型号+版本检索",
            "命中才展示，链到规避措施",
            "P1",
          ],
          [
            "口径生成",
            "复制五问口径",
            "发生了什么 / 哪一层 / 依据 / 正在做 / 需配合",
            "P1",
          ],
        ]}
        striped
      />

      <Stack gap={8}>
        <H3>主界面信息架构（一张工单页）</H3>
        <Table
          headers={["区域", "内容"]}
          rows={[
            ["顶栏", "严重度、持续时间、影响站点/功能、当前层次结论"],
            ["左：拓扑", "爆炸半径着色，点击实体看该实体探针"],
            ["中：假设列表", "Top 假设、置信度、支持/反对证据"],
            ["右：时间轴", "信号 + 变更，可刷选故障窗口"],
            ["底：检查与动作", "未跑探针、建议动作、导出"],
          ]}
        />
      </Stack>

      <Callout tone="info" title="和现有监控怎么切">
        监控页继续管「看状态」；点某条严重告警「开始诊断」才进入工单。不要在诊断页再堆一排图表，图表只作为证据卡片出现。
      </Callout>
    </Stack>
  );
}

function BuildSection() {
  return (
    <Stack gap={18}>
      <Stack gap={8}>
        <H2>实现路径</H2>
        <Text>
          按「先能开单和填清单，再自动隔离，最后才匹配已知问题」推进。规则包与采集插件分开发，避免等齐所有硬件协议再上线。
        </Text>
      </Stack>

      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Text size="small">MVP</Text>}>
            能开单、能隔离
          </CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text size="small">告警转工单 + 手工开单</Text>
              <Text size="small">拓扑爆炸半径（站点/柜/交换/服务）</Text>
              <Text size="small">L1/L2/L3 清单自动回填已有信号</Text>
              <Text size="small">证据时间轴（指标断点 + 变更）</Text>
              <Text size="small">五问口径草稿</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Text size="small">V1</Text>}>
            能自动预判
          </CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text size="small">规则包驱动的层次置信度</Text>
              <Text size="small">只读探针插件（BMC、SNMP、应用健康、中间件、证书）</Text>
              <Text size="small">数据新鲜度/对账探针</Text>
              <Text size="small">诊断包导出</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Text size="small">V2</Text>}>
            能复用、能协同
          </CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text size="small">已知问题库与厂商缺陷号</Text>
              <Text size="small">有限的可逆动作（主从切换、流量改切）</Text>
              <Text size="small">同一引擎挂设备诊断规则包</Text>
              <Text size="small">跨站点模式沉淀</Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={8}>
        <H2>采集最小集（没有这些，引擎会瞎）</H2>
        <Table
          headers={["层", "MVP 必接", "可以后补"]}
          rows={[
            [
              "L1",
              "BMC 事件、服务器在线、交换端口 up/CRC、防火墙 HA/会话",
              "光功率趋势、精细环境量",
            ],
            [
              "L2",
              "服务健康、API 错误率、采集延迟、查询失败、License 状态、发布事件",
              "全链路追踪",
            ],
            [
              "L3",
              "节点 CPU/内存/磁盘、DB/队列存活与积压、证书到期、组件版本",
              "内核连续剖析、厂商专有 Agent",
            ],
            [
              "横切",
              "CMDB 关系、变更单（发布/策略/固件）",
              "自动发现补全",
            ],
          ]}
          striped
        />
      </Stack>

      <Stack gap={8}>
        <H3>工程约束</H3>
        <Table
          headers={["项", "建议"]}
          rows={[
            [
              "规则与代码分离",
              "判定表以 YAML/JSON 规则包发布，引擎只解释执行",
            ],
            [
              "探针只读",
              "MVP/V1 禁止写配置；写操作单独开权限和审计",
            ],
            [
              "可回放",
              "工单保存当时信号切片，事后能按同一规则包重跑",
            ],
            [
              "数据缺失显式化",
              "「未知」是合法结果，进入证据包，促使补采集",
            ],
            [
              "边缘与中心",
              "现场可离线完成 L1 快检；完整关联在中心或站点控制节点",
            ],
          ]}
        />
      </Stack>

      <Callout tone="success" title="对外可承诺的软件结果">
        值班从告警点「开始诊断」进入工单；系统自动给出影响面和三层预判；每一条结论都能点开证据；导出的诊断包可直接给客户或厂商，而不再是聊天记录和截图拼盘。
      </Callout>
    </Stack>
  );
}
