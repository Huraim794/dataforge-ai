# Roadmap

This document outlines the planned development direction for DataForge AI. Items are organized by timeframe and are subject to change based on community feedback and project priorities.

## Short-term

- **AI Provider Expansion**: Add support for additional LLM providers (Mistral AI, Cohere, Together AI, AWS Bedrock) with provider-agnostic fallback chains.
- **WebSocket Real-time Updates**: Push job status, scrape progress, and extraction results to the frontend via WebSocket connections for live monitoring.
- **Rate Limiting Per API Key**: Per-key rate limit tiers with configurable quotas, burst allowances, and usage tracking. Expose rate limit headers in API responses.
- **Export Integrations**: Direct export to external storage (AWS S3, Google Cloud Storage, Azure Blob) and data platforms (PostgreSQL, BigQuery, Snowflake).
- **Extraction Result Caching**: Cache extraction results at the content-hash level to avoid redundant LLM calls for identical pages.

## Medium-term

- **Multi-tenant Isolation**: Complete tenant-level data isolation with dedicated database schemas, separate connection pools, and tenant-aware caching.
- **Team Collaboration Features**: Shared workspaces with real-time collaboration, commenting on extraction results, and approval workflows for extraction schemas.
- **Advanced Scheduling with Conditions**: Conditional triggers (e.g., "run after job X completes", "run only if data changed"), time-window constraints, and dependent job chains.
- **Plugin System for Custom Extractors**: A plugin architecture allowing users to write custom extractors in Python, with lifecycle management, versioning, and a marketplace distribution mechanism.
- **Notification System**: Multi-channel notifications (email, Slack, Discord, webhook) for job completion, failure, and schedule alerts.
- **API Versioning Strategy**: Formalize API versioning with deprecation headers, migration guides, and backward compatibility guarantees.

## Long-term

- **Distributed Scraping Grid**: Horizontally scalable scraping workers deployed across regions with automatic load distribution, geographical targeting, and fault-tolerant job reassignment.
- **Federated Proxy Network**: A peer-to-peer proxy network where users can contribute and consume proxy resources with reputation scoring, bandwidth accounting, and encryption.
- **Self-hosted LLM Fine-tuning**: Tools to fine-tune open-source LLMs (Llama, Mistral) on domain-specific extraction tasks with automated dataset generation from user corrections.
- **Marketplace for Extraction Templates**: A community marketplace for sharing, rating, and monetizing extraction schemas, prompt templates, and classifier models.
- **Visual Extraction Builder**: A no-code drag-and-drop interface for building extraction pipelines, with live preview, schema inference, and one-click testing.

## How to Contribute to the Roadmap

We welcome community input on the roadmap. Here is how you can contribute:

1. **Open a Discussion**: Start a GitHub Discussion with the `roadmap` tag to propose new items or suggest changes to existing ones.
2. **Upvote Existing Items**: Use emoji reactions on roadmap issues to indicate support for specific features.
3. **Submit a RFC**: For significant features, submit a Request for Comments (RFC) pull request describing the motivation, design, and implementation plan.
4. **Contribute Code**: If a roadmap item interests you, reach out on the issue tracker. We maintain a list of `help wanted` and `good first issue` tags for items where contributions are especially welcome.

The core team reviews roadmap suggestions quarterly and publishes updates to this document with any changes.

---

**Note**: This roadmap reflects current plans and priorities. Items may be added, rescheduled, or removed as the project evolves.
