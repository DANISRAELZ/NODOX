# Manuscript Figure And Table Specifications

## Purpose

This document defines concrete manuscript-ready figure and table specifications. It does not generate image files or tables. These figures and tables support manuscript communication but are not themselves biological validation or experimental validation.

## Figure 1: Functional Nodes Conceptual Framework

Must show:

- theory-first prioritization;
- curated evidence layers;
- functional constraints;
- interpretable candidate scoring;
- conservative interpretation boundaries.

Publication role: explain the conceptual architecture of Nodos Funcionales / Functional Nodes.

Boundary: conceptual communication does not validate therapeutic targets.

## Figure 2: user_curated Workflow

Must show:

- curator-provided inputs;
- manifest and provenance checks;
- quality gate;
- expert review;
- scoring readiness;
- limitations and missing-evidence warnings.

Publication role: explain how `user_curated` evidence enters the workflow.

Boundary: `user_curated` evidence is curator-provided and not automatic external validation.

## Figure 3: GUI-Assisted Execution And Run-Review Workflow

Must show:

- onboarding;
- controlled execution;
- isolated run directory;
- logs;
- outputs;
- run-local publication package;
- review comparison.

Publication role: explain how GUI-assisted execution remains controlled, isolated and reviewable.

Boundary: GUI workflow validation is not clinical validation, biological validation or experimental validation.

## Figure 4 Or Supplementary Figure: Isolated Publication Package Structure

Must show:

- `results/gui_runs/<run_id>/`;
- `outputs/`;
- `publication_package/`;
- `review/`;
- base package read-only comparison boundary.

Publication role: document isolation between execution outputs, manuscript package artifacts and review comparison outputs.

Boundary: package structure supports auditability; it does not confirm therapeutic validity.

## Table 1: Model Variables And Interpretation Boundaries

Must include:

- `therapeutic_priority_score`;
- `evidence_confidence_score`;
- `evolutionary_escape_risk_score` when available;
- key score components and missing-evidence flags;
- interpretation boundary for each variable.

Publication role: prevent conflation between therapeutic priority, evidence confidence and risk.

## Table 2: Evidence/Provenance Classes

Must include distinctions already used in project docs, including:

- `user_curated`;
- controlled/reference evidence;
- demo evidence;
- proxy evidence;
- cache-derived evidence;
- online evidence;
- missing or not-assessed evidence.

Publication role: explain provenance and evidence classes.

Boundary: provenance class does not automatically establish external validation.

## Table 3: Validation And Testing Boundaries

Must separate:

- workflow validation;
- software validation;
- biological validation;
- clinical validation;
- experimental validation.

Publication role: clarify what the tests and demos do and do not validate.

Boundary: software and workflow validation do not replace wet-lab, clinical or pharmacological validation.

## Table 4: Demo Output Artifacts And Interpretation

Must include:

- `ranking_nodos.csv`;
- `report_phase2.md` or equivalent report;
- `candidate_explanations_simple.csv`;
- `candidate_audit.csv`;
- `evidence_strength_audit.csv`;
- `layer_resolution_summary.csv`;
- `publication_package/`.

Publication role: map demo outputs to manuscript/supporting-material use.

Boundary: demo artifacts are computational reporting outputs and do not validate therapeutic targets.
