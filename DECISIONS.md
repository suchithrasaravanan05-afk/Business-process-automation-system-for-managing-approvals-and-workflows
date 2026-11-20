# Decision Log

Record every important decision here with the date and the reason. This becomes raw material for your report.

## 2026-11-20

- **Use case:** Leave management.
  - Why: universally understood, easy to demo, and has natural conditional rules (leave length decides how many approvals are needed) that show off a configurable workflow engine.
- **Roles:** Employee, Manager/Approver, HR/Admin.
- **Core states:** Draft -> Submitted -> In Review -> Approved / Rejected / Sent Back.
- **Open decisions:**
  - [ ] Tech stack (backend, frontend, database)
  - [ ] Solo or team, and who owns which module
  - [ ] Notification channel (email only, or in-app as well)
  - [ ] Second workflow to show the engine is generic (optional, e.g. expense approval)

## Questions for my guide

- Is leave management an acceptable scope?
- Which deliverables and documents are mandatory (SRS, UML, test report)?
- What are the review dates?
