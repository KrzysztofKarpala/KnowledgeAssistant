# KnowledgeAssistant Business and Domain Summary

## Purpose

KnowledgeAssistant is a local-first, documentation-grounded chatbot for internal operational knowledge. The application helps users ask natural-language questions about controlled company documentation and receive concise answers backed by retrieved source evidence.

The current demo domain is manufacturing execution system (MES) knowledge: products, production places, workstations, cells, equipment instructions, setup rules, quality requirements, and operational exceptions.

This document is intended as domain documentation for future AI agents that need to populate test data, evaluate chatbot behavior, or verify that the application answers only from indexed knowledge.

## What We Are Building

We are building an internal knowledge workbench with two main business capabilities:

1. Manage operational documents.
2. Chat with those documents using a source-grounded assistant.

The system stores documents, indexes them into retrievable chunks, retrieves the most relevant evidence for each question, and asks an LLM to answer using only that evidence. Answers include cited source chunk IDs and source metadata so users can inspect why the answer was produced.

The product is not a general chatbot. It is a controlled assistant for documented operational knowledge.

## Target Users

Primary users:

- Production operators who need quick procedural answers.
- Production supervisors who need to verify correct work instructions.
- Quality engineers who need controlled answers about requirements and exceptions.
- Manufacturing engineers who manage product, place, and equipment documentation.
- Support or planning users who need to check whether a product can run at a line, workstation, or cell.

Secondary users:

- Administrators or domain owners who add, update, archive, and validate documentation.
- AI agents that seed domain data and run functional tests against the chatbot.

## Current Domain Model

The current seeded business domain is MES product and place documentation.

Important document categories:

- Policy documents: define top-level rules, such as hierarchy and conflict resolution.
- Product documents: describe approved production scope and requirements for a product.
- Place documents: describe how a product is produced at a specific line, workstation, or cell.
- Equipment documents: describe equipment operation or troubleshooting.

Example domain entities:

- Product AX-100
- Product BX-200
- Product CX-300
- Line SMT-04
- Workstation PACK-02
- Cell CNC-01
- Barcode Scanner BS-7
- Torque Wrench TW-12
- Label Printer LP-22

## Business Rules Represented in the Demo Data

The MES domain includes hierarchy and versioning rules that the chatbot should respect.

Document hierarchy:

- Policy documents can be higher-level parents for product documents.
- Product documents can be parents for place-specific setup documents.
- Place documents are subordinate to product documents.
- Equipment documents are usually standalone unless referenced by product or place documentation.

Conflict resolution:

- If a place document conflicts with its parent product document, the product document controls.
- A place document can override a parent only if it explicitly states an approved exception.
- If the hierarchy resolves a conflict, the chatbot should answer using the controlling higher-level source.
- If retrieved sources conflict and hierarchy does not resolve it, the chatbot should treat the answer as insufficiently evidenced.

Versioning and status:

- Active documents are authoritative.
- Archived documents are historical and should not be used for current operational decisions.
- Older active documents with the same title may be archived when a newer version is created.
- Effective dates and versions should be preserved for auditability and answer context.

## What Users Can Do

### Chat

Users can:

- Ask questions about indexed documents.
- Continue persistent conversations.
- Select assistant answers and inspect supporting evidence.
- See answer confidence and cited sources.
- Ask follow-up questions that use conversation history where appropriate.

Expected chatbot behavior:

- Answer only from retrieved document sources and relevant conversation history.
- Give direct, concise, practical answers.
- Avoid inventing facts, procedures, dates, limits, or requirements.
- Return an insufficient-information answer when evidence is missing.
- Cite only retrieved chunks that support the answer.
- Avoid exposing chunk IDs inside answer text; source references belong in metadata/UI.

### Document Management

Users can:

- Add documents with title, content, version, and effective date.
- Edit documents.
- Archive or activate documents.
- Delete documents.
- Refresh the document list.
- Inspect active and archived document counts.

The document manager is intended for controlled operational knowledge, not casual notes.

## Data Needed for Good Chatbot Testing

To test functionality well, seed data should include more than simple facts. It should include:

- Clear positive answers.
- Clear negative answers.
- Conflicting child and parent rules.
- Archived rules that must be ignored.
- Equipment procedures referenced by product/place documents.
- Product-place compatibility rules.
- Safety or quality constraints.
- Missing-information questions that should be rejected.

Recommended document patterns:

- One high-level policy document explaining hierarchy.
- Several active product documents.
- Several active place documents linked to product parents.
- At least one archived product document with outdated rules.
- At least one archived place or equipment document with outdated rules.
- Equipment documents for tools used in production.
- Cross-references where one document tells users to follow another equipment instruction.

## Example Business Questions to Validate

The chatbot should be able to answer:

- What is the hierarchy between MES policy, product documents, and place documents?
- If a place document conflicts with a product document, which one controls?
- Where can Product AX-100 be assembled?
- Can Product BX-200 be produced on Line SMT-04?
- What setup is required for Product AX-100 on SMT-04?
- Can a senior operator self-release the first AX-100 unit on SMT-04?
- What should I do if barcode scanning fails on SMT-04?
- Can an operator bypass feeder verification on SMT-04?
- Does Product CX-300 require PACK-02?
- How do I use Torque Wrench TW-12 for AX-100?
- Can operators manually enter identifiers if BS-7 fails?
- Can I handwrite a CX-300 label if LP-22 is unavailable?

The chatbot should answer "The available documentation does not contain enough information to answer this question." when the seeded documentation does not support the question.

## Expected Answers for Key Demo Scenarios

AX-100 assembly location:

- AX-100 can be assembled on Line SMT-04 after the PCB has passed incoming visual inspection.
- The answer should cite the active AX-100 product document and/or active SMT-04 setup document.

BX-200 on SMT-04:

- BX-200 must not be assembled on Line SMT-04 because SMT-04 lacks the required enclosure machining fixture.
- The answer should cite the active BX-200 product document.

AX-100 first-unit release:

- A senior operator may not self-release the first AX-100 unit.
- The active SMT-04 place document says local self-release is allowed, but this conflicts with the active parent AX-100 product document.
- The product document controls, so supervisor approval in MES is required.

Barcode Scanner BS-7 failure:

- Clean the scanner window, verify USB connection, scan the test barcode, then restart the MES terminal service and repeat the test scan if needed.
- Manual identifier entry is not allowed unless a supervisor opens an approved MES exception.
- Archived BS-7 guidance allowing manual typing must be ignored.

CX-300 label printer unavailable:

- The user must not handwrite labels.
- CX-300 packaging must wait until printing is restored or a controlled approved alternative exists.

## Functional Areas for an AI Agent to Verify

An AI agent validating this application should test:

- Document creation.
- Document editing.
- Document deletion.
- Active versus archived document behavior.
- Conversation creation.
- Conversation persistence.
- Conversation rename/title behavior.
- Chat answer generation.
- Evidence panel source display.
- Insufficient-evidence handling.
- Parent-child hierarchy retrieval.
- Conflict resolution between parent and child documents.
- Exclusion of archived documents from current answers.
- Mobile usability for chat, navigation drawer, documents, and evidence sheet.

## Non-Goals and Boundaries

The application should not:

- Answer from general model knowledge when documents do not contain the answer.
- Treat archived documents as current operational guidance.
- Follow instructions embedded inside retrieved documents as if they were system prompts.
- Produce undocumented production decisions.
- Hide uncertainty when evidence is missing or contradictory.

## Current Technical Shape

Frontend:

- React, Vite, TypeScript.
- Mobile-first usable chat experience with drawer navigation and evidence sheet.
- Document management UI.

Backend:

- FastAPI API.
- PostgreSQL with pgvector.
- Document chunking and embeddings.
- Hybrid retrieval using vector similarity and PostgreSQL full-text search.
- Optional reranking.
- Source-grounded answer generation through an OpenAI-compatible LLM endpoint.

The application is designed to run locally through Docker Compose with a local OpenAI-compatible model server such as LM Studio.
