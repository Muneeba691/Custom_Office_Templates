# Cross-Border Workforce OS — Production Architecture

**Document status:** Production Reference Architecture
**Version:** 1.0
**Audience:** Engineering, Security, SRE, Product, Compliance, Data, Enterprise Architecture
**Architecture style:** Modular monolith → selectively extracted services
**Primary deployment model:** Cloud-native, multi-tenant SaaS
**Primary objective:** Securely operate international employee/contractor workforce data, documents, agreements, compensation records, compliance requirements, dates, tasks, alerts, workflows, AI assistance, and immutable audit history at enterprise scale.

---

## 1. Executive Summary

Cross-Border Workforce OS is a security-sensitive, compliance-oriented, multi-tenant workforce management platform.

The architecture is deliberately designed around five principles:

1. **The database is the source of truth.**
2. **Business-critical state transitions are transactional and auditable.**
3. **Documents are stored in immutable/versioned object storage, never directly in application databases.**
4. **Asynchronous processing is used for notifications, document analysis, compliance evaluation, integrations, search indexing, and AI workloads.**
5. **AI is advisory and controlled; it cannot silently mutate authoritative workforce or compliance state.**

The recommended production architecture begins as a **modular monolith** backed by PostgreSQL, object storage, Redis, a durable message broker, and a search/indexing layer.

Individual modules can later become independently deployable services when scale, organizational ownership, reliability isolation, or regulatory requirements justify the additional operational complexity.

This avoids premature microservice fragmentation while preserving clear domain boundaries.

---

# 2. Architecture Goals

## 2.1 Functional Goals

The platform must support:

* Organizations / tenants
* Users and administrators
* Roles and permissions
* Workers
* Employees
* Contractors
* Country assignments
* Employment / engagement relationships
* Worker documents
* Document versions
* Agreements and contracts
* Compensation records
* Currency information
* Compliance requirements
* Compliance assessments
* Important dates
* Tasks
* Alerts
* Notifications
* Approval workflows
* Risk management
* Comments / collaboration
* Integrations
* Regulatory intelligence
* Search
* Reporting
* AI assistant
* Audit history
* Data export
* Data retention
* Enterprise security controls

---

## 2.2 Non-Functional Goals

Target production characteristics:

| Area              | Target                                         |
| ----------------- | ---------------------------------------------- |
| Availability      | 99.9% initially; 99.95%+ for mature production |
| API latency       | p95 < 500 ms for normal CRUD operations        |
| Read-heavy APIs   | p95 < 300 ms                                   |
| Critical writes   | p95 < 750 ms                                   |
| Background jobs   | Durable and retryable                          |
| Audit events      | No silent loss                                 |
| Data durability   | Designed for multi-zone durability             |
| Disaster recovery | Automated backups + tested restoration         |
| RPO               | ≤ 15 minutes target                            |
| RTO               | ≤ 60 minutes target                            |
| Tenant isolation  | Mandatory                                      |
| Encryption        | At rest and in transit                         |
| Authentication    | Enterprise-grade identity                      |
| Authorization     | RBAC + scoped permissions + policy enforcement |
| Observability     | Logs + metrics + traces + security events      |
| Deployment        | Automated CI/CD                                |
| Infrastructure    | Infrastructure as Code                         |
| Secrets           | Dedicated secret manager                       |
| AI                | No uncontrolled direct database mutation       |

These are architectural targets, not guarantees. Final SLAs must be established contractually based on deployment topology and cloud-provider capabilities.

---

# 3. Architectural Principles

## 3.1 Source of Truth

Authoritative business state lives in the transactional relational database.

Caches, search indexes, analytics warehouses, vector stores, and AI indexes are derived systems.

They must never become the authoritative source for:

* worker status
* employment relationships
* contracts
* compensation
* compliance state
* approvals
* permissions
* audit records

---

## 3.2 Tenant Isolation

Every tenant-owned record must be associated with a `tenant_id`.

Tenant isolation is enforced at multiple layers:

```text
API Authentication
        ↓
Tenant Resolution
        ↓
Authorization Policy
        ↓
Application Query Scope
        ↓
Database Row-Level Security
        ↓
Storage/Object Authorization
```

Application-level filtering alone is insufficient.

---

## 3.3 Explicit State Machines

Critical entities must use explicit state transitions rather than arbitrary boolean flags.

Examples:

```text
Contract:
DRAFT → PENDING_REVIEW → APPROVED → ACTIVE → EXPIRING → EXPIRED
                     ↘ REJECTED
```

```text
Compliance:
UNKNOWN → COMPLIANT
        → AT_RISK
        → NON_COMPLIANT
        → WAIVED
```

```text
Document:
UPLOADING → PROCESSING → VERIFIED
                     ↘ REJECTED
                     ↘ QUARANTINED
```

Invalid transitions must be rejected by domain logic.

---

## 3.4 Immutable Auditability

All security-sensitive and business-critical actions produce audit events.

Examples:

* worker created
* worker updated
* document uploaded
* document downloaded
* document deleted
* contract approved
* compensation changed
* compliance requirement changed
* compliance assessment overridden
* permission changed
* user invited
* integration credential changed
* AI action approved
* data exported

Audit records must be append-only from the application perspective.

---

## 3.5 Eventual Consistency Where Appropriate

The transactional system handles authoritative state.

Derived workloads use asynchronous events:

```text
Transactional Commit
       ↓
Outbox Event
       ↓
Message Broker
       ↓
Consumers
 ├── Notifications
 ├── Search
 ├── Compliance Engine
 ├── Analytics
 ├── Integrations
 ├── AI Index
 └── Audit Processing
```

No business-critical event should depend on a best-effort HTTP call to another subsystem.

---

# 4. High-Level System Architecture

```text
                           ┌───────────────────────────────┐
                           │          Users                │
                           │ HR / Legal / Finance / Admin   │
                           │ Managers / Auditors / Worker  │
                           └───────────────┬───────────────┘
                                           │
                                  HTTPS / TLS 1.2+
                                           │
                           ┌───────────────▼───────────────┐
                           │ CDN / WAF / DDoS Protection    │
                           └───────────────┬───────────────┘
                                           │
                           ┌───────────────▼───────────────┐
                           │ API Gateway / Load Balancer    │
                           └───────────────┬───────────────┘
                                           │
                ┌──────────────────────────▼──────────────────────────┐
                │              Application Layer                     │
                │                                                    │
                │  Identity & Access                                 │
                │  Workforce                                          │
                │  Documents                                           │
                │  Agreements                                          │
                │  Compensation                                        │
                │  Compliance                                          │
                │  Tasks & Alerts                                      │
                │  Workflow                                            │
                │  Notifications                                       │
                │  Integrations                                        │
                │  Audit                                               │
                │  Search                                               │
                │  AI Orchestration                                    │
                └───────────┬────────────┬────────────┬───────────────┘
                            │            │            │
                    ┌───────▼─────┐ ┌────▼─────┐ ┌───▼──────────────┐
                    │ PostgreSQL  │ │  Redis   │ │ Object Storage   │
                    │ Source of   │ │ Cache /  │ │ Documents        │
                    │ Truth       │ │ Locks    │ │ Versions         │
                    └───────┬─────┘ └──────────┘ └──────────────────┘
                            │
                    ┌───────▼─────────────┐
                    │ Transactional       │
                    │ Outbox              │
                    └───────┬─────────────┘
                            │
                    ┌───────▼─────────────┐
                    │ Durable Message     │
                    │ Broker              │
                    └───────┬─────────────┘
                            │
          ┌─────────────────┼──────────────────┬──────────────────┐
          ▼                 ▼                  ▼                  ▼
   Compliance Engine   Notifications       Search Index       Integrations
          │                 │                  │                  │
          └─────────────────┴──────────────────┴──────────────────┘

                              AI Platform
                                  │
                     ┌────────────▼────────────┐
                     │ AI Gateway / Policy     │
                     │ + Retrieval             │
                     └────────────┬────────────┘
                                  │
                    Approved external/model APIs
```

---

# 5. Recommended Technology Baseline

The architecture is technology-neutral at the domain level, but the following stack is a strong production baseline.

## 5.1 Frontend

Recommended:

* React
* TypeScript
* Next.js or equivalent enterprise frontend framework
* Accessible component system
* Server-side rendering where useful
* Client-side state management kept minimal
* Strict Content Security Policy

Frontend responsibilities:

* presentation
* navigation
* forms
* local validation
* optimistic UX where safe
* workflow visualization
* dashboard rendering

Frontend must not implement authoritative authorization.

---

## 5.2 Backend

Recommended:

* TypeScript
* Node.js
* NestJS or equivalent modular enterprise framework

Alternative:

* .NET / ASP.NET Core is equally suitable for organizations standardized on Microsoft technology.

The architecture must remain independent of either implementation choice.

---

## 5.3 Primary Database

**PostgreSQL** is recommended.

Reasons:

* ACID transactions
* mature indexing
* JSON support
* strong consistency
* row-level security
* partitioning
* extensions
* mature backup tooling
* excellent relational modeling
* suitable transaction semantics for compliance-sensitive workloads

---

## 5.4 Cache

Redis-compatible distributed cache.

Use for:

* short-lived cache
* distributed locks
* rate limiting
* idempotency helpers
* session-adjacent ephemeral state

Do not use Redis as the authoritative business database.

---

## 5.5 Object Storage

Use enterprise object storage for:

* passports
* identity documents
* contracts
* certificates
* tax documents
* compliance evidence
* generated reports

Requirements:

* encryption
* versioning
* lifecycle policies
* private buckets/containers
* malware scanning pipeline
* signed temporary access
* audit logging
* retention controls
* legal hold capability where required

---

## 5.6 Message Broker

Use a durable managed messaging platform supporting:

* at-least-once delivery
* retries
* dead-letter queues
* consumer groups
* message ordering where required
* observability

Examples include managed Kafka-compatible systems, cloud-native queues/topics, or enterprise service buses.

The application must not assume exactly-once message delivery.

---

## 5.7 Search

Use a dedicated search engine for:

* workers
* documents
* agreements
* tasks
* alerts
* audit exploration

Search indexes are derived.

Authorization filters must be applied before returning search results.

---

## 5.8 Analytics

Separate operational workloads from analytical workloads.

Recommended flow:

```text
PostgreSQL
   ↓
CDC / Event Pipeline
   ↓
Data Warehouse / Lakehouse
   ↓
BI / Reporting
```

Do not run large analytical queries against the primary OLTP database.

---

# 6. Domain Architecture

The application is divided into bounded modules.

```text
Identity
Organization
Workforce
Engagement
Documents
Agreements
Compensation
Compliance
Important Dates
Tasks
Alerts
Workflow
Notifications
Audit
Integrations
Search
Reporting
AI
Regulatory Intelligence
Platform Administration
```

Each module owns its domain rules.

Cross-module access should occur through explicit application interfaces rather than arbitrary direct access to another module's internal implementation.

---

# 7. Core Domain Model

Conceptual relationships:

```text
Tenant
  │
  ├── Users
  │
  ├── Roles
  │
  ├── Workers
  │     │
  │     ├── Worker Profiles
  │     ├── Engagements
  │     ├── Documents
  │     ├── Agreements
  │     ├── Compensation
  │     ├── Compliance Assessments
  │     ├── Important Dates
  │     ├── Tasks
  │     └── Alerts
  │
  ├── Countries
  │
  ├── Policies
  │
  ├── Workflows
  │
  ├── Integrations
  │
  └── Audit Events
```

---

# 8. Tenant Model

Every tenant represents a logically isolated customer organization.

Recommended hierarchy:

```text
Tenant
 ├── Business Units
 ├── Legal Entities
 ├── Locations
 ├── Countries
 ├── Users
 ├── Workers
 ├── Policies
 └── Integrations
```

A single tenant may have multiple legal entities and countries.

Do not equate:

```text
tenant = country
tenant = legal entity
tenant = organization user
```

These are separate concepts.

---

# 9. Worker Model

A worker represents a human resource managed by the platform.

Recommended structure:

```text
Worker
 ├── Identity/Profile
 ├── Contact Information
 ├── Country Associations
 ├── Engagements
 ├── Documents
 ├── Agreements
 ├── Compensation Records
 ├── Compliance Records
 ├── Important Dates
 ├── Tasks
 └── Alerts
```

Worker identity and engagement must be separated.

A person can have:

* multiple engagements
* changing legal entities
* changing countries
* historical contracts
* multiple compensation records

---

# 10. Engagement Model

An engagement represents a worker's relationship with an organization.

Fields conceptually include:

```text
engagement_id
worker_id
tenant_id
engagement_type
legal_entity_id
country
start_date
end_date
status
contract_id
currency
created_at
updated_at
```

Possible engagement types:

* employee
* contractor
* consultant
* temporary worker
* other configured types

Avoid encoding engagement type as an unvalidated free-text field.

---

# 11. Document Architecture

Documents are security-sensitive.

## 11.1 Storage

Store binary files in object storage.

Database stores metadata:

```text
document
 ├── document_id
 ├── tenant_id
 ├── worker_id
 ├── document_type
 ├── status
 ├── storage_key
 ├── version
 ├── mime_type
 ├── checksum
 ├── file_size
 ├── uploaded_by
 ├── created_at
 └── retention metadata
```

---

## 11.2 Upload Flow

```text
Client
  ↓
Request Upload Session
  ↓
Authorization
  ↓
Pre-signed Upload URL
  ↓
Object Storage
  ↓
Object Created Event
  ↓
Malware Scanner
  ↓
Document Processor
  ↓
Metadata Extraction
  ↓
Compliance Evaluation
  ↓
Document Status = VERIFIED
```

Never mark an uploaded document trusted merely because the upload succeeded.

---

## 11.3 Document Security

Required controls:

* MIME type verification
* file signature validation
* malware scanning
* size limits
* decompression bomb protection
* encrypted storage
* signed download URLs
* short URL expiration
* access logging
* tenant authorization
* optional watermarking
* document versioning

---

# 12. Agreement / Contract Architecture

Contracts should be immutable once finalized.

Recommended model:

```text
Agreement
 ├── Draft
 ├── Versions
 ├── Approval
 ├── Effective Date
 ├── Expiration Date
 ├── Signatures / Evidence
 └── Audit History
```

Contract changes create a new version rather than overwriting historical content.

---

# 13. Compensation Architecture

Compensation is highly sensitive.

Separate:

```text
Compensation Definition
Compensation Effective Period
Compensation Currency
Compensation Components
Compensation Change Event
```

Example:

```text
Base Salary
Bonus
Commission
Allowance
Equity
Other
```

Do not overwrite historical compensation records.

Use effective dating:

```text
2026-01-01 → 2026-06-30
2026-07-01 → CURRENT
```

---

# 14. Compliance Architecture

Compliance must be modeled as structured requirements rather than hard-coded country-specific conditionals.

Conceptual model:

```text
Country
   ↓
Requirement Set
   ↓
Requirement
   ↓
Applicability Rules
   ↓
Evidence Requirements
   ↓
Worker / Engagement
   ↓
Assessment
   ↓
Risk
   ↓
Task / Alert
```

---

## 14.1 Compliance Requirement

Example conceptual record:

```text
requirement_id
jurisdiction
requirement_type
title
description
effective_from
effective_until
severity
evidence_type
applicability_rule
source_reference
version
status
```

---

## 14.2 Compliance Assessment

```text
assessment_id
worker_id
requirement_id
status
risk_level
evaluated_at
evidence_document_id
evaluated_by
rule_version
override_reason
```

---

## 14.3 Compliance State

Use explicit states:

```text
NOT_APPLICABLE
UNKNOWN
PENDING
COMPLIANT
AT_RISK
NON_COMPLIANT
WAIVED
```

Manual overrides require:

* authorized actor
* reason
* timestamp
* previous value
* new value
* expiration if applicable

---

# 15. Regulatory Intelligence

Regulatory intelligence is a separate domain from compliance execution.

```text
External Regulatory Sources
          ↓
Ingestion
          ↓
Normalization
          ↓
Source Verification
          ↓
Change Detection
          ↓
Human Review
          ↓
Published Regulatory Rule
          ↓
Compliance Rule Version
```

AI may assist with:

* summarization
* change detection
* classification
* comparison

AI must not autonomously publish legally authoritative rules without an appropriate controlled review process.

Every regulatory rule must retain:

* source
* source URL/reference
* jurisdiction
* effective date
* captured date
* version
* reviewer
* approval status
* provenance

---

# 16. Tasks and Alerts

Tasks represent actionable work.

Alerts represent detected conditions requiring attention.

They are related but not identical.

```text
Compliance Failure
       ↓
Risk Event
       ├── Alert
       └── Task
```

Examples:

* passport expires in 60 days
* contract expires in 30 days
* mandatory document missing
* compliance requirement unresolved
* compensation approval pending
* integration failure

Alert lifecycle:

```text
OPEN → ACKNOWLEDGED → RESOLVED
```

Task lifecycle:

```text
OPEN → IN_PROGRESS → BLOCKED → COMPLETED
                         ↘ CANCELLED
```

---

# 17. Workflow Engine

Workflows should be configuration-driven where possible.

Example:

```text
Trigger:
Contract expiration < 60 days

        ↓

Create Alert

        ↓

Create HR Task

        ↓

Notify Manager

        ↓

Escalate after 7 days

        ↓

Escalate to Compliance Admin
```

Workflow executions require:

* workflow version
* execution ID
* trigger event
* actor/system identity
* timestamps
* step status
* retries
* error information
* idempotency key

---

# 18. Notification Architecture

Notification channels:

* in-app
* email
* enterprise messaging integrations
* optional SMS where legally and commercially appropriate

Architecture:

```text
Business Event
     ↓
Notification Policy
     ↓
Notification Job
     ↓
Template Renderer
     ↓
Channel Provider
```

Notification delivery must be asynchronous.

Retries use exponential backoff.

Permanent failures go to a dead-letter queue and operational alerting.

---

# 19. Audit Architecture

Audit is a first-class subsystem.

## 19.1 Audit Event

Conceptual structure:

```text
audit_event_id
tenant_id
actor_type
actor_id
action
resource_type
resource_id
request_id
correlation_id
ip_address
user_agent
before_hash / before_snapshot_reference
after_hash / after_snapshot_reference
metadata
occurred_at
```

Avoid storing unnecessary sensitive payloads inside audit logs.

---

## 19.2 Audit Guarantees

For critical transactions:

```text
Business Transaction
       +
Audit Event
       ↓
Same Database Transaction
```

Then use an outbox mechanism to distribute the event.

This prevents:

```text
Business update succeeded
Audit publication failed
```

from creating an untraceable state.

---

# 20. Transactional Outbox

The Outbox Pattern is mandatory for important domain events.

Example:

```sql
BEGIN;

UPDATE worker
SET status = 'ACTIVE'
WHERE worker_id = ...;

INSERT INTO outbox_event (
    event_id,
    tenant_id,
    event_type,
    aggregate_type,
    aggregate_id,
    payload,
    created_at
)
VALUES (...);

COMMIT;
```

A publisher later delivers the event to the broker.

If the publisher crashes:

```text
Database transaction remains committed
Outbox event remains present
Publisher retries
```

Consumers must be idempotent.

---

# 21. Event Architecture

Recommended event naming:

```text
worker.created
worker.updated
worker.engagement.created
worker.engagement.ended

document.uploaded
document.verified
document.rejected
document.expiring

agreement.created
agreement.approved
agreement.expiring
agreement.expired

compensation.created
compensation.changed

compliance.assessment.created
compliance.status.changed
compliance.requirement.updated

task.created
task.completed

alert.created
alert.resolved

integration.sync.started
integration.sync.completed
integration.sync.failed

ai.recommendation.created
ai.action.approved
ai.action.executed
```

Events should contain stable identifiers and schema versions.

Example:

```json
{
  "event_id": "uuid",
  "event_type": "worker.updated",
  "event_version": 1,
  "tenant_id": "uuid",
  "aggregate_id": "uuid",
  "occurred_at": "ISO-8601",
  "correlation_id": "uuid",
  "payload": {}
}
```

---

# 22. Idempotency

Every externally retried mutation must support idempotency.

Example:

```http
Idempotency-Key: <client-generated-key>
```

The server stores:

```text
tenant_id
idempotency_key
request_hash
response_reference
created_at
expires_at
```

A repeated request with the same key and equivalent payload returns the original result.

A reused key with a different payload must fail.

---

# 23. API Architecture

Use REST/JSON for the primary public API.

Recommended structure:

```text
/api/v1/tenants
/api/v1/workers
/api/v1/engagements
/api/v1/documents
/api/v1/agreements
/api/v1/compensation
/api/v1/compliance
/api/v1/tasks
/api/v1/alerts
/api/v1/workflows
/api/v1/integrations
/api/v1/audit
/api/v1/search
/api/v1/ai
```

API versioning is mandatory.

Breaking changes require a new major API version.

---

# 24. API Security

Every request passes through:

```text
TLS
 ↓
Authentication
 ↓
Tenant Resolution
 ↓
Authorization
 ↓
Input Validation
 ↓
Business Rules
 ↓
Transaction
```

Never trust:

* tenant ID from request body
* worker ownership from client input
* role supplied by client
* document ownership from client
* authorization decisions made in frontend code

The server derives these relationships from authenticated identity and persisted authorization data.

---

# 25. Authorization Model

Use layered authorization.

```text
Authentication
     ↓
Tenant Membership
     ↓
Role
     ↓
Permission
     ↓
Resource Scope
     ↓
Policy Decision
```

Example:

```text
HR_ADMIN
  can:
    worker.read
    worker.write
    document.read
    document.write

MANAGER
  can:
    worker.read
  only for:
    assigned business unit
```

Fine-grained resource authorization must be enforced server-side.

---

# 26. Authentication

Support:

* enterprise SSO
* OIDC
* SAML
* MFA
* passwordless authentication where appropriate
* session revocation
* device/session management

Enterprise identity providers should remain the source of truth for enterprise authentication where SSO is configured.

Do not build custom authentication cryptography.

---

# 27. Database Architecture

Recommended logical schema organization:

```text
identity.*
organization.*
workforce.*
engagement.*
documents.*
agreements.*
compensation.*
compliance.*
workflow.*
tasks.*
notifications.*
integrations.*
audit.*
platform.*
```

Alternatively, a single PostgreSQL schema with strict module ownership can be used initially.

The critical requirement is logical ownership, not schema naming.

---

# 28. Database Rules

Required:

* foreign keys
* unique constraints
* check constraints
* not-null constraints
* indexes
* transaction boundaries
* optimistic concurrency where appropriate
* soft deletion only where semantically required

Do not use application code as the only enforcement mechanism for fundamental integrity constraints.

---

# 29. Soft Delete Policy

Soft deletion should not be applied blindly.

For records requiring historical integrity:

```text
status = ARCHIVED
```

is generally preferable to destructive deletion.

For personal data subject to legitimate deletion requirements:

```text
Retention Policy
     ↓
Eligibility Check
     ↓
Legal Hold Check
     ↓
Approval / Authorization
     ↓
Deletion / Anonymization
     ↓
Audit Event
```

Audit data itself must follow the organization's legal and retention policy.

---

# 30. Concurrency Control

Use optimistic locking for frequently edited business records.

Example:

```text
version = 12
```

Client submits:

```text
expected_version = 12
```

If database version is now 13:

```text
409 CONFLICT
```

This prevents silent overwrites.

Critical workflows may additionally use database locks.

---

# 31. Caching Strategy

Cache only data where stale values are acceptable.

Good candidates:

* country metadata
* non-sensitive configuration
* UI configuration
* regulatory reference metadata
* permission metadata with short TTL

Poor candidates:

* current compliance status during mutation
* compensation during authorization decisions
* security policy
* contract approval state

Never use cache contents as the sole authorization source.

---

# 32. Search Architecture

Search indexing:

```text
PostgreSQL
    ↓
Domain Event
    ↓
Search Consumer
    ↓
Search Index
```

Search documents must contain tenant scope.

Example:

```json
{
  "tenant_id": "...",
  "resource_type": "worker",
  "resource_id": "...",
  "searchable_text": "...",
  "permissions_scope": {}
}
```

Before returning search results:

1. Validate authenticated tenant.
2. Apply resource-level authorization.
3. Return only authorized records.

---

# 33. Reporting Architecture

Operational reports:

```text
Application APIs
```

Large reports:

```text
OLTP
 ↓
CDC / Events
 ↓
Warehouse
 ↓
Reporting Model
 ↓
BI
```

Generated exports should be asynchronous.

Example:

```text
POST /reports
       ↓
202 Accepted
       ↓
Job Created
       ↓
Warehouse Query
       ↓
File Generated
       ↓
Private Object Storage
       ↓
Short-Lived Download URL
```

---

# 34. AI Architecture

AI is a controlled subsystem, not a privileged database administrator.

```text
User
 ↓
AI Assistant API
 ↓
AI Gateway
 ├── Authentication
 ├── Tenant Scope
 ├── Permission Check
 ├── Prompt Injection Defense
 ├── Sensitive Data Policy
 ├── Tool Authorization
 ├── Retrieval
 └── Audit
 ↓
LLM Provider
 ↓
Response Validation
 ↓
User
```

---

# 35. AI Retrieval

AI retrieval should use permission-aware retrieval.

```text
User Query
    ↓
Intent Classification
    ↓
Authorization Context
    ↓
Tenant-Scoped Retrieval
    ↓
Relevant Records
    ↓
Policy Filtering
    ↓
LLM
```

The model must never receive data the requesting user is not allowed to access.

---

# 36. AI Tool Architecture

AI tools should be categorized:

### Read-only

Examples:

```text
get_worker
search_workers
get_contract
get_compliance_status
list_expiring_documents
get_task_summary
```

### Mutating

Examples:

```text
create_task
assign_task
create_alert
request_document
start_workflow
```

Mutating tools require explicit policy controls.

For high-impact actions:

```text
AI Recommendation
      ↓
Human Confirmation
      ↓
Authorization
      ↓
Domain Validation
      ↓
Transaction
      ↓
Audit
```

AI must not bypass standard APIs.

---

# 37. AI Safety Rules

The AI subsystem must:

* respect tenant boundaries
* respect RBAC
* respect resource authorization
* avoid exposing secrets
* avoid exposing hidden system prompts
* treat retrieved documents as untrusted content
* defend against prompt injection
* identify uncertainty
* cite internal records when appropriate
* never fabricate regulatory requirements
* distinguish source facts from generated interpretation
* log tool invocations
* log high-impact decisions
* support model/version traceability

---

# 38. AI Regulatory Answers

For regulatory questions:

```text
User Question
      ↓
Jurisdiction Detection
      ↓
Regulatory Source Retrieval
      ↓
Source Validation
      ↓
Effective-Date Validation
      ↓
Relevant Rule Retrieval
      ↓
AI Explanation
```

The response should clearly distinguish:

```text
Source-backed fact
Interpretation
Recommendation
Uncertainty
```

AI-generated legal/compliance guidance must not be presented as professional legal advice unless the organization's legal/compliance governance explicitly supports that use.

---

# 39. Integrations Architecture

Integrations must use adapters.

```text
Integration Interface
       │
       ├── HRIS Adapter
       ├── Payroll Adapter
       ├── Identity Adapter
       ├── Accounting Adapter
       ├── E-signature Adapter
       └── Communication Adapter
```

The core domain must not contain provider-specific logic.

---

# 40. Integration Sync Model

```text
Integration Scheduler
       ↓
Sync Job
       ↓
External API
       ↓
Raw Response
       ↓
Normalization
       ↓
Validation
       ↓
Domain Mapping
       ↓
Transactional Upsert
       ↓
Domain Events
```

Every sync needs:

* cursor/checkpoint
* provider request ID
* retry policy
* rate-limit handling
* timeout
* idempotency
* reconciliation
* error classification

---

# 41. External API Failure Handling

Classify failures:

```text
Transient
 ├── timeout
 ├── 429
 ├── temporary 5xx
 └── network failure

Permanent
 ├── invalid credentials
 ├── invalid request
 ├── unsupported object
 └── authorization failure
```

Transient:

```text
retry with exponential backoff + jitter
```

Permanent:

```text
mark failed
notify integration administrator
do not endlessly retry
```

---

# 42. Rate Limiting

Rate limits should exist at:

* edge
* tenant
* user
* IP where appropriate
* endpoint
* integration provider
* AI usage

Example conceptual policy:

```text
Anonymous/public:
strict

Authenticated:
higher limit

Enterprise:
tenant-configurable quota

AI:
separate token/request quota
```

Never expose internal infrastructure limits as the only protection.

---

# 43. Security Architecture

Security is defense-in-depth.

```text
Internet
 ↓
DDoS Protection
 ↓
WAF
 ↓
TLS
 ↓
Load Balancer
 ↓
Private Application Network
 ↓
Private Database Network
 ↓
Encrypted Storage
```

---

# 44. Network Architecture

Production deployment should separate:

```text
Public Edge
Private Application
Private Data
Management Plane
```

Database should never be directly internet accessible.

Object storage should use private access policies where supported.

Administrative access should use controlled identity-aware mechanisms.

---

# 45. Encryption

Use encryption:

### In transit

TLS for:

* browser → API
* service → service
* application → database
* application → storage
* application → external integrations

### At rest

Encrypt:

* database
* backups
* object storage
* queues where supported
* logs
* analytics data
* search indexes

Sensitive fields may require application-level encryption.

---

# 46. Key Management

Use a managed KMS/HSM-capable service.

Do not store encryption keys:

* in source code
* in Git
* in Docker images
* in frontend bundles
* in environment files committed to repositories

Key rotation must be planned.

For highly sensitive fields, use envelope encryption:

```text
Master Key
    ↓
Data Encryption Key
    ↓
Sensitive Data
```

---

# 47. Secrets Management

All secrets must be stored in a dedicated secrets manager.

Examples:

* database credentials
* API keys
* OAuth client secrets
* signing keys
* webhook secrets
* encryption keys

Applications receive only the secrets they require.

Prefer short-lived credentials where infrastructure supports them.

---

# 48. File Security

Uploaded files must be considered hostile until validated.

Required pipeline:

```text
Upload
 ↓
Quarantine
 ↓
Malware Scan
 ↓
Content Validation
 ↓
Metadata Extraction
 ↓
Classification
 ↓
Approved Storage
```

Do not process arbitrary uploaded files directly inside the main application process.

---

# 49. Privacy Architecture

The platform may contain highly sensitive personal and employment information.

Apply:

* data minimization
* purpose limitation
* retention policies
* access controls
* encryption
* auditability
* export controls
* deletion/anonymization workflows
* regional data policies where required

Privacy requirements vary by jurisdiction and customer contract and must be mapped to applicable legal obligations during implementation.

---

# 50. Data Classification

Recommended classification:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
HIGHLY_SENSITIVE
RESTRICTED
```

Examples:

| Data                    | Classification   |
| ----------------------- | ---------------- |
| Worker name             | Confidential     |
| Employment details      | Confidential     |
| Compensation            | Highly Sensitive |
| Identity document       | Restricted       |
| Authentication secret   | Restricted       |
| Audit security metadata | Restricted       |
| Public country metadata | Public/Internal  |

Actual classification should be finalized with security/legal stakeholders.

---

# 51. Logging

Application logs must be structured.

Example:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "workforce-api",
  "environment": "production",
  "request_id": "...",
  "correlation_id": "...",
  "tenant_id": "...",
  "user_id": "...",
  "operation": "worker.update",
  "duration_ms": 123
}
```

Never log:

* passwords
* access tokens
* refresh tokens
* API secrets
* full identity documents
* unnecessary compensation data
* private document contents

---

# 52. Observability

Use the three pillars:

```text
Logs
Metrics
Traces
```

Recommended telemetry:

### API

* request rate
* p50/p95/p99 latency
* error rate
* 4xx/5xx
* saturation

### Database

* CPU
* memory
* connections
* slow queries
* lock waits
* replication lag
* storage

### Queue

* queue depth
* consumer lag
* retry count
* dead-letter count

### Workflows

* executions
* failures
* duration
* stuck executions

### AI

* request count
* token usage
* latency
* tool calls
* refusal/error rate
* retrieval failures
* cost

---

# 53. Distributed Tracing

Every request receives:

```text
request_id
correlation_id
trace_id
```

Propagate tracing across:

```text
Frontend
 ↓
API
 ↓
Database
 ↓
Broker
 ↓
Worker
 ↓
External API
```

This is essential for debugging asynchronous enterprise workflows.

---

# 54. Error Handling

All API errors use a consistent structure.

Example:

```json
{
  "error": {
    "code": "WORKER_NOT_FOUND",
    "message": "The requested worker could not be found.",
    "request_id": "..."
  }
}
```

Do not expose stack traces or infrastructure details to clients.

---

# 55. Background Processing

Background jobs handle:

* notifications
* document scanning
* OCR
* compliance evaluation
* expiration detection
* report generation
* search indexing
* integration synchronization
* regulatory ingestion
* AI indexing
* data exports

Every job must have:

```text
job_id
tenant_id
job_type
attempt
status
created_at
started_at
completed_at
error
```

---

# 56. Job Reliability

Jobs require:

* retry
* exponential backoff
* jitter
* timeout
* idempotency
* dead-letter handling
* monitoring

Avoid infinite retries.

---

# 57. Scheduled Jobs

Examples:

```text
Daily:
  evaluate upcoming expirations

Hourly:
  evaluate critical compliance changes

Every few minutes:
  process due workflow tasks

Periodic:
  integration sync

Continuous:
  outbox publishing
```

Schedulers must be distributed-safe.

Use leader election, scheduler locking, or a managed scheduler.

---

# 58. Time and Date Architecture

Cross-border workforce software must treat time carefully.

Rules:

* Store timestamps in UTC.
* Store user/organization timezone separately.
* Store dates as dates when time is not semantically meaningful.
* Never convert a date-only field into a timestamp unnecessarily.
* Use IANA timezone identifiers.
* Handle daylight-saving transitions.
* Do not calculate legal deadlines using server-local time.

Example:

```text
Contract Start Date:
2026-09-01

Worker Timezone:
Europe/London

Audit Timestamp:
2026-08-13T11:55:00Z
```

---

# 59. Currency Architecture

Never store monetary amounts as floating-point values.

Use:

```text
amount_minor_units
currency_code
```

Example:

```text
amount_minor_units = 125000
currency_code = USD
```

Currency conversion must record:

* source currency
* destination currency
* exchange rate
* source
* timestamp
* rate type

Historical compensation should not silently change because today's exchange rate changed.

---

# 60. Data Import Architecture

Bulk imports should be asynchronous.

```text
Upload CSV/XLSX
      ↓
Validate
      ↓
Preview Errors
      ↓
User Confirmation
      ↓
Import Job
      ↓
Transactional Batches
      ↓
Results
```

Each row needs a deterministic result:

```text
IMPORTED
UPDATED
SKIPPED
FAILED
```

Do not perform massive imports in one database transaction.

---

# 61. Bulk Operations

Bulk mutations require:

* explicit authorization
* preview
* validation
* idempotency
* batch processing
* progress status
* audit records
* rollback strategy where feasible

For irreversible operations, require explicit confirmation.

---

# 62. API Pagination

All collection endpoints must paginate.

Prefer cursor-based pagination for large/high-change datasets.

Example:

```http
GET /api/v1/workers?limit=50&cursor=...
```

Do not rely on unbounded queries.

---

# 63. Database Indexing Strategy

Every tenant-scoped high-volume table should consider:

```text
(tenant_id, created_at)
(tenant_id, status)
(tenant_id, worker_id)
```

Additional indexes must be based on real query patterns.

Avoid indexing every column.

Use query plans and production telemetry to tune indexes.

---

# 64. Partitioning

Partition only when justified by actual data volume.

Candidates:

* audit events
* notifications
* workflow executions
* integration logs
* high-volume event tables

A common strategy:

```text
Partition by time
```

combined with tenant filtering.

Do not introduce partitioning prematurely.

---

# 65. Multi-Region Architecture

Initial deployment:

```text
Single primary region
Multi-AZ
Automated backups
Disaster recovery region
```

Mature enterprise architecture:

```text
                    Global DNS / Edge
                           │
                ┌──────────┴──────────┐
                │                     │
          Region A               Region B
          Primary                DR / Secondary
             │                       │
        PostgreSQL              Replica / Backup
        Object Storage          Object Replication
        Application             Application
```

Active-active transactional architecture should not be introduced without a strong business requirement because it materially increases consistency and operational complexity.

---

# 66. Data Residency

For enterprise/regulatory requirements, support logical residency policies.

Potential architecture:

```text
Global Control Plane
        │
        ├── EU Data Plane
        ├── US Data Plane
        ├── APAC Data Plane
        └── Other Regional Data Planes
```

A future data-residency architecture should ensure that:

* tenant data location is explicit
* backups follow residency rules
* logs do not accidentally leak restricted data across regions
* AI providers are approved for the applicable region
* support access is controlled and audited

Do not advertise data residency until the complete data flow has been validated.

---

# 67. Disaster Recovery

Required:

* automated database backups
* point-in-time recovery
* object-storage versioning
* backup encryption
* cross-region backup strategy
* infrastructure recreation capability
* documented recovery procedures

Recovery must be tested.

A backup that has never been restored is not considered verified.

---

# 68. Disaster Recovery Test

At least periodically:

```text
1. Provision clean environment.
2. Restore database.
3. Restore object storage metadata/content.
4. Restore secrets/configuration.
5. Start application.
6. Validate migrations.
7. Validate authentication.
8. Validate tenant isolation.
9. Validate documents.
10. Validate workflows.
11. Validate integrations.
12. Measure RTO/RPO.
13. Document deviations.
14. Remediate.
15. Repeat.
```

---

# 69. Business Continuity

Critical capabilities should degrade gracefully.

If AI is unavailable:

```text
Core workforce management continues.
```

If search is unavailable:

```text
Direct database-backed navigation remains available where practical.
```

If notification provider is unavailable:

```text
Notification jobs remain queued.
```

If regulatory intelligence ingestion fails:

```text
Existing published rules remain available.
```

The system must not make the entire workforce platform dependent on AI availability.

---

# 70. Deployment Architecture

Recommended:

```text
Developer
   ↓
Pull Request
   ↓
CI
 ├── Build
 ├── Unit Tests
 ├── Integration Tests
 ├── Static Analysis
 ├── Dependency Scan
 ├── Secret Scan
 ├── Container Scan
 └── Security Tests
   ↓
Artifact Registry
   ↓
Staging
   ↓
Automated Verification
   ↓
Production
```

---

# 71. Infrastructure as Code

All production infrastructure must be reproducible.

Manage through IaC:

* networks
* databases
* queues
* storage
* IAM
* secrets references
* monitoring
* DNS
* compute
* autoscaling
* backups
* disaster recovery configuration

Never make undocumented production changes manually when they can be represented as code.

---

# 72. Environment Strategy

Minimum:

```text
local
development
test
staging
production
```

Production data must never be copied into lower environments without approved anonymization/sanitization.

---

# 73. CI/CD Quality Gates

A production deployment should fail if any required gate fails:

```text
Compile
 ↓
Unit tests
 ↓
Lint
 ↓
Type checking
 ↓
SAST
 ↓
Dependency scanning
 ↓
Secret scanning
 ↓
Container scanning
 ↓
Integration tests
 ↓
Migration validation
 ↓
Deployment
 ↓
Smoke tests
```

---

# 74. Database Migration Strategy

Migrations must be backward-compatible where rolling deployments are used.

Preferred pattern:

```text
Expand
 ↓
Deploy compatible application
 ↓
Backfill
 ↓
Switch reads/writes
 ↓
Contract
```

Avoid:

```text
Deploy code that requires a column
while old application instances cannot understand it.
```

Never modify production schema manually without recording the change in the migration system.

---

# 75. Deployment Strategy

Preferred:

* rolling deployment
* blue/green deployment
* canary deployment

For high-risk releases:

```text
5% traffic
 ↓
Observe
 ↓
25%
 ↓
Observe
 ↓
50%
 ↓
Observe
 ↓
100%
```

Rollback must be automated.

---

# 76. Feature Flags

Use feature flags for:

* major UI changes
* new compliance engines
* AI features
* new integrations
* risky workflows

Feature flags must be:

* tenant-aware where required
* audited for administrative changes
* time-limited
* documented
* removed after stabilization

---

# 77. Security Testing

Minimum security program:

```text
SAST
DAST
Dependency scanning
Container scanning
Secret scanning
API security testing
Authorization testing
Tenant isolation testing
File-upload testing
Rate-limit testing
SSRF testing
Injection testing
CSRF testing where applicable
XSS testing
Session security testing
```

Conduct periodic independent penetration testing for production systems.

---

# 78. Tenant Isolation Testing

This is a mandatory security test category.

Example:

```text
Tenant A worker = A123
Tenant B worker = B123
```

Attempt:

```text
GET /workers/B123
```

using a Tenant A identity.

Expected:

```text
404 or 403
```

The exact response should be selected to avoid unnecessary information disclosure.

Repeat for:

* API
* search
* exports
* reports
* documents
* AI retrieval
* background jobs
* integrations
* caches
* object storage
* audit
* analytics

---

# 79. Authorization Testing Matrix

Build automated tests across:

```text
Role × Resource × Action × Tenant × Scope
```

Example:

| Role        | Worker     | Compensation | Document | Audit   |
| ----------- | ---------- | ------------ | -------- | ------- |
| Super Admin | RW         | RW           | RW       | R       |
| HR Admin    | RW         | RW           | RW       | R       |
| Manager     | Scoped R/W | Scoped R     | Scoped R | Limited |
| Auditor     | R          | R            | R        | R       |
| Worker      | Own R      | Own R        | Own R    | Limited |

Actual permissions must be configured according to customer policy.

---

# 80. Audit Verification

For every sensitive operation verify:

```text
Mutation succeeded
AND
Audit event exists
AND
Audit actor is correct
AND
Tenant is correct
AND
Resource is correct
AND
Timestamp exists
AND
Correlation ID exists
```

---

# 81. Compliance Engine Testing

Test:

### Positive

Requirement satisfied → `COMPLIANT`

### Negative

Required evidence missing → `NON_COMPLIANT`

### Expiration

Evidence expired → `AT_RISK` / `NON_COMPLIANT` according to rule.

### Boundary

Expiration exactly at threshold.

### Timezone

Deadline crosses timezone boundaries.

### Effective dates

Rule becomes active/inactive on exact date.

### Versioning

Historical assessment remains associated with historical rule version.

### Override

Authorized override works and creates audit trail.

### Unauthorized override

Must fail.

---

# 82. Document Testing

Test:

* valid PDF
* invalid extension
* malicious content
* oversized file
* corrupt file
* duplicate upload
* interrupted upload
* expired signed URL
* unauthorized download
* cross-tenant download
* document replacement
* version creation
* deletion policy
* retention policy

---

# 83. Workflow Testing

For every workflow:

```text
Trigger
 ↓
Condition
 ↓
Action
 ↓
Retry
 ↓
Failure
 ↓
Recovery
 ↓
Completion
```

Also test duplicate events.

A duplicate event must not create duplicate:

* tasks
* alerts
* payments
* notifications
* approvals

unless explicitly designed to do so.

---

# 84. Integration Testing

Each integration needs:

* authentication test
* happy path
* pagination
* rate limiting
* timeout
* retry
* malformed response
* schema change
* duplicate event
* deleted external record
* revoked credentials
* partial sync
* full reconciliation

---

# 85. AI Testing

AI must be tested separately from conventional application logic.

Test:

* prompt injection
* indirect prompt injection
* tenant leakage
* permission bypass
* sensitive-data leakage
* hallucinated compliance rules
* malicious uploaded documents
* tool misuse
* unauthorized mutation
* incorrect worker identification
* ambiguous requests
* conflicting evidence
* stale regulatory information
* model failure
* provider outage

---

# 86. AI Evaluation

Maintain a versioned evaluation suite containing realistic scenarios.

Each release should evaluate:

```text
Groundedness
Authorization
Correctness
Safety
Tool selection
Tool arguments
Refusal behavior
Citation/provenance
Latency
Cost
```

AI model changes must not be deployed based solely on qualitative manual testing.

---

# 87. Performance Testing

Test at minimum:

```text
Baseline
Load
Stress
Spike
Soak
Recovery
```

Test realistic tenant distributions.

Do not test only one large tenant.

Example:

```text
10,000 tenants
5,000 small
4,500 medium
450 large
50 enterprise
```

Actual production traffic model must be based on expected business scale.

---

# 88. Scalability Strategy

Scale horizontally:

```text
API instances
Worker instances
Notification consumers
Search consumers
Integration workers
AI gateway workers
```

Database scaling:

```text
Read replicas
Query optimization
Partitioning
Archival
Warehouse separation
```

Do not solve every performance issue by adding infrastructure.

First inspect:

```text
Query plans
Indexes
N+1 queries
Serialization
Network calls
Cache behavior
Payload sizes
```

---

# 89. Backpressure

Every asynchronous subsystem must handle backpressure.

Example:

```text
Traffic ↑
   ↓
Queue depth ↑
   ↓
Consumer autoscaling
   ↓
Controlled processing
```

Never allow unbounded memory growth.

Large payloads should be stored externally with references rather than pushed through every event.

---

# 90. Event Payload Policy

Events should generally contain:

```text
IDs
event metadata
small business fields
```

Avoid embedding:

* large documents
* entire worker profiles
* unnecessary PII
* credentials
* large AI prompts
* binary files

Consumers can retrieve authorized data when necessary.

---

# 91. Webhook Architecture

Inbound webhooks:

```text
External Provider
 ↓
Webhook Endpoint
 ↓
Signature Verification
 ↓
Replay Protection
 ↓
Persist Raw Event
 ↓
Acknowledge Quickly
 ↓
Async Processing
```

Never perform long-running processing before acknowledging a provider webhook unless the provider explicitly requires synchronous processing.

---

# 92. Webhook Security

Require:

* signature validation
* timestamp tolerance
* replay protection
* provider allowlisting where possible
* payload size limit
* schema validation
* rate limiting
* idempotency

---

# 93. Data Export Security

Exports are high-risk operations.

Require:

* authorization
* scope validation
* export reason where appropriate
* audit event
* asynchronous generation
* encrypted storage
* short-lived URL
* automatic expiration
* optional approval for sensitive exports

---

# 94. Administrative Access

Production administrative access must be:

* identity-based
* MFA protected
* least privilege
* time-limited where possible
* logged
* audited

Break-glass access must be separately controlled and monitored.

---

# 95. Support Access

Support personnel must not receive unrestricted customer data.

Use:

```text
Support Request
 ↓
Customer Authorization / Policy
 ↓
Time-Limited Access
 ↓
Specific Tenant
 ↓
Specific Resource Scope
 ↓
Audit
 ↓
Automatic Expiration
```

---

# 96. Security Incident Architecture

Security events flow into:

```text
Application
 ↓
Security Event Pipeline
 ↓
SIEM
 ↓
Detection Rules
 ↓
Alert
 ↓
Incident Response
```

Potential events:

* repeated authorization failures
* unusual exports
* mass document downloads
* privilege escalation
* suspicious API patterns
* abnormal AI tool usage
* credential changes

---

# 97. Abuse Prevention

Protect against:

* credential stuffing
* brute force
* enumeration
* scraping
* bulk export abuse
* document harvesting
* API abuse
* AI quota abuse
* malicious file uploads

Use layered controls:

```text
WAF
Rate limiting
Authentication controls
Authorization
Behavior monitoring
Quotas
Audit
```

---

# 98. Data Retention

Retention must be configurable by:

```text
Data Type
Tenant Policy
Jurisdiction
Legal Requirement
Contract
Legal Hold
```

Never implement one global deletion rule for every data type.

---

# 99. Legal Hold

Where supported:

```text
Legal Hold
 ↓
Prevent deletion/anonymization
 ↓
Record holder
 ↓
Scope
 ↓
Created At
 ↓
Released At
```

All deletion jobs must check legal hold status.

---

# 100. API Contract Governance

Maintain:

* OpenAPI specification
* API changelog
* versioning policy
* deprecation policy
* SDK generation where useful
* contract tests

Every public API change requires contract review.

---

# 101. Frontend Architecture

Recommended feature structure:

```text
src/
  app/
  features/
    workers/
    documents/
    agreements/
    compensation/
    compliance/
    tasks/
    alerts/
    workflows/
    integrations/
    ai/
  components/
  auth/
  api/
  hooks/
  lib/
  telemetry/
```

Avoid one giant global state store.

---

# 102. Frontend Security

Never put secrets in frontend code.

Frontend must assume:

```text
Browser = untrusted
```

Never trust:

* hidden fields
* disabled buttons
* client-side role checks
* route guards alone

Server authorization is authoritative.

---

# 103. Accessibility

Enterprise UI should target WCAG 2.2 AA or the organization's selected accessibility standard.

Test:

* keyboard navigation
* screen readers
* focus management
* forms
* error messages
* contrast
* data tables
* dialogs
* notifications

---

# 104. Internationalization

Support:

* locale-aware dates
* locale-aware numbers
* currencies
* timezones
* translated UI
* right-to-left languages where required

Do not hard-code:

```text
MM/DD/YYYY
```

as a universal date format.

---

# 105. Localization vs Legal Rules

Do not mix:

```text
UI localization
```

with:

```text
jurisdictional compliance logic
```

They are different concerns.

---

# 106. Configuration Management

Separate:

```text
Code
Configuration
Secrets
Tenant Configuration
Regulatory Rules
```

Regulatory rules should be versioned data, not environment variables.

---

# 107. Tenant Configuration

Tenant-configurable settings may include:

* working days
* notification preferences
* escalation rules
* document policies
* task priorities
* role mappings
* integration settings
* AI availability
* retention preferences where contractually supported

Tenant configuration changes must be audited.

---

# 108. Feature Entitlements

Enterprise SaaS should distinguish:

```text
Authentication
Authorization
Entitlements
```

Example:

```text
Tenant has AI feature
AND
User has AI permission
AND
AI policy allows operation
```

All three may be required.

---

# 109. SaaS Billing Boundary

Billing should remain separated from core workforce domain.

```text
Billing System
      ↕
Entitlement Service
      ↓
Application
```

Do not spread subscription checks throughout business logic.

---

# 110. Operational Dashboards

Required dashboards:

### Executive

* active workers
* countries
* compliance risk
* expiring documents
* expiring contracts
* unresolved tasks

### Operations

* queue health
* integration health
* workflow failures
* notification failures

### Engineering

* API latency
* errors
* database health
* broker lag
* deployment health

### Security

* authentication anomalies
* authorization failures
* exports
* privileged access
* suspicious downloads

---

# 111. Alerting

Alert only on actionable conditions.

Bad:

```text
CPU > 70%
```

Better:

```text
CPU > 85% for 10 minutes
AND
request latency > SLO
AND
error rate increasing
```

Alert fatigue is a production reliability problem.

---

# 112. SLO Framework

Recommended initial SLOs:

```text
API Availability: ≥ 99.9%

Read API latency:
p95 < 500 ms

Write API latency:
p95 < 750 ms

Background job success:
≥ 99.5%

Critical event processing:
≥ 99.9%

Authentication availability:
≥ 99.95%
```

Tune after production measurement.

---

# 113. Reliability Error Budgets

For every SLO:

```text
SLO
 ↓
Error Budget
 ↓
Release Policy
```

If the service repeatedly burns its error budget:

```text
Reduce feature release velocity
Prioritize reliability work
```

---

# 114. Production Runbooks

Required runbooks:

* API outage
* database outage
* database failover
* queue backlog
* dead-letter spike
* object-storage outage
* authentication outage
* integration outage
* AI provider outage
* security incident
* data corruption
* accidental deletion
* failed deployment
* rollback
* certificate expiration
* secret rotation
* disaster recovery

---

# 115. Production Readiness Checklist

Before General Availability:

* [ ] Tenant isolation verified
* [ ] Authorization matrix automated
* [ ] Database backups enabled
* [ ] Restore test completed
* [ ] Object storage protection enabled
* [ ] Malware scanning enabled
* [ ] Audit trail implemented
* [ ] Audit integrity tested
* [ ] Secrets manager configured
* [ ] KMS configured
* [ ] TLS enforced
* [ ] WAF configured
* [ ] Rate limiting configured
* [ ] API documentation published
* [ ] OpenAPI contract validated
* [ ] CI/CD configured
* [ ] IaC reviewed
* [ ] Monitoring configured
* [ ] Alerting configured
* [ ] SLOs defined
* [ ] Runbooks written
* [ ] Disaster recovery tested
* [ ] Security testing completed
* [ ] Dependency vulnerabilities reviewed
* [ ] Penetration testing completed
* [ ] Privacy review completed
* [ ] Regulatory model reviewed
* [ ] AI safety evaluation completed
* [ ] Integration failure scenarios tested
* [ ] Production load test completed
* [ ] Rollback tested
* [ ] Data retention policies configured

---

# 116. Verification and Validation Protocol

This architecture should be treated as verified only after the following gates pass.

## Gate 1 — Static Architecture Review

Verify:

* no circular domain dependencies
* no direct client-to-database access
* no public database endpoint
* no uncontrolled AI database access
* all critical mutations are transactional
* critical events use an outbox
* document binaries are separated from OLTP
* analytics does not overload OLTP

**Pass criteria:** zero critical findings.

---

## Gate 2 — Security Review

Verify:

* authentication
* authorization
* tenant isolation
* secrets
* encryption
* object storage access
* file uploads
* exports
* audit
* admin access
* support access
* AI access

**Pass criteria:** no unresolved critical/high security vulnerabilities.

---

## Gate 3 — Failure Testing

Intentionally fail:

```text
Database
Message broker
Cache
Object storage
Email provider
Integration provider
AI provider
Search
One application instance
One worker instance
One availability zone
```

Verify the platform degrades or recovers according to design.

---

## Gate 4 — Data Integrity Testing

Verify:

```text
No orphan records
No cross-tenant records
No duplicate critical mutations
No missing audit events
No inconsistent contract states
No invalid compliance transitions
No corrupted document metadata
```

---

## Gate 5 — Recovery Testing

Perform actual:

```text
Database restore
Point-in-time recovery
Application recreation
Object restoration
Message replay
Outbox replay
```

Measure:

```text
RPO
RTO
Data completeness
Service correctness
```

---

## Gate 6 — Load Testing

Test:

```text
Normal load
2× expected load
5× expected load
Spike load
Long-running load
```

Record:

```text
p50
p95
p99
error rate
database utilization
queue latency
CPU
memory
network
```

---

## Gate 7 — AI Safety Testing

Attempt:

```text
Cross-tenant retrieval
Prompt injection
Indirect prompt injection
Unauthorized mutation
Regulatory hallucination
Sensitive-data extraction
Tool abuse
Document poisoning
```

All must be blocked or safely handled.

---

# 117. Architecture Invariants

The following invariants must never be violated:

### Invariant 1

**No request may access another tenant's data.**

### Invariant 2

**No AI operation may bypass normal authorization.**

### Invariant 3

**No critical mutation may rely on an eventually consistent cache for correctness.**

### Invariant 4

**No important business event may depend on an unreliable synchronous side effect.**

### Invariant 5

**No historical compensation, contract, compliance, or audit state may be silently overwritten.**

### Invariant 6

**No uploaded document is trusted before security validation.**

### Invariant 7

**No production secret is stored in source control.**

### Invariant 8

**No destructive production database change is made outside the migration process.**

### Invariant 9

**No regulatory rule becomes authoritative without provenance and controlled publication.**

### Invariant 10

**No critical system depends on AI availability.**

---

# 118. Recommended Initial Deployment

For the first production release:

```text
                         Internet
                            │
                         CDN/WAF
                            │
                     Load Balancer
                            │
                  ┌─────────┴─────────┐
                  │                   │
             App Instance       App Instance
                  │                   │
                  └─────────┬─────────┘
                            │
                     PostgreSQL
                     Multi-AZ
                            │
              ┌─────────────┼─────────────┐
              │             │             │
            Redis        Object        Message
                         Storage        Broker
              │             │             │
              │             │       Background Workers
              │             │             │
              └─────────────┴─────────────┘
                            │
                     Search / Analytics
                            │
                      AI Gateway
```

This architecture is sufficient for a serious first production deployment without forcing the organization to operate dozens of microservices.

---

# 119. Evolution Path

## Phase 1 — Production Foundation

```text
Modular Monolith
PostgreSQL
Redis
Object Storage
Message Broker
Search
Basic AI Gateway
```

Focus:

* correctness
* security
* tenant isolation
* auditability
* observability

---

## Phase 2 — Scale

Extract high-load workers:

```text
Document Processing
Notification Service
Integration Workers
Search Indexer
Compliance Evaluation
```

---

## Phase 3 — Enterprise

Add:

```text
Data Warehouse
Advanced Integrations
Regional Data Planes
Advanced Regulatory Intelligence
Enterprise SSO
SCIM
Customer-managed keys where required
Advanced audit export
SIEM integration
```

---

## Phase 4 — Global Workforce OS

Expand into:

```text
Global Workforce Graph
Regulatory Intelligence
Payroll Integrations
HRIS Integrations
E-signature
Identity Lifecycle
Global Mobility
Workforce Cost Intelligence
Advanced Compliance Automation
AI Workforce Operations
```

The original domain boundaries should remain intact while capabilities expand.

---

# 120. Architecture Decision Records

Every significant architectural decision should have an ADR.

Recommended initial ADRs:

```text
ADR-001 PostgreSQL as System of Record
ADR-002 Modular Monolith First
ADR-003 Transactional Outbox
ADR-004 Object Storage for Documents
ADR-005 Multi-Tenant Isolation Model
ADR-006 RBAC and Resource Authorization
ADR-007 Immutable Audit Architecture
ADR-008 Compliance Rule Versioning
ADR-009 AI Gateway Architecture
ADR-010 Human Approval for High-Impact AI Actions
ADR-011 Regional Data Architecture
ADR-012 Disaster Recovery Strategy
ADR-013 Integration Adapter Architecture
ADR-014 Search as Derived Data
ADR-015 Analytics Warehouse Separation
```

---

# 121. Recommended Repository Structure

```text
cross-border-workforce-os/
│
├── apps/
│   ├── web/
│   ├── api/
│   ├── worker/
│   └── ai-gateway/
│
├── packages/
│   ├── domain/
│   ├── auth/
│   ├── database/
│   ├── events/
│   ├── observability/
│   ├── security/
│   └── shared/
│
├── modules/
│   ├── identity/
│   ├── organization/
│   ├── workforce/
│   ├── engagement/
│   ├── documents/
│   ├── agreements/
│   ├── compensation/
│   ├── compliance/
│   ├── tasks/
│   ├── alerts/
│   ├── workflows/
│   ├── notifications/
│   ├── integrations/
│   ├── audit/
│   ├── search/
│   ├── reporting/
│   ├── regulatory-intelligence/
│   └── ai/
│
├── infrastructure/
│   ├── terraform/
│   ├── kubernetes/
│   ├── monitoring/
│   └── policies/
│
├── migrations/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── security/
│   ├── performance/
│   ├── tenant-isolation/
│   ├── disaster-recovery/
│   └── ai-evaluation/
│
├── docs/
│   ├── adr/
│   ├── runbooks/
│   ├── api/
│   └── security/
│
└── README.md
```

---

# 122. Definition of Production-Grade

The platform is **not production-grade merely because it works in a browser**.

It is production-grade when it demonstrates:

```text
Correctness
+
Security
+
Tenant Isolation
+
Durability
+
Auditability
+
Recoverability
+
Observability
+
Scalability
+
Operational Discipline
+
Controlled AI
```

All ten are required.

---

# 123. Final Architecture Decision

The recommended architecture for Cross-Border Workforce OS is:

```text
             ┌─────────────────────────────┐
             │        Enterprise UI        │
             └──────────────┬──────────────┘
                            │
                    CDN / WAF / TLS
                            │
             ┌──────────────▼──────────────┐
             │       API / Application     │
             │        Modular Monolith      │
             └──────────────┬──────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
 PostgreSQL              Redis             Object Storage
 Source of Truth          Cache              Documents
       │
       ▼
 Transactional Outbox
       │
       ▼
 Durable Message Broker
       │
 ┌─────┼────────┬─────────┬───────────┬─────────────┐
 ▼     ▼        ▼         ▼           ▼             ▼
Compliance  Workflow  Notifications Search    Integrations   Analytics
 │                                                       
 └──────────────────────────────┐
                                ▼
                           AI Gateway
                                │
                       Permission-Aware RAG
                                │
                          Approved LLMs
```

The central architectural decision is to **keep authoritative workforce, contractual, compensation, compliance, and audit state strongly consistent in a relational transactional core, while moving expensive, asynchronous, analytical, integration, document-processing, search, and AI workloads behind durable event-driven boundaries.**

This provides a practical balance between:

* enterprise reliability
* security
* regulatory traceability
* development velocity
* operational simplicity
* horizontal scalability
* future service extraction
* AI extensibility

The system should begin as a **well-modularized production platform**, not as an uncontrolled collection of microservices. Services should be extracted only when there is measurable justification.

---

# 124. Architecture Acceptance Criteria

This document is considered implementation-ready when the engineering team has converted the architecture into:

```text
[ ] Domain model
[ ] Database schema
[ ] OpenAPI specification
[ ] Event contracts
[ ] Authorization matrix
[ ] Threat model
[ ] Data classification matrix
[ ] Retention matrix
[ ] Compliance rule model
[ ] Workflow model
[ ] Infrastructure-as-Code
[ ] CI/CD pipelines
[ ] Observability dashboards
[ ] SLOs
[ ] Disaster recovery procedures
[ ] Security test suite
[ ] Tenant-isolation test suite
[ ] Performance test suite
[ ] AI evaluation suite
[ ] Integration contract suite
[ ] Production runbooks
[ ] ADR repository
[ ] Incident response process
```

**Final engineering principle:**

> Build the platform so that a bug, failed dependency, compromised client, malicious document, incorrect AI response, duplicated event, partial deployment, or regional outage cannot silently corrupt the authoritative workforce state.

That principle should govern every implementation decision made after this architecture.
