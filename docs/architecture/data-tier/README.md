# Data Tier Architecture

This directory contains documentation specific to the data tier architecture, including database design, migration plans, and implementation details.

## Contents

- **database_migration_plan.md** - Comprehensive plan for migrating from PostgreSQL to Apache Iceberg
- **database_migration_enhancements.md** - Enhancements to the database migration strategy
- **data_tier_implementation_summary.md** - Summary of the data tier implementation
- **data_tier_architecture.html** - Visual diagram of the data tier architecture (HTML format)
- **data_plan.md** - Initial data design plan
- **data_plan_phase2.md** - Phase 2 data design plan
- **data_sections_update.md** - Updates to data organization and sections

## Purpose

These documents provide detailed information about the dual database architecture that allows seamless switching between PostgreSQL and Apache Iceberg. They outline the repository pattern implementation, abstraction layers, and migration strategy that enables development flexibility while maintaining production performance.

## Key Concepts

- Dual database architecture (PostgreSQL/Iceberg)
- Repository pattern implementation
- Abstraction layers
- Schema synchronization
- Feature flags for database backends
- Data lake configuration on Azure

## Related Sections

- See **phase-results/** for implementation results by phase
- See **infrastructure/** for cloud resources configuration
- See **deployment/** for environment-specific deployment information