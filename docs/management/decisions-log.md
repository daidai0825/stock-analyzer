# Decisions Log

| ID | Date | Decision | Context | Decided By |
|----|------|----------|---------|------------|
| D001 | 2026-04-09 | Skip formal Phase 1 docs, use CLAUDE.md + prompt-manager.md as spec baseline | Phase 1 approved by human, architecture docs not produced but skeleton code exists | Manager |
| D002 | 2026-04-09 | Use existing skeleton code as starting point, extend rather than rewrite | Models (Stock, Watchlist), routes, config already follow CLAUDE.md conventions | Manager |
| D003 | 2026-04-09 | Phase 2 will produce missing models (DailyPrice, Indicator, etc.) inline with CLAUDE.md ERD expectations | No formal data-model.md exists; Data Engineer will define based on CLAUDE.md API conventions | Manager |
| D004 | 2026-04-09 | Parallel launch Wave 3 (Backend API) + Wave 4 (Frontend) instead of sequential | All dependencies met (DE models + QN services done). Frontend uses mock data first, reduces total elapsed time | Manager (Jamie) |
