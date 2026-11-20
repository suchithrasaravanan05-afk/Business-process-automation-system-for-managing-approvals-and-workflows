# Business Process Automation System: Leave Management

A web-based system that automates leave requests and multi-level approvals, with configurable workflows, notifications, and a full audit trail.

## Use Case

Employees submit leave requests through the system. Each request is routed automatically according to rules defined by the admin:

1. **Employee** submits a leave request (type, dates, reason, optional attachment such as a medical certificate).
2. **Reporting Manager** receives a notification and can approve, reject, send back for changes, or delegate.
3. If the leave exceeds a set limit (e.g. more than 5 days), the request moves to a **second-level approver (HR)**.
4. When the final approver acts, the employee is notified and the leave balance is updated automatically.
5. Every action (submit, approve, reject, comment, delegate) is recorded in an **audit log**.
6. Requests pending too long trigger **reminder notifications**.

**Roles:** Employee, Manager/Approver, HR/Admin.

## Problem Statement

Many organizations and institutions still handle approvals through paper forms, emails, or messaging apps. This makes the process slow, hard to track, and error-prone. Requests get lost, approvers are not reminded, there is no reliable record of who approved what and when, and leave balances are updated manually. This project builds a system that automates request routing, tracks every request's status in real time, and keeps a complete audit trail.

## Objectives

1. Design and implement a digital system for submitting leave requests and routing them to the correct approvers.
2. Provide a configurable multi-level approval workflow with conditional rules, so approval steps are not hardcoded.
3. Give users real-time status tracking and automatic notifications and reminders for pending actions.
4. Maintain a complete, tamper-resistant audit trail of every action taken on a request.
5. Provide role-based access control and a dashboard with reports (pending requests, turnaround time, rejection rate).

## Tech Stack

_To be decided. See DECISIONS.md._

## Project Structure

```
/docs     Report, diagrams, SRS, meeting notes
/backend  Server code
/frontend Client code
```

## Status

- [x] Use case chosen
- [x] Problem statement and objectives drafted
- [ ] Guide approval of scope
- [ ] User stories
- [ ] Workflow state diagram, use case diagram, ER diagram
- [ ] Tech stack finalized
