# Qoder Academic Research Skills Auto-Enable

## Enabled Skills Configuration (2026-07-30)

When processing research-related tasks, Qoder will automatically invoke:

### Primary Skills (Human-in-the-loop):
1. **Academic Research Skills (ARS)**
   - deep-research (literature search)
   - academic-paper (writing & editing)
   - academic-paper-reviewer (peer review)
   - academic-pipeline (workflow orchestration)

### Secondary Skills (Autonomous):
2. **Orchestra AI-research-SKILLs**
   - autoresearch-skill (main orchestrator)
   - 94+ domain-specific skills

---

## Trigger Patterns

Automatic activation occurs for keywords like:
- literature review, 文献综述，survey
- research paper, 研究论文，academic paper
- experimental design, 实验设计，hypothesis testing
- data analysis, 数据分析，visualization
- write paper, 写论文，manuscript, abstract
- peer review, 同行评审，reference formatting

---

## Activation Priority

1. **Priority 1**: ARS for guided planning & detailed control
2. **Priority 2**: Orchestra for autonomous execution
3. **Hybrid Mode**: Phase 1(ARS) → Phase 2(Orchestra) → Phase 3(ARS)

---

## Quick Start Commands

```bash
# Guided workflow with ARS
You: "/ars-plan [topic]"
You: "Guide my research on [topic]"

# Autonomous workflow with Orchestra
You: "Start autoresearch on [topic]"
You: "Run /loop with autoresearch"
```

---

## Installation Paths

**ARS Skills**: `C:\Users\48186\.claude\skills\academic-research-skills\`
**Orchestra Skills**: `C:\Users\48186\.qoder\skills\`

See INSTALLATION_GUIDE.md for full details.
