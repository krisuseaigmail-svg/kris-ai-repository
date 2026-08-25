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
  UsageBar,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type TabId = "overview" | "layers" | "isolation" | "scenarios" | "rollout";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "策略总览" },
  { id: "layers", label: "分层方案" },
  { id: "isolation", label: "隔离判定" },
  { id: "scenarios", label: "典型场景" },
  { id: "rollout", label: "落地与机制" },
];

export default function FaultDiagnosisStrategy() {
  const [tab, setTab] = useCanvasState<TabId>("briefing-tab", "overview");

  return (
    <Stack gap={22}>
      <Stack gap={8}>
        <H1>数据中心与分析产品 · 自身故障诊断策略</H1>
        <Text tone="secondary">
          面向边缘集群 + 中心分析平台的一体交付。诊断对象是产品自身（服务器、交换机、防火墙、自研软件、三方件），不是客户被管设备。颗粒度定位：能对外讲清「先判哪一层、凭什么、谁负责」，不展开到命令级 runbook。
        </Text>
      </Stack>

      <Callout tone="info" title="一句话策略">
        先收口影响面，再隔离层次，后取证定责。硬件、自研软件、三方件必须分开判定；未完成层次隔离前，不并行换件、回滚和升级三方件。
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value="3 层" label="硬件 / 自研软件 / 三方件" />
        <Stat value="4 步" label="影响面 → 隔离 → 根因 → 闭环" />
        <Stat value="30 min" label="P1 层次隔离时间盒" tone="info" />
        <Stat value="3 类" label="可用性 · 性能 · 数据正确性" />
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

      {tab === "overview" && <OverviewSection />}
      {tab === "layers" && <LayersSection />}
      {tab === "isolation" && <IsolationSection />}
      {tab === "scenarios" && <ScenariosSection />}
      {tab === "rollout" && <RolloutSection />}
    </Stack>
  );
}

function OverviewSection() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H2>诊断管什么、不管什么</H2>
        <Text>
          本策略覆盖现场售卖集群与集团中心分析平台的自身故障：整柜中断、查询失败、无新数据、数不对、升级后回退、License/证书失效。客户产线设备的工艺/传感器故障走产品内的设备诊断能力，不与本文混用同一套路径。
        </Text>
      </Stack>

      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Text size="small">L1</Text>}>
            硬件层
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                计算/存储服务器、接入与汇聚交换机、防火墙、光模块与线缆、电源与散热。
              </Text>
              <Text size="small" tone="secondary">
                问题形态：单点损坏、链路误码、整柜掉电、防火墙 HA 异常。
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Text size="small">L2</Text>}>
            自研软件层
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                采集接入、分析计算、存储检索、可视化、权限与 License、系统自监控、现场工具与发布配置。
              </Text>
              <Text size="small" tone="secondary">
                问题形态：功能失败、积压、错误发布、配置漂移、监控盲区。
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Text size="small">L3</Text>}>
            三方件层
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                OS/内核、固件与驱动、容器编排、数据库/消息队列/对象存储、安全套件、厂商 Agent。
              </Text>
              <Text size="small" tone="secondary">
                问题形态：内核恐慌、中间件脑裂、驱动丢包、证书过期、已知缺陷。
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={10}>
        <H2>四步漏斗</H2>
        <Text tone="secondary" size="small">
          每一步都有退出条件：证据足够就停止发散，避免「全层一起查」。
        </Text>
        <Grid columns={4} gap={16}>
          <FunnelStep
            n="1"
            title="定影响面"
            desc="单节点、单柜、单集群、单站点，还是中心平台某功能。先回答「谁不能用」。"
          />
          <FunnelStep
            n="2"
            title="定层次"
            desc="按连通性 → 三方件基线 → 自研服务的顺序隔离。先回答「坏在哪一层」。"
          />
          <FunnelStep
            n="3"
            title="定根因"
            desc="层内按清单取证：硬件事件码、变更窗口、版本矩阵、缺陷公告。先回答「凭什么」。"
          />
          <FunnelStep
            n="4"
            title="定闭环"
            desc="临时恢复、永久修复、厂商协同、复盘入库。先回答「何时恢复、如何防再发」。"
          />
        </Grid>
      </Stack>

      <Stack gap={8}>
        <H2>三条原则</H2>
        <Table
          headers={["原则", "含义", "对外价值"]}
          rows={[
            [
              "先范围后细节",
              "影响面未收口，不进入单机深挖",
              "避免把局部故障说成全站事故",
            ],
            [
              "先隔离后深挖",
              "层次未判定，不换件、不回滚、不升三方件",
              "减少误伤，缩短无效排查",
            ],
            [
              "先证据后定责",
              "结论必须对应日志/指标/硬件事件/缺陷号",
              "对客户和厂商可辩护，不靠猜测",
            ],
          ]}
        />
      </Stack>

      <Callout tone="neutral" title="分析产品多看一维">
        除可用性和性能外，必须把「数据正确性」单列：采集断了、算错了、查到的是旧数，对分析产品都是故障，不能只按服务是否存活来结案。
      </Callout>
    </Stack>
  );
}

function FunnelStep({
  n,
  title,
  desc,
}: {
  n: string;
  title: string;
  desc: string;
}) {
  const t = useHostTheme();
  return (
    <Stack gap={8}>
      <Row gap={8} align="center">
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 11,
            background: t.accent.primary,
            color: t.text.onAccent,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          {n}
        </div>
        <Text weight="semibold">{title}</Text>
      </Row>
      <Text size="small" tone="secondary">
        {desc}
      </Text>
    </Stack>
  );
}

function LayersSection() {
  return (
    <Stack gap={16}>
      <Stack gap={6}>
        <H2>分层诊断方案</H2>
        <Text tone="secondary">
          每层只回答四个问题：查什么对象、看什么信号、如何下结论、下一步动作。细节命令放现场手册，不进汇报材料。
        </Text>
      </Stack>

      <CollapsibleSection
        title="L1 硬件：服务器 / 交换机 / 防火墙"
        leading={<Swatch color="orange" />}
        defaultOpen
      >
        <Stack gap={10}>
          <Text size="small" tone="secondary">
            默认顺序：供电与环境 → 带外管理 → 交换链路 → 防火墙会话/策略 → 主机硬件子系统。单节点优先看主机；同交换机下多节点同时中断，优先看交换与上联。
          </Text>
          <Table
            headers={["检查域", "关键信号", "如何判定", "动作"]}
            rows={[
              [
                "带外管理",
                "BMC 可达、传感器、硬件事件日志",
                "BMC 不通多为电源或管理网；有内存/磁盘/温度事件则属硬件",
                "现场确认，开硬件工单或换件",
              ],
              [
                "计算与存储节点",
                "ECC、磁盘 SMART/RAID、网卡协商、PCIe",
                "单盘 vs 阵列降级 vs 整机下线，三者处置不同",
                "热备切换、降级运行或更换",
              ],
              [
                "交换机",
                "端口状态、CRC/光功率、STP/MLAG、设备 CPU",
                "单口、级联、整机故障要分开，避免误换服务器",
                "换光模块/线缆/整机，保留配置备份",
              ],
              [
                "防火墙",
                "HA 状态、会话表、策略命中、吞吐与丢弃",
                "策略误配、会话耗尽、HA 脑裂是三类不同根因",
                "回退策略、扩容会话、修复 HA",
              ],
              [
                "供电与散热",
                "PSU 冗余、进风温度、风扇转速",
                "环境问题与硬件损坏分开，避免反复换件",
                "机房协同或更换电源/风扇",
              ],
            ]}
            striped
          />
        </Stack>
      </CollapsibleSection>

      <CollapsibleSection
        title="L2 自研软件：平台 / 分析 / 运维应用"
        leading={<Swatch color="blue" />}
        defaultOpen
      >
        <Stack gap={10}>
          <Text size="small" tone="secondary">
            先分控制面还是数据面：登录/权限/License/配置属控制面；采集、计算、查询、可视化属数据面。分析产品必须额外验证「有没有数、数是否延迟、数是否正确」。
          </Text>
          <Table
            headers={["检查域", "关键信号", "如何判定", "动作"]}
            rows={[
              [
                "控制面",
                "API 错误率、认证失败、License 状态",
                "基础设施正常但全站不可配置/不可登录，优先控制面",
                "回滚配置、续期 License、修复认证",
              ],
              [
                "数据接入",
                "采集延迟、丢失率、位点/积压",
                "现场有数、中心无数，多在接入或回传链路",
                "重放、扩容接入、检查回传策略",
              ],
              [
                "分析与查询",
                "任务失败率、查询 P95、引擎饱和",
                "写入正常但查询失败，多在计算或索引",
                "限流、重建索引、隔离热点查询",
              ],
              [
                "发布与配置",
                "变更窗口、版本一致性、配置漂移",
                "故障紧随发布，默认先回滚再争论",
                "回滚、冻结变更、对比差异",
              ],
              [
                "自监控",
                "探针覆盖、告警静默、仪表盘空白",
                "监控自己挂了会造成「看起来没事」",
                "先恢复可观测，再继续诊断",
              ],
            ]}
            striped
          />
        </Stack>
      </CollapsibleSection>

      <CollapsibleSection
        title="L3 三方件：OS / 中间件 / 固件驱动 / 安全套件"
        leading={<Swatch color="purple" />}
        defaultOpen
      >
        <Stack gap={10}>
          <Text size="small" tone="secondary">
            三方件是最容易被误判成「自研 bug」的一层。判定关键是：是否偏离版本基线、组件自身健康是否已坏、是否命中厂商已知缺陷。
          </Text>
          <Table
            headers={["检查域", "关键信号", "如何判定", "动作"]}
            rows={[
              [
                "OS / 内核",
                "dmesg、OOM、文件系统只读、内核版本",
                "panic、OOM killer、驱动报错优先归本层",
                "规避参数、内核热补丁或计划升级",
              ],
              [
                "中间件",
                "复制延迟、连接数、锁等待、集群角色",
                "数据库/队列/对象存储自身不健康，应用错误只是表象",
                "主从切换、扩容、修复脑裂",
              ],
              [
                "固件与驱动",
                "版本矩阵、网卡/RAID/BMC 日志、厂商公告",
                "特定型号+特定版本复现，高度疑似固件缺陷",
                "走厂商 TAC，按批准矩阵升级",
              ],
              [
                "安全与证书",
                "拦截日志、证书有效期、策略变更",
                "升级后「连不上」常是证书或安全软件误拦",
                "更新证书、加白名单、回退安全策略",
              ],
              [
                "编排与运行时",
                "节点 Ready、调度失败、镜像拉取、存储卷",
                "容器层异常时，业务探针失败不能直接定自研代码",
                "恢复节点、修复存储类、对齐镜像仓库",
              ],
            ]}
            striped
          />
        </Stack>
      </CollapsibleSection>
    </Stack>
  );
}

function IsolationSection() {
  return (
    <Stack gap={18}>
      <Stack gap={6}>
        <H2>跨层隔离：这是整套策略的核心</H2>
        <Text>
          对外最需要讲清楚的不是「我们会查日志」，而是：如何在 30 分钟内证明故障属于哪一层，从而决定换件、回滚还是开厂商工单。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H3>默认顺序与快捷跳转</H3>
        <Text size="small" tone="secondary">
          默认走 L1 连通性 → L3 底座 → L2 自研。原因：机器不通时软件诊断无意义；中间件挂了时应用错误是表象。若故障紧随自研发布且基础设施绿灯，可直接进入 L2，但必须补做一次 L1/L3 快检以免误判。
        </Text>
        <Table
          headers={["时间盒", "动作", "退出条件"]}
          rows={[
            ["T+0", "定级（P1/P2/P3），指定事件指挥官", "有唯一负责人"],
            ["T+5", "收口影响面：站点 / 集群 / 功能 / 数据是否停更", "范围图可对外陈述"],
            ["T+10", "L1 快检：带外、交换、防火墙、供电", "连通性排除或坐实硬件"],
            ["T+20", "L3 快检：OS、中间件、证书、版本基线", "底座排除或坐实三方件"],
            ["T+30", "L2 深挖：控制面/数据面、近期变更、数据正确性", "给出层次结论与证据"],
          ]}
          rowTone={["info", "info", "warning", "warning", "success"]}
        />
      </Stack>

      <Stack gap={8}>
        <H3>现象到层次的判定表</H3>
        <Table
          headers={["观察到的现象", "更像 L1", "更像 L2", "更像 L3"]}
          rows={[
            ["单节点宕机，BMC 有硬件事件", "是", "否", "偶发：固件"],
            ["同交换机下多节点同时中断", "交换/链路/供电", "否", "否"],
            ["仅某业务功能失败，主机与网络正常", "否", "是", "视中间件"],
            ["紧随自研版本发布", "否", "优先", "若同时升了三方件"],
            ["内核 panic / 中间件 hang / 证书过期", "否", "表象", "是"],
            ["全站不可达，但 BMC 正常", "交换或防火墙", "否", "路由/隧道组件"],
            ["现场有数、中心无数", "回传链路/防火墙策略", "接入任务", "消息队列/对象存储"],
            ["服务存活，但查询结果错误或过期", "否", "计算/同步逻辑", "副本延迟/索引损坏"],
          ]}
          striped
        />
      </Stack>

      <Callout tone="warning" title="隔离未完成时禁止的动作">
        不并行换硬盘、回滚应用、升级固件。三件事同时做会毁掉证据链，事后无法对客户和厂商定责。临时恢复只能用可逆手段（主从切换、流量改切、只读降级）。
      </Callout>

      <Stack gap={8}>
        <H3>对外口径模板</H3>
        <Table
          headers={["必须回答", "示例口径"]}
          rows={[
            ["发生了什么", "A 站点边缘集群采集中断 40 分钟，中心平台该站点无新数据"],
            ["判定在哪一层", "当前排除服务器硬件，偏向防火墙策略在变更窗口被改动"],
            ["依据是什么", "BMC 无硬件事件；交换机端口正常；防火墙策略命中日志与变更单时间对齐"],
            ["正在做什么", "回退该策略，采集已恢复；保留包与日志待确认无误拦"],
            ["需要谁配合", "客户侧确认窗口内是否有并行安全策略下发；必要时开防火墙厂商工单"],
          ]}
        />
      </Stack>
    </Stack>
  );
}

function ScenariosSection() {
  return (
    <Stack gap={16}>
      <Stack gap={6}>
        <H2>六类典型场景</H2>
        <Text tone="secondary">
          用于汇报时举例：每类只给「首选隔离路径 + 常见根因 + 对外怎么说」，不展开操作步骤。
        </Text>
      </Stack>

      <Table
        headers={["场景", "首选隔离", "常见根因", "对外怎么说"]}
        rows={[
          [
            "边缘集群整柜业务中断",
            "先供电与上联交换，再防火墙 HA，最后主机",
            "上联中断、整柜掉电、防火墙会话表打满",
            "先讲影响柜数，再讲已排除/未排除的层",
          ],
          [
            "中心分析无新数据或查询失败",
            "先问现场是否有数，再查回传与中心数据面",
            "接入积压、队列堵塞、查询引擎饱和",
            "区分「没采到」和「采到了查不出」",
          ],
          [
            "数台服务器反复重启或性能断崖",
            "BMC 事件 → 内存/磁盘/温度 → 内核/驱动",
            "ECC、磁盘阵列、固件缺陷、内核 OOM",
            "未拿到硬件事件前，不承诺换机或改代码",
          ],
          [
            "网络变更后部分站点掉线",
            "对变更单做差分，查交换 ACL 与防火墙策略",
            "策略误配、NAT/会话、HA 切换不对称",
            "明确是变更引入，给回退时间而不是扩硬件",
          ],
          [
            "升级后功能异常",
            "先对版本矩阵：自研、OS、中间件、固件谁变了",
            "自研回归缺陷、三方件不兼容、证书未更新",
            "能回滚先回滚；层次不清时不把锅先甩研发",
          ],
          [
            "看起来活着，功能「假死」",
            "License、证书、权限策略、自监控是否静默",
            "授权过期、证书失效、权限误配、告警被静音",
            "这是控制面问题，不是算力不够",
          ],
        ]}
        striped
      />

      <Callout tone="info" title="现场与中心要分开陈述">
        同一表面现象，根因可能在现场集群、回传路径或中心平台。汇报时强制写清故障域，避免把边缘问题说成中心能力不足，或相反。
      </Callout>
    </Stack>
  );
}

function RolloutSection() {
  return (
    <Stack gap={18}>
      <Stack gap={6}>
        <H2>机制与落地</H2>
        <Text>
          策略要能运转，取决于三件事：有人拍板层次结论、有统一证据包、有分阶段补齐的可观测能力。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H3>P1 首小时时间盒（规划值，非历史统计）</H3>
        <UsageBar
          total={60}
          topLeftLabel="影响面 8′ · 层次隔离 22′ · 层内取证 20′ · 恢复与同步 10′"
          topRightLabel="60 分钟"
          segments={[
            { id: "scope", value: 8, color: "gray" },
            { id: "isolate", value: 22, color: "blue" },
            { id: "dig", value: 20, color: "orange" },
            { id: "fix", value: 10, color: "green" },
          ]}
        />
        <Text size="small" tone="secondary">
          层次隔离占最大头，是刻意设计：这一步错了，后面全是浪费。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>谁负责什么</H2>
        <Table
          headers={["活动", "现场/基础设施", "平台研发", "分析应用", "厂商窗口", "事件指挥官"]}
          rows={[
            ["层次隔离结论", "配合", "配合", "配合", "知情", "负责"],
            ["L1 深挖与换件", "负责", "配合", "知情", "配合", "拍板"],
            ["L2 深挖与回滚", "知情", "负责", "负责", "知情", "拍板"],
            ["L3 深挖与升级", "配合", "负责", "配合", "负责", "拍板"],
            ["对外口径", "提供事实", "提供事实", "提供事实", "知情", "负责"],
          ]}
        />
        <Text size="small" tone="secondary">
          事件指挥官对「坏在哪一层」负责，不对每一层的专业细节负责。层次争论未决时，由其冻结发散动作。
        </Text>
      </Stack>

      <Stack gap={10}>
        <H2>分阶段落地</H2>
        <Grid columns={3} gap={12}>
          <Card>
            <CardHeader trailing={<Text size="small">0–1 月</Text>}>
              先能判定
            </CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text size="small">三层检查清单与报障模板</Text>
                <Text size="small">P1 升级路径和指挥官值班</Text>
                <Text size="small">变更窗口与版本矩阵对齐</Text>
                <Text size="small">对外口径五问纳入值班</Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Text size="small">1–3 月</Text>}>
              证据可追
            </CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text size="small">硬件事件、软件黄金信号、三方件日志对齐同一时间轴</Text>
                <Text size="small">现场/中心诊断包标准目录</Text>
                <Text size="small">已批准固件/中间件基线库</Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Text size="small">3–6 月</Text>}>
              预判可复用
            </CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text size="small">告警自动给出层次预判</Text>
                <Text size="small">已知问题库对接厂商缺陷号</Text>
                <Text size="small">季度故障演练（整柜中断、无数据、升级回退）</Text>
              </Stack>
            </CardBody>
          </Card>
        </Grid>
      </Stack>

      <Stack gap={8}>
        <H3>结案最低证据包</H3>
        <Table
          headers={["条目", "要求"]}
          rows={[
            ["时间线", "发现、隔离、恢复三个时间点，精确到分钟"],
            ["影响面", "站点/集群/功能/数据是否停更，有无客户业务中断"],
            ["层次结论", "L1 / L2 / L3 / 交叉，附 1–3 条证据"],
            ["措施", "临时措施与永久措施分开写，写明是否可逆"],
            ["协同", "客户窗口、厂商单号、是否需要换件或升级"],
          ]}
        />
      </Stack>

      <Callout tone="success" title="汇报时建议强调的三个结果">
        一是有标准隔离方法，不再把「产品故障」混为一谈；二是 30 分钟内能给出可对外的层次结论；三是硬件换件、软件回滚、三方件升级三条路径有明确触发条件，避免现场拍脑袋。
      </Callout>
    </Stack>
  );
}
