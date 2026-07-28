# Paper A GC-GraphFormer Design Specification

**Status:** Approved design  
**Approval date:** 2026-07-28  
**Project:** Paper A - reliable inverse design of graded TPMS  
**Implementation window:** 14-16 weeks  
**Primary implementation root:** `paper_A_reliable_inverse_design/`

## 1. Decision Summary

Paper A will replace neither the inverse diffusion model nor the existing forward models by name alone. It will introduce a geometry-compiler-informed forward model, provisionally named **GC-GraphFormer**, and integrate it with the conditional diffusion generator through a generation-compilation-prediction-risk-ranking loop.

The central scientific hypothesis is:

> Relations supplied by the graded-TPMS geometry compiler provide a useful inductive bias. Combined with low-cost geometry pretraining, this bias can improve out-of-distribution nonlinear-response prediction under limited high-fidelity data and enable uncertainty-aware, manufacturing-robust inverse design.

The method has four linked contributions:

1. A sample-specific parameter-to-geometry relation graph derived from the deterministic geometry compiler.
2. Geometry-only self-supervised pretraining followed by nonlinear-mechanics fine-tuning.
3. Strain-resolved relation attribution validated by prospective Abaqus counterfactuals.
4. Conditional diffusion candidate generation followed by uncertainty and CVaR-aware robust ranking.

The graph, pretraining, interpretation and risk-ranking claims are conditional on the preregistered experiments in this specification. Packaging the same nine-column vector as a PyG object is not considered an innovation.

## 2. Evidence and Design Rationale

The current `TPMSForwardTransformer` is a parameter-token Transformer. It embeds nine scalar columns, adds learned parameter-type embeddings and predicts a 20-point curve from a CLS token. It has no graph edges or message-passing topology.

The current dense GAT treats the same nine scalar columns as graph nodes and supplies an all-ones adjacency matrix. Consequently, all parameter pairs communicate equally before learned attention is applied. This model is retained as a baseline but is not described as a topology GNN.

The public workbooks contain 25,555 precision-expanded rows but only 5,111 inferred base finite-element structures. The legacy public test curves all occur in the public training workbook. Therefore:

- all precision variants of a base FE structure must remain in one split;
- the public test result is labelled `legacy_split` and is not primary evidence;
- the primary historical mechanics sample size is 5,111 base FE structures;
- prospective Abaqus analyses provide the external OOD and robust-design evidence.

Prior work also constrains the novelty claim:

- GraphMetaMat already represents real metamaterial topology in graph space;
- T2G-Former already organizes generic tabular features into learned relation graphs;
- MetaFO already combines graph representations, forward prediction and OOD-oriented metamaterial learning;
- DiffuMeta already demonstrates conditional DiT generation from target mechanical properties without a separate forward surrogate, using a much larger high-fidelity dataset and FE validation.

GC-GraphFormer is differentiated by using a deterministic graded-TPMS compiler to construct sample-specific, finite-difference relation edges and by validating their predictive and explanatory value under leakage-free and prospective OOD protocols.

## 3. Scope and Boundaries

### 3.1 Included

- The three graded-Gyroid generation methods from Small.
- Compression responses from 0% to 25% strain, represented by 20 non-zero stress samples.
- Method-dependent independent variables and five compiler-derived geometry descriptors.
- Group-IID, Parameter-OOD, Curve-OOD and prospective Abaqus OOD evaluation.
- Geometry-only pretraining without FE labels.
- Forward deep-ensemble uncertainty and calibration.
- Conditional diffusion candidate generation.
- Nominal, mean-robust and CVaR-robust candidate ranking.
- A 225-analysis preregistered Abaqus budget plus at most 15 reserve runs.
- Small-scale repeated SLS TPU compression experiments.

### 3.2 Excluded

- DiffuMeta-style free algebraic surface grammar, which belongs to Paper B.
- Arbitrary 3D spatial coefficient fields or regional collapse-order control.
- Mesh-, voxel- or finite-element-node Graph Transformers as the primary Paper A model.
- RL, MCTS and gradient-guided diffusion in the main method.
- Treating derived geometry descriptors as freely generated inverse variables.
- Claiming causal discovery, topology learning or universal metamaterial generalization.
- Selecting an application before the mechanical results justify one.

## 4. Domain Model and Terminology

### 4.1 Independent design variables

The independent variable representation is

\[
x=[c_0,c_1,c_2,w].
\]

The public columns `Vx`, `Vy` and `Vz` are referred to in the manuscript as \(c_0,c_1,c_2\), because the supplementary formulation defines them as bias-field values at three axial positions rather than three Cartesian vector components.

The method-specific valid variables are:

| Generation method | Independent variables | Enforced constraints |
|---|---|---|
| Method 1 | \(c_0,c_1,c_2\) | \(w=0\) |
| Method 2 | \(c,w\) | \(c_0=c_1=c_2=c\) |
| Method 3 | \(c_0,c_1,c_2,w\) | Parameter bounds only |

### 4.2 Derived geometry descriptors

The geometry compiler recomputes:

- relative volume;
- relative surface area;
- average thickness;
- pore diameter;
- mean area.

These quantities are valid design-time inputs because they are deterministically available from generated geometry. They are not target leakage and are never independently sampled or decoded by the inverse model.

### 4.3 Response descriptors

Response descriptors are extracted from the target or realized stress-strain curve and remain distinct from geometry descriptors. They include initial stiffness, peak stress and strain, plateau stress, energy absorption, softening length, densification state and a reproducible response-regime label.

## 5. Graph Construction

### 5.1 Graph object

Each design is stored as a `torch_geometric.data.Data` object and batched with `torch_geometric.data.Batch`. A homogeneous PyG graph with explicit `node_type` and `edge_type` fields is preferred over `HeteroData` for the first implementation because the node vocabulary is fixed and the selected attention operator must consume continuous edge attributes directly.

The object contract is:

```python
Data(
    x=node_features,
    node_type=node_type,
    edge_index=edge_index,
    edge_type=edge_type,
    edge_attr=edge_features,
    method_id=method_id,
    y_curve=stress_curve,
    y_descriptors=response_descriptors,
    descriptor_mask=response_descriptor_mask,
    base_structure_id=base_structure_id,
)
```

### 5.2 Nodes

Each graph contains 11 nodes:

1. one generation-method node;
2. four independent-variable nodes \(c_0,c_1,c_2,w\);
3. five derived-geometry nodes;
4. one global readout node.

Node features contain:

- standardized scalar value;
- value-validity mask;
- node-type embedding index;
- normalized axial coordinate for \(c_0,c_1,c_2\);
- independent-variable indicator;
- derived-descriptor indicator;
- method-validity indicator.

Method identity is represented by the method node and is not redundantly concatenated to every node.

### 5.3 Edges

Three edge families are used.

#### Axial interpolation edges

Bidirectional edges connect

\[
c_0\leftrightarrow c_1\leftrightarrow c_2.
\]

Their attributes include normalized axial separation and the local control-field difference \(c_1-c_0\) or \(c_2-c_1\).

#### Compiler relation edges

Directed edges connect each valid independent variable to each derived geometry descriptor. The main continuous edge value is the standardized finite-difference sensitivity

\[
S_{ij}
=
\frac{\sigma_{x_i}}{\sigma_{g_j}}
\frac{\partial g_j}{\partial x_i},
\]

where \(x_i\) is an independent variable and \(g_j\) a derived geometry descriptor. Standard-deviation scaling remains defined when a variable value is zero, unlike samplewise relative sensitivity.

Central finite differences are preferred:

\[
\frac{\partial g_j}{\partial x_i}
\approx
\frac{g_j(x_i+h_i)-g_j(x_i-h_i)}{2h_i}.
\]

If one side is geometrically invalid, the pipeline uses a one-sided difference and records reduced confidence. If both sides are invalid, it retains the edge type with `valid_mask=0`; it never records the failed derivative as a valid zero.

Each compiler edge contains:

\[
[S_{ij}, |S_{ij}|, \operatorname{sign}(S_{ij}),
\log(1+|S_{ij}|), m_{ij}, q_{ij}],
\]

where \(m_{ij}\) is a validity mask and \(q_{ij}\) is derivative confidence.

Second derivatives and pairwise Hessian terms are excluded from the first implementation. Higher-order interactions are learned by message passing and can be reconsidered only after the primary ablations.

#### Method and readout edges

Directed method-to-variable edges encode which variables are valid and which equalities are enforced. All non-global nodes send messages to the global readout node. Ordinary nodes do not communicate through an unrestricted global feedback edge, preventing the model from silently reverting to a fully connected parameter Transformer.

## 6. GC-GraphFormer Architecture

The primary configuration is deliberately compact:

- hidden width 128;
- three edge-aware Graph Transformer blocks;
- four attention heads;
- continuous edge features;
- residual connections;
- LayerNorm;
- GELU feed-forward sublayers;
- dropout 0.1;
- approximately 1-3 million trainable parameters.

The default PyG operator is `TransformerConv` with `edge_dim`. If its treatment of relation types proves inadequate in unit experiments, the fallback is a small custom edge-biased attention layer with the same input/output contract. Model comparison remains parameter-matched.

### 6.1 Strain-query decoder

The model does not map one pooled vector directly to 20 stresses. It creates a query embedding for each fixed strain coordinate:

\[
q_k=\operatorname{MLP}(\varepsilon_k),
\qquad k=1,\ldots,20,
\]

and applies cross-attention from each query to the final graph-node states:

\[
h_k=\operatorname{CrossAttention}(q_k,H_{\mathrm{graph}}).
\]

This supports strain-resolved prediction and attribution.

### 6.2 Amplitude-shape decomposition

The curve amplitude is defined smoothly as

\[
A=\sqrt{\frac{1}{20}\sum_{k=1}^{20}\sigma_k^2+\epsilon},
\qquad
s_k=\frac{\sigma_k}{A}.
\]

The global node predicts a positive amplitude through Softplus. The strain queries predict the normalized non-negative shape. The final output is

\[
\hat\sigma_k=\hat A\hat s_k.
\]

No monotonicity constraint is imposed because valid curves include softening, plateau and re-hardening.

## 7. Geometry-Only Pretraining

### 7.1 Dataset

The geometry compiler generates unique samples without Abaqus labels. The scaling experiment uses 0, 10,000, 50,000 and 100,000 samples. The primary configuration is 50,000 unless the 100,000-sample experiment gives a material improvement.

Approximately 20%-30% of the pretraining candidates are sampled near feasibility boundaries or retained as invalid examples. Invalid samples contribute only to tasks whose labels remain defined.

The geometry-only dataset is described as an original auxiliary geometry dataset, not as an original high-fidelity mechanical dataset.

### 7.2 Pretraining tasks

1. **Masked descriptor reconstruction:** mask 20%-30% of derived geometry values and reconstruct them from variables, relations and remaining descriptors.
2. **Sensitivity reconstruction:** reconstruct valid standardized compiler sensitivities.
3. **Geometry feasibility classification:** predict closed-surface, connectivity and meshing success flags.
4. **Descriptor consistency discrimination:** detect graphs in which one or more derived descriptors have been replaced by values from another design.

The loss is

\[
\mathcal L_{\mathrm{pre}}
=
\lambda_{\mathrm{mask}}\mathcal L_{\mathrm{mask}}
+\lambda_{\mathrm{sens}}\mathcal L_{\mathrm{sens}}
+\lambda_{\mathrm{valid}}\mathcal L_{\mathrm{valid}}
+\lambda_{\mathrm{cons}}\mathcal L_{\mathrm{cons}}.
\]

The initial implementation uses equal task weights after per-loss scale normalization. Automatic task weighting is excluded until fixed-weight behavior is established.

## 8. Mechanics Fine-Tuning

The encoder is initialized from geometry pretraining and fine-tuned on the leakage-aware Small splits. The first fine-tuning phase freezes the graph encoder for ten epochs; subsequent epochs update the complete model. A no-freeze run is retained as a training ablation.

The forward loss is

\[
\mathcal L_{\mathrm{forward}}
=
\mathcal L_{\mathrm{curve}}
+0.2\mathcal L_{\mathrm{amp}}
+0.5\mathcal L_{\mathrm{shape}}
+0.2\mathcal L_{\mathrm{mechanics}}
+0.1\mathcal L_{\mathrm{regime}}.
\]

Components are:

- normalized Huber or MSE curve loss, selected on the frozen validation protocol;
- amplitude regression loss;
- normalized-shape regression loss;
- differentiable response-descriptor loss for initial stiffness, peak, plateau and energy;
- response-regime classification loss.

Right-censored or undefined descriptors use explicit masks. Densification is never assigned a fabricated value when it does not occur within 25% strain.

## 9. Uncertainty and Calibration

The primary uncertainty estimator is a five-member deep ensemble trained with independent seeds and identical frozen splits.

For member predictions \(f_m(x)\), the ensemble mean and epistemic variance are

\[
\mu(x)=\frac{1}{M}\sum_{m=1}^{M}f_m(x),
\]

\[
u_{\mathrm{epi}}(x)
=
\frac{1}{M-1}\sum_{m=1}^{M}(f_m(x)-\mu(x))^2.
\]

An independent calibration set supplies conformal residual calibration. The evaluation reports 90% coverage and interval width separately for Group-IID, Parameter-OOD and Curve-OOD. OOD coverage is descriptive rather than guaranteed by in-domain conformal assumptions.

MC dropout is a low-cost baseline, not the primary uncertainty result.

## 10. Conditional Diffusion Adaptation

The inverse model generates only method-conditioned independent variables. It never generates the five derived geometry descriptors.

One shared conditional diffusion model consumes:

- target 20-point curve;
- response-regime token;
- continuous response descriptors;
- TPMS generation-method token;
- method-specific variable-validity mask.

The output is a padded four-dimensional vector \([c_0,c_1,c_2,w]\). Method constraints are enforced during training and decoding. At inference, the system enumerates all three generation-method conditions instead of asking diffusion to generate a discrete method class.

The Paper A primary method remains a lightweight conditional diffusion network. A DiT replacement and differentiable forward-guided denoising are excluded from the primary scope because the design vector is low-dimensional and the external geometry compiler is not fully differentiable.

## 11. Candidate Generation and Robust Ranking

For every target, the fixed default sampling budget is 128 candidates per generation method, or 384 candidates total.

The pipeline is:

```text
target curve and response descriptors
-> method-conditioned diffusion sampling
-> method and parameter constraint enforcement
-> geometry compilation and feasibility checks
-> descriptor and sensitivity recomputation
-> GC-GraphFormer ensemble prediction and UQ
-> manufacturing-perturbation evaluation
-> quality-risk-diversity selection
-> preregistered Top-k Abaqus verification
```

For target \(y^*\), candidate \(x\) and manufacturing perturbation \(\delta\), define

\[
e(x,\delta)
=
d(f_{\mathrm{GC-GT}}(G(x,\delta)),y^*).
\]

The robust score is

\[
J(x)
=
\mathbb E_{\delta}[e(x,\delta)]
+\lambda_{\mathrm{CVaR}}\operatorname{CVaR}_{0.9}[e(x,\delta)]
+\lambda_uU_{\mathrm{epi}}(x)
+\lambda_fP_{\mathrm{invalid}}(x).
\]

Weights are tuned only on the calibration protocol and frozen before formal target generation. Before printing calibration is available, `-5%, 0%, +5%` perturbations are used solely for pipeline testing. Final ranking uses the measured 5th, 50th and 95th percentile manufacturing states.

### 11.1 Diversity selection

The system retains the top 10% by risk score and then applies greedy max-min selection using a distance that combines:

- standardized independent-variable distance;
- derived-geometry distance;
- GC-GraphFormer latent distance;
- generation-method difference.

All compared inverse methods receive the same candidate and evaluation budgets.

## 12. Interpretability and Counterfactual Validation

Attention weights are auxiliary visualizations and are not treated as explanations.

Primary relation attribution uses:

- node integrated gradients;
- edge integrated gradients;
- edge occlusion;
- method-node intervention;
- attribution stability across ensemble members.

Attributions are computed for response stages rather than only the total curve:

- initial response;
- softening or local-instability response;
- plateau response;
- late hardening or densification response.

The prospective 60-run forward OOD budget is allocated as:

| Subset | Analyses | Purpose |
|---|---:|---|
| Independent Parameter-OOD structures | 30 | Unpaired forward generalization test |
| Six OOD anchors at five states each | 30 | Counterfactual parameter-path validation |
| Total | 60 | Fixed budget |

Each anchor has:

1. baseline;
2. positive perturbation of the highest-attribution independent variable;
3. negative perturbation of the highest-attribution independent variable;
4. positive perturbation of a matched lowest-attribution independent variable;
5. negative perturbation of that lowest-attribution variable.

The perturbation magnitude is 0.1-0.2 training standard deviations subject to valid geometry. All descriptors and sensitivity edges are recomputed after intervention. Statistical resampling uses the six anchors as groups rather than treating 30 analyses as independent structures.

The relation interpretation is called **mechanistically informed**, not causal.

## 13. Evaluation Matrix

### 13.1 Forward baselines

1. Small ResMLP.
2. Existing parameter-token Transformer.
3. Existing dense parameter-graph GAT.
4. Parameter-matched fully connected PyG Graph Transformer.
5. Static physics-edge Graph Transformer.
6. Dynamic-sensitivity GC-GraphFormer without pretraining.
7. Pretrained GC-GraphFormer.
8. Five-member pretrained GC-GraphFormer ensemble.

### 13.2 Required graph and training ablations

- fully connected edges;
- axial edges only;
- axial plus fixed parameter-to-descriptor edges;
- full dynamic sensitivity edges;
- shuffled sensitivity edge values;
- shuffled node identities;
- no method node;
- no derived geometry nodes;
- no geometry pretraining;
- no strain-query decoder;
- no amplitude-shape decomposition;
- no response-descriptor auxiliary loss;
- no deep-ensemble UQ.

Shuffled-sensitivity ablation is mandatory. If it performs equivalently to the full model, the compiler-edge claim is withdrawn.

### 13.3 Inverse baselines

1. Original Small six-pipeline ResMLP.
2. CVAE.
3. Conditional diffusion without forward ranking.
4. Conditional diffusion plus parameter-token Transformer ranking.
5. Conditional diffusion plus nominal GC-GraphFormer ranking.
6. Conditional diffusion plus mean-robust GC-GraphFormer ranking.
7. Complete conditional diffusion plus UQ and CVaR ranking.

The same ten preregistered OOD targets, sampling budget, candidate count and Abaqus budget apply to all methods.

## 14. Metrics and Success Gates

### 14.1 Forward metrics

- full-curve NRMSE, MAE and \(R^2\);
- amplitude and normalized-shape errors;
- initial stiffness, peak, plateau and energy errors;
- Group-IID to OOD generalization gap;
- 90% interval coverage and average width;
- AUROC for detecting candidates with Abaqus NRMSE above 10%;
- parameters, training time and inference time.

### 14.2 Inverse metrics

- Abaqus full-curve NRMSE;
- success at 5%, 10% and 15% NRMSE thresholds;
- geometry-valid and mesh-valid rates;
- candidate uniqueness and diversity;
- distance to the nearest training structure;
- finite-element calls per successful design;
- nominal error, worst-state error and CVaR90;
- nominal-to-robust performance trade-off.

### 14.3 Frozen gates

1. Group-IID NRMSE does not degrade by more than 5% relative to the best baseline.
2. Mean NRMSE on 30 independent prospective Parameter-OOD structures improves by at least 10% relative to the parameter-token Transformer for a strong accuracy claim.
3. Paired or grouped bootstrap differences support the reported improvement direction.
4. A nominal 90% conformal interval attains 85%-95% in-domain coverage; OOD coverage is reported without guaranteed-coverage language.
5. Uncertainty usefully identifies `NRMSE > 10%` failures.
6. High-attribution perturbations have larger Abaqus response effects than matched low-attribution perturbations for at least four of six anchors.
7. Shuffling sensitivity edges measurably degrades OOD prediction or counterfactual attribution consistency.
8. CVaR-robust ranking does not worsen nominal error by more than 5%.
9. Relative to nominal ranking, robust ranking lowers CVaR90 by at least 20% or improves success rate by at least 15 percentage points on the ten OOD targets.

Failure of Gate 2 does not invalidate the reliable-ranking claim if calibration, failure detection and robust Abaqus results remain positive.

## 15. Abaqus and Physical-Experiment Budget

The formal high-fidelity budget remains:

| Work package | Analyses |
|---|---:|
| Reproduction, mesh, material and contact calibration | 45 |
| Prospective forward OOD and counterfactual validation | 60 |
| Robust inverse validation | 120 |
| Formal analyses | 225 |
| Failure/restart reserve | At most 15 |

The robust inverse allocation is

\[
10\text{ targets}
\times2\text{ ranking methods}
\times2\text{ candidates}
\times3\text{ perturbation states}
=120.
\]

The two ranking methods are nominal and CVaR-robust, not TPMS generation methods.

The physical program retains 36 core TPMS specimens:

- four targets;
- nominal/robust paired designs;
- three independent prints per design;
- controlled adverse-perturbation groups for two difficult targets.

Natural print variability and controlled adverse perturbations are reported separately.

## 16. Statistical Protocol

- Train each primary neural model with at least five independent seeds.
- Treat the base FE structure, not an Excel row, as the statistical unit.
- Group all precision variants by base structure before splitting.
- Use structure-grouped bootstrap for prospective forward OOD.
- Use target-paired bootstrap for inverse comparisons.
- Use target-stratified bootstrap for physical experiments.
- Treat repeated prints as repeats of one design, not independent designs.
- Treat perturbation states as repeated analyses of one candidate.
- Report individual curves and failures alongside summaries.
- Freeze target rules, seeds, candidate budgets, thresholds and failure handling before formal inference.

## 17. Error Handling and Reproducibility

### 17.1 Geometry and derivative failures

- Archive every compiler request, parameter vector, method, version and outcome.
- Record closedness, connectivity and meshing status separately.
- Use one-sided derivatives only when exactly one central-difference side is invalid.
- Mark both-side failures as unavailable edges.
- Never replace an invalid geometry or missing curve with zeros.

### 17.2 Model and data provenance

- Store split, target, candidate and perturbation manifests with hashes.
- Store fitted scalers in every checkpoint.
- Record geometry-compiler commit/version and finite-difference steps.
- Store model configuration, seed, data hashes and dependency versions.
- Keep raw Abaqus outputs immutable and derive processed curves into a separate directory.
- Preserve all solver failures and reserve-run decisions.

### 17.3 Test coverage required before training

- method-specific independent-variable masks;
- compiler descriptor recomputation;
- central and one-sided sensitivity calculations;
- graph node and edge schema;
- PyG batching without cross-graph edges;
- model output shapes and finite outputs;
- amplitude-shape reconstruction;
- split lineage and no base-structure overlap;
- inverse decoding followed by compiler recomputation;
- robust-score calculation and CVaR convention;
- deterministic manifest generation from a frozen seed.

## 18. Claim Levels and Downgrade Rules

### Level A: full strong claim

Use when graph edges improve OOD prediction, UQ is calibrated, counterfactual interpretation is supported and robust designs outperform nominal designs in Abaqus and experiments.

Positioning: mechanistically informed, OOD-reliable and manufacturing-robust generative inverse design.

### Level B: reliable closed-loop claim

Use when point prediction is comparable to the parameter-token Transformer but calibration, failure detection and CVaR candidate selection improve.

Positioning: trustworthy candidate evaluation and manufacturing-aware inverse design. Do not claim superior forward accuracy.

### Level C: engineering validation claim

Use when graph and robust-ranking gates are not met but the prospective Abaqus and physical datasets remain complete.

Positioning: systematic OOD evaluation of graded-TPMS inverse design, including leakage-aware historical re-evaluation and documented failure modes. Do not change test targets or remove failed designs after seeing results.

## 19. Expected Reviewer Concerns

### Why use a Graph Transformer for 11 nodes?

The answer must rely on dynamic compiler edges, parameter-matched baselines, shuffled-edge controls and prospective OOD results. Model naming or attention visualization is insufficient.

### Are deterministic descriptors redundant?

They are design-time compiler outputs rather than learned targets. Masked reconstruction, descriptor-removal ablation and consistency discrimination quantify whether they add transferable geometry information.

### Does attention explain mechanics?

No. The primary evidence is integrated gradients, edge occlusion and prospective Abaqus interventions.

### Are the forward and inverse models merely concatenated?

The evaluation holds the diffusion samples fixed and changes only the ranking model, then holds the forward model fixed and changes nominal, mean-robust and CVaR scoring. This separates each contribution.

### Is OOD selected after seeing results?

No. The OOD domains, targets, seeds, budgets, thresholds and failure rules are frozen before model selection and Abaqus execution.

### Does Paper A still depend on the Small dataset?

Yes. The historical mechanics training data come from Small. Original evidence consists of the geometry-only pretraining dataset, prospective Abaqus analyses, manufacturing calibration and repeated compression specimens. The manuscript states this boundary explicitly.

## 20. Implementation Sequence

| Week | Deliverable |
|---:|---|
| 1-2 | PyG graph builder, finite-difference edges, geometry-only data generator |
| 3 | Pretraining tasks and graph-contract tests |
| 4-5 | GC-GraphFormer, strain decoder, matched baselines and initial ablations |
| 6 | Ensemble UQ, calibration, inverse-output adaptation and model freeze |
| 7-9 | Formal 225-run Abaqus program |
| 8-10 | Printing, metrology and compression testing |
| 10-12 | Statistical analysis, counterfactual validation and failure audit |
| 12-14 | Figures, methods and manuscript draft |
| 15-16 | Internal review, bounded supplementary analyses and submission package |

## 21. Literature Anchors

- Zong et al., *Machine-Learning-Powered Rapid, Accurate, and Multi-Target Mechanical Metamaterials Inverse Design*, Small, 2025, DOI: 10.1002/smll.202500634.
- Zheng et al., *Algebraic language models for inverse design of metamaterials via diffusion transformers*, Nature Machine Intelligence, 2026, DOI: 10.1038/s42256-026-01218-8.
- Zheng et al., *Designing metamaterials with programmable nonlinear responses and geometric constraints in graph space*, Nature Machine Intelligence, 2025, DOI: 10.1038/s42256-025-01067-x.
- Yan et al., *T2G-Former: Organizing Tabular Features into Relation Graphs Promotes Heterogeneous Feature Interaction*, arXiv:2211.16887.
- *Toward a robust and generalizable metamaterial foundation model*, npj Computational Materials, 2025, DOI: 10.1038/s41524-025-01925-7.

## 22. Approval Record

The user approved the architecture, detailed network and pretraining configuration, diffusion coupling, robust-ranking protocol, experimental matrix, claim boundaries and downgrade routes in sequence on 2026-07-28. This specification is the design baseline for the subsequent implementation plan. Any material change to graph semantics, formal data splits, prospective targets, Abaqus allocation or success gates requires a dated amendment before the affected experiment is run.
