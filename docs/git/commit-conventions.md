# Git Commit Conventions

## Purpose

Forge follows a consistent commit message convention so that the Git history remains clear, searchable, and useful as the product evolves.

Commit messages should communicate **what changed and why it changed**, without requiring someone to inspect the entire commit to understand its intent.

---

## Commit Format

Forge uses the following format:

```text
<type>(<scope>): <short description>
```

Example:

```text
feat(experience): introduce experience definition schema
```

### Components

**type**
Describes the nature of the change.

**scope**
Identifies the area of the product affected.

**description**
A concise description of the change.

---

# Commit Types

| Type       | Purpose                                                   |
| ---------- | --------------------------------------------------------- |
| `feat`     | Introduces new functionality                              |
| `fix`      | Fixes an existing defect                                  |
| `refactor` | Changes code structure without changing intended behavior |
| `test`     | Adds or modifies tests                                    |
| `docs`     | Documentation changes                                     |
| `chore`    | Maintenance or repository changes                         |
| `build`    | Build system or dependency changes                        |
| `ci`       | CI/CD changes                                             |
| `perf`     | Performance improvements                                  |
| `security` | Security-related changes                                  |

Use the type that best represents the **primary intent** of the commit.

---

# Scopes

Scopes identify the area of Forge affected by the change.

Initial scopes include:

```text
core
api
config
database
experience
runtime
authoring
admin
workflow
content
analytics
security
integration
```

These scopes are not considered permanent.

As the architecture evolves, new scopes may be introduced and obsolete scopes may be removed.

**Architecture by discovery applies here as well.**

---

# Examples

### New functionality

```text
feat(experience): introduce experience definition schema
```

```text
feat(runtime): add threshold slider interaction
```

```text
feat(authoring): add experience preview
```

### Bug fixes

```text
fix(workflow): prevent publishing unapproved experiences
```

```text
fix(runtime): handle missing interaction configuration
```

### Refactoring

```text
refactor(experience): separate definition validation from persistence
```

```text
refactor(runtime): decouple interaction renderer from experience model
```

### Tests

```text
test(workflow): add approval transition tests
```

```text
test(experience): add invalid definition scenarios
```

### Documentation

```text
docs(architecture): document experience runtime boundary
```

```text
docs(git): add commit conventions
```

### Maintenance

```text
chore(core): update project dependencies
```

### Build / CI

```text
build(core): configure production dependency groups
```

```text
ci(core): add automated test validation
```

### Security

```text
security(runtime): sanitize authored interaction definitions
```

---

# Commit Description Guidelines

Keep the first line concise.

Prefer:

```text
feat(experience): add experience versioning
```

Avoid:

```text
feat(experience): added some changes related to experience versioning and made some modifications to the database and service layer
```

Use imperative language where practical:

```text
add
introduce
implement
prevent
support
remove
separate
enable
```

For example:

```text
feat(workflow): add change-request transition
```

rather than:

```text
feat(workflow): added change-request transition
```

---

# One Logical Change Per Commit

A commit should represent one logical change.

Good:

```text
feat(experience): introduce experience schema
test(experience): add schema validation tests
```

Less desirable:

```text
feat(experience): add schema, database models, workflow, UI and tests
```

Small, focused commits make the history easier to understand, review, revert, and troubleshoot.

---

# When a Commit Needs More Detail

For changes that are complex or potentially difficult to understand, use the extended format:

```text
<type>(<scope>): <short description>

<additional context>

<optional rationale or impact>
```

Example:

```text
feat(experience): introduce immutable experience versions

Published experience versions are now immutable.
Authors create a new version when modifying published content.

This allows an approved version to remain available while
the next version is being reviewed.
```

The additional explanation should be used when it provides useful context, not as a requirement for every commit.

---

# Breaking Changes

If a change intentionally breaks an existing contract, clearly identify it.

Example:

```text
feat(api): change experience definition contract

BREAKING CHANGE: experience definitions now require a version field.
```

Breaking changes should normally be accompanied by:

* updated tests
* updated documentation
* an ADR when the change has architectural impact

---

# Architecture Changes

A commit should not be used as a substitute for architectural documentation.

When a change introduces or modifies a significant architectural decision:

1. Identify the decision.
2. Create or update an Architecture Decision Record.
3. Implement the change.
4. Reference the ADR in the commit or pull request where useful.

Example:

```text
docs(architecture): add ADR for experience schema strategy
```

followed by:

```text
feat(experience): implement versioned experience schema
```

---

# Commit Quality

Before committing, the author should ensure:

```text
✓ The commit represents one logical change
✓ The commit type is appropriate
✓ The scope accurately identifies the affected area
✓ The description is concise and meaningful
✓ Tests are included when applicable
✓ Documentation is updated when required
✓ No secrets or environment-specific files are included
```

---

# Architecture by Discovery

Forge is intentionally being developed using an **architecture by discovery** approach.

We will not attempt to predict every future requirement or create a large architecture framework before the product exists.

Instead:

```text
Build
  ↓
Observe
  ↓
Learn
  ↓
Make a deliberate decision
  ↓
Document when significant
  ↓
Refactor when necessary
  ↓
Continue
```

The Git history should therefore reflect the evolution of the product.

A commit does not need to anticipate future architecture.

It needs to accurately represent the decision and implementation **at the point in time it was made**.

---

# Guiding Principle

> **Keep commits small, meaningful, and honest about what changed.**

The objective is not to create perfect Git history.

The objective is to create a history that helps the next engineer understand **how Forge evolved and why it evolved that way**.
