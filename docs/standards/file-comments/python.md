# Python File Header Standard

Every Python source file in AIXP should begin with a consistent module header.

The header should provide enough context for an engineer to quickly understand what the file is and why it exists.

## Standard Format

```python
"""
<Module / File Name>

Author:
-------
<Author Name>

Purpose:
--------
<Short description of why this module exists.>

Responsibilities:
-----------------
- <Responsibility 1>
- <Responsibility 2>
- <Responsibility 3>
"""
```

## Example

```python
"""
Application Configuration

Author:
-------
Ranjoy Sen

Purpose:
--------
Provides centralized configuration for
the AIXP application and its runtime
environments.

Responsibilities:
-----------------
- Define application settings
- Load environment configuration
- Validate configuration values
- Provide settings to application components
"""
```

## Guidelines

### Module / File Name

Use a clear human-readable name describing the module.

```text
Application Configuration
Experience Definition
Experience Repository
Health API
Structured Logging
```

Do not simply repeat the filename unless the filename itself is meaningful.

---

### Author

Identify the primary author of the file.

```text
Author:
-------
Ranjoy Sen
```

Git history remains the source of truth for subsequent contributors.

---

### Purpose

Explain **why the module exists**.

Keep it concise, normally two to four lines.

Good:

```text
Purpose:
--------
Validates experience definitions before
they enter the trusted AIXP runtime.
```

Avoid explaining implementation details here.

---

### Responsibilities

List the major responsibilities owned by the module.

Keep the list short, normally three to six items.

Example:

```text
Responsibilities:
-----------------
- Validate experience structure
- Validate interaction definitions
- Validate required dependencies
- Return validation results
```

---

## What Should NOT Be Included

Do not add information that Git, the project documentation, or the code already provides.

Avoid:

```text
Created:
Modified:
Version:
Last Updated:
Reviewed By:
```

Git provides change history, while project documentation and ADRs provide architectural history.

Do not include implementation details, temporary notes, or personal comments.

---

## Architectural Files

For files that represent an important architectural boundary, the Purpose or Responsibilities section should make that boundary clear.

Example:

```python
"""
Experience Definition Validator

Author:
-------
Ranjoy Sen

Purpose:
--------
Validates externally supplied experience
definitions before they enter the trusted
AIXP runtime.

Responsibilities:
-----------------
- Validate experience schema
- Validate interaction capabilities
- Reject unsupported definitions
- Prevent unsafe runtime configuration
"""
```

This helps communicate architectural intent directly from the source file.

---

## Rule

**Every Python file gets a header. Keep it short, meaningful, and focused on purpose and responsibility.**

> **The header explains what the file is responsible for. The code explains how it does it.**
