
// demoData.js
// GitHub Pages 静态演示数据
// 不需要请求 FastAPI 或 DeepSeek

export const demoConversations = [
    {
        id: 1,
        title: 'OSTrack',

        messages: [
            {
                id: 101,
                role: 'user',
                text: 'OSTrack 是做什么的？',
                docs: [],
            },

            {
                id: 102,
                role: 'assistant',
                text: `## OSTrack 简介

OSTrack 是一种基于 Transformer 的视觉单目标跟踪方法。

它采用 One-Stream 架构，将模板图像与搜索区域的特征提取和交互过程统一到一个网络中。

**主要特点：**
1. 使用统一的 Transformer 主干处理模板和搜索区域。
2. 实现目标特征提取与交互建模。
3. 通过候选消除策略减少背景 Token 的计算开销。`,

                docs: [
                    {
                        id: 'DEMO-C1',
                        filename: 'OSTrack.pdf',
                        page_number: 3,
                        content: '演示证据占位内容，后续替换为论文中可公开的真实摘录。',
                        source: ['BGE', 'BM25'],
                        rrf_score: 0.03,
                    },
                ],
            },
        ],
    },


    {
        id: 2,
        title: 'DUTrack 在不同数据集上的表现如何？',

        messages: [
            {
                id: 201,
                role: 'user',
                text: 'DUTrack-256 和 DUTrack-384 在不同数据集上的实验表现如何？',
                docs: [],
            },

            {
                id: 202,
                role: 'assistant',

                text: `## DUTrack 实验结果分析

根据 DUTrack 论文中的实验结果，DUTrack-256 和 DUTrack-384 在多个视觉目标跟踪数据集上进行了评测。

### 1. 实验指标对比

论文第 7 页的 Table 7 给出了以下结果：

| 数据集 | DUTrack-256 | DUTrack-384 |
|---|---:|---:|
| GOT-10k* | 76.7 | 77.8 |
| UAV123 | 69.3 | 70.1 |

以上数值来自论文中的实验对比表。

### 2. 实验结果分析

**GOT-10k* 数据集：**

- DUTrack-256：76.7
- DUTrack-384：77.8

DUTrack-384 的表现优于 DUTrack-256。

**UAV123 数据集：**

- DUTrack-256：69.3
- DUTrack-384：70.1

DUTrack-384 同样取得了更高的实验指标。

### 3. 总结

从这两个数据集的结果来看：

1. DUTrack-384 在两个数据集上的指标均高于 DUTrack-256。
2. 更高的输入分辨率可能有助于提升跟踪表现，但仅凭这两组结果不能确定提升完全来自分辨率。
3. 完整的性能评价仍需要结合其他数据集和推理效率。

**参考来源：** DUTrack 论文，第 7 页，Table 7。`,

                docs: [
                    {
                        id: 'DEMO-C2',
                        filename: 'DUTrack.pdf',
                        page_number: 7,
                        section: 'Experimental Results - Table 7',

                        content: `||SiamFC|MDNet|Ocean|SiamPRN++|TrDimp|TransT|SimaTrack|VideoTrack|SeqTrack|ODTrack|DUTrack-256|DUTrack-384|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|GOT-10k*|34.8|29.9|61.1|51.7|67.1|67.1|68.6|72.9|74.7|77.0|76.7|77.8|
|UAV123|46.8|52.8|57.4|61.0|69.1|69.1|69.8|69.7|69.2|-|69.3|70.1|`,

                        source: ['演示摘录'],
                    },
                ],
            },
        ],
    }

]
