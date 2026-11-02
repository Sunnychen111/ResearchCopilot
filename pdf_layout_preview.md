
==============================
第 1 页
==============================
# **MPDTrack: Multi-Peak Disambiguation for Visual Tracking**

## **Anonymous submission**

#### **Abstract**

Similar Object Interference (SOI) is a key challenge in Single Object Tracking. Response-map-based trackers commonly select the highest-response position as the target center. However, when visually similar objects appear in the search region, a distractor may produce the highest response while the true target remains at a lower-ranked peak, causing localization errors and identity drift. We term this target selection uncertainty arising from multiple competing response peaks “multi-peak ambiguity.” To address it, we propose MPDTrack, a decision-level module that improves target center selection without modifying the host tracker. MPDTrack retains multiple high-confidence candidate peaks and jointly evaluates their response competition and temporal identity consistency through a selectively updated temporal identity memory and reliability-aware peak reranking. The resulting response is processed by the frozen host’s native decoding path. We further construct SOIEval, an evaluation dataset for targeted assessment of tracking robustness under SOI. Experiments with multiple representative host trackers demonstrate consistent improvements on SOIEval and competitive performance on general tracking benchmarks, supporting the effectiveness and cross-host applicability of decision-level multi-peak disambiguation across diverse tracking architectures.

## **Introduction**

Single Object Tracking (SOT) localizes a target in subsequent frames from its initial state and supports applications such as surveillance, autonomous driving, and robotic perception. Recent advances in deep representations and Transformer architectures have substantially improved performance on general tracking benchmarks (Chen et al. 2021; Ye et al. 2022; Zheng et al. 2024; Chen et al. 2025). Nevertheless, tracking remains difficult when visually similar objects surround the target, because the tracker must preserve target identity among competing candidates (Wang et al. 2025).

We study SOI at the center-selection stage of responsemap-based trackers, which typically choose the highestscoring position as the target center. Under SOI, similar distractors can produce competing peaks and outrank the true target. We term this score-map multi-peak ambiguity.

This is an anonymized submission for review purposes only. Distribution, citation, or public sharing of this manuscript is strictly prohibited. Copyright and publication details will appear in the final version if accepted.

<!-- Start of picture text -->
Original Frame Score Map Results<br>(a) Correct Top-1 selection                 |   Target Peak Rank: 1<br>(b) Multi-peak ambiguity                     |   Target Peak Rank: 2<br>(c) Target retained by MPDTrack        |   Target Peak Rank: 2<br>Ground Truth Host Tracker Top-1 Peak<br>Search Region MPDTrack Top-2–8 Peaks<br><!-- End of picture text -->

Figure 1: Qualitative illustration of score-map multi-peak ambiguity under SOI. In the ambiguous frame, the host’s Top-1 corresponds to a distractor, while the target remains among other high-response candidates and can still be recovered by MPDTrack through candidate reranking.

Tracking drift can arise from selecting the wrong peak even when the target response remains present.

To examine whether this ambiguity constitutes a systematic failure source, we conduct a multi-peak diagnostic analysis on sequences containing visually similar distractors. Figure 1 illustrates a representative SOI failure: a distractor occupies the Top-1 peak while the true target remains among other high-response candidates. We quantify this recoverability through a prediction-aware Top- _K_ oracle analysis under the standard online tracking rollout. Oracle@8 is a diagnostic upper bound that uses ground truth to select the


==============================
第 2 页
==============================
|Method|Top-1|Oracle@8|∆|
|---|---|---|---|
|OSTrack (Ye et al. 2022)|71.1|**73.7**|+2.6|
|ODTrack (Zheng et al. 2024)|73.2|**74.7**|+1.5|
|SUTrack (Chen et al. 2025)|74.0|**76.1**|+2.1|

Table 1: Prediction-aware Top-8 oracle analysis on LaSOT in terms of AUC.

highest-IoU box among the retained Top-8 score-map candidates, including the original Top-1 prediction. Table 1 shows that Oracle@8 exceeds Top-1 by 1.5–2.6 AUC points across representative trackers on LaSOT. This gap reveals a nonnegligible class of decision-level failures in which the target remains recoverable but the wrong peak is selected.

Based on this motivation, we propose MPDTrack, a decision-level module for multi-peak disambiguation under SOI. Rather than committing directly to the highest response, MPDTrack retains multiple candidate peaks and reranks them according to response competition and temporal consistency with a selectively updated target identity memory. The resulting response is then processed by the native decoding path of the frozen host tracker. Since MPDTrack operates on the host score map, search feature map, and regression maps, it requires neither additional modality inputs nor updates to the host model. A separate MPDTrack instance is trained for each host, while the same architecture and learning objective are used across the response-map-based tracking frameworks evaluated in this work.

To support targeted evaluation, we construct SOIEval, an evaluation dataset for tracking under SOI. It is derived from the test splits of LaSOT, LaSOT-Extension, and TNL2K (Fan et al. 2021; Wang et al. 2021), and focuses on sequences where visually similar distractors make target-identity preservation particularly challenging. During construction, multipeak responses within the search regions of representative trackers provide sequence-level SOI evidence for a fixed selection protocol that determines which complete video sequences are ultimately included.

In summary, this work characterizes response-map multipeak ambiguity under SOI, introduces MPDTrack to mitigate its adverse effects on tracking, and constructs SOIEval for targeted evaluation. The main contributions are as follows:

- We characterize recoverable SOI failures as response-map multi-peak ambiguity, revealing a decision-level failure mode in single-object tracking caused by incorrect selection among competing peaks.

- We propose MPDTrack, a multi-peak disambiguation module that combines Top- _K_ candidate generation, temporal identity memory, and reliability-aware candidate reranking for identity-aware center selection, thereby mitigating erroneous peak selection and identity drift caused by SOI in scenes containing visually similar distractors.

- We construct SOIEval, an evaluation dataset comprising sequences with visually similar distractors, and evaluate MPDTrack across multiple host trackers. MPDTrack improves tracking performance under SOI and remains competitive on general tracking benchmarks.

## **Related Work**

### **Transformer-based Visual Tracking**

Transformer-based architectures have become a dominant paradigm in single-object tracking by improving template–search interaction, target representation, and temporal reasoning. TransT and STARK introduced attention-based template–search matching (Chen et al. 2021; Yan et al. 2021), while OSTrack and SimTrack developed unified one-stream architectures (Ye et al. 2022; Chen et al. 2022). Subsequent studies further explored mixed attention, autoregressive prediction, online temporal modeling, and unified multi-task learning (Cui et al. 2022; Chen et al. 2023a; Wei et al. 2023; Zheng et al. 2024; Chen et al. 2025). Despite these advances, many response-map-based trackers still localize the target using the highest response. MPDTrack instead addresses the selection risk introduced by competing peaks and refines final localization without modifying the host representation.

### **Distractor-Aware Tracking and Association**

SOI weakens discrimination between targets and distractors and can cause identity drift (Wang, Hu, and Zhao 2023; Wang et al. 2025). Existing approaches process response maps, rank targets against hard negatives, associate candidates, or exploit multimodal cues, as in ATCTrack and DUTrack (Feng et al. 2025; Li et al. 2025b).

Response-map methods handle ambiguous peaks differently. FMCF searches multiple response peaks during redetection; RAN predicts tracking confidence from responsemap shapes; SPSTracker combines Peak Response Pooling with Boundary Response Truncation to suppress sub-peaks; and PRR regularizes feature responses to reinforce dominant peaks (Xing et al. 2022; Yang et al. 2022; Hu et al. 2020; Yu et al. 2024). In contrast, MPDTrack retains the Top- _K_ competing peaks and temporally reranks them at the decision stage; the resulting response is then decoded by the frozen host’s native decoding path to produce the final prediction.

Ranking-based trackers separate positive proposals from hard-negative distractors (Tang and Ling 2022), whereas candidate-association methods maintain richer identity states across frames. KeepTrack associates target and distractor candidates and uses association-derived confidence to manage online target-model updates; DMTrack combines oneshot detection with re-identification association and maintainspotential targetanddistractor tracklets;andMFDSTrack associates current candidates with historical target and distractor trajectories (Mayer et al. 2021; Zhang et al. 2021; Han et al. 2025). Unlike these methods, MPDTrack maintains only a target-centric temporal memory. It does not explicitly propagate distractor identities or maintain distractor trajectories, and it leaves the host tracker frozen. Consequently, MPDTrack treats response ambiguity as a local, decisionlevel peak reranking problem rather than full candidate association or tracking-by-detection.

### **Modular Enhancements for Visual Tracking**

Modular methods improve tracking robustness without redesigning the full host architecture. DTPTrack calibrates historical-state reliability and synthesizes temporal priors to


==============================
第 3 页
==============================
<!-- Start of picture text -->
Host Tracker MPDTrack<br>Candidate Features Identity Token<br>Template Image Search Image Multi-Peak Candidate Generation ···<br>Top-K Peaks ···<br>Similarity Matching<br>Candidate Cues<br>Patch Embedding GridSample( ) ··· Candidate Descriptor  ( ) Identity<br>···<br>Gap<br>Bootstrap features Reranking MLP Ratio<br>Transformer Encoder Temporal Identity Memory Reranking Probabilities Score<br>··· Rank<br>Memory Bank Selective Scan Ambiguity<br>Tracking Head ··· Host Response Fallback<br>Identity Token<br>(oldest) (newest) Mamba Aggregation ··· Alternative Selected Top-1 Retained<br>Size Map Offset Map Score Map Feature Map<br>Reliable Memory  update Sparse Response Host Response<br>Update<br>Prediction  ( )<br>Size Map Offset Map Selected Response Host Decoder<br>Host Outputs + +<br>(Host Outputs) (Host Outputs)<br><!-- End of picture text -->

Figure 2: Overview of MPDTrack. MPDTrack reranks retained response peaks using temporal identity memory. If RPR retains the input Top-1, the dense host response is preserved; otherwise, a sparse reranked response is used for the selected alternative. The host’s native decoding path processes the selected response together with the original size and offset maps.

suppress history-induced drift (Huang et al. 2026). HIPTrack retrieves historical prompts to enhance current target prediction, while HAFE aligns historical features to strengthen current-frame representations (Cai, Liu, and Wang 2024; Gong, Liu, and Xing 2026). NeighborTrack is a training-free post-processor that uses neighboring tracklets and bipartite matching to validate an already predicted result (Chen et al. 2023b). MPDTrack operates at a different stage: it intervenes after score-map prediction but before final host decoding, using a learned temporal identity memory to rerank the retained Top- _K_ peaks. Unlike feature enhancement, temporal prompting, or output-level validation, MPDTrack directly refines the target-center decision while leaving the host representation, parameters, and decoding procedure unchanged. This confines the intervention to candidate selection while preserving the host’s original localization pipeline throughout sequential tracking inference.

## **Methodology**

### **Overview**

MPDTrack converts the host tracker’s Top-1 localization into a closed-loop multi-candidate decision process. As shown in Figure 2, Multi-Peak Candidate Generation (MPCG) first retains the Top- _K_ response peaks and samples their local search features. Temporal Identity Memory (TIM) then compares these candidates with reliable historical target states, while Reliability-Aware Peak Reranking (RPR) combines the resulting identity evidence with response cues to select a candidate. The selected index determines the decoder input: the original dense host response when Top-1 is retained, or a sparse reranked response when an alternative is selected. The host’s native decoding path uses this response and the

original size and offset maps to produce the final box. Finally, only reliable selected states are admitted into TIM to support candidate selection in subsequent frames.

Here, **S** _t ∈_ R<sup>_H×W_</sup> is the score map received by MPDTrack before the native spatial processing of the host, **M**<sup>sz</sup> _t_<sup>and</sup><sup>**M**off</sup> _t_ are the original host regression maps, and **F** _t ∈_ R<sup>_C×Hf ×Wf_</sup> is the search feature map.

For reference, we denote the highest-response candidate in the input score map and the native host output as

where _Dh_ ( _·_ ) denotes the complete native decoding path of the host, including its fixed spatial score processing when applicable. Thus, **p**<sup>base</sup> _t_ denotes the input Top-1 candidate, whereas **b**<sup>base</sup> _t_ is the native host output obtained from the original dense response. MPDTrack therefore performs temporal multi-peak disambiguation at the error-prone responseselection stage while preserving the host parameters, regression maps, and native decoding procedure.

### **Multi-Peak Candidate Generation**

MPCG expands the original Top-1 decision into a compact set of competing locations. Given the input score map **S** _t_ , we first identify its local maxima using max pooling:


==============================
第 4 页
==============================
where Ω is the spatial domain of the score map and _κ_ denotes the local pooling-window size. After suppressing non-peak positions, we retain the _K_ highest-response peak locations:

where TopK returns locations in descending response order. Accordingly, **p** _t,_ 1 = **p** _t_<sup>base</sup> and _st,i_ = **S** _t_ ( **p** _t,i_ ). The candidate set therefore preserves the input Top-1 while exposing _K −_ 1 alternative peaks for subsequent disambiguation. For each candidate, we sample its spatially aligned feature from the search feature map:

where _G_ ( _·_ ) maps each peak to normalized feature-map coordinates, and Proj _h_ denotes the host-specific feature projection. TIM evaluates the resulting triplets _{_ ( **p** _t,i, st,i,_ **f** _t,i_ ) _}i_<sup>_K_</sup> =1 for temporal identity consistency, and RPR combines this evidence with response cues for reranking.

### **Temporal Identity Memory**

MPCG exposes multiple plausible locations, but currentframe response strength alone cannot determine which candidate preserves the target identity. TIM therefore maintains an ordered sequence of selectively admitted target features:

where **h** _j_ denotes an admitted target feature and _L_ mem is the memory capacity. TIM is bootstrapped from reliable host Top-1 states before reranking is enabled. Thereafter, a selected feature is appended only when the current prediction satisfies the update conditions defined below. When the capacity is exceeded, the oldest entry is removed, forming a selectively updated FIFO history.

The stored features are arranged chronologically as **Ψ** _t_ = [ **h** 1 _,_ **h** 2 _, . . . ,_ **h** _Lt−_ 1] and encoded by a residual Mamba block (Gu and Dao 2024):

Here, LN( _·_ ) denotes layer normalization, and [ _·_ ] _Lt−_ 1 extracts the final output state. The resulting token **Γ** _t_ provides a dynamic representation of the target identity across reliable observations accumulated over time.

TIM then measures the agreement between each current candidate and this temporal identity representation:

A larger _γt,i_ indicates greater temporal identity consistency and provides RPR with evidence for favoring the corresponding candidate during the subsequent reranking process.

### **Reliability-Aware Peak Reranking**

TIM provides temporal identity evidence, while the response scores describe the current competition among candidates. RPR integrates these cues to estimate a selection probability for each retained peak. We first standardize the Top- _K_ response scores before cue construction:

where _µt_ and _σt_ are the mean and standard deviation of the candidate scores, and _ϵ >_ 0 prevents numerical instability when the score variance is small.

We then define the response gap, relative score, response rank, and frame-level ambiguity as

Together with the temporal identity similarity _γt,i_ from TIM, these quantities form the candidate descriptor

The descriptor captures standardized response strength, competition with the input Top-1 peak, temporal identity consistency, response rank, and frame-level ambiguity. Its continuous components are fused by the subsequent multilayer perceptron (MLP) without cue-specific thresholds.

An MLP maps each descriptor to a reranking logit, followed by a candidate-wise softmax normalization:

The reranked candidate and its probability margin are

**Host Response Fallback.** The reranking probabilities are embedded into a sparse response over the retained locations:

Output routing depends only on whether RPR selects an alternative candidate. Let _gt_ = I[ _i_<sup>_⋆_</sup> _t̸_<sup>=1].Theresponse</sup> provided to the host’s native decoding path is

and the final box is then produced by the same decoding path:

When the input Top-1 candidate is retained, **S**<sup>dec</sup> _t_ = **S** _t_ , preserving the native host output. When an alternative is selected, the sparse reranked response is decoded with the original size and offset maps. This routing rule depends solely on the selected index and introduces no additional probability, confidence, or margin threshold.

**Reliable Memory Update.** Output routing and memory admission are separate decisions. Let _qt_ = _πt,i_<sup>_⋆_</sup> _t_<sup>denote the</sup> probability assigned to the selected candidate. The corresponding feature is admitted into TIM only when

where _Ut_ represents the temporal update policy, including the initial bootstrap and periodic refresh conditions. We set _τq_ = 0 _._ 55, _τm_ = 0 _._ 03, and _τα_ = 0 _._ 85 for all experiments


==============================
第 5 页
==============================
based on training-set rollouts and keep them fixed throughout evaluation. The memory evolves as

where _∥_ denotes chronological append. Reliability controls admission to TIM, whereas FIFO discards the oldest state once the memory is full.

### **Training and Inference**

With the host tracker frozen, a host-specific MPDTrack instance is trained for 40 offline epochs and subsequently refined for six rollout epochs.

**Offline Candidate-Level Training.** For each frame, the frozen host extracts the Top- _K_ candidates and decodes **b** _t,i_ from its regression maps at each peak. Let _ot,i_ = IoU( **b** _t,i,_ **b** _t_<sup>gt)and</sup><sup>_i_IoU</sup> _t_ = arg max _i ot,i_ . A frame is initially valid if its ground truth lies inside the search crop and max _i ot,i ≥_ 0 _._ 3.

Utility-aware candidate labels assign _yt_ = _i_<sup>IoU</sup> _t_ only to reliable non-Top-1 improvements, retain Top-1 when it is already reliable, and exclude uncertain weak-gain cases; all thresholds are provided in the supplementary material.

Let _V_ denote the retained training frames. Candidate classification uses the standard cross-entropy loss _L_ ce with target _yt_ , together with a margin-ranking loss (Tang and Ling 2022). Let _V_ sw _⊆V_ denote the eligible switch frames satisfying _yt >_ 1 and _ot,yt > ot,_ 1. The ranking loss is

where _µ_ = 0 _._ 2, and the loss is set to zero when _V_ sw = ∅.

Let _ct_ = I[ _yt >_ 1] for _t ∈V_ . A training-only auxiliary head outputs **a** _t_ = [ _a_<sup>sw</sup> _t_<sup>_, a_</sup> _t_<sup>keep</sup> ]<sup>_⊤_</sup> , with target **y** _t_<sup>aux</sup> = [ _ct,_ 1 _− ct_ ]<sup>_⊤_</sup> and equal weights **w** = [0 _._ 5 _,_ 0 _._ 5]<sup>_⊤_</sup> assigned to the switch and retention loss terms:

Here, _T_ aux is the auxiliary temperature, and BCE denotes element-wise binary cross-entropy applied to the switch and keep logits from the auxiliary head.

All loss hyperparameters and memory settings are fixed before evaluation. This auxiliary supervision introduces no additional inference-time threshold.

**Online Rollout Refinement.** We further refine MPDTrack for six epochs on short sequential rollouts to reduce the discrepancy between offline candidate training and closed-loop inference. The same candidate-level and auxiliary objectives are retained during the rollout stage. Rollouts progressively replace reference-guided states with model-generated predictions, allowing the model to learn from accumulated localization and memory errors.

**Inference.** At test time, the learnable parameters of both the host tracker and MPDTrack remain fixed. MPDTrack performs candidate generation, temporal identity matching, and reranking, while the state of TIM is selectively updated according to the reliability conditions defined above.

## **Experiments**

We evaluate MPDTrack on SOIEval and four standard tracking benchmarks. SOIEval focuses on challenging sequences affected by SOI, whereas GOT-10K (Huang, Zhao, and Huang 2019), LaSOT, LaSOT-Extension, and TNL2K examine whether the improvements persist under general tracking conditions. We further evaluate cross-host generalization and component effectiveness.

### **Experimental Setup**

**Evaluation protocols.** We report the area under the success curve (AUC), normalized center precision ( _P_ Norm), and raw center precision ( _P_ ) on LaSOT, LaSOT-Extension, TNL2K, and SOIEval. On GOT-10K, we report average overlap (AO) and success rates at 0 _._ 5 and 0 _._ 75 IoU ( _SR_ 0 _._ 5 and _SR_ 0 _._ 75). In Table 2, unstarred results are recomputed from publicly released sequence-level predictions using the same toolkit; in all tables,<sup>_∗_</sup> marks officially reproduced results, and<sup>VL</sup> denotes vision-language trackers.

**Implementation details.** MPDTrack uses the frozen host’s score map before native spatial processing, together with its size, offset, and search features. Each host uses a separately trained instance with its native search-feature dimension. For LaSOT, LaSOT-Extension, TNL2K, and SOIEval, MPDTrack is trained on the LaSOT and GOT-10K training splits. For GOT-10K, we use the host’s official checkpoint and train MPDTrack exclusively on the GOT-10K training split, following the official protocol. Instances share the same architecture and objective but use separate checkpoints. Training uses 40 offline and six rollout epochs.

Throughout evaluation, we set _K_ = 8 and _L_ mem = 16. All training and inference thresholds are fixed before evaluation, and their values are provided in the supplementary material. Sensitivity analyses of _K_ and _L_ mem are also reported. No test sequence from any reported benchmark, including SOIEval, is used for training, tuning, or checkpoint selection. Training and reproduced efficiency measurements use an NVIDIA RTX 4090 GPU and an Intel Core i9-14900KF CPU. The best and second-best results are shown in boldface and underlined, respectively. “–” denotes unavailable results.

### **Construction and Analysis of SOIEval**

To evaluate tracking robustness under SOI, we construct SOIEval from the test sets of LaSOT, LaSOT-Extension, and TNL2K. It contains complete sequences where visually similar distractors challenge target identity. Related datasets differ in construction and scope. DiDi distills benchmark sequences using DINOv2-based target–background similarity evidence (Videnovic, Lukezic, and Kristan 2025), whereas SOIBench uses semantically annotated LaSOT frames to study semantic guidance (Wang et al. 2025). SOIEval instead uses multitracker multi-peak responses only for automated mining and evaluates trackers under their standard closed-loop protocols without requiring additional semantic annotations.

SOIEval construction uses neither MPDTrack predictions, intervention decisions, nor performance gains. Instead, we mine candidate frames exclusively from the original outputs of SUTrack, OSTrack, and ODTrack, which serve as


==============================
第 6 页
==============================
|Method|Pub.||SOIEval||L|aSOT-SO|I|TN|L2K-SO|I|LaS|OT-Ext-S|OI|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||AUC|_P_N_orm_|P|AUC|_P_N_orm_|P|AUC|_P_N_orm_|P|AUC|_P_N_orm_|P|
|MPDTrack-SU-B384 (Ours)|–|**57.8**|**68.5**|**63.5**|**62.0**|68.4|67.5|**58.1**|**75.1**|**63.6**|**48.2**|**53.7**|55.3|
|SUTrack-B384<sup>_∗_</sup>(Chen et al. 2025)|AAAI’25|56.8|66.9|62.6|61.5|67.9|68.0|57.5|73.6|62.2|42.9|47.8|49.4|
|ATCTrack-B<sup>VL </sup>(Feng et al. 2025)|ICCV’25|56.3|66.9|62.0|60.0|66.5|66.6|57.3|73.6|60.9|47.4|52.9|56.0|
|DUTrack-B384<sup>VL </sup>(Li et al. 2025b)|CVPR’25|56.1|66.6|61.8|60.8|68.2|67.6|57.8|73.9|61.8|43.6|47.9|51.1|
|MambaLCT-B384 (Li et al. 2025a)|AAAI’25|55.6|62.8|63.2|59.9|67.7|66.9|–|–|–|47.6|**53.7**|**56.3**|
|TemTrack-B384 (Xie et al. 2025)|AAAI’25|51.9|57.6|58.2|56.7|63.2|62.4|–|–|–|43.0|47.4|50.3|
|AQATrack-B384 (Xie et al. 2024)|CVPR’24|50.6|60.9|55.4|57.4|64.5|63.7|47.4|62.6|49.1|45.3|50.8|53.8|
|LoRAT-B378 (Lin et al. 2024)|ECCV’24|51.6|62.3|55.5|56.7|62.9|60.7|50.2|67.2|52.3|45.2|50.5|53.0|
|ODTrack-B384 (Zheng et al. 2024)|AAAI’24|54.0|65.4|59.8|61.9|**69.2**|**69.2**|52.0|69.0|54.8|44.5|50.2|53.8|
|OSTrack-B384 (Ye et al. 2022)|ECCV’22|48.5|58.1|52.0|55.6|62.3|61.2|–|–|–|41.8|45.1|48.3|

Table 2: Comparison on SOIEval and its source subsets; MPDTrack-SU-B384 uses a frozen SUTrack-B384 host.

|Method|Pub.||GOT-1|0K||LaSOT||La|SOT-E|xt|TNL|2K|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||AO|_SR_0_._5|_SR_0_._75|AUC|_P_N_orm_|P|AUC|_P_N_orm_|P|AUC|P|
|MPDTrack-SU-B384 (Ours)|–|**80.2**|**89.1**|**80.2**|**74.7**|**86.2**|81.2|53.1|63.4|60.8|**67.7**|**74.2**|
|SUTrack-B384<sup>_∗_</sup>(Chen et al. 2025)|AAAI’25|79.3|88.0|80.0|74.0|83.6|81.9|51.4|61.5|58.5|65.6|69.3|
|DTPTrack-B224 (Huang et al. 2026)|CVPR’26|76.5|87.6|74.9|74.3|83.6|80.7|–|–|–|60.3|–|
|ADTrack-384<sup>VL </sup>(Zhang et al. 2026)|AAAI’26|76.1|–|–|72.6|–|80.3|51.2|–|59.1|66.1|71.5|
|MoDTrack-B384 (Yang et al. 2026)<br>|AAAI’26|76.3|86.4|75.6|74.4|84.6|81.5|**53.2**|63.9|**61.3**|59.7|62.3|
|DUTrack-B384<sup>VL </sup>(Li et al. 2025b)|CVPR’25|77.8|–|–|74.1|84.9|**82.9**|52.5|63.6|60.5|65.6|71.9|
|ARPTrack-B256 (Liang et al. 2025)|CVPR’25|77.7|87.3|74.3|72.6|81.4|78.5|52.0|62.9|58.7|–|–|
|LoRATv2-B384 (Lin et al. 2025)|NeurIPS’25|75.8|85.7|75.4|74.3|83.6|80.9|–|–|–|60.9|64.9|
|AQATrack-384 (Xie et al. 2024)|CVPR’24|76.0|85.2|74.9|72.7|82.9|80.2|52.7|64.2|60.8|59.2|–|
|HIPTrack-B384 (Cai, Liu, and Wang 2024)|CVPR’24|77.4|88.0|74.5|72.7|82.9|79.5|53.0|**64.3**|60.6|–|–|
|ODTrack-B384 (Zheng et al. 2024)|AAAI’24|77.0|87.9|75.1|73.2|83.2|80.6|52.4|63.9|60.1|60.9|–|
|ARTrack-B384 (Wei et al. 2023)|CVPR’23|75.5|84.3|74.3|72.6|81.7|79.1|51.9|62.0|58.5|59.8|–|
|NeighborTrack-B384 (Chen et al. 2023b)|CVPRW’23|75.7|85.7|73.3|72.3|81.8|78.1|–|–|–|–|–|
|OSTrack-B384 (Ye et al. 2022)|ECCV’22|73.7|83.2|70.8|71.1|81.1|77.6|50.5|61.3|57.6|–|–|

Table 3: General-benchmark comparison with representative recent trackers.

the evidence-generating trackers. For each tracker, we jointly consider four complementary signals: 1) failure of the original Top-1 localization; 2) recoverability of the true target among the Top- _K_ response peaks; 3) the degree of scoremap multi-peak ambiguity; and 4) cross-tracker agreement on the detected ambiguity.

A candidate frame is regarded as consensus SOI evidence only when it is supported by at least two of the three evidence-generating trackers. Sequence-level selection is then performed based on the accumulated consensus evidence within each sequence. The resulting SOIEval contains 150 sequences, including 55 from LaSOT, 30 from LaSOTExtension, and 65 from TNL2K. The complete frame-level mining criteria, sequence-selection procedure, and thresholds are provided in the supplementary material.

Top- _K_ recoverability measures whether a Top-1 failure remains recoverable among retained high-response candidates. Among frames where the original Top-1 prediction has an IoU below the failure threshold, Rec@K denotes the proportion of such frames for which at least one box decoded from the Top-K peaks using the host regression maps achieves an IoU of at least _τ_ rec with the ground truth.

Compared with the complete source test sets, SOIEval contains a higher concentration of recoverable multi-peak failures. Averaged over the three evidence-generating trackers, the localization failure rate and Top-2/Top-1 ratio increase from 29.1% and 0.261 to 42.7% and 0.356, respectively. Rec@8 increases from 8.1% to 13.6%, while the mean frame-level Oracle-IoUGain@8 rises from 0.030 to 0.067. These statistics indicate that SOIEval concentrates cases where the native Top-1 localization fails while the target remains recoverable among the retained response peaks.

### **Comparison on SOIEval**

Table 2 compares MPDTrack with representative trackers, including the vision-language trackers ATCTrack and DUTrack, on SOIEval and its three source subsets. It achieves the best overall AUC, _P_ Norm, and precision on SOIEval among the trackers, as well as the highest AUC across all three subsets. It also remains competitive in _P_ Norm and precision on these subsets. Overall, these results demonstrate performance advantages across diverse SOI scenarios and show that explicit multi-peak refinement is effective under strong candidate competition across challenging sequences.


==============================
第 7 页
==============================
|Method|Params.|FPS||LaSOT|||SOIEval||
|---|---|---|---|---|---|---|---|---|
||||AUC|_P_N_orm_|P|AUC|_P_N_orm_|P|
|SUTrack-B384<sup>_∗_</sup>(Chen et al. 2025)|89M|63.0|74.0|83.6|81.9|56.8|66.9|62.6|
|**+ MPDTrack**|+1.7M|57.3 (_−_5_._7)|74.7 (+0_._7)|86.2 (+2_._6)|81.2 (_−_0_._7)|57.8 (+1_._0)|68.5 (+1_._6)|63.5 (+0_._9)|
|OSTrack-B384 (Ye et al. 2022)|93M|96.4|71.1|81.1|77.6|48.5|58.1|52.0|
|**+ MPDTrack**|+3.7M|91.3 (_−_5_._1)|71.9 (+0_._8)|81.3 (+0_._2)|77.5 (_−_0_._1)|49.0 (+0_._5)|58.5 (+0_._4)|52.4 (+0_._4)|
|SUTrack-B224<sup>_∗_</sup>(Chen et al. 2025)|89M|93.2|73.0|82.6|80.1|55.9|66.3|60.9|
|**+ MPDTrack**|+1.7M|85.4 (_−_7_._8)|73.6 (+0_._6)|85.9 (+3_._3)|80.0 (_−_0_._1)|56.9 (+1_._0)|67.9 (+1_._6)|62.3 (+1_._4)|
|EVPTrack-B224<sup>_∗_</sup>(Shi et al. 2024)|73M|110.5|70.4|80.9|77.2|50.5|60.3|53.7|
|**+ MPDTrack**|+1.7M|105.2 (_−_5_._3)|71.3 (+0_._9)|81.2 (+0_._3)|77.4 (+0_._2)|51.0 (+0_._5)|60.9 (+0_._6)|54.4 (+0_._7)|

Table 4: Generalizability analysis of MPDTrack. It consistently improves AUC across three host trackers and two search resolutions with limited parameter overhead and moderate FPS reductions.

|Evidence Support|Eval. Host|Seq.|Base|MPD|∆AUC|
|---|---|---|---|---|---|
|OSTrack + ODTrack|SUTrack|112|55.6|57.8|+2.2|
|SUTrack + ODTrack|OSTrack|89|45.9|46.6|+0.7|
|Full SOIEval|EVPTrack<sup>_†_</sup>|150|50.5|51.0|+0.5|

Table 5: Bias-controlled evaluation on SOIEval using hostexcluded evidence for SUTrack and OSTrack; _†_ denotes a host not involved in evidence mining.

|Variant|LaSOT|-Ext-SOI|LaSO|T-Ext|
|---|---|---|---|---|
||AUC|_P_N_orm_|AUC|_P_N_orm_|
|Full MPDTrack|**48.2**|**53.7**|**53.1**|**63.4**|
|Mamba_→_GRU|46.1|51.4|51.9|58.3|
|Mamba_→_EMA|46.5|51.6|50.5|56.5|
|w/o Dynamic Memory|47.5|52.8|52.3|62.6|
|w/o Host Response Fallback|45.9|51.4|49.3|58.9|
|<br>w/o RPR|43.4|47.9|51.0|60.5|

### **Comparison on General Tracking Benchmarks**

To determine generalization beyond SOI-focused evaluation, Table 3 compares MPDTrack with representative recent trackers on four general benchmarks. Relative to the reproduced SUTrack-B384 baseline, MPDTrack improves the primary overlap metric by 0.9, 0.7, 1.7, and 2.1 points on GOT-10K, LaSOT, LaSOT-Extension, and TNL2K, respectively. These gains show that multi-peak decision refinement also benefits standard tracking scenarios.

### **Cross-host Evaluation**

To examine whether MPDTrack generalizes across host architectures and search resolutions, Table 4 reports the corresponding results. MPDTrack improves AUC on both LaSOT and SOIEval in all settings, with 1.7–3.7M additional parameters and moderate FPS reductions. Raw center precision (P) decreases slightly in three LaSOT host-resolution settings, indicating that the gains are more consistent in overlap robustness than in center precision. OSTrack incurs the larger overhead because its higher-dimensional search features require a larger host-specific projection. Overall, these results support broad cross-host applicability.

### **Bias-Controlled Evaluation**

To assess tracker-specific selection bias, we restrict SUTrack and OSTrack to sequences containing at least two consensus SOI frames supported by the other two mining trackers, while evaluating EVPTrack on the full SOIEval because it was not involved in evidence mining. As shown in Table 5, MPDTrack improves AUC for the three hosts by 2.2, 0.7, and 0.5 points, respectively, suggesting that the gains are not solely induced by the trackers used for dataset construction.

Table 6: Ablation of MPDTrack on LaSOT-Ext-SOI and LaSOT-Extension under a shared inference protocol.

### **Ablation Studies**

To assess component effectiveness, Table 6 reports the ablation results. Removing RPR causes the largest drop on LaSOT-Extension-SOI, highlighting the importance of identity-aware candidate discrimination. Removing Host Response Fallback lowers AUC by 2.3 and 3.8 points on LaSOT-Extension-SOI and LaSOT-Extension, respectively, and changes the predicted trajectories on most LaSOTExtension sequences, showing that unnecessary redecoding in Top-1-retained cases perturbs online states and accumulates errors across frames. A GRU, an EMA-based memory, and the absence of dynamic memory all lead to lower performance. Sensitivity analysis shows that AUC ranges from 47.4 to 48.2 across memory lengths, while performance decreases when _K >_ 8. All other hyperparameters were fixed beforehand and unchanged across evaluations.

## **Conclusion**

This work revisits localization in response-map-based tracking and characterizes multi-peak ambiguity, rather than the complete disappearance of target responses, as an important failure mode under SOI. We propose MPDTrack, a decision-level module that combines temporal identity memory with reliability-aware peak reranking while keeping the host tracker frozen. We further construct SOIEval for targeted evaluation. Experiments show AUC gains across multiple hosts, supporting decision-level multi-peak disambiguation as a promising direction for robust tracking.


==============================
第 8 页
==============================
## **References**

Cai, W.; Liu, Q.; and Wang, Y. 2024. HIPTrack: Visual tracking with historical prompts. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 19258–19267.

Chen, B.; Li, P.; Bai, L.; Qiao, L.; Shen, Q.; Li, B.; Gan, W.; Wu, W.; and Ouyang, W. 2022. Backbone is all your need: A simplified architecture for visual object tracking. In _European Conference on Computer Vision_ , 375–392. Springer.

Chen, X.; Kang, B.; Geng, W.; Zhu, J.; Liu, Y.; Wang, D.; and Lu, H. 2025. SUTrack: Towards simple and unified single object tracking. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 39, 2239–2247.

Chen, X.; Peng, H.; Wang, D.; Lu, H.; and Hu, H. 2023a. SeqTrack: Sequence to sequence learning for visual object tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 14572–14581. Chen, X.; Yan, B.; Zhu, J.; Wang, D.; Yang, X.; and Lu, H. 2021. Transformer tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 8126–8135.

Chen, Y.-H.; Wang, C.-Y.; Yang, C.-Y.; Chang, H.-S.; Lin, Y.L.; Chuang, Y.-Y.; and Liao, H.-Y. M. 2023b. NeighborTrack: Single object tracking by bipartite matching with neighbor tracklets and its applications to sports. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops_ , 5139–5148.

Cui, Y.; Jiang, C.; Wang, L.; and Wu, G. 2022. MixFormer: End-to-end tracking with iterative mixed attention. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 13608–13618.

Fan, H.; Bai, H.; Lin, L.; Yang, F.; Chu, P.; Deng, G.; Yu, S.; Harshit; Huang, M.; Liu, J.; et al. 2021. LaSOT: A high-quality large-scale single object tracking benchmark. _International Journal of Computer Vision_ , 129(2): 439–461.

Feng, X.; Hu, S.; Li, X.; Zhang, D.; Wu, M.; Zhang, J.; Chen, X.; and Huang, K. 2025. ATCTrack: Aligning TargetContext Cues with Dynamic Target States for Robust VisionLanguage Tracking. In _Proceedings of the IEEE/CVF International Conference on Computer Vision_ , 19850–19861.

Gong, X.; Liu, Y.; and Xing, G. 2026. A history-aware framework with multi-scale hybrid attention for robust visual object tracking. _Expert Systems with Applications_ , 305: 130914.

Gu, A.; and Dao, T. 2024. Mamba: Linear-time sequence modeling with selective state spaces. In _First Conference on Language Modeling_ .

Han, Y.; Cai, M.; Wu, J.; Bai, Z.; Zhuo, T.; Zhang, H.; and Zhang, Y. 2025. Visual Object Tracking With Multi-Frame Distractor Suppression. _IEEE Transactions on Circuits and Systems for Video Technology_ , 35(3): 2556–2569.

Hu, Q.; Zhou, L.; Wang, X.; Mao, Y.; Zhang, J.; and Ye, Q. 2020. SPSTracker: Sub-peak suppression of response map for robust object tracking. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 34, 10989– 10996.

Huang, L.; Zhao, X.; and Huang, K. 2019. GOT-10k: A large high-diversity benchmark for generic object tracking in the wild. _IEEE Transactions on Pattern Analysis and Machine Intelligence_ , 43(5): 1562–1577.

Huang, Y.; Lin, L.; Zhuang, W.; He, Z.; and Li, X. 2026. Drift-Resilient Temporal Priors for Visual Tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 6847–6856.

Li, X.; Zhong, B.; Liang, Q.; Li, G.; Mo, Z.; and Song, S. 2025a. MambaLCT: Boosting tracking via long-term context state space model. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 39, 4986–4994.

Li, X.; Zhong, B.; Liang, Q.; Mo, Z.; Nong, J.; and Song, S. 2025b. Dynamic updates for language adaptation in visuallanguage tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 19165– 19174.

Liang, S.; Bai, Y.; Gong, Y.; and Wei, X. 2025. Autoregressive Sequential Pretraining for Visual Tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 7254–7264.

Lin, L.; Fan, H.; Zhang, Z.; Huang, Y.; Wang, Y.; Xu, Y.; and Ling, H. 2025. LoRATv2: Enabling Low-Cost Temporal Modeling in One-Stream Trackers. In Belgrave, D.; Zhang, C.; Lin, H.; Pascanu, R.; Koniusz, P.; Ghassemi, M.; and Chen, N., eds., _Advances in Neural Information Processing Systems_ , volume 38, 119714–119732. Curran Associates, Inc.

Lin, L.; Fan, H.; Zhang, Z.; Wang, Y.; Xu, Y.; and Ling, H. 2024. Tracking meets LoRA: Faster training, larger model, stronger performance. In _European Conference on Computer Vision_ , 300–318. Springer.

Mayer, C.; Danelljan, M.; Paudel, D. P.; and Van Gool, L. 2021. Learning target candidate association to keep track of what not to track. In _Proceedings of the IEEE/CVF International Conference on Computer Vision_ , 13444–13454.

Shi, L.; Zhong, B.; Liang, Q.; Li, N.; Zhang, S.; and Li, X. 2024. Explicit visual prompts for visual object tracking. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 38, 4838–4846.

Tang, F.; and Ling, Q. 2022. Ranking-based siamese visual tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 8741–8750.

Videnovic, J.; Lukezic, A.; and Kristan, M. 2025. A distractor-aware memory for visual object tracking with SAM2. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 24255–24264.

Wang, X.; Shu, X.; Zhang, Z.; Jiang, B.; Wang, Y.; Tian, Y.; and Wu, F. 2021. Towards more flexible and accurate object tracking with natural language: Algorithms and benchmark. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 13763–13773.

Wang, Y.; Hu, S.; Jia, S.; Xu, P.; Ma, H.; Ma, Y.; Zhang, J.; Lu, X.; and Zhao, X. 2025. SOI Is the Root of All Evil: Quantifying and Breaking Similar Object Interference in Single Object Tracking. arXiv:2508.09524.


==============================
第 9 页
==============================
Wang, Y.; Hu, S.; and Zhao, X. 2023. Rethinking similar object interference in single object tracking. In _Proceedings of the 2023 7th International Conference on Computer Science and Artificial Intelligence_ , 251–258.

Wei, X.; Bai, Y.; Zheng, Y.; Shi, D.; and Gong, Y. 2023. Autoregressive visual tracking. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 9697–9706.

Xie, J.; Zhong, B.; Liang, Q.; Li, N.; Mo, Z.; and Song, S. 2025. Robust tracking via Mamba-based context-aware token learning. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 39, 8727–8735.

Xie, J.; Zhong, B.; Mo, Z.; Zhang, S.; Shi, L.; Song, S.; and Ji, R. 2024. Autoregressive queries for adaptive tracking with spatio-temporal transformers. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 19300–19309.

Xing, W.; Zhang, H.; Chen, H.; Yang, Y.; and Yuan, D. 2022. Feature adaptation-based multipeak-redetection spatial-aware correlation filter for object tracking. _Neurocomputing_ , 488: 299–314.

Yan, B.; Peng, H.; Fu, J.; Wang, D.; and Lu, H. 2021. Learning spatio-temporal transformer for visual tracking. In _Proceedings of the IEEE/CVF International Conference on Computer Vision_ , 10448–10457.

Yang, H.; Zhong, B.; Liang, Q.; Hu, X.; Tan, Y.; Xia, H.; and Song, S. 2026. Motion-aware object tracking via motion and geometry-aware cues. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 40, 11604–11612.

Yang, X.; Song, Y.; Zhang, Z.; Zhao, Y.; Li, L.; and Li, W. 2022. Robust correlation filter tracking based on response map analysis network. _Signal Processing: Image Communication_ , 108: 116768.

Ye, B.; Chang, H.; Ma, B.; Shan, S.; and Chen, X. 2022. Joint feature learning and relation modeling for tracking: A onestream framework. In _European Conference on Computer Vision_ , 341–357. Springer.

Yu, J.; Yao, J.; Zhao, C.; Zhao, X.; and Hu, Q. 2024. Peak response regularization for localization. _Scientific Reports_ , 14(1): 14936.

Zhang, G.; Zhong, B.; Yang, S.; Wang, Y.; and Bai, T. 2026. Aware distillation for robust vision-language tracking under linguistic sparsity. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 40, 12439–12447.

Zhang, Z.; Zhong, B.; Zhang, S.; Tang, Z.; Liu, X.; and Zhang, Z. 2021. Distractor-aware fast tracking via dynamic convolutions and MOT philosophy. In _Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition_ , 1024–1033.

Zheng, Y.; Zhong, B.; Liang, Q.; Mo, Z.; Zhang, S.; and Li, X. 2024. ODTrack: Online dense temporal token learning for visual tracking. In _Proceedings of the AAAI Conference on Artificial Intelligence_ , volume 38, 7588–7596.
