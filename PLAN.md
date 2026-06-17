# 课程项目计划

## 候选可验证环境

### 1. WeightedIntervalScheduling
- 任务描述：给定 `N` 个带权区间 `[l_i, r_i]` 和对应权重 `w_i`，选择若干两两不重叠的区间，使总权重最大。
- 输出形式：输出一个整数，表示最大总权重。
- 可验证性：标准做法是先按区间结束位置排序，再用动态规划求最优值，验证成本低且结果唯一。
- 难度控制：
  - 区间数量 `N`
  - 坐标范围
  - 区间重叠密度
  - 权重范围

### 2. EditDistance
- 任务描述：给定两个字符串 `S` 和 `T`，计算把 `S` 变成 `T` 所需的最少编辑次数。允许的操作包括插入、删除和替换。
- 输出形式：输出一个整数，表示最小编辑距离。
- 可验证性：可用经典的 `O(|S||T|)` 动态规划精确计算，验证稳定直接。
- 难度控制：
  - 字符串 `S` 的长度
  - 字符串 `T` 的长度
  - 字符集大小
  - 两个字符串之间的扰动强度

### 3. CoinChange
- 任务描述：给定若干硬币面额和目标金额，计算凑出目标金额所需的最少硬币数；如果无法凑出，则输出 `-1`。
- 输出形式：输出一个整数，表示最少硬币数，或 `-1`。
- 可验证性：可用标准完全背包 / 动态规划精确求解，验证简单明确。
- 难度控制：
  - 硬币种类数
  - 目标金额大小
  - 面额范围
  - 是否保证有解

### 4. LongestCommonSubsequence
- 任务描述：给定两个字符串 `S` 和 `T`，计算它们的最长公共子序列长度。
- 输出形式：输出一个整数，表示最长公共子序列长度。
- 可验证性：可用标准二维动态规划精确计算，验证开销低。
- 难度控制：
  - 字符串 `S` 的长度
  - 字符串 `T` 的长度
  - 字符集大小
  - 两个字符串的相似程度

## 为什么选择这四个环境
- 这四个环境都可以用精确的多项式时间算法求解，天然适合作为 verifiable environment。
- 四个环境都可以把答案设计成短整数输出，便于答案抽取和自动打分。
- 四个环境都可以构造出清晰的单调难度变化，适合比较 `static difficulty` 和 `adaptive difficulty`。
- 与当前仓库已有环境相比，这四个环境与现有题目的直接重合度较低，尤其比网格最短路类环境更适合作为新增候选。

## 预期实验使用方式
- 训练环境：从这 4 个环境中选 3 个用于 RL 训练。
- Held-out 环境：保留 1 个环境，在训练阶段完全不使用，只在最终评估时测试泛化能力。
- Static difficulty：训练时对每个环境使用固定难度，不随模型表现变化。
- Adaptive difficulty：当模型在某个环境上的近期正确率超过阈值时，自动提升该环境难度。

## 课程项目三个落点的对应方案

### 落点 1：设计 3-5 个 verifiable envs
- 本项目最终设计 4 个新环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
  - `LongestCommonSubsequence`
- 每个环境都需要实现以下内容：
  - `generator()`：按随机种子和难度参数生成题目实例
  - `prompt_generator()`：把题目实例转换为模型输入 prompt
  - `_process()`：从模型输出中抽取答案
  - `scorer()`：计算 reward / accuracy
  - `ParameterController`：控制难度随训练推进的变化
- 每个环境统一采用“短整数答案”格式：
  - 降低答案抽取错误
  - 降低 verifier 复杂度
  - 让不同环境之间的 reward 统计更可比

### 落点 2：比较 static difficulty vs adaptive difficulty
- 在相同模型、相同训练步数、相同训练环境集合下，对比两种训练方式：
  - `Static difficulty`
  - `Adaptive difficulty`
- `Static difficulty` 的定义：
  - 每个环境固定在某个难度级别采样
  - 训练过程中不因模型表现而改变
- `Adaptive difficulty` 的定义：
  - 初始从较低难度开始
  - 当模型在某个环境上的近期正确率超过阈值后，提升该环境难度
  - 该逻辑可直接复用仓库现有的 RLVE difficulty update 机制

### 落点 3：评估训练前后与 held-out env 泛化
- 对每个实验设置，都要进行两次评估：
  - `训练前评估`：基座模型在各评测集上的表现
  - `训练后评估`：RL 训练后模型在相同评测集上的表现
- 泛化分成两层：
  - `Seen env 泛化`：训练环境内的新样本、新 seed、新参数组合
  - `Held-out env 泛化`：完全未参与训练的新环境
- 核心问题不是“训练后在训练环境上是否变强”，而是：
  - static 和 adaptive 哪个提升更大
  - 这种提升是否能迁移到 held-out environment

## 环境拆分方案

### 方案 A：固定一个 held-out 环境
- 训练环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
- Held-out 环境：
  - `LongestCommonSubsequence`
- 优点：
  - 实现最简单
  - 汇报结构清晰
  - 足够完成课程项目

### 方案 B：轮换 held-out 环境
- 进行 4 轮实验，每轮留出一个环境：
  - Round 1：held-out = `WeightedIntervalScheduling`
  - Round 2：held-out = `EditDistance`
  - Round 3：held-out = `CoinChange`
  - Round 4：held-out = `LongestCommonSubsequence`
- 优点：
  - 结果更稳健
  - 不会因为某一个 held-out 环境“刚好太难或太容易”导致结论偏差
- 缺点：
  - 实验成本更高
- 课程项目建议：
  - 若算力有限，优先使用方案 A
  - 若后期时间充足，再补做方案 B 作为扩展实验

## 难度设计

### WeightedIntervalScheduling
- Difficulty 0：
  - 区间数 `N = 6-8`
  - 坐标范围 `0-20`
  - 单个区间长度 `1-4`
  - 权重范围 `1-10`
  - 重叠密度较低，约 `20%-30%` 的区间与前面区间发生重叠
- Difficulty 1-3：
  - Difficulty 1：
    - 区间数 `N = 9-12`
    - 坐标范围 `0-30`
    - 单个区间长度 `2-6`
    - 权重范围 `1-20`
    - 重叠密度中等，约 `35%-50%`
  - Difficulty 2：
    - 区间数 `N = 13-16`
    - 坐标范围 `0-50`
    - 单个区间长度 `3-8`
    - 权重范围 `1-40`
    - 重叠密度较高，约 `50%-70%`
  - Difficulty 3：
    - 区间数 `N = 17-22`
    - 坐标范围 `0-80`
    - 单个区间长度 `4-12`
    - 权重范围 `1-80`
    - 重叠密度很高，约 `70%-85%`
    - 增加“局部高权重但全局次优”的干扰区间，削弱贪心策略效果

### EditDistance
- Difficulty 0：
  - `|S|, |T| = 4-6`
  - 字符集大小 `2-3`
  - 由同一基础串经过 `1-2` 次编辑生成，保证两串相似度高
  - 编辑操作以单次替换或插入为主
- Difficulty 1-3：
  - Difficulty 1：
    - `|S|, |T| = 6-8`
    - 字符集大小 `3-4`
    - 生成时施加 `2-3` 次编辑
    - 插入、删除、替换三种操作开始均衡出现
  - Difficulty 2：
    - `|S|, |T| = 8-12`
    - 字符集大小 `4-5`
    - 生成时施加 `3-5` 次编辑
    - 允许连续局部扰动，例如连续删除或连续替换
  - Difficulty 3：
    - `|S|, |T| = 12-16`
    - 字符集大小 `5-7`
    - 生成时施加 `5-8` 次编辑
    - 增加更强的长度不平衡，例如 `||S|-|T|| = 3-6`
    - 降低表面相似度，使简单对位比较更容易失效

### CoinChange
- Difficulty 0：
  - 硬币种类数 `m = 3-4`
  - 目标金额 `A = 10-25`
  - 面额范围 `1-10`
  - 保证包含 `1`，且面额较规则，如接近等差或小整数集合
  - 大部分样例存在解
- Difficulty 1-3：
  - Difficulty 1：
    - 硬币种类数 `m = 4-5`
    - 目标金额 `A = 20-50`
    - 面额范围 `1-20`
    - 保证包含 `1`
    - 开始加入非贪心最优的组合，例如 `{1, 4, 6}`
  - Difficulty 2：
    - 硬币种类数 `m = 5-6`
    - 目标金额 `A = 40-90`
    - 面额范围 `1-35`
    - 不再总是包含 `1`
    - 无解样例比例控制在 `20%-30%`
    - 增加更强的近似干扰面额，如多个彼此接近的大面额
  - Difficulty 3：
    - 硬币种类数 `m = 6-8`
    - 目标金额 `A = 80-160`
    - 面额范围 `1-60`
    - 无解样例比例控制在 `30%-40%`
    - 面额组合显式避免简单贪心可解模式
    - 增加“最优解硬币数接近但不同”的对抗样例

### LongestCommonSubsequence
- Difficulty 0：
  - `|S|, |T| = 5-7`
  - 字符集大小 `2-3`
  - 两串由同一基础串轻度扰动得到，共享较长公共子序列
  - 干扰字符较少，相对容易通过直觉对齐
- Difficulty 1-3：
  - Difficulty 1：
    - `|S|, |T| = 7-10`
    - 字符集大小 `3-4`
    - 在共享骨架外插入少量干扰字符
    - 两串顺序仍较接近
  - Difficulty 2：
    - `|S|, |T| = 10-14`
    - 字符集大小 `4-5`
    - 干扰字符明显增多
    - 共用字符出现重复，增加多种对齐可能
    - 两串重合度下降到中等水平
  - Difficulty 3：
    - `|S|, |T| = 14-20`
    - 字符集大小 `5-7`
    - 大量重复字符与交错模式并存
    - 共享子序列被更多无关字符打散
    - 增加多个长度接近的候选子序列，削弱启发式猜测效果

## 训练方案

### 模型选择
- 优先选择仓库中已有 `1.5B` 级别脚本对应的模型进行实验。
- 不建议一开始直接用 `7B`，原因是：
  - 训练成本高
  - 调试周期长
  - 课程项目更需要稳定跑通而不是追求极限性能

### Reward 设计
- 主实验建议统一采用二值奖励：
  - 正确输出记为 `1`
  - 错误输出记为 `0`
- 原因：
  - 更容易比较 static 和 adaptive 的差异
  - 避免 reward shaping 干扰结论
- 本项目统一设置：
  - `reward_key = accuracy`
  - 训练时使用二值正确率作为优化目标
  - 评测时使用 `mean_accuracy` 作为主指标
- 训练脚本层面也统一采用：
  - `--reward-key accuracy`
  - `--eval-reward-key accuracy`
- 不再额外引入 shaped reward 作为主实验训练目标。
- 如果时间充足，可增加一个扩展实验：
  - 比较二值奖励和 shaped reward 的差异

### 环境实现约定
- 四个新增环境都应遵循同一套最小实现接口：
  - `generator()` 负责按 `seed + difficulty 参数` 生成单题实例
  - `prompt_generator()` 负责把实例转成统一风格的题面
  - `_process()` 负责从模型输出中提取最终整数答案
  - `scorer()` 负责返回至少包含 `accuracy` 的打分结果
- 为了减少无效样本，`generator()` 应在以下情况下重采样：
  - 样例不满足当前 difficulty 的参数约束
  - verifier 无法稳定求得唯一正确答案
  - 题目文本过于异常，可能导致 prompt 格式损坏
- 四个环境统一采用“最终答案是一个整数”的 prompt 约定：
  - 训练与评测统一采用 `apply_chat_template = true`
  - 题面中统一要求模型可在 `<think></think>` 中给出过程
  - 最终答案必须写在 `<answer></answer>` 中，且内容为一个整数
- 当前 RLVE 代码中 `answer_marker_type` 与 `apply_chat_template` 存在耦合，因此实现新实验代码时应同步兼容：
  - `ChatTemplate_NoSystemPrompt + <answer></answer>`
  - 不再要求新环境迁就 `\boxed{}` 方案
- 四个环境统一采用以下答案抽取规则：
  - `_process()` 只解析 `<answer></answer>` 标签内部内容
  - 在标签内部提取最后一个合法整数
  - 若未提取到合法整数，则记为格式错误并判错
- `scorer()` 的输出键名统一为 `accuracy`：
  - 正确返回 `1`
  - 错误返回 `0`
  - 这样可直接兼容训练中的 `reward_key = accuracy` 以及评测中的 `mean_accuracy`
- `generator()` 的统一重采样规则：
  - 单次样本生成最多重试 `20` 次
  - 若仍失败，则返回 `False`，由上层更换 seed 或重新生成
  - 不允许在环境内部无限重试

### Static difficulty 训练设置
- 为每个环境设定固定 difficulty level，例如 `difficulty = 2`
- 训练全程不改变
- 对应仓库参数思路：
  - 固定 `initial_difficulty`
  - 令 difficulty 不再上升
- 在当前仓库实现中的推荐设置：
  - `initial_difficulty = target_difficulty`
  - `difficulty_sliding_window_size = 1`
  - `min_metric_to_increase_difficulty = 1.1`
- 设置理由：
  - `initial_difficulty = target_difficulty`
    - 直接把环境最高可采样难度固定在目标档位
  - `difficulty_sliding_window_size = 1`
    - 避免 static 训练时混入更低 difficulty 样本
  - `min_metric_to_increase_difficulty = 1.1`
    - 由于 accuracy 不可能超过 `1.0`，因此 difficulty 不会继续上升

### Adaptive difficulty 训练设置
- 初始 difficulty 从较低等级开始，例如 `difficulty = 0`
- 当近期 accuracy 超过阈值后提升到下一等级
- 对应仓库参数思路：
  - `initial_difficulty = 0`
  - 设定 `min_metric_to_increase_difficulty`
  - 设定 `min_prompts_before_difficulty_check`
- 与当前仓库实现兼容的 `ParameterController.update()` 设计原则：
  - `update()` 必须是确定性的，不能在其中引入随机采样
  - `update()` 必须单调增加难度，不能回退
  - `get_parameter_list()` 只返回当前 difficulty 档位对应的参数候选，不混入其他档位
  - 题目实例的随机性应来自外层对 `parameter_list` 的随机采样，而不是来自 `update()` 本身
  - 由于当前 RLVE 实现会持续增加环境 difficulty，因此如果项目只定义 `difficulty = 0-3`，`update()` 应在 `difficulty = 3` 后饱和，不再继续升高
- 推荐统一实现方式：
  - 每个新环境的 `ParameterController` 都维护唯一状态变量 `level`
  - 初始时 `level = 0`，对应 `difficulty = 0`
  - 每次调用 `update()` 时执行 `level = min(3, level + 1)`
  - `get_parameter_list()` 根据 `level` 返回该 difficulty 档位下的一组参数组合
  - 建议每个 difficulty 返回 `4` 个参数模板，保证同难度下仍有一定分布宽度
- 四个新增环境的推荐写法：
  - `WeightedIntervalScheduling`
    - `update()` 只推进 `level`
    - `get_parameter_list()` 按 `level` 返回当前档位的 `N`、坐标范围、区间长度范围、权重范围、重叠密度组合
  - `EditDistance`
    - `update()` 只推进 `level`
    - `get_parameter_list()` 按 `level` 返回字符串长度范围、字符集大小、编辑步数范围、长度失衡范围组合
  - `CoinChange`
    - `update()` 只推进 `level`
    - `get_parameter_list()` 按 `level` 返回硬币种类数、目标金额范围、面额范围、是否包含 `1`、无解样例比例组合
  - `LongestCommonSubsequence`
    - `update()` 只推进 `level`
    - `get_parameter_list()` 按 `level` 返回字符串长度范围、字符集大小、重合度、干扰强度组合
- 对自适应难度采样机制的理解：
  - 当前仓库不会只采样“当前最高 difficulty”，而是从最近几档 difficulty 的滑动窗口中采样
  - 因此 `ParameterController` 内部不需要再额外实现跨 difficulty 混采逻辑
  - `ParameterController` 只需要负责“第几档 difficulty 对应什么参数分布”
- 本项目建议的自适应超参数：
  - `initial_difficulty = 0`
  - `difficulty_sliding_window_size = 2`
  - `min_prompts_before_difficulty_check = 8`
  - `min_metric_to_increase_difficulty = 0.9`
- 参数设置理由：
  - `initial_difficulty = 0`
    - 让模型从最低难度开始学习，符合课程项目中的 curriculum 设定
  - `difficulty_sliding_window_size = 2`
    - 让训练时主要覆盖“当前最高难度”和“前一档难度”
    - 能保留一定过渡样本，同时避免过多低难度样本持续干扰
  - `min_prompts_before_difficulty_check = 8`
    - 避免在样本数过少时过早升难度
  - `min_metric_to_increase_difficulty = 0.9`
    - 只有当模型在当前最高难度上接近稳定做对时才升到下一档
- 若实验时间很短时的替代设置：
  - 可把 `min_prompts_before_difficulty_check` 降到 `4`
  - 但这会让 difficulty 升级更快，也更容易因为统计波动过早进入高难度

### 随机性控制
- 训练集、验证集、测试集必须使用互不重合的 seed 区间。
- 每条曲线对应的评测集一旦生成，就在整个实验中固定不变。
- 主实验中的评测集统一采用“离线预生成并固定保存”的方式，不在评测时在线重采样。
- 建议先统一使用单随机种子版本完成主实验：
  - `seed = 0`
  - 先保证四个实验都能稳定跑通并形成可比较结论
- 如果后续时间和算力允许，再补充多随机种子重复实验：
  - 建议使用 `seed = 0, 1, 2`
  - 最终报告 `mean ± std`
- 对于需要对比的实验组，除明确对比因素外，其余随机性来源保持一致：
  - 训练 seed
  - 评测集 seed
  - difficulty 参数范围
  - prompt 模板
  - 答案抽取规则

## 评测执行约定

### 评测集设置
- 每条训练曲线上的所有 checkpoint 必须使用同一份固定评测集：
  - 固定评测 seed
  - 固定 difficulty
  - 固定参数采样范围
- 固定评测集建议统一保存到项目内独立目录，例如：
  - `data/EXPERIMENTS/`
  - 按实验、环境、difficulty 分文件组织
- 评测集大小统一建议：
  - 快速实验版本：每个评测集 `128` 题
  - 正式实验版本：每个评测集 `256` 题
- 正式版本中，建议每个评测集在对应 difficulty 下的 `4` 个参数模板之间均匀采样。

### 评测与存档间隔
- 本项目统一建议：
  - `eval_every = 10 steps`
  - `save_every = 10 steps`
- 图上的每个点都对应一次固定评测间隔下的评测结果。

### 结果统计口径
- 主曲线统一绘制原始 `mean_accuracy`，不做平滑。
- 默认最终结果取最后一个 checkpoint 的评测分数。
- 如果额外报告 `best checkpoint`，必须与 `final checkpoint` 分开列示，不能混用。

### 单次运行步数建议
- 当前统一执行口径：
  - 所有实验先统一跑 `100 steps`
  - 所有实验都先产出 `100 steps` 版本的结果，再决定是否继续扩展
- 本项目所有实验统一采用以下绘图粒度：
  - 先完成 `100 steps` 的初始版本
  - 每训练 `10 steps` 保存、评测并在图上绘制 `1` 个数据点
- 训练过程中的作图与存档频率统一采用：
  - `eval_every = 10 steps`
  - `save_every = 10 steps`
- 因此一条 `100 steps` 的训练曲线默认会得到约 `10` 个评测点。

## 实验章节

### 实验 1：单环境分布外泛化与跨难度泛化
- 实验目标：
  - 对落点 1 中设计的四个环境分别单独训练并评测
  - 观察模型在同一环境内的“训练集外但同难度”泛化能力
  - 观察模型在同一环境内向更高难度迁移的泛化能力
- 参与环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
  - `LongestCommonSubsequence`
- 实验方式：
  - 对四个环境分别独立进行 1 次训练，共 4 组训练
  - 每组训练只使用单一环境，不混合其他环境
  - 每组训练都使用相同的模型规模、训练步数、batch size 和 reward 设计

### 实验 1.1：第一个实验设置
- 训练设置：
  - 对每个环境分别训练一个模型
  - 四个环境的训练都固定在最低难度 `difficulty = 0` 上采样
  - 对应 static 参数建议：
    - `initial_difficulty = 0`
    - `difficulty_sliding_window_size = 1`
    - `min_metric_to_increase_difficulty = 1.1`
  - 主实验建议步数：
    - 当前统一先训练 `100 steps`
    - 每 `10 steps` 评测并记录一次 `mean_accuracy`
  - 训练集与评测集严格使用不同随机 seed 和不同实例参数，避免样本重复
- 评测 1：同难度训练集外泛化
  - 评测集仍来自同一个环境
  - 难度与训练时保持一致
  - 但题目实例必须来自训练数据集外，即新的 seed、新的参数组合、新生成的问题实例
  - 该指标用于衡量模型是否只记住训练分布中的具体样本，还是学到了该环境上的可迁移求解能力
- 评测 2：更高难度泛化
  - 评测集仍来自同一个环境
  - 但难度高于训练难度；由于训练固定在 `difficulty = 0`，主实验固定评测 `difficulty = 1`
  - 评测样本同样必须与训练集无重合
  - 该指标用于衡量模型是否具备从低难度训练向高难度样本迁移的能力
- 四个环境的执行方式：
  - `WeightedIntervalScheduling`：在固定训练难度上训练，测试同难度新实例与更高重叠密度/更大规模实例
  - `EditDistance`：在固定训练难度上训练，测试同难度新字符串对与更长字符串/更强扰动实例
  - `CoinChange`：在固定训练难度上训练，测试同难度新面额组合与更大目标金额/更多硬币种类实例
  - `LongestCommonSubsequence`：在固定训练难度上训练，测试同难度新字符串对与更长串/更低重合度实例
- 控制变量：
  - 初始模型保持一致
  - 训练步数保持一致
  - rollout 和 batch size 保持一致
  - prompt 模板和答案抽取方式保持一致
  - reward 统一使用二值奖励
- 记录指标：
  - `Train-env IID accuracy`
    - 训练环境、训练难度、训练集外新样本上的 accuracy
  - `Train-env OOD accuracy`
    - 训练环境、`difficulty = 1` 新样本上的 accuracy
  - `Mean accuracy over training steps`
    - 在训练过程中按固定评测间隔记录 `mean_accuracy`
    - 每个环境绘制两条曲线：
      - `difficulty = 0` 训练集外评测集上的 `mean_accuracy`
      - `difficulty = 1` 评测集上的 `mean_accuracy`
  - `Generalization drop`
    - `IID accuracy - OOD accuracy`
    - 用于衡量跨难度泛化退化程度
  - `Improvement over base model`
    - 分别记录训练前后在 IID 与 OOD 集上的提升
- 结果展示建议：
  - 表格按环境列出 4 组结果，每组包含 `before` 和 `after`
  - 分别报告同难度训练集外 accuracy 和更高难度 accuracy
  - 对每个环境绘制 `mean_accuracy` 随训练 step 变化的曲线图
  - 每张图包含两条曲线：
    - `difficulty = 0` 训练集外评测数据的 `mean_accuracy`
    - `difficulty = 1` 评测数据的 `mean_accuracy`
  - 可额外画出四个环境在 `IID` 与 `OOD` 两类评测上的柱状图，直观看不同环境的泛化差异
- 希望回答的问题：
  - RL 训练是否能提升模型在单一 verifiable environment 内的样本外泛化能力？
  - 这种提升主要体现在同难度新样本上，还是也能迁移到更高难度样本上？
  - 四个环境中，哪一类任务最容易出现“同难度泛化可以，但跨难度泛化较弱”的现象？

### 实验 2：Static difficulty 与 Adaptive difficulty 对比
- 实验目标：
  - 比较固定高难度训练和自适应难度训练在四个环境上的效果差异
  - 重点观察两种训练方式对最高难度验证集表现的影响
- 参与环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
  - `LongestCommonSubsequence`
- 实验方式：
  - 对四个环境分别独立进行 2 组训练
  - 每个环境都训练两种设置：
    - `Adaptive difficulty`
    - `Static difficulty @ difficulty = 3`
  - 因此总计进行 `4 x 2 = 8` 组训练
  - 每组训练只使用单一环境，不混合其他环境

### 实验 2.1：第二个实验设置
- 训练设置：
  - `Adaptive difficulty`：
    - 从 `difficulty = 0` 开始训练
    - 随着近期表现提升，按既定规则逐步提升到更高 difficulty
    - 具体采用：
      - `initial_difficulty = 0`
      - `difficulty_sliding_window_size = 2`
      - `min_prompts_before_difficulty_check = 8`
      - `min_metric_to_increase_difficulty = 0.9`
    - 四个环境都使用相同的 `ParameterController` 设计原则：
      - `update()` 只推进 difficulty level
      - 在 `difficulty = 3` 后饱和
      - `get_parameter_list()` 只返回当前 difficulty 的参数组合
  - `Static difficulty`：
    - 训练全程固定在最高难度 `difficulty = 3`
    - 具体采用：
      - `initial_difficulty = 3`
      - `difficulty_sliding_window_size = 1`
      - `min_metric_to_increase_difficulty = 1.1`
  - 主实验建议步数：
    - 两种设置都统一先训练 `100 steps`
    - 每 `10 steps` 在最高难度验证集上评测一次
  - 两种设置都使用相同的初始模型、训练步数、batch size、rollout 配置和 reward 形式
  - 训练集与评测集严格使用不同随机 seed 和不同实例参数，避免样本重复
- 统一评测方式：
  - 对每个训练 checkpoint，都在该环境的最高难度验证集上进行评测
  - 评测难度固定为 `difficulty = 3`
  - 验证集样本必须来自训练数据集外，即新的 seed、新的参数组合、新生成的问题实例
  - 核心评测指标为该验证集上的 `mean_accuracy`
- 记录指标：
  - `Hard-validation mean_accuracy`
    - 最高难度 `difficulty = 3` 验证集上的 `mean_accuracy`
  - `Final hard-validation accuracy`
    - 最终 checkpoint 在最高难度验证集上的 `mean_accuracy`
  - `Adaptive gain on hard set`
    - `Adaptive final mean_accuracy - Static final mean_accuracy`
    - 用于衡量自适应难度训练在最高难度评测上的额外收益
- 结果展示建议：
  - 对每个环境绘制 1 张图，共 4 张图
  - 横轴为训练 `step` 或固定评测间隔
  - 纵轴为最高难度验证集上的 `mean_accuracy`
  - 每张图包含两条曲线：
    - `Adaptive difficulty` 训练下的 `mean_accuracy` 曲线
    - `Static difficulty @ difficulty = 3` 训练下的 `mean_accuracy` 曲线
  - 可额外补充 1 张汇总表，对比四个环境最终的 hard-validation `mean_accuracy`
- 希望回答的问题：
  - 自适应难度训练是否比“直接在最高难度上静态训练”更稳定？
  - 自适应难度训练是否能在最高难度验证集上取得更高的最终准确率？
  - 哪些环境更依赖 curriculum，哪些环境在直接高难度训练下也能学到有效策略？

### 实验 3：三环境联合训练下的 held-out 环境泛化
- 实验目标：
  - 评估在 3 个环境上进行 `Adaptive difficulty` 联合训练时，模型对未参与训练的第 4 个环境的泛化能力
  - 观察 held-out 环境上的 `mean_accuracy` 是否会随着训练推进而提升
- 参与环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
  - `LongestCommonSubsequence`
- 实验方式：
  - 共进行 4 组实验
  - 每组实验选择其中 3 个环境参与训练，剩余 1 个环境作为 held-out 环境仅用于评测
  - 4 组实验分别轮换 held-out 环境，使四个环境都各自充当一次未见环境
  - 四组实验除训练环境组合不同外，其余配置保持一致

### 实验 3.1：第三个实验设置
- 四组实验划分：
  - Group 1：
    - 训练环境：`EditDistance`、`CoinChange`、`LongestCommonSubsequence`
    - Held-out 评测环境：`WeightedIntervalScheduling`
  - Group 2：
    - 训练环境：`WeightedIntervalScheduling`、`CoinChange`、`LongestCommonSubsequence`
    - Held-out 评测环境：`EditDistance`
  - Group 3：
    - 训练环境：`WeightedIntervalScheduling`、`EditDistance`、`LongestCommonSubsequence`
    - Held-out 评测环境：`CoinChange`
  - Group 4：
    - 训练环境：`WeightedIntervalScheduling`、`EditDistance`、`CoinChange`
    - Held-out 评测环境：`LongestCommonSubsequence`
- 训练设置：
  - 四组实验都采用 `Adaptive difficulty` 训练
  - 每组实验中的 3 个训练环境都按相同自适应规则调整 difficulty
  - 具体采用：
    - `initial_difficulty = 0`
    - `difficulty_sliding_window_size = 2`
    - `min_prompts_before_difficulty_check = 8`
    - `min_metric_to_increase_difficulty = 0.9`
  - 每个训练环境都使用同一套 `ParameterController` 约定：
    - `update()` 只推进 difficulty level
    - 在 `difficulty = 3` 后饱和
    - `get_parameter_list()` 只描述当前 difficulty 对应的参数分布
  - 三环境联合训练时，训练环境采样权重统一保持为等权采样
  - 直接沿用当前 RLVE 实现中的均匀环境采样逻辑，不额外引入环境加权
  - 主实验建议步数：
    - 四组实验都统一先训练 `100 steps`
    - 每 `10 steps` 对 held-out 环境固定评测一次
  - 初始模型、训练步数、batch size、rollout 配置、采样温度和 reward 形式在四组实验中保持一致
  - held-out 环境在训练阶段完全不参与采样、reward 计算和 difficulty 更新
- 评测方式：
  - 在训练过程中按 step 或固定评测间隔，对 held-out 环境进行评测
  - 评测集来自 held-out 环境，且与训练数据严格无重合
  - 主实验固定在 held-out 环境的 `difficulty = 0` 上评测
  - 核心指标为 held-out 环境评测集上的 `mean_accuracy`
- 记录指标：
  - `Held-out mean_accuracy over training steps`
    - held-out 环境 `difficulty = 0` 评测集上的 `mean_accuracy` 随训练 step 变化的曲线
  - `Final held-out mean_accuracy`
    - 最终 checkpoint 在 held-out 环境评测集上的 `mean_accuracy`
  - `Held-out improvement`
    - `训练后 held-out mean_accuracy - 训练前 held-out mean_accuracy`
- 结果展示建议：
  - 共绘制 4 张图，每组实验对应 1 张图
  - 横轴为训练 `step` 或固定评测间隔
  - 纵轴为对应 held-out 环境 `difficulty = 0` 评测集上的 `mean_accuracy`
  - 每张图展示该组实验中 held-out 环境的 `mean_accuracy` 随训练变化趋势
  - 可额外补充 1 张汇总表，对比四组实验最终的 held-out `mean_accuracy`
- 希望回答的问题：
  - 在 3 个环境上进行自适应训练时，模型是否会自然提升对未见第 4 个环境的表现？
  - 哪个环境最容易从其他 3 个环境中获得迁移收益，哪个环境最难泛化到？
  - held-out 环境上的提升是稳定增长，还是只在训练后期出现有限改善？

### 实验 4：不同模型规模下的 Adaptive difficulty 对比
- 实验目标：
  - 比较不同模型规模在四个环境上使用 `Adaptive difficulty` 训练时的学习动态差异
  - 重点观察小模型和大模型在最高难度评测集上的 `mean_accuracy` 变化趋势
- 参与环境：
  - `WeightedIntervalScheduling`
  - `EditDistance`
  - `CoinChange`
  - `LongestCommonSubsequence`
- 比较模型：
  - `DeepSeek-R1-Distill-Qwen-1.5B`
  - `DeepSeek-R1-Distill-Qwen-7B`
- 实验方式：
  - 对四个环境分别独立进行 2 组训练
  - 每个环境都使用相同的 `Adaptive difficulty` 训练策略
  - 仅改变模型规模，其余训练配置尽量保持一致
  - 因此总计进行 `4 x 2 = 8` 组训练

### 实验 4.1：第四个实验设置
- 训练设置：
  - 对每个环境分别训练两种模型：
    - `DeepSeek-R1-Distill-Qwen-1.5B`
    - `DeepSeek-R1-Distill-Qwen-7B`
  - 两种模型都采用 `Adaptive difficulty` 训练
  - 都从 `difficulty = 0` 开始，并按相同规则逐步提升 difficulty
  - 具体采用：
    - `initial_difficulty = 0`
    - `difficulty_sliding_window_size = 2`
    - `min_prompts_before_difficulty_check = 8`
    - `min_metric_to_increase_difficulty = 0.9`
  - 四个环境在两种模型规模下共用同一套 `ParameterController` 设计：
    - `update()` 只推进 difficulty level
    - 在 `difficulty = 3` 后饱和
    - `get_parameter_list()` 只返回当前 difficulty 档位参数
  - 对于同一个环境，除模型规模外，其余配置保持一致：
    - 训练环境
    - difficulty 更新规则
    - 训练步数
    - 评测间隔
    - reward 形式
    - prompt 模板与答案抽取方式
  - 允许与模型规模强相关的底层训练配置沿用各自稳定设置，例如：
    - 学习率
    - 并行配置
    - `rollout-max-response-len`
    - `max_tokens_per_gpu`
  - 主实验建议步数：
    - 两种模型在同一环境上都统一先训练 `100 steps`
    - 每 `10 steps` 在最高难度评测集上评测一次
  - 训练集与评测集严格使用不同随机 seed 和不同实例参数，避免样本重复
- 统一评测方式：
  - 对每个训练 checkpoint，都在该环境的最高难度评测集上进行评测
  - 评测难度固定为 `difficulty = 3`
  - 评测样本必须来自训练数据集外，即新的 seed、新的参数组合、新生成的问题实例
  - 核心评测指标为该评测集上的 `mean_accuracy`
- 记录指标：
  - `Hard-set mean_accuracy over training steps`
    - 最高难度 `difficulty = 3` 评测集上的 `mean_accuracy` 随训练 step 变化曲线
  - `Final hard-set mean_accuracy`
    - 最终 checkpoint 在最高难度评测集上的 `mean_accuracy`
  - `Model-scale gain`
    - `7B final mean_accuracy - 1.5B final mean_accuracy`
    - 用于衡量更大模型在该环境上的最终优势
- 结果展示建议：
  - 对每个环境绘制 1 张图，共 4 张图
  - 横轴为训练 `step` 或固定评测间隔
  - 纵轴为最高难度评测集上的 `mean_accuracy`
  - 每张图包含两条曲线：
    - `DeepSeek-R1-Distill-Qwen-1.5B` 的 `mean_accuracy` 曲线
    - `DeepSeek-R1-Distill-Qwen-7B` 的 `mean_accuracy` 曲线
  - 可额外补充 1 张汇总表，对比四个环境上两种模型最终的 hard-set `mean_accuracy`
- 希望回答的问题：
  - 更大模型是否在最高难度评测集上从训练一开始就更强？
  - 更大模型的训练曲线是否上升更快、更稳定？
  - 不同环境中，模型规模带来的收益是否一致，还是只在某些任务上更明显？

## 实现细则

### 所有实验均支持 Resume
- 所有实验都默认支持 `resume` 继续训练。
- 这意味着实验可以按“短程验证 -> 长程扩展”的方式逐步推进，而不需要每次都从头重新训练。
- 例如：
  - 可以先运行某个实验的 `100 step` 版本，用于快速检查训练是否稳定、评测脚本是否正常、曲线是否合理。
  - 如果结果值得继续，再直接从该 `100 step` checkpoint 恢复训练，扩展到更长版本，例如 `300 step`、`500 step` 或 `1000 step`。
- 该策略适用于实验 1 到实验 4 的所有训练设置：
  - 单环境训练
  - `Static difficulty` 训练
  - `Adaptive difficulty` 训练
  - 三环境联合训练
  - 不同模型规模对比训练
- 当前默认推进方式：
  - 先统一跑完实验 1 到实验 4 的 `100 steps` 版本
  - 每个实验都按 `10 steps` 一个评测点的粒度产出曲线
  - 后续若需要更长曲线，再从已有 checkpoint 继续扩展

### 推荐执行方式
- 当前统一执行口径：
  - 所有实验先跑 `100 steps`
  - 所有实验每 `10 steps` 评测、保存并绘制一个数据点
- 在 `100 step` 版本上优先确认以下内容：
  - loss / reward / accuracy 日志是否正常
  - difficulty 更新是否符合预期
  - checkpoint 保存与恢复是否正常
  - 评测曲线是否能正常生成
- 在 `100 step` 版本验证通过后，再选择重点实验继续 `resume` 到更长步数。
- 这样可以显著降低一次性长程训练失败带来的时间浪费。
- 推荐执行顺序：
  - 先跑四个环境的单环境 `100 step` 冒烟实验
  - 再跑实验 1 与实验 2 的正式版本
  - 最后再补实验 3 和实验 4 这种总成本更高的组合实验

### 对结果记录的要求
- 在使用 `resume` 扩展训练时，应保持以下配置不变：
  - 初始实验定义
  - 训练环境组合
  - 模型规模
  - reward 形式
  - difficulty 规则
  - 评测集定义
- 扩展后的训练结果应视为同一实验的更长版本，而不是新的独立实验。
- 在作图时，可以把 `100 step`、`300 step`、`1000 step` 的结果统一放在同一条训练轨迹上，只要它们来自同一次连续恢复训练。

### 输出目录与版本管理约定
- 所有实验过程中产生的输出内容统一放在项目根目录下的 `outputs/` 文件夹中。
- 建议在 `outputs/` 下按实验类型、环境、模型规模和步数进一步分目录保存，便于后续对比与恢复训练。
- 建议目录结构保持统一，例如：
  - `outputs/exp1/<env>/<model>/`
  - `outputs/exp2/<env>/<adaptive_or_static>/`
  - `outputs/exp3/<held_out_env>/<model>/`
  - `outputs/exp4/<env>/<model_size>/`
- `outputs/` 中的模型权重、checkpoint 和其他大体积训练产物默认不提交到 GitHub。
- `outputs/` 中生成的图线、结果汇总表和较小的数据文件应保留并可以提交到 GitHub，例如：
  - 曲线图
  - 对比图
  - 汇总 `json/csv/txt` 数据
  - 小规模评测结果文件
- 这样可以保证：
  - 仓库不会被大模型文件和训练 checkpoint 膨胀
  - 实验图表和关键结果数据仍然能够被版本管理和共享

### 实验代码组织与统一运行方式
- 所有实验代码统一放在项目根目录下的 `experiments/` 文件夹中。
- `experiments/` 下应提供统一入口脚本 `run.sh`，并由该脚本指定本轮目标训练步数 `target_steps`。
- 每次执行 `run.sh` 时，按预先定义好的实验顺序逐个运行实验 1 到实验 4 对应的各个子实验。
- 建议 `experiments/` 的目录结构至少包含：
  - `experiments/configs/`
  - `experiments/eval/`
  - `experiments/plot/`
  - `experiments/utils/`
  - `experiments/run.sh`
- 对于某个子实验：
  - 如果其当前已完成步数小于 `target_steps`，则从已有 checkpoint `resume` 继续训练，直到补足到 `target_steps`
  - 如果其当前已完成步数已经达到 `target_steps`，则直接跳过，继续执行下一个实验
- 当后续把 `run.sh` 中指定的步数从较小值改为更大值时，例如从 `100 steps` 改到 `1000 steps`：
  - 所有尚未跑满新目标步数的实验都继续 `resume`
  - 脚本仍按统一顺序逐个把它们补到新的目标步数
- 为保证“从任意较小步数继续跑到更大步数”时一定可恢复：
  - 外部接口仍接受用户指定的 `target_steps`
  - 但内部实际训练目标应自动向上对齐到最近的 `save_every` 整数倍
  - 例如 `save_every = 10` 时，请求跑到 `137 steps`，则实际训练并持久化到 `140 steps`
  - 这样可以保证最终一定存在可恢复 checkpoint，后续扩展到更大步数时不会因为最后几步未保存而重跑或触发恢复问题
- 每个子实验都应具有唯一 `experiment_id`，例如：
  - `exp1_weighted_interval_scheduling`
  - `exp2_coin_change_adaptive`
  - `exp3_holdout_lcs`
  - `exp4_edit_distance_7b`
- 每个子实验都应维护一份统一的进度文件，例如 `progress.json`，至少记录：
  - `experiment_id`
  - `requested_steps`
  - `target_steps`
  - `completed_steps`
  - `last_checkpoint`
  - `status`
- `progress.json` 用于记录实验元数据与最近一次请求目标步数，但是否真正已完成应优先以 checkpoint 中可恢复的最新步数为准。
- 每个实验或子实验在完成本轮目标步数后，都必须立即产出对应分析结果：
  - 按本方案要求绘制对应曲线图
  - 或生成后续制作表格所需的原始结果数据
- 这些图像和原始数据也统一保存到 `outputs/` 下对应实验目录中，保证训练、评测、作图三者的产物一一对应。

### 环境参数协议
- 四个新环境都应把 difficulty 相关参数写成显式 `parameter` 字典，而不是散落在环境内部逻辑里。
- `WeightedIntervalScheduling` 推荐参数字段：
  - `difficulty`
  - `n_range`
  - `coord_max`
  - `length_range`
  - `weight_range`
  - `overlap_ratio_range`
  - `trap_ratio`
- `EditDistance` 推荐参数字段：
  - `difficulty`
  - `len_s_range`
  - `len_t_range`
  - `alphabet_size`
  - `edit_steps_range`
  - `imbalance_range`
  - `burst_edit_prob`
- `CoinChange` 推荐参数字段：
  - `difficulty`
  - `num_coins_range`
  - `amount_range`
  - `coin_value_max`
  - `must_include_one`
  - `unsat_ratio`
  - `anti_greedy`
- `LongestCommonSubsequence` 推荐参数字段：
  - `difficulty`
  - `len_s_range`
  - `len_t_range`
  - `alphabet_size`
  - `shared_backbone_range`
  - `noise_range`
  - `repeat_bias`
- `reference_answer` 不由 `ParameterController` 提供，而是在环境 `_generate()` 中根据实际采样实例求解后写入。

### 配置文件协议
- 每个子实验建议使用一份独立 manifest 配置，统一描述：
  - `experiment_id`
  - `train`
  - `eval`
  - `plot`
- `train` 段至少包含：
  - `model`
  - `environment_list`
  - `difficulty_mode`
  - `target_steps`
  - `output_dir`
- `eval` 段至少包含：
  - `eval_sets`
  - `eval_every`
  - `primary_metric`
- `plot` 段至少包含：
  - `curve_keys`
  - `figure_path`
  - `table_data_path`

### 评测原始数据协议
- 每次固定评测完成后，都应向统一结果文件追加一行记录，建议文件名为 `curve.csv`。
- `curve.csv` 建议至少包含以下字段：
  - `experiment_id`
  - `model`
  - `train_envs`
  - `eval_env`
  - `difficulty_mode`
  - `eval_difficulty`
  - `step`
  - `split`
  - `mean_accuracy`
  - `num_examples`
  - `checkpoint_path`
- 每个子实验在本轮运行结束后，还应额外产出：
  - `summary.json`
  - 对应的曲线图 `png/pdf`
- 作图脚本统一只读取 `curve.csv` 等评测原始数据文件，不直接依赖训练日志。
