# 名词解释

- 有效提示率：指在一次动态采样过程中，所有已完成展开并获得奖励的提示词中，其多次展开结果对应的奖励并不完全相
  同的提示词所占比例。设一个提示词被展开为 n_samples_per_prompt 个回答，若这些回答的奖励标准差大于 0，则该提示词被视为有效；若所有回
  答奖励完全相同，则该提示词会被动态采样过滤掉，不计入有效提示词。形式化地，若某一步共完成了 N 个提示词的展开，其中有 N_eff 个提示词
  满足奖励存在差异，则有效提示率定义为 N_eff / N，通常以百分比表示，即 100% × N_eff / N。该指标反映了当前策略下，采样到的提示词中有
  多少能够提供区分不同回答优劣的训练信号。

- Static Difficulty [a,b]: 按照均匀分布从[a,b]中采样一个难度d

- Adaptive Difficulty [h-1,h]:

1. 维护当前最高难度 h。
  2. 训练时从区间 [h-1, h] 中采样问题。
  3. 只统计最高难度 h 上的表现，不用 h-1 的样本更新难度。
  4. 记：
      - a：在难度 h 上答对的展开次数
      - b：在难度 h 上的总展开次数

  5. 当 b 达到最小样本阈值 τ_num 后，计算准确率 a/b：
      - 如果 a/b ≥ τ_acc，说明模型已基本掌握当前最高难度，更新为 h ← h+1
      - 如果 a/b < τ_acc，则保持 h 不变

  6. 无论是否升级，检查完成后都将 (a, b) 重置，再进入下一轮统计。

  在 [h-1, h] 这个特例下，难度窗口会这样滑动：

  - 初始：[0, 0]
  - 达标后：[0, 1]
  - 再达标后：[1, 2]
  - 再达标后：[2, 3]

实现中采用
  - τ_acc = 0.9
    对应参数 --min-metric-to-increase-difficulty，见 slime/utils/arguments.py:875

  - τ_num = 8
    对应参数 --min-prompts-before-difficulty-check，见 slime/utils/arguments.py:881

# 新增环境设计

给出难度d

## digit_sum_interval

给定 L, R，求区间内所有整数的数位和之和。

难度设定：
  max_digits = min(2 + d // 10, 12)
  span_digits = min(1 + d // 15, max_digits)
  allow_arbitrary_L = (d >= 20)

  生成时可以这样：

  R_max = 10 ** max_digits - 1
  R = random.randint(1, R_max)

  span_max = min(10 ** span_digits - 1, R - 1)
  span = random.randint(0, span_max)

  if allow_arbitrary_L:
      L = R - span
  else:
      L = 1

## binary_string_no_adjacent_count

长度为 n 的 01 串中，不含相邻两个 1 的串有多少个。

难度设定：
  长度为d

## grid_path_counting_with_blocks

给一个正方形小网格和若干障碍，求从左上到右下路径数。

难度设定：
  边长= min(2 + d // 8, 14)，障碍比例p

  if d < 20:
      p = 0.05 + 0.005 * d
  elif td < 50:
      p = 0.15 + 0.002 * (d - 20)
  else:
      p = 0.21

# 实验

## 实验1：在论文外其他环境验证Static与Adaptive Difficulty效果

### 实验维度

- 训练步数 400
- 一张图上包含4条配置的线，其他每个维度展开一张图，一共指标数x环境数张图

#### 指标
- 有效提示率
- 分布内accuracy
    生成训练的环境上从[0,19]均匀采样的4000道题计算平均准确率
- 分布外accuracy
    在data/HELD-OUT_ENVIRONMENTS/test.json 2500条数据的平均准确率。

#### 配置

- Adaptive Difficulty [h,h-1]
- Static Difficulty [0,1]
- Static Difficulty [0,20]
- Static Difficulty [0,100]

#### 环境

- Gym/environments/division
- digit_sum_interval
- binary_string_no_adjacent_count
- grid_path_counting_with_blocks

## 实验2: 不同数量的环境按照Adaptive训练，在held-out的表现


### 实验维度

- 训练步数 400
- 使用Adaptive Difficulty [h,h-1]
- 一张图，包含四条不同数量训练环境的线

#### 指标

- 分布外accuracy
    在新增的几个环境（见新增环境设计）、难度[1,19]中均匀采样2500条样本，落盘作为该实验评测集。

#### 训练环境

参照scripts/training/DeepSeek-R1-Distill-Qwen-1.5B/rlve下配置
- 1
- 4
- 16
- 256

## 实验3:不同尺寸模型的表现

Gym/environments/sorting环境，Adaptive Difficulty [h,h-1]，训练400步，绘制DeepSeek-R1-Distill-Qwen-1.5B和DeepSeek-R1-Distill-Qwen-7B的有效提示率和分布内accuracy；一共两张图，每张图两条不同大小的模型的线
模型文件在项目上一级目录

# 实现细节

新增环境写到Gym对应文件下，必要时创建文件夹；其他所有新增代码都写到experiments文件夹下
训练每10步缓存一次模型，后续可断点续训；所有缓存与结果输出到outputs文件夹
所有实验每20步得到图上一个数据点

每套训练配置一个bash脚本放到experiments下，例如exp1_adapt_diff_division.sh对应实验一的Adaptive Difficulty与Division环境，支持--step指定训练步数

写一个run_all.sh，，以steps=100按顺序依次运行所有实验；已经跑到100步的实验就跳过